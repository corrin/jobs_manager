class PreconditionFailedError(Exception):
    """Raised when optimistic concurrency preconditions are not met."""

    pass


__all__ = ["PreconditionFailedError"]

