import importlib
import os
import re
import signal
import sys
import traceback
from tempfile import TemporaryFile

import b3.functions

__author__ = 'ThorN'
__version__ = '3.31.8'

modulePath = b3.functions.resource_directory(__name__)

versionEdition = "WindyCity"
versionId = f'v{__version__}'
version = f'^0(^8b3^0) ^9{versionId} ^9[{versionEdition}^9]^3'

confdir = None
console = None

# TEAMS
TEAM_UNKNOWN = -1
TEAM_FREE = 0
TEAM_SPEC = 1
TEAM_RED = 2
TEAM_BLUE = 3

# PLAYER STATE
STATE_DEAD = 1
STATE_ALIVE = 2
STATE_UNKNOWN = 3

# CUSTOM TYPES FOR DYNAMIC CASTING
STRING = STR = 1
INTEGER = INT = 2
BOOLEAN = BOOL = 3
FLOAT = 4
LEVEL = 5  # b3.clients.Group level
DURATION = 6  # b3.functions.time2minutes conversion
PATH = 7  # b3.getAbsolutePath path conversion
TEMPLATE = 8  # b3.functions.vars2printf conversion
LIST = 9  # string split into list of tokens

HOMEDIR = b3.functions.get_home_path()


def decode_text(text):
    """
    Return a copy of text decoded using the default system encoding.
    :param text: the text to decode
    :return: string
    """
    if hasattr(text, 'decode'):
        return text.decode(sys.getfilesystemencoding())
    return text


def getB3Path(decode=False):
    """
    Return the path to the main B3 directory.
    :param decode: if True will decode the path string using the default file system encoding before returning it
    """
    path = os.path.normpath(os.path.expanduser(modulePath))
    return path if not decode else decode_text(path)


def getConfPath(decode=False, conf=None):
    """
    Return the path to the B3 main configuration directory.
    :param decode: if True will decode the path string using the default file system encoding before returning it.
    :param conf: the current configuration being used :type XmlConfigParser|CfgConfigParser|MainConfig|str:
    """
    if conf:
        if isinstance(conf, str):
            path = os.path.dirname(conf)
        elif isinstance(conf, XmlConfigParser) or isinstance(conf, CfgConfigParser) or isinstance(conf, MainConfig):
            path = os.path.dirname(conf.fileName)
        else:
            raise TypeError(
                "Invalid configuration type specified: expected "
                "str|XmlConfigParser|CfgConfigParser|MainConfig, "
                f"got {type(conf)} instead"
            )
    else:
        path = confdir or os.path.dirname(console.config.fileName)

    return path if not decode else decode_text(path)


def getAbsolutePath(path, decode=False, conf=None):
    """
    Return an absolute path name and expand the user prefix (~).
    :param path: the relative path we want to expand
    :param decode: if True will decode the path string using the default file system encoding before returning it
    :param conf: the current configuration being used :type XmlConfigParser|CfgConfigParser|MainConfig|str:
    """
    if path.startswith('@'):
        if path[1:4] in ('b3\\', 'b3/'):
            path = os.path.join(getB3Path(decode=False), path[4:])
        elif path[1:6] in ('conf\\', 'conf/'):
            path = os.path.join(getConfPath(decode=False, conf=conf), path[6:])
        elif path[1:6] in ('home\\', 'home/'):
            path = os.path.join(HOMEDIR, path[6:])
    path = os.path.normpath(os.path.expanduser(path))
    return path if not decode else decode_text(path)


def getB3versionString():
    """
    Return the B3 version as a string.
    """
    return re.sub(r'\^[0-9a-z]', '', version)


def getWritableFilePath(filepath, decode=False):
    """
    Return an absolute filepath making sure the current user can write it.
    If the given path is not writable by the current user, the path will be converted
    into an absolute path pointing inside the B3 home directory (defined in the `HOMEDIR` global
    variable) which is assumed to be writable.
    :param filepath: the relative path we want to expand
    :param decode: if True will decode the path string using the default file system encoding before returning it
    """
    filepath = getAbsolutePath(filepath, decode)
    if not filepath.startswith(HOMEDIR):
        try:
            with TemporaryFile(dir=os.path.dirname(filepath)) as tf:
                pass
        except (OSError, IOError):
            # no need to decode again since HOMEDIR is already decoded
            # and os.path.join will handle everything itself
            filepath = os.path.join(HOMEDIR, os.path.basename(filepath))
    return filepath


def getShortPath(filepath, decode=False, first_time=True):
    """
    Convert the given absolute path into a short path.
    Will replace path string with proper tokens (such as @b3, @conf, ~, ...)
    :param filepath: the path to convert
    :param decode: if True will decode the path string using the default file system encoding before returning it
    :param first_time: whether this is the first function call attempt or not
    :return: string
    """
    # NOTE: make sure to have os.path.sep at the end otherwise also files starting with 'b3' will be matched
    homepath = getAbsolutePath('@home/', decode) + os.path.sep
    if filepath.startswith(homepath):
        return filepath.replace(homepath, '@home' + os.path.sep)
    confpath = getAbsolutePath('@conf/', decode) + os.path.sep
    if filepath.startswith(confpath):
        return filepath.replace(confpath, '@conf' + os.path.sep)
    b3path = getAbsolutePath('@b3/', decode) + os.path.sep
    if filepath.startswith(b3path):
        return filepath.replace(b3path, '@b3' + os.path.sep)
    userpath = getAbsolutePath('~', decode) + os.path.sep
    if filepath.startswith(userpath):
        return filepath.replace(userpath, '~' + os.path.sep)
    if first_time:
        return getShortPath(filepath, not decode, False)
    return filepath


def loadParser(pname):
    """
    Load the parser module given it's name.
    :param pname: The parser name
    :return The parser module
    """
    mod = importlib.import_module(f'b3.parsers.{pname}')
    return getattr(mod, f'{pname.title()}Parser')


def stdout_write(message, flush=True):
    sys.stdout.write(message)
    if flush:
        sys.stdout.flush()


def start(mainconfig, options):
    """
    Main B3 startup.
    :param mainconfig: The B3 configuration file instance :type: b3.config.MainConfig
    :param options: command line options
    """
    b3.functions.clearscreen()
    global confdir
    confdir = os.path.dirname(mainconfig.fileName)

    stdout_write(f'Starting B3      : {getB3versionString()}\n')

    # not real loading but the user will get what's configuration he is using
    stdout_write(f'Loading config   : {getShortPath(mainconfig.fileName, True)}\n')

    parsertype = mainconfig.get('b3', 'parser')
    stdout_write(f'Loading parser   : {parsertype}\n')

    parser = loadParser(parsertype)
    global console
    console = parser(mainconfig, options)

    def termSignalHandler(signum, frame):
        """
        Define the signal handler so to handle B3 shutdown properly.
        """
        console.bot("TERM signal received: shutting down")
        console.shutdown()
        raise SystemExit(0)

    try:
        # necessary if using the functions profiler,
        # because signal.signal cannot be used in threads
        signal.signal(signal.SIGTERM, termSignalHandler)
    except Exception:
        pass

    try:
        console.start()
    except KeyboardInterrupt:
        console.shutdown()
        print('Goodbye')
        return
    except SystemExit as msg:
        print(f'EXITING: {msg}')
        raise
    except Exception as msg:
        print(f'ERROR: {msg}')
        traceback.print_exc()
        sys.exit(223)


from b3.config import XmlConfigParser, CfgConfigParser, MainConfig
