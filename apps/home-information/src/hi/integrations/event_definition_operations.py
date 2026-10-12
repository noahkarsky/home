"""
Operations on EventDefinition rows with respect to integration ownership.

Integration-scoped cleanup with a deliberately narrow policy:

  * Only EventDefinition rows whose own ``integration_id`` matches are
    removed. User-owned EventDefinition rows (``integration_id IS NULL``)
    are never touched here, even when they reference an entity state that
    an integration is about to delete. The silent semantic change of a
    user-owned multi-clause rule losing one of its clauses is a known gap.
  * No general "EntityState delete cascades to parent EventDefinition"
    rule exists -- cleanup runs only at the integration disconnect /
    sync-removal boundary.

EventDefinition has no FK back to Entity; the reverse path is
``EventDefinition -> EventClause -> EntityState -> Entity``, traversed
explicitly in the queries below. Children (``EventClause``,
``ControlAction``, ``AlarmAction``, ``EventHistory``) cascade from the
parent delete and are not enumerated here.
"""

import logging
from typing import Iterable, List

from hi.apps.entity.models import Entity
from hi.apps.event.models import EventDefinition

logger = logging.getLogger(__name__)


class EventDefinitionOperations:
    """Callers must wrap invocations in ``transaction.atomic``; the helpers
    do not open transactions themselves."""

    @staticmethod
    def delete_for_integration( integration_id : str ) -> int:
        """
        Delete every EventDefinition whose own ``integration_id`` matches.
        Does not traverse clauses -- the integration_id on the EventDefinition
        itself is the ownership signal.
        """
        if not integration_id:
            return 0
        _, per_model = EventDefinition.objects.filter(
            integration_id = integration_id,
        ).delete()
        deleted_count = per_model.get( EventDefinition._meta.label, 0 )
        if deleted_count:
            logger.debug(
                f'Removed {deleted_count} integration EventDefinitions '
                f'for integration_id={integration_id}'
            )
        return deleted_count

    @classmethod
    def delete_for_entity( cls, entity : Entity ) -> int:
        """
        Delete EventDefinitions owned by this entity's integration whose
        clauses reference any of this entity's states. Returns 0 when the
        entity is not currently integration-attached, so callers may invoke
        unconditionally.
        """
        if not entity.integration_id:
            return 0
        return cls.delete_for_entity_closure(
            entity_ids = [ entity.id ],
            integration_id = entity.integration_id,
        )

    @staticmethod
    def delete_for_entity_closure( entity_ids     : Iterable[int],
                                   integration_id : str ) -> int:
        """
        Batched form of ``delete_for_entity`` for a closure of entities.

        Deletes every EventDefinition where:
          * the EventDefinition's own ``integration_id`` matches, AND
          * at least one of its EventClauses references an EntityState
            owned by an entity in ``entity_ids``.

        Two-step (lookup-then-delete) to avoid issues with
        ``queryset.delete()`` on a ``.distinct()`` queryset across a
        joined relation.
        """
        entity_id_list : List[int] = list( entity_ids )
        if not entity_id_list or not integration_id:
            return 0
        target_ids = list(
            EventDefinition.objects.filter(
                integration_id = integration_id,
                event_clauses__entity_state__entity_id__in = entity_id_list,
            ).values_list( 'id', flat = True ).distinct()
        )
        if not target_ids:
            return 0
        _, per_model = EventDefinition.objects.filter(
            id__in = target_ids,
        ).delete()
        deleted_count = per_model.get( EventDefinition._meta.label, 0 )
        if deleted_count:
            logger.debug(
                f'Removed {deleted_count} integration EventDefinitions '
                f'for integration_id={integration_id} '
                f'over {len(entity_id_list)} entities'
            )
        return deleted_count
