from types import MethodType
from unittest.mock import Mock

from mockito import when

from b3.events import Event
from b3.functions import getAbsolutePath
from tests.fake import FakeClient
from tests.plugins.spamcontrol import SpamcontrolTestCase


class Test_game_specific_spam(SpamcontrolTestCase):

    def setUp(self):
        SpamcontrolTestCase.setUp(self)

        with open(getAbsolutePath('@b3/conf/plugin_spamcontrol.ini')) as default_conf:
            self.init_plugin(default_conf.read())

        self.joe = FakeClient(self.console, name="Joe", exactName="Joe", guid="zaerezarezar", groupBits=1)
        self.joe.connects("1")

        # let's say our game has a new event : EVT_CLIENT_RADIO
        EVT_CLIENT_RADIO = self.console.Events.createEvent('EVT_CLIENT_RADIO', 'Event client radio')

        # teach the Spamcontrol plugin how to react on such events
        def onRadio(this, event):
            new_event = Event(type=event.type, client=event.client, target=event.target, data=event.data['text'])
            this.onChat(new_event)

        self.p.onRadio = MethodType(onRadio, self.p)
        self.p.registerEvent('EVT_CLIENT_RADIO', self.p.onRadio)

        # patch joe to make him able to send radio messages
        def radios(me, text):
            me.console.queueEvent(Event(type=EVT_CLIENT_RADIO, client=me, data={'text': text}))

        self.joe.radios = MethodType(radios, self.joe)

    def test_radio_spam(self):
        when(self.p).getTime().thenReturn(0)
        self.joe.warn = Mock()
        self.joe.says("doh 1")
        self.joe.radios("doh 2")
        self.joe.says("doh 3")
        self.joe.radios("doh 4")
        self.joe.says("doh 5")
        self.assertEqual(1, self.joe.warn.call_count)
