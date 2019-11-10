import logging

from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class mixin_conf(object):

    def setUp(self):
        super(mixin_conf, self).setUp()
        self.conf = CfgConfigParser()
        self.p = PoweradminurtPlugin(self.console, self.conf)
        self.init_default_cvar()
        logger = logging.getLogger('output')
        logger.setLevel(logging.INFO)

    def test_empty_config(self):
        self.conf.loadFromString("""
[foo]
        """)
        self.p.onLoadConfig()
        # should not raise any error

    ####################################### matchmode #######################################

    def test_matchmode__plugins_disable(self):
        # empty
        self.conf.loadFromString("""
[matchmode]
plugins_disable:
        """)
        self.p.loadMatchMode()
        self.assertEqual([], self.p._match_plugin_disable)

        # one element
        self.conf.loadFromString("""
[matchmode]
plugins_disable: foo
        """)
        self.p.loadMatchMode()
        self.assertEqual(['foo'], self.p._match_plugin_disable)

        # many
        self.conf.loadFromString("""
[matchmode]
plugins_disable: foo, bar
        """)
        self.p.loadMatchMode()
        self.assertEqual(['foo', 'bar'], self.p._match_plugin_disable)


class Test_43(mixin_conf, Iourt43TestCase):
    """
    call the mixin tests using the Iourt43TestCase parent class
    """
