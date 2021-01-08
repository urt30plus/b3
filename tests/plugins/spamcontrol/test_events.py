from mockito import when, unstub

import b3
from b3.plugins.admin import AdminPlugin
from tests.fake import FakeClient
from tests.plugins.spamcontrol import SpamcontrolTestCase


class Test_plugin(SpamcontrolTestCase):

    def setUp(self):
        SpamcontrolTestCase.setUp(self)

        self.adminPlugin = AdminPlugin(self.console, '@b3/conf/plugin_admin.ini')
        when(self.console).getPlugin("admin").thenReturn(self.adminPlugin)
        self.adminPlugin.onLoadConfig()
        self.adminPlugin.onStartup()

        with open(b3.functions.getAbsolutePath('@b3/conf/plugin_spamcontrol.ini')) as default_conf:
            self.init_plugin(default_conf.read())

        self.joe = FakeClient(self.console, name="Joe", guid="zaerezarezar", groupBits=1)
        self.joe.connects("1")

        self.superadmin = FakeClient(self.console, name="Superadmin", guid="superadmin_guid", groupBits=128)
        self.superadmin.connects("2")

    def assertSpaminsPoints(self, client, points):
        actual = client.var(self.p, 'spamins', 0).value
        self.assertEqual(points, actual, "expecting %s to have %s spamins points" % (client.name, points))

    def test_say(self):
        when(self.p).getTime().thenReturn(0).thenReturn(1).thenReturn(20).thenReturn(120)

        self.assertSpaminsPoints(self.joe, 0)

        self.joe.says("doh")  # 0s
        self.assertSpaminsPoints(self.joe, 2)

        self.joe.says("foo")  # 1s
        self.assertSpaminsPoints(self.joe, 4)

        self.joe.says("bar")  # 20s
        self.assertSpaminsPoints(self.joe, 3)

        self.joe.says("hi")  # 120s
        self.assertSpaminsPoints(self.joe, 0)
