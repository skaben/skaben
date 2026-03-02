__all__ = ["ConfigException"]


class SkabenException(Exception):
    """Basic SKABEN system exception"""

    pass


class ConfigException(SkabenException):
    """Basic configuration exception"""

    pass
