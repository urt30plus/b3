import configparser
import os
import re
import time
from io import StringIO

import b3
import b3.functions
import b3.storage

__author__ = "ThorN, Courgette, Fenix"
__version__ = "1.7.9"

NoOptionError = configparser.NoOptionError
NoSectionError = configparser.NoSectionError

# list of plugins that cannot be loaded as disabled from configuration file
MUST_HAVE_PLUGINS = ("admin",)


class ConfigFileNotFound(Exception):
    """
    Raised whenever the configuration file can't be found.
    """

    def __init__(self, message):
        Exception.__init__(self, message)

    def __str__(self):
        return repr(self.args[0])


class ConfigFileNotValid(Exception):
    """
    Raised whenever we are parsing an invalid configuration file.
    """

    def __init__(self, message):
        Exception.__init__(self, message)

    def __str__(self):
        return repr(self.args[0])


class MissingRequirement(Exception):
    """
    Raised whenever we can't initialize a functionality because some modules are missing.
    """

    def __init__(self, message, throwable=None):
        Exception.__init__(self, message)
        self.throwable = throwable

    def __str__(self):
        if self.throwable:
            return f"{self.args[0]} - {repr(self.throwable)!r}"
        return repr(self.args[0])


class B3ConfigParserMixin:
    """
    Mixin implementing ConfigParser methods more useful for B3 business.
    """

    def get(self, *args, **kwargs):
        """
        Return a configuration value as a string.
        """
        raise NotImplementedError

    def getboolean(self, section, setting):
        """
        Return a configuration value as a boolean.
        :param section: The configuration file section.
        :param setting: The configuration file setting.
        """
        value_raw = self.get(section, setting)
        value = value_raw.lower() if value_raw else ""
        if value in ("yes", "1", "on", "true"):
            return True
        elif value in ("no", "0", "off", "false"):
            return False
        else:
            raise ValueError(f"{section}.{setting} : '{value}' is not a boolean value")

    def getDuration(self, section, setting=None):
        """
        Return a configuration value parsing the duration time
        notation and converting the value into minutes.
        :param section: The configuration file section.
        :param setting: The configuration file setting.
        """
        value = self.get(section, setting).strip()
        return b3.functions.time2minutes(value)

    def getpath(self, section, setting):
        """
        Return an absolute path name and expand the user prefix (~).
        :param section: The configuration file section.
        :param setting: The configuration file setting.
        """
        return b3.functions.getAbsolutePath(self.get(section, setting), decode=True)

    def getTextTemplate(self, section, setting=None, **kwargs):
        """
        Return a text template from the configuration file: will
        substitute all the tokens with the given kwargs.
        :param section: The configuration file section.
        :param setting: The configuration file setting.
        :param kwargs: A dict with variables used for string substitution.
        """
        value = b3.functions.vars2printf(self.get(section, setting, True)).strip()
        if kwargs:
            return value % kwargs
        return value


class CfgConfigParser(B3ConfigParserMixin, configparser.ConfigParser):
    """
    A config parser class that mimics the ConfigParser, reads the cfg format.
    """

    fileName = ""
    fileMtime = 0

    def __init__(self, allow_no_value=False):
        """
        Object constructor.
        :param allow_no_value: Whether or not to allow empty values in configuration sections
        """
        opts = {
            "allow_no_value": allow_no_value,
            "inline_comment_prefixes": ";",
            "interpolation": None,
        }
        configparser.ConfigParser.__init__(self, **opts)

    def add_comment(self, section, comment):
        """
        Add a comment
        :param section: The section where to place the comment
        :param comment: The comment to add
        """
        if not section or section == "DEFAULT":
            sectdict = self._defaults
        else:
            try:
                sectdict = self._sections[section]
            except KeyError:
                raise NoSectionError(section) from None
        sectdict[f"; {comment}"] = None

    def get(self, section, option, *args, **kwargs):
        """
        Return a configuration value as a string.
        """
        # Some calls will pass `raw` in the args (True,) and others
        # will have kwargs {raw: True, vars: None}. There should not
        # be a situation where both args and kwargs are present. But...
        # TODO: remove print statements after confirming they are not fired
        opts = kwargs
        if args:
            if opts:
                print(
                    f"ERROR: CfgConfigParser.get(option={option}) args and kwargs: args={args} / kwargs={opts}"
                )
            else:
                opts = {"raw": args[0]}
                if len(args) > 1:
                    print(
                        f"ERROR: CfgConfigParser.get(option={option}) too many values: {args}"
                    )
                    opts["vars"] = args[1]
        try:
            value = configparser.ConfigParser.get(self, section, option, **opts)
            return "" if value is None else value
        except NoSectionError:
            # plugins are used to only catch NoOptionError
            raise NoOptionError(option, section) from None

    def load(self, filename):
        """
        Load a configuration file.
        """
        with open(filename) as f:
            self.readfp(f)
        self.fileName = filename
        self.fileMtime = os.path.getmtime(self.fileName)
        return True

    def loadFromString(self, cfg_string):
        """
        Read the cfg config from a string.
        """
        fp = StringIO(cfg_string)
        self.readfp(fp)
        fp.close()
        self.fileName = None
        self.fileMtime = time.time()
        return True

    def readfp(self, fp, filename=None):
        """
        Inherits from configparser.ConfigParser to throw our custom exception if needed
        """
        try:
            configparser.ConfigParser.read_file(self, fp, filename)
        except Exception as e:
            raise ConfigFileNotValid("%s" % e) from None

    def save(self):
        """
        Save the configuration file.
        """
        with open(self.fileName, "w") as f:
            self.write(f)
        return True

    def write(self, fp, **kwargs):
        """
        Write an .ini-format representation of the configuration state.
        :param fp: a file-like object
        :param **kwargs: not used
        """
        if self._defaults:
            fp.write("[%s]\n" % configparser.DEFAULTSECT)
            for key, value in self._defaults.items():
                self._write_item(fp, key, value)
            fp.write("\n")
        for section in self._sections:
            fp.write("[%s]\n" % section)
            for key, value in self._sections[section].items():
                self._write_item(fp, key, value)
            fp.write("\n")

    @staticmethod
    def _write_item(fp, key, value):
        if key.startswith((";", "#")) and value is None:
            # consider multiline comments
            for line in key.split("\n"):
                line = line.removeprefix(";")
                line = line.removeprefix("#")
                fp.write(f"; {line.strip()}\n")
        else:
            if value is not None and str(value).strip() != "":
                fp.write("{}: {}\n".format(key, str(value).replace("\n", "\n\t")))
            else:
                fp.write("%s: \n" % key)


def load(filename):
    """
    Load a configuration file.
    Will instantiate the correct configuration object parser.
    """
    # allow the use of empty keys to support the new b3.ini configuration file
    config = CfgConfigParser(allow_no_value=True)

    filename = b3.functions.getAbsolutePath(filename, True)

    # return the config if it can be loaded
    return config if config.load(filename) else None


class MainConfig(B3ConfigParserMixin):
    """
    Class to use to parse the B3 main config file.
    Responsible for reading the file in ini format.
    """

    def __init__(self, config_parser):
        self._config_parser = config_parser
        self._plugins = []
        if isinstance(self._config_parser, CfgConfigParser):
            self._init_plugins_from_cfg()
        else:
            raise NotImplementedError(
                "unexpected config type: %r" % self._config_parser.__class__
            )

    def _init_plugins_from_cfg(self):
        # Load the list of disabled plugins
        try:
            disabled_plugins_raw = self._config_parser.get("b3", "disabled_plugins")
        except NoOptionError:
            disabled_plugins = []
        else:
            disabled_plugins = re.split(r"\W+", disabled_plugins_raw.lower())

        def get_custom_plugin_path(plugin_name):
            try:
                return self._config_parser.get("plugins_custom_path", plugin_name)
            except NoOptionError:
                return None

        self._plugins = []
        if self._config_parser.has_section("plugins"):
            for name in self._config_parser.options("plugins"):
                self._plugins.append(
                    {
                        "name": name,
                        "conf": self._config_parser.get("plugins", name),
                        "path": get_custom_plugin_path(name),
                        "disabled": name.lower() in disabled_plugins
                        and name.lower() not in MUST_HAVE_PLUGINS,
                    }
                )

    def get_plugins(self):
        """
        :return: list[dict] A list of plugin settings as a dict.
            I.E.:
            [
                {'name': 'admin', 'conf': @conf/plugin_admin.ini, 'path': None, 'disabled': False},
                {'name': 'adv', 'conf': @conf/plugin_adv.ini, 'path': None, 'disabled': False},
            ]
        """
        return self._plugins

    def get_external_plugins_dir(self):
        """
        the directory path (as a string) where additional plugin modules can be found
        :return: str or configparser.NoOptionError
        """
        if isinstance(self._config_parser, CfgConfigParser):
            return self._config_parser.getpath("b3", "external_plugins_dir")
        else:
            raise NotImplementedError(
                "unexpected config type: %r" % self._config_parser.__class__
            )

    def get(self, *args, **kwargs):
        """
        Override the get method defined in the B3ConfigParserMixin
        """
        return self._config_parser.get(*args, **kwargs)

    def analyze(self):
        """
        Analyze the main configuration file checking for common mistakes.
        This will mostly check configuration file values and will not perform any further check related,
        i.e: connection with the database can be established using the provided dsn, rcon password is valid etc.
        Such validations needs to be handled somewhere else.
        :return: A list of strings highlighting problems found (so they can be logged/displayed easily)
        """
        analysis = []

        def _mandatory_option(section, option):
            if not self.has_option(section, option):
                analysis.append(f"missing configuration value {section}::{option}")

        _mandatory_option("b3", "parser")
        _mandatory_option("b3", "database")
        _mandatory_option("b3", "bot_name")

        # PARSER CHECK
        if self.has_option("b3", "parser"):
            try:
                b3.functions.getModule("b3.parsers.%s" % self.get("b3", "parser"))
            except ImportError as ie:
                analysis.append(
                    "invalid parser specified in b3::parser (%s-%s)"
                    % (self.get("b3", "parser"), ie)
                )

        # DSN DICT
        if self.has_option("b3", "database"):
            if not (dsndict := b3.functions.splitDSN(self.get("b3", "database"))):
                analysis.append(
                    "invalid database source name specified in b3::database (%s)"
                    % self.get("b3", "database")
                )
            elif dsndict["protocol"] not in b3.storage.PROTOCOLS:
                analysis.append(
                    "invalid storage protocol specified in b3::database (%s) : "
                    "valid protocols are : %s"
                    % (dsndict["protocol"], ", ".join(b3.storage.PROTOCOLS))
                )

        # ADMIN PLUGIN CHECK
        has_admin = False
        has_admin_config = False
        for plugin in self.get_plugins():
            if plugin["name"] == "admin":
                has_admin = True
                if plugin["conf"]:
                    has_admin_config = True
                break

        if not has_admin:
            analysis.append("missing admin plugin in plugins section")
        elif not has_admin_config:
            analysis.append("missing configuration file for admin plugin")

        return analysis

    def __getattr__(self, name):
        """
        Act as a proxy in front of self._config_parser.
        Any attribute or method call which does not exists in this
        object (MainConfig) is then tried on the self._config_parser
        :param name: str Attribute or method name
        """
        if hasattr(self._config_parser, name):
            attr = getattr(self._config_parser, name)
            if callable(attr):

                def newfunc(*args, **kwargs):
                    return attr(*args, **kwargs)

                return newfunc
            else:
                return attr
        else:
            raise AttributeError(name)


def getConfPath(decode=False, conf=None):
    """
    Return the path to the B3 main configuration directory.
    :param decode: if True will decode the path string using the default file system encoding before returning it.
    :param conf: the current configuration being used :type CfgConfigParser|MainConfig|str:
    """
    if conf:
        if isinstance(conf, str):
            path = os.path.dirname(conf)
        elif isinstance(conf, CfgConfigParser | MainConfig):
            path = os.path.dirname(conf.fileName)
        else:
            raise TypeError(
                "Invalid configuration type specified: expected "
                "str|CfgConfigParser|MainConfig, "
                f"got {type(conf)} instead"
            )
    else:
        path = b3.confdir or os.path.dirname(b3.console.config.fileName)

    return path if not decode else b3.functions.decode_text(path)


def get_main_config(config_path):
    config = None
    if config_path:
        config = b3.functions.getAbsolutePath(config_path, True)
        if not os.path.isfile(config):
            b3.functions.console_exit(
                f"ERROR: configuration file not found ({config})."
            )
    else:
        home_dir = b3.functions.get_home_path(create=False)
        for p in (
            "b3.ini",
            "conf/b3.ini",
            "b3/conf/b3.ini",
            os.path.join(home_dir, "b3.ini"),
            os.path.join(home_dir, "conf", "b3.ini"),
            os.path.join(home_dir, "b3", "conf", "b3.ini"),
            "@b3/conf/b3.ini",
        ):
            path = b3.functions.getAbsolutePath(p, True)
            if os.path.isfile(path):
                print(f"Using configuration file: {path}")
                config = path
                break
        else:
            b3.functions.console_exit(
                "ERROR: could not find any valid configuration file."
            )

    return b3.config.MainConfig(load(config))
