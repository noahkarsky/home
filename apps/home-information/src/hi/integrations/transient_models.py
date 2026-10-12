from dataclasses import dataclass
from datetime import datetime
from typing import Dict, FrozenSet, List, Optional

from hi.apps.system.enums import HealthStatusType
from .enums import IntegrationAttributeType, IntegrationCapability


@dataclass
class IntegrationMetaData:

    integration_id            : str  # unique across all integrations
    label                     : str
    attribute_type            : IntegrationAttributeType
    allow_entity_deletion     : bool
    allow_internal_attributes : bool = True
    logo_static_path          : str  = 'img/integrations/default.svg'
    capabilities              : FrozenSet[IntegrationCapability] = frozenset({
        IntegrationCapability.CONNECT,
    })

    def __post_init__(self):
        if not self.capabilities:
            raise ValueError(
                f"Integration '{self.integration_id}' must declare at "
                f"least one IntegrationCapability."
            )

    
@dataclass
class IntegrationControlResult:

    new_value    : str
    error_list   : List[ str ]

    @property
    def has_errors(self):
        return bool( self.error_list )


@dataclass
class IntegrationKey:
    """
    Internal identifier to help map to/from an integration's
    external names/identifiers
    """

    integration_id    : str
    integration_name  : str

    def __post_init__(self):
        # Canonicalize both fields so matching is robust against case variation
        # in external names.
        self.integration_id = self.normalize( self.integration_id )
        self.integration_name = self.normalize( self.integration_name )
        return

    @staticmethod
    def normalize( value : str ) -> str:
        """Canonical normalization applied to ``integration_id`` and
        ``integration_name``. Exposed so callers can apply the same rule when
        comparing raw strings against stored values, without constructing a
        full IntegrationKey. Prefer full ``IntegrationKey`` objects when
        possible (``__hash__`` / ``__eq__`` use this rule); this static is the
        escape hatch for one-shot string normalization."""
        return value.lower()
    
    def __str__(self):
        return self.integration_key_str

    def __eq__(self, other):
        if isinstance(other, IntegrationKey):
            return self.integration_key_str == other.integration_key_str
        return False

    def __hash__(self):
        return hash(self.integration_key_str)
    
    @property
    def integration_key_str(self):
        return f'{self.integration_id}.{self.integration_name}'

    @classmethod
    def from_string( cls, a_string : str ):
        prefix, suffix = a_string.split( '.', 1 )
        return IntegrationKey(
            integration_id = prefix,
            integration_name = suffix,
        )


@dataclass
class IntegrationDetails:
    """IntegrationKey plus an optional payload of integration-specific data."""
    key      : IntegrationKey
    payload  : Optional[Dict] = None


@dataclass
class IntegrationRemovalSummary:
    """Classification of an integration's attached entities: raw counts
    only, with derived values as properties so the object stays consistent."""

    total_count: int
    user_data_count: int

    @property
    def deletable_count(self) -> int:
        return self.total_count - self.user_data_count

    @property
    def has_mixed_state(self) -> bool:
        """True when at least one entity has user data."""
        return self.user_data_count > 0


@dataclass
class ConnectionTestResult:
    """Result from a live integration connection probe (network probe with
    bounded timeout against the proposed configuration). Distinct from
    ``IntegrationValidationResult``, which represents schema-level validation
    outcomes."""

    is_success     : bool
    message        : Optional[str] = None

    @classmethod
    def success(cls, message: Optional[str] = None) -> 'ConnectionTestResult':
        return cls(is_success=True, message=message)

    @classmethod
    def failure(cls, message: str) -> 'ConnectionTestResult':
        return cls(is_success=False, message=message)


@dataclass
class IntegrationValidationResult:

    is_valid       : bool
    status         : HealthStatusType
    error_message  : Optional[str] = None
    timestamp      : Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            import hi.apps.common.datetimeproxy as datetimeproxy
            self.timestamp = datetimeproxy.now()

    @classmethod
    def success(cls) -> 'IntegrationValidationResult':
        return cls(
            is_valid=True,
            status=HealthStatusType.HEALTHY
        )

    @classmethod
    def error(cls, status: HealthStatusType, error_message: str) -> 'IntegrationValidationResult':
        return cls(
            is_valid=False,
            status=status,
            error_message=error_message
        )

