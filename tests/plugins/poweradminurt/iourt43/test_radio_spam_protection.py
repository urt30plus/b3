import sys
from unittest.mock import Mock, call

from mockito import when

from b3.config import CfgConfigParser
from b3.plugins.poweradminurt import PoweradminurtPlugin
from tests.plugins.poweradminurt.iourt43 import Iourt43TestCase


class Test_radio_spam_protection(Iourt43TestCase):
    def setUp(self):
        super().setUp()
        self.conf = CfgConfigParser()
        self.p = PoweradminurtPlugin(self.console, self.conf)
        self.init_default_cvar()

    def init(self, config_content=None):
        if config_content:
            self.conf.loadFromString(config_content)
        else:
            self.conf.loadFromString(
                """
[radio_spam_protection]
enable: True
mute_duration: 2
        """
            )
        self.p.onLoadConfig()
        self.p.onStartup()

    def test_conf_nominal(self):
        self.init(
            """
[radio_spam_protection]
enable: True
mute_duration: 2
        """
        )
        self.assertTrue(self.p._rsp_enable)
        self.assertEqual(2, self.p._rsp_mute_duration)

    def test_conf_nominal_2(self):
        self.init(
            """
[radio_spam_protection]
enable: no
mute_duration: 1
        """
        )
        self.assertFalse(self.p._rsp_enable)
        self.assertEqual(1, self.p._rsp_mute_duration)

    def test_conf_broken(self):
        self.init(
            """
[radio_spam_protection]
enable: f00
mute_duration: 0
        """
        )
        self.assertFalse(self.p._rsp_enable)
        self.assertEqual(1, self.p._rsp_mute_duration)

    def test_spam(self):
        # GIVEN
        self.init(
            """
[radio_spam_protection]
enable: True
mute_duration: 2
"""
        )
        self.joe.connects("0")
        self.console.write = Mock(wraps=lambda x: sys.stderr.write("%s\n" % x))
        self.joe.warn = Mock()

        def joe_radio(msg_group, msg_id, location, text):
            self.console.parseLine(
                '''Radio: 0 - %s - %s - "%s" - "%s"'''
                % (msg_group, msg_id, location, text)
            )

        def assertSpampoints(points):
            self.assertEqual(points, self.joe.var(self.p, "radio_spamins", 0).value)

        assertSpampoints(0)

        # WHEN
        when(self.p).getTime().thenReturn(0)
        joe_radio(3, 3, "Patio Courtyard", "Requesting medic. Status: healthy")
        # THEN
        assertSpampoints(0)
        self.assertEqual(0, self.joe.warn.call_count)
        self.assertEqual(0, self.console.write.call_count)

        # WHEN
        when(self.p).getTime().thenReturn(0)
        joe_radio(3, 3, "Patio Courtyard", "Requesting medic. Status: healthy")
        # THEN
        assertSpampoints(8)
        self.assertEqual(0, self.joe.warn.call_count)
        self.assertEqual(0, self.console.write.call_count)

        # WHEN
        when(self.p).getTime().thenReturn(1)
        joe_radio(3, 1, "Patio Courtyard", "f00")
        # THEN
        assertSpampoints(5)
        self.assertEqual(0, self.joe.warn.call_count)
        self.console.write.assert_has_calls([call("mute 0 2")])

    def test_spam_with_maxlevel(self):
        # GIVEN a config with maxlevel set at moderator
        self.init(
            """
[radio_spam_protection]
enable: True
mute_duration: 2
maxlevel: mod
"""
        )
        self.moderator.connects("0")
        self.console.write = Mock(wraps=lambda x: sys.stderr.write("%s\n" % x))
        self.moderator.warn = Mock()

        def moderator_radio(msg_group, msg_id, location, text):
            self.console.parseLine(
                '''Radio: 0 - %s - %s - "%s" - "%s"'''
                % (msg_group, msg_id, location, text)
            )

        def assertSpampoints(points):
            self.assertEqual(
                points, self.moderator.var(self.p, "radio_spamins", 0).value
            )

        assertSpampoints(0)

        # WHEN the moderator spams messages
        when(self.p).getTime().thenReturn(0)
        moderator_radio(3, 1, "Patio Courtyard", "Requesting medic. Status: healthy")
        moderator_radio(3, 1, "Patio Courtyard", "Requesting medic. Status: healthy")
        moderator_radio(3, 1, "Patio Courtyard", "Requesting medic. Status: healthy")

        # THEN the moderator is not warned
        assertSpampoints(0)
        self.assertEqual(0, self.moderator.warn.call_count)
        self.console.write.assert_has_calls([])

        # THEN WHEN we set the maxlevel about moderator
        self.init(
            """
[radio_spam_protection]
enable: True
mute_duration: 2
maxlevel: fulladmin
"""
        )

        # AND we spam again
        moderator_radio(3, 1, "Patio Courtyard", "Requesting medic. Status: healthy")
        moderator_radio(3, 1, "Patio Courtyard", "Requesting medic. Status: healthy")
        moderator_radio(3, 1, "Patio Courtyard", "Requesting medic. Status: healthy")

        # THEN this time the moderator is warned for spamming
        assertSpampoints(5)
        self.assertEqual(0, self.moderator.warn.call_count)
        self.console.write.assert_has_calls([call("mute 0 2")])
