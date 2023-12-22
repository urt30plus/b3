"""
Depending on the B3 parser loaded, this module will load the correct plugin version
"""

from b3 import __version__ as b3_version

__version__ = "1.26"
__author__ = "xlr8or, courgette"


class PoweradminurtPlugin:
    requiresConfigFile = True
    requiresPlugins = []
    loadAfterPlugins = []
    requiresVersion = b3_version
    requiresParsers = ["iourt41", "iourt42", "iourt43"]
    requiresStorage = []

    def __new__(cls, *args, **kwargs):
        console, plugin_config = args
        if console.gameName == "iourt43":
            from .iourt43 import Poweradminurt43Plugin

            return Poweradminurt43Plugin(*args, **kwargs)
        else:
            raise AssertionError(
                "poweradminurt plugin can only work with Urban Terror 4.3"
            )
