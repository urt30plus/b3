import os
import sys

__author__ = 'ThorN'
__version__ = '1.4'
__all__ = ['resource_directory']


def resource_directory(module):
    """
    Use this if pkg_resources is NOT installed
    """
    return os.path.dirname(sys.modules[module].__file__)


try:
    import pkg_resources
except ImportError:
    pkg_resources = None
    pass
else:
    # package tools is installed
    def resource_directory_from_pkg_resources(module):
        """
        Use this if pkg_resources is installed
        """
        return pkg_resources.resource_filename(module, '')


    resource_directory = resource_directory_from_pkg_resources
