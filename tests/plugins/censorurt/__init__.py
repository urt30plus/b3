import logging

from mock import Mock, patch

import b3
import b3.events
from b3.config import XmlConfigParser
from b3.fake import FakeClient
from b3.plugins.censorurt import CensorurtPlugin
from tests import B3TestCase


class CensorurtTestCase(B3TestCase):
    """
    Ease testcases that need an working B3 console and need to control the censorurt plugin config
    """

    def setUp(self):
        # Timer needs to be patched or the Censor plugin would schedule a 2nd check one minute after
        # penalizing a player.
        self.timer_patcher = patch('threading.Timer')
        self.timer_patcher.start()

        self.log = logging.getLogger('output')
        self.log.propagate = False

        B3TestCase.setUp(self)
        self.console.startup()
        self.log.propagate = True

        self.joe = FakeClient(self.console, name="Joe", exactName="Joe", guid="zaerezarezar", groupBits=1,
                              team=b3.TEAM_UNKNOWN)

        self.conf = XmlConfigParser()
        self.p = CensorurtPlugin(self.console, self.conf)

    def tearDown(self):
        B3TestCase.tearDown(self)
        self.timer_patcher.stop()

    def init_plugin(self, config_content):
        self.conf.setXml(config_content)
        self.log.setLevel(logging.DEBUG)
        self.log.info("============================= Censor plugin: loading config ============================")
        self.p.onLoadConfig()
        self.log.info("============================= Censor plugin: starting  =================================")
        self.p.onStartup()


class Detection_TestCase(CensorurtTestCase):
    """
    Base class for TestCase that verify bad words and bad names are correctly detected.
    """

    def setUp(self):
        CensorurtTestCase.setUp(self)
        self.init_plugin(r"""
            <configuration>
                <badwords>
                    <penalty type="warning" reasonkeyword="racist"/>
                </badwords>
                <badnames>
                    <penalty type="warning" reasonkeyword="badname"/>
                </badnames>
            </configuration>
        """)

    def assert_name_penalized_count(self, name, count):
        self.p.penalizeClientBadname = Mock()

        mock_client = Mock()
        mock_client.connected = True
        mock_client.exactName = name

        self.p.checkBadName(mock_client)
        self.assertEquals(count, self.p.penalizeClientBadname.call_count,
                          "name '%s' should have been penalized %s time" % (name, count))

    def assert_name_is_penalized(self, name):
        self.assert_name_penalized_count(name, 1)

    def assert_name_is_not_penalized(self, name):
        self.assert_name_penalized_count(name, 0)

    def assert_chat_is_penalized(self, text):
        self.p.penalizeClient = Mock()
        mock_client = Mock()
        mock_client.connected = True

        try:
            self.p.checkBadWord(text, mock_client)
            self.fail("text [%s] should have raised a VetoEvent" % text)
        except b3.events.VetoEvent as e:
            self.assertEquals(1, self.p.penalizeClient.call_count, "text [%s] should have been penalized" % text)
            return self.p.penalizeClient.call_args[0] if len(self.p.penalizeClient.call_args) else None

    def assert_chat_is_not_penalized(self, text):
        self.p.penalizeClient = Mock()

        mock_client = Mock()
        mock_client.connected = True

        try:
            self.p.checkBadWord(text, mock_client)
        except b3.events.VetoEvent as e:
            self.fail("text [%s] should not have raised a VetoEvent" % text)
        else:
            self.assertEquals(0, self.p.penalizeClient.call_count, "text [%s] should not have been penalized" % text)
