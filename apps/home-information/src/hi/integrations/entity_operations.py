"""
Operations on entities with respect to their integration attachment.

This module holds mutating operations (disconnect, preserve, detach) that
act on Entity instances relative to the integration that owns them. These
are distinct from the read-only analytical methods on EntityUserDataDetector.

EventDefinition cleanup is integration-scoped: only EventDefinition rows
whose own ``integration_id`` matches are removed; user-owned EventDefinitions
referencing the entity's states are intentionally left alone. See
``EventDefinitionOperations`` for the full policy.
"""

import logging
from typing import Dict, Iterable, List, Optional, Set

from django.db import transaction

from hi.apps.attribute.enums import AttributeType
from hi.apps.entity.models import Entity, EntityState, EntityStateDelegation
from hi.apps.sense.models import Sensor
from hi.apps.control.models import Controller

from hi.integrations.event_definition_operations import EventDefinitionOperations
from hi.integrations.transient_models import IntegrationKey, IntegrationRemovalSummary

from hi.integrations.connector.sync_result import IntegrationSyncResult
from hi.integrations.connector.user_data_detector import EntityUserDataDetector

logger = logging.getLogger(__name__)


class EntityIntegrationOperations:

    @staticmethod
    def collect_removal_closure( initial_entity_ids : Iterable[int] ) -> Set[int]:
        """
        Expand a set of entity IDs to include delegate entities that would
        be orphaned by the removal.

        Pure graph operation over EntityStateDelegation:

          - From each entity already in the closure, find delegates reached
            via that entity's EntityStates' delegations.
          - A delegate is added only when *every* entity that delegates to
            it is already in the closure (otherwise the delegate is still
            serving a non-removed entity and must remain).
          - Iterates until no new entities are added (handles chained and
            diamond-shaped delegations; cycles are bounded by the visited set).

        This function is integration-agnostic -- callers pass whatever seed
        set defines the explicit removal scope.
        """
        closure : Set[int] = set(initial_entity_ids)
        if not closure:
            return closure

        while True:
            candidate_ids = set(
                EntityStateDelegation.objects.filter(
                    entity_state__entity_id__in = closure,
                ).exclude(
                    delegate_entity_id__in = closure,
                ).values_list( 'delegate_entity_id', flat = True )
            )
            if not candidate_ids:
                break

            # Bulk-query then group in Python to avoid O(passes x candidates) DB hits.
            principals_by_candidate : Dict[int, Set[int]] = {}
            for delegate_id, principal_id in EntityStateDelegation.objects.filter(
                    delegate_entity_id__in = candidate_ids,
            ).values_list( 'delegate_entity_id', 'entity_state__entity_id' ):
                principals_by_candidate.setdefault( delegate_id, set() ).add( principal_id )

            added_this_pass = {
                candidate_id
                for candidate_id, principal_ids in principals_by_candidate.items()
                if principal_ids and principal_ids.issubset( closure )
            }

            if not added_this_pass:
                break
            closure |= added_this_pass

        return closure

    @staticmethod
    def get_removal_entity_ids( integration_id : str ) -> Set[int]:
        """
        Return the full set of entity IDs that a Remove of the given
        integration should target: every actively-attached
        (EXTERNAL) entity for the integration, plus any delegate
        entities that would be orphaned by their removal. Imported /
        detached rows for the same integration are HI-owned and
        outside the removal scope.
        """
        seed = set(
            Entity.objects.external_for(
                integration_id = integration_id,
            ).values_list( 'id', flat = True )
        )
        return EntityIntegrationOperations.collect_removal_closure( seed )

    @classmethod
    def remove_entities_with_closure(
            cls,
            seed_entity_ids    : Iterable[int],
            integration_name   : str,
            preserve_user_data : bool                              = True,
            result             : Optional[IntegrationSyncResult]   = None ):
        """Canonical removal for integration-owned entities.

        Walks ``collect_removal_closure(seed_entity_ids)`` so every delegate
        entity that would be orphaned by the removal (e.g., the Area
        auto-created when a camera was placed in a view) is included. Each
        entity in the closure is handled per ``preserve_user_data``:

          * ``True`` (SAFE pattern): entities carrying operator-added
            attributes are detached from the integration (active integration
            identity cleared, previous identity recorded for the auto-
            reconnect path); others are hard-deleted.

          * ``False`` (DELETE ALL pattern): every entity in the closure is
            hard-deleted, including those with user-added data.

        When ``result`` is provided, each closure entity's name is appended
        to either ``result.removed_list`` (hard-delete branch) or
        ``result.detached_list`` (preserve branch) -- never both. The
        preserve branch also adds its diagnostic note to ``result.info_list``.

        Each entity in the closure is classified by its *own* user data,
        independent of the seed's classification. This produces the right
        outcome in the camera-preserved / Area-no-user-data corner: an
        auto-created Area's display purpose depends on the principal's live
        state, which the preserve path removes -- so deleting the
        now-purposeless Area is correct even when its principal is being kept.
        """
        closure_ids = cls.collect_removal_closure( seed_entity_ids )
        for entity in Entity.objects.filter( id__in = closure_ids ):
            if preserve_user_data and EntityUserDataDetector.has_user_created_attributes( entity ):
                # preserve_with_user_data appends to result.detached_list
                # itself; nothing to record here on this branch.
                cls.preserve_with_user_data(
                    entity = entity,
                    integration_name = integration_name,
                    result = result,
                )
            else:
                if result is not None:
                    result.removed_list.append( entity.name )
                # Django's DB-level CASCADE from Entity.delete() reaches
                # EventClause / ControlAction (the children) but stops
                # there -- the parent EventDefinition row is never
                # touched. Delete integration-owned EventDefinitions
                # for this entity first, then let CASCADE handle the
                # rest of the entity graph.
                EventDefinitionOperations.delete_for_entity( entity )
                entity.delete()
        return

    @staticmethod
    def summarize_for_removal( integration_id : str ) -> IntegrationRemovalSummary:
        """
        Classify the entities attached to the integration: total (including
        orphan-after-removal delegates) and how many carry user-created data.
        Used to populate the policy choice in the operator confirmation
        dialogs (retain user-data items vs delete).

        This is a policy classification, not the actual dropped set. For
        Refresh, the dropped set is decided at sync execution against fresh
        upstream -- the operator's choice expresses the policy that applies
        if drops include user-data items.
        """
        target_ids = EntityIntegrationOperations.get_removal_entity_ids(
            integration_id = integration_id,
        )
        total_count = 0
        user_data_count = 0
        for entity in Entity.objects.filter( id__in = target_ids ):
            total_count += 1
            if EntityUserDataDetector.has_user_created_attributes( entity ):
                user_data_count += 1
        return IntegrationRemovalSummary(
            total_count = total_count,
            user_data_count = user_data_count,
        )

    @classmethod
    def find_reconnect_candidates(
            cls,
            integration_id : str,
            upstream_keys  : Iterable[ IntegrationKey ],
            result         : Optional[ IntegrationSyncResult ] = None,
    ) -> Dict[ IntegrationKey, Entity ]:
        """
        Auto-reconnect candidate lookup. Pure read.

        Given a set of upstream IntegrationKeys that the synchronizer's
        primary-match step did NOT match, return a map of
        ``upstream_key -> matching disconnected entity`` for every key that
        uniquely aligns with a disconnected entity's
        ``previous_integration_id`` / ``previous_integration_name``.

        Ambiguous matches (multiple disconnected entities sharing the same
        previous identity) are dropped from the result map; the contract is
        to leave the duplicate for the user to resolve via merge, since the
        system has no basis to pick one side over the other. A WARNING is
        logged and a breadcrumb is appended to ``result.info_list`` (when
        provided) for each ambiguous case.

        The per-entity reconnect mutations and converter dispatch are
        deliberately not performed here -- each integration's converter has a
        different signature and callers also want to enrich ``result`` with
        their own messages.

        Single batched DB query -- O(1) round trips regardless of how many
        upstream keys are passed.
        """
        upstream_keys = list( upstream_keys )
        if not upstream_keys:
            return {}

        upstream_keys_by_name : Dict[ str, IntegrationKey ] = {
            key.integration_name: key for key in upstream_keys
        }

        candidate_entities = Entity.objects.detached_for(
            integration_id = integration_id,
        ).filter(
            previous_integration_name__in = list( upstream_keys_by_name.keys() ),
        )

        candidates_by_name : Dict[ str, List[ Entity ] ] = {}
        for entity in candidate_entities:
            candidates_by_name.setdefault(
                entity.previous_integration_name, [],
            ).append( entity )

        reconnect_map : Dict[ IntegrationKey, Entity ] = {}
        for previous_name, entities in candidates_by_name.items():
            upstream_key = upstream_keys_by_name.get( previous_name )
            # Defensive: the IN-filter guarantees previous_name is in
            # the dict, but a corrupted row could slip through.
            if upstream_key is None:
                continue

            if len( entities ) > 1:
                ambiguity_message = (
                    f'Auto-reconnect skipped for {integration_id} item '
                    f'"{previous_name}": {len(entities)} disconnected '
                    f'entities share that previous identity. Resolve via '
                    f'merge.'
                )
                logger.warning( ambiguity_message )
                if result is not None:
                    result.info_list.append( ambiguity_message )
                continue

            reconnect_map[ upstream_key ] = entities[0]

        return reconnect_map

    @staticmethod
    def preserve_with_user_data( entity           : Entity,
                                 integration_name : str,
                                 result           : Optional[IntegrationSyncResult] = None ):
        """
        Preserve an entity with user-created data by disconnecting it from
        its integration and removing only integration-related components
        (sensors, controllers, orphaned states, integration-owned attributes,
        integration-owned EventDefinitions). The entity's previous integration
        identity is recorded on the entity so the auto-reconnect path can
        recognize it if the same upstream key reappears later. The detached
        state is signaled structurally: ``integration_id`` becomes NULL and
        ``previous_integration_id`` carries the prior identity.

        Integration-owned EventDefinitions are deleted first inside the atomic
        block, before the entity-state and controller deletions that would
        otherwise leave dangling parent rows (CASCADE reaches the children but
        not the parents). User-owned EventDefinitions (``integration_id IS NULL``)
        referencing this entity's states are intentionally NOT touched.

        Args:
            entity: The Entity to preserve.
            integration_name: Name of the integration (used in result messages).
            result: Optional IntegrationSyncResult to append a status
                message to.
        """
        original_name = entity.name

        sensor_ids_to_remove = EntityUserDataDetector.get_integration_related_sensors(entity)
        controller_ids_to_remove = EntityUserDataDetector.get_integration_related_controllers(entity)

        orphaned_state_ids = EntityUserDataDetector.get_orphaned_entity_states(
            entity, sensor_ids_to_remove, controller_ids_to_remove
        )

        with transaction.atomic():
            EventDefinitionOperations.delete_for_entity( entity )

            if sensor_ids_to_remove:
                removed_sensor_count = Sensor.objects.filter(
                    id__in=sensor_ids_to_remove
                ).delete()[0]
                logger.debug(f'Removed {removed_sensor_count} integration sensors for {entity}')

            if controller_ids_to_remove:
                removed_controller_count = Controller.objects.filter(
                    id__in=controller_ids_to_remove
                ).delete()[0]
                logger.debug(f'Removed {removed_controller_count} integration controllers for {entity}')

            if orphaned_state_ids:
                removed_state_count = EntityState.objects.filter(
                    id__in=orphaned_state_ids
                ).delete()[0]
                logger.debug(f'Removed {removed_state_count} orphaned entity states for {entity}')

            # Drop integration-created attributes, keep user-added ones. Provenance
            # is in attribute_type_str: PREDEFINED is system-created, CUSTOM is
            # user-added. queryset.delete() intentionally bypasses the
            # SoftDeleteAttributeModel.delete() override -- integration attributes
            # should not accumulate as soft-deleted rows.
            removed_attr_count = entity.attributes.exclude(
                attribute_type_str=str(AttributeType.CUSTOM),
            ).delete()[0]
            if removed_attr_count:
                logger.debug(f'Removed {removed_attr_count} integration attributes for {entity}')

            entity.previous_integration_key = entity.integration_key
            entity.integration_key = None

            # Restore user-management flags. Integration converters typically set
            # these to False to lock the entity against user changes; on detach
            # the entity is no longer integration-managed.
            entity.can_user_delete = True
            entity.allow_internal_attributes = True

            # has_video_stream: the backing sensor was deleted, so the capability
            # is genuinely lost. is_disabled: the general capability gate that
            # keeps a detached entity out of capability-driven enumerations.
            entity.has_video_stream = False
            entity.is_disabled = True

            entity.save()

        if result is not None:
            # detached_list surfaces in the operator-visible summary;
            # info_list carries the diagnostic note for the details view.
            result.detached_list.append( entity.name )
            result.info_list.append(
                f'Preserved {integration_name} item "{original_name}" with user data; '
                f'detached from integration.'
            )
