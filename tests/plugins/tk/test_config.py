from textwrap import dedent
from unittest.mock import patch, call

import b3
import b3.functions
from b3.config import CfgConfigParser, NoOptionError
from b3.plugins.tk import TkPlugin
from tests import B3TestCase
from tests.plugins.tk import Test_Tk_plugin


class Test_onLoadConfig(Test_Tk_plugin):

    def test_onLoadConfig_minimal(self):
        # GIVEN
        self.conf.loadFromString(r"")
        # WHEN
        self.p = TkPlugin(self.console, self.conf)
        self.p.onLoadConfig()
        # THEN
        self.assertEqual(400, self.p._max_points)
        self.assertDictEqual({
            0: (2.0, 1.0, 2),
            1: (2.0, 1.0, 2),
            2: (1.0, 0.5, 1),
            20: (1.0, 0.5, 0),
            40: (0.75, 0.5, 0)
        }, self.p._levels)
        self.assertEqual(40, self.p._max_level)
        self.assertEqual(7, self.p._round_grace)
        self.assertEqual("sfire", self.p._issue_warning)
        self.assertTrue(self.p._grudge_enable)
        self.assertTrue(self.p._private_messages)
        self.assertEqual(100, self.p._damage_threshold)
        self.assertEqual(2, self.p._warn_level)
        self.assertEqual(0, self.p._tk_points_halflife)
        self.assertEqual('1h', self.p._tk_warn_duration)

    def test_onLoadConfig(self):
        # GIVEN
        self.conf.loadFromString(dedent(r"""
            [settings]
            max_points: 350
            levels: 0,1,2
            round_grace: 3
            issue_warning: foo
            grudge_enable: no
            private_messages: off
            damage_threshold: 99
            warn_level: 10
            halflife: 3
            warn_duration: 3h
            [level_0]

            kill_multiplier: 2
            damage_multiplier: 1
            ban_length: 3
            [level_1]

            kill_multiplier: 2
            damage_multiplier: 1
            ban_length: 4
            [level_2]

            kill_multiplier: 1
            damage_multiplier: 0.5
            ban_length: 5
        """))
        self.p = TkPlugin(self.console, self.conf)
        # WHEN
        self.p.onLoadConfig()
        # THEN
        self.assertEqual(350, self.p._max_points)
        self.assertDictEqual({
            0: (2.0, 1.0, 3),
            1: (2.0, 1.0, 4),
            2: (1.0, 0.5, 5),
        }, self.p._levels)
        self.assertEqual(2, self.p._max_level)
        self.assertEqual(3, self.p._round_grace)
        self.assertEqual("foo", self.p._issue_warning)
        self.assertFalse(self.p._grudge_enable)
        self.assertFalse(self.p._private_messages)
        self.assertEqual(99, self.p._damage_threshold)
        self.assertEqual(10, self.p._warn_level)
        self.assertEqual(3, self.p._tk_points_halflife)
        self.assertEqual('3h', self.p._tk_warn_duration)


class Test_get_config_for_levels(Test_Tk_plugin):

    def setUp(self):
        Test_Tk_plugin.setUp(self)
        self.error_patcher = patch.object(self.p, 'error')
        self.error_mock = self.error_patcher.start()

    def tearDown(self):
        Test_Tk_plugin.tearDown(self)
        self.error_patcher.stop()

    def test_missing_level(self):
        # GIVEN
        self.conf.loadFromString(dedent(r"""
        """))
        # WHEN
        try:
            self.p.load_config_for_levels()
            self.fail("expecting NoOptionError")
        except NoOptionError:
            pass
        # THEN
        self.assertListEqual([], self.error_mock.mock_calls)

    def test_nominal_one_level(self):
        # GIVEN
        self.conf.loadFromString(dedent(r"""
            [settings]
            levels: 0

            [level_0]
            kill_multiplier: 1.3
            damage_multiplier: 1.1
            ban_length: 3
        """))
        # WHEN
        levels = self.p.load_config_for_levels()
        # THEN
        self.assertDictEqual({
            0: (1.3, 1.1, 3),
        }, levels)
        self.assertListEqual([], self.error_mock.mock_calls)

    def test_nominal_many_levels(self):
        # GIVEN
        self.conf.loadFromString(dedent(r"""
            [settings]
            levels: 0,20,80

            [level_0]
            kill_multiplier: 1.3
            damage_multiplier: 1.1
            ban_length: 3

            [level_20]
            kill_multiplier: 1.8
            damage_multiplier: 1.3
            ban_length: 2

            [level_80]
            kill_multiplier: 1
            damage_multiplier: 1
            ban_length: 1
        """))
        # WHEN
        levels = self.p.load_config_for_levels()
        # THEN
        self.assertDictEqual({
            0: (1.3, 1.1, 3),
            20: (1.8, 1.3, 2),
            80: (1.0, 1.0, 1),
        }, levels)
        self.assertListEqual([], self.error_mock.mock_calls)

    def test_nominal_many_levels_keywords(self):
        # GIVEN
        self.conf.loadFromString(dedent(r"""
            [settings]
            levels: guest,mod,senioradmin

            [level_0]
            kill_multiplier: 1.3
            damage_multiplier: 1.1
            ban_length: 3

            [level_mod]
            kill_multiplier: 1.8
            damage_multiplier: 1.3
            ban_length: 2

            [level_80]
            kill_multiplier: 1
            damage_multiplier: 1
            ban_length: 1
        """))
        # WHEN
        levels = self.p.load_config_for_levels()
        # THEN
        self.assertDictEqual({
            0: (1.3, 1.1, 3),
            20: (1.8, 1.3, 2),
            80: (1.0, 1.0, 1),
        }, levels)
        self.assertListEqual([], self.error_mock.mock_calls)

    def test_level_junk(self):
        # GIVEN
        self.conf.loadFromString(dedent(r"""
            [settings]
            levels: f00
        """))
        # WHEN
        try:
            self.p.load_config_for_levels()
            self.fail("expecting ValueError")
        except ValueError:
            pass
        # THEN
        self.assertListEqual([call("'f00' is not a valid level")], self.error_mock.mock_calls)

    def test_missing_section(self):
        # GIVEN
        self.conf.loadFromString(dedent(r"""
            [settings]
            levels: 0,mod,80

            [level_0]
            kill_multiplier: 1.3
            damage_multiplier: 1.1
            ban_length: 3

            [level_80]
            kill_multiplier: 1
            damage_multiplier: 1
            ban_length: 1
        """))
        # WHEN
        try:
            self.p.load_config_for_levels()
            self.fail("expecting ValueError")
        except ValueError:
            pass
        # THEN
        self.assertListEqual([call("section 'level_mod' is missing from the config file")], self.error_mock.mock_calls)

    def test_missing_kill_multiplier(self):
        # GIVEN
        self.conf.loadFromString(dedent(r"""
            [settings]
            levels: 0

            [level_0]
            damage_multiplier: 1.1
            ban_length: 3
        """))
        # WHEN
        try:
            self.p.load_config_for_levels()
            self.fail("expecting ValueError")
        except ValueError:
            pass
        # THEN
        self.assertListEqual([
            call('option kill_multiplier is missing in section level_0'),
        ], self.error_mock.mock_calls)

    def test_missing_damage_multiplier(self):
        # GIVEN
        self.conf.loadFromString(dedent(r"""
            [settings]
            levels: 0

            [level_0]
            kill_multiplier: 1.3
            ban_length: 3
        """))
        # WHEN
        try:
            self.p.load_config_for_levels()
            self.fail("expecting ValueError")
        except ValueError:
            pass
        # THEN
        self.assertListEqual([
            call('option damage_multiplier is missing in section level_0'),
        ], self.error_mock.mock_calls)

    def test_missing_ban_length(self):
        # GIVEN
        self.conf.loadFromString(dedent(r"""
            [settings]
            levels: 0

            [level_0]
            kill_multiplier: 1.3
            damage_multiplier: 1.1
        """))
        # WHEN
        try:
            self.p.load_config_for_levels()
            self.fail("expecting ValueError")
        except ValueError:
            pass
        # THEN
        self.assertListEqual([
            call('option ban_length is missing in section level_0'),
        ], self.error_mock.mock_calls)

    def test_bad_kill_multiplier(self):
        # GIVEN
        self.conf.loadFromString(dedent(r"""
            [settings]
            levels: 0

            [level_0]
            kill_multiplier: f00
            damage_multiplier: 1.1
            ban_length: 3
        """))
        # WHEN
        try:
            self.p.load_config_for_levels()
            self.fail("expecting ValueError")
        except ValueError:
            pass
        # THEN
        self.assertListEqual([
            call('value for kill_multiplier is invalid. '
                 'could not convert string to float: {}'
                 .format("'f00'")),
        ], self.error_mock.mock_calls)

    def test_bad_damage_multiplier(self):
        # GIVEN
        self.conf.loadFromString(dedent(r"""
            [settings]
            levels: 0

            [level_0]
            kill_multiplier: 1.3
            damage_multiplier: f00
            ban_length: 3
        """))
        # WHEN
        try:
            self.p.load_config_for_levels()
            self.fail("expecting ValueError")
        except ValueError:
            pass
        # THEN
        self.assertListEqual([
            call('value for damage_multiplier is invalid. '
                 'could not convert string to float: {}'
                 .format("'f00'")),
        ], self.error_mock.mock_calls)

    def test_bad_ban_length(self):
        # GIVEN
        self.conf.loadFromString(dedent(r"""
            [settings]
            levels: 0

            [level_0]
            kill_multiplier: 1.3
            damage_multiplier: 1.1
            ban_length:
        """))
        # WHEN
        try:
            self.p.load_config_for_levels()
            self.fail("expecting ValueError")
        except ValueError:
            pass
        # THEN
        self.assertListEqual([
            call("value for ban_length is invalid. invalid literal for int() with base 10: ''"),
        ], self.error_mock.mock_calls)


class Test_Tk_default_config(B3TestCase):

    def setUp(self):
        super(Test_Tk_default_config, self).setUp()
        self.console.gameName = 'f00'
        self.conf = CfgConfigParser()
        self.conf.load(b3.functions.getAbsolutePath('@b3/conf/plugin_tk.ini'))
        self.p = TkPlugin(self.console, self.conf)
        self.p.onLoadConfig()

    def test_settings(self):
        self.assertEqual(1000, self.p._max_points)
        self.assertEqual(1, self.p._max_level)
        self.assertEqual({
            0: (2.0, 1.0, 2),
            1: (1.0, 1.0, 2),
        }, self.p._levels)
        self.assertEqual(7, self.p._round_grace)
        self.assertEqual("sfire", self.p._issue_warning)
        self.assertTrue(self.p._grudge_enable)
        self.assertTrue(self.p._private_messages)
        self.assertEqual(100, self.p._damage_threshold)
        self.assertEqual(2, self.p._warn_level)
        self.assertEqual(0, self.p._tk_points_halflife)
        self.assertEqual('5m', self.p._tk_warn_duration)

    def test_messages(self):
        self.assertEqual("^7team damage over limit", self.p.config.get('messages', 'ban'))
        self.assertEqual("^7$vname^7 has forgiven $aname [^3$points^7]", self.p.config.get('messages', 'forgive'))
        self.assertEqual("^7$vname^7 has a ^1grudge ^7against $aname [^3$points^7]",
                         self.p.config.get('messages', 'grudged'))
        self.assertEqual("^7$vname^7 has forgiven $attackers", self.p.config.get('messages', 'forgive_many'))
        self.assertEqual(
            "^1ALERT^7: $name^7 auto-kick if not forgiven. Type ^3!forgive $cid ^7to forgive. [^3damage: $points^7]",
            self.p.config.get('messages', 'forgive_warning'))
        self.assertEqual("^7no one to forgive", self.p.config.get('messages', 'no_forgive'))
        self.assertEqual("^7Forgive who? %s", self.p.config.get('messages', 'players'))
        self.assertEqual("^7$name^7 has ^3$points^7 TK points", self.p.config.get('messages', 'forgive_info'))
        self.assertEqual("^7$name^7 cleared of ^3$points^7 TK points", self.p.config.get('messages', 'forgive_clear'))
        self.assertEqual("^3Do not attack teammates, ^1Attacked: ^7$vname ^7[^3$points^7]",
                         self.p.config.get('messages', 'tk_warning_reason'))

    def test__default_messages(self):
        conf_items = self.p.config.items('messages')
        for conf_message_id, conf_message in conf_items:
            if conf_message_id not in self.p._default_messages:
                self.fail("%s should be added to the _default_messages dict" % conf_message_id)
            if conf_message != self.p._default_messages[conf_message_id]:
                self.fail(
                    "default message in the _default_messages dict for %s does not match the message from the config file" % conf_message_id)
        for default_message_id in self.p._default_messages:
            if default_message_id not in list(zip(*conf_items))[0]:
                self.fail("%s exists in the _default_messages dict, but not in the config file" % default_message_id)
