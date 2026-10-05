class GenesisError(RuntimeError):
    """Base error for expected Genesis application failures."""


class ConfigurationError(GenesisError):
    pass


class PersistenceError(GenesisError):
    pass


class IntegrationError(GenesisError):
    pass


class StaleUpstreamError(IntegrationError):
    """Upstream data is missing, empty, or unsafe to replace authoritative state."""
