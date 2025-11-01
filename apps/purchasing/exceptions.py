class PreconditionFailedError(Exception):
    """Raised when optimistic concurrency preconditions are not met."""


__all__ = ["PreconditionFailedError"]
