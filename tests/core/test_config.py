import configparser
import logging
import unittest
from unittest import TestCase

from b3.config import CfgConfigParser, ConfigFileNotValid
from tests import B3TestCase


class CommonTestMethodsMixin:
    def _assert_func(self, func, expected, conf_value):
        self.conf.loadFromString(self.__class__.assert_func_template % conf_value)
        try:
            self.assertEqual(expected, func("section_foo", "foo"))
        except (configparser.Error, ValueError) as err:
            self.fail("expecting %s, but got %r" % (expected, err))

    def _assert_func_raises(self, func, expected_error, section, name, conf):
        try:
            self.conf.loadFromString(conf)
            func(section, name)
        except expected_error:
            pass
        except Exception as err:
            self.fail("expecting %s, but got %r" % (expected_error, err))
        else:
            self.fail("expecting %s" % expected_error)

    def assert_get(self, expected, conf_value):
        self._assert_func(self.conf.get, expected, conf_value)

    def assert_get_raises(self, expected_error, section, name, conf):
        self._assert_func_raises(self.conf.get, expected_error, section, name, conf)

    def assert_getint(self, expected, conf_value):
        self._assert_func(self.conf.getint, expected, conf_value)

    def assert_getint_raises(self, expected_error, section, name, conf):
        self._assert_func_raises(self.conf.getint, expected_error, section, name, conf)

    def assert_getfloat(self, expected, conf_value):
        self._assert_func(self.conf.getfloat, expected, conf_value)

    def assert_getfloat_raises(self, expected_error, section, name, conf):
        self._assert_func_raises(
            self.conf.getfloat, expected_error, section, name, conf
        )

    def assert_getboolean(self, expected, conf_value):
        self._assert_func(self.conf.getboolean, expected, conf_value)

    def assert_getboolean_raises(self, expected_error, section, name, conf):
        self._assert_func_raises(
            self.conf.getboolean, expected_error, section, name, conf
        )

    def assert_getDuration(self, expected, conf_value):
        self._assert_func(self.conf.getDuration, expected, conf_value)

    def test_get(self):
        self.assert_get("bar", "bar")
        self.assert_get("", "")
        self.assert_get_raises(
            configparser.NoOptionError,
            "section_foo",
            "bar",
            self.assert_func_template % "",
        )
        self.assert_get_raises(
            configparser.NoOptionError,
            "section_bar",
            "foo",
            self.assert_func_template % "",
        )

    def test_getint(self):
        self.assert_getint(-54, "-54")
        self.assert_getint(0, "0")
        self.assert_getint(64, "64")
        self.assert_getint_raises(
            ValueError, "section_foo", "foo", self.assert_func_template % "bar"
        )
        self.assert_getint_raises(
            ValueError, "section_foo", "foo", self.assert_func_template % "64.5"
        )
        self.assert_getint_raises(
            ValueError, "section_foo", "foo", self.assert_func_template % ""
        )
        self.assert_getint_raises(
            configparser.NoOptionError,
            "section_foo",
            "bar",
            self.assert_func_template % "",
        )
        self.assert_getint_raises(
            configparser.NoOptionError,
            "section_bar",
            "foo",
            self.assert_func_template % "",
        )

    def test_getfloat(self):
        self.assert_getfloat(-54.0, "-54")
        self.assert_getfloat(-54.6, "-54.6")
        self.assert_getfloat(0.0, "0")
        self.assert_getfloat(0.0, "0.0")
        self.assert_getfloat(64.0, "64")
        self.assert_getfloat(64.45, "64.45")
        self.assert_getfloat_raises(
            ValueError, "section_foo", "foo", self.assert_func_template % "bar"
        )
        self.assert_getfloat_raises(
            ValueError, "section_foo", "foo", self.assert_func_template % "64,5"
        )
        self.assert_getfloat_raises(
            ValueError, "section_foo", "foo", self.assert_func_template % ""
        )
        self.assert_getfloat_raises(
            configparser.NoOptionError,
            "section_foo",
            "bar",
            self.assert_func_template % "",
        )
        self.assert_getfloat_raises(
            configparser.NoOptionError,
            "section_bar",
            "foo",
            self.assert_func_template % "",
        )

    def test_getboolean(self):
        self.assert_getboolean(False, "false")
        self.assert_getboolean(False, "0")
        self.assert_getboolean(False, "off")
        self.assert_getboolean(False, "OFF")
        self.assert_getboolean(False, "no")
        self.assert_getboolean(False, "NO")
        self.assert_getboolean(True, "true")
        self.assert_getboolean(True, "1")
        self.assert_getboolean(True, "on")
        self.assert_getboolean(True, "ON")
        self.assert_getboolean(True, "yes")
        self.assert_getboolean(True, "YES")
        self.assert_getboolean_raises(
            ValueError, "section_foo", "foo", self.assert_func_template % "bar"
        )
        self.assert_getboolean_raises(
            ValueError, "section_foo", "foo", self.assert_func_template % "64,5"
        )
        self.assert_getboolean_raises(
            ValueError, "section_foo", "foo", self.assert_func_template % ""
        )
        self.assert_getboolean_raises(
            configparser.NoOptionError,
            "section_foo",
            "bar",
            self.assert_func_template % "",
        )
        self.assert_getboolean_raises(
            configparser.NoOptionError,
            "section_bar",
            "foo",
            self.assert_func_template % "",
        )

    def test_getDuration(self):
        self.assert_getDuration(0, "0")
        self.assert_getDuration(50, "50")
        self.assert_getDuration(24 * 60, "24h")
        self.assert_getDuration(0.5, "30s")


class Test_ConfigFileNotValid(TestCase):
    def test_exception_message(self):
        try:
            raise ConfigFileNotValid("f00")
        except ConfigFileNotValid as e:
            self.assertEqual(repr("f00"), str(e))

    def test_loading_invalid_conf(self):
        config = CfgConfigParser()
        try:
            config.loadFromString(r"""[server""")
        except ConfigFileNotValid as e:
            self.assertEqual(
                "\"File contains no section headers.\\nfile: '<???>', line: 1\\n'[server'\"",
                str(e),
            )
        except Exception as e:
            self.fail("unexpected exception %r" % e)
        else:
            self.fail("expecting exception")


class Test_CfgConfigParser(CommonTestMethodsMixin, B3TestCase):
    assert_func_template = """
[section_foo]
foo = %s
"""

    def setUp(self):
        B3TestCase.setUp(self)
        self.conf = CfgConfigParser()
        self.conf.loadFromString("[foo]")
        log = logging.getLogger("output")
        log.setLevel(logging.DEBUG)


if __name__ == "__main__":
    unittest.main()
