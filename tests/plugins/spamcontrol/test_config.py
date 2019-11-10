from textwrap import dedent

import b3
from tests.plugins.spamcontrol import SpamcontrolTestCase


class Test_config(SpamcontrolTestCase):
    """
    Test different config are correctly loaded.
    """
    default_max_spamins = 10
    default_mod_level = 20
    default_falloff_rate = 6.5

    def test_default_conf(self):
        with open(b3.getAbsolutePath('@b3/conf/plugin_spamcontrol.ini')) as default_conf:
            self.init_plugin(default_conf.read())
        self.assertEqual(self.default_max_spamins, self.p._maxSpamins)
        self.assertEqual(self.default_mod_level, self.p._modLevel)
        self.assertEqual(self.default_falloff_rate, self.p._falloffRate)

    def test_emtpy_conf(self):
        self.init_plugin(r"""
        """)
        self.assertEqual(self.default_max_spamins, self.p._maxSpamins)
        self.assertEqual(self.default_mod_level, self.p._modLevel)
        self.assertEqual(self.default_falloff_rate, self.p._falloffRate)

    def test_max_spamins_empty(self):
        self.init_plugin(dedent("""
            [settings]
            max_spamins:
        """))
        self.assertEqual(self.default_max_spamins, self.p._maxSpamins)

    def test_max_spamins_NaN(self):
        self.init_plugin(dedent("""
            [settings]
            max_spamins: fo0
        """))
        self.assertEqual(self.default_max_spamins, self.p._maxSpamins)

    def test_max_spamins_negative(self):
        self.init_plugin(dedent("""
            [settings]
            max_spamins: -15
        """))
        self.assertEqual(0, self.p._maxSpamins)

    def test_mod_level_empty(self):
        self.init_plugin(dedent("""
            [settings]
            mod_level:
        """))
        self.assertEqual(0, self.p._modLevel)

    def test_mod_level_NaN(self):
        self.init_plugin(dedent("""
            [settings]
            mod_level: fo0
        """))
        self.assertEqual(self.default_mod_level, self.p._modLevel)

    def test_mod_level_nominal(self):
        self.init_plugin(dedent("""
            [settings]
            mod_level: 60
        """))
        self.assertEqual(60, self.p._modLevel)

    def test_mod_level_by_group_keyword(self):
        self.init_plugin(dedent("""
            [settings]
            mod_level: senioradmin
        """))
        self.assertEqual(80, self.p._modLevel)
