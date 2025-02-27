from typing import NamedTuple


class _version_info(NamedTuple):
    # similar to sys._version_info
    major: int
    minor: int
    micro: int


version_info = _version_info(0, 11, 1)
__version__ = '.'.join(map(str, version_info))


def config_for_app(config):
    import warnings
    warnings.warn((
        "It is safe to remove this function call now. "
        "import biothings.hub will take care of it."
    ), DeprecationWarning)
