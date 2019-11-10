from mock import patch, call, Mock
from mockito import when, any as ANY

from b3.fake import FakeClient
from tests.plugins.adv import AdvTestCase


class Test_keywords(AdvTestCase):

    def setUp(self):
        AdvTestCase.setUp(self)
        self.init_plugin()

    def test_admins(self):
        # GIVEN
        when(self.p._msg).getnext().thenReturn("@admins")
        joe = FakeClient(self.console, name="Joe", guid="joeguid", groupBits=128)
        when(self.p._admin_plugin).getAdmins().thenReturn([joe])
        with patch.object(self.console, "say") as say_mock:
            # WHEN
            self.p.adv()
        # THEN
        say_mock.assert_has_calls([call('^7Admins online: Joe^7^7 [^3100^7]')])

    def test_regulars(self):
        # GIVEN
        when(self.p._msg).getnext().thenReturn("@regulars")
        joe = FakeClient(self.console, name="Joe", guid="joeguid", groupBits=2)
        when(self.p._admin_plugin).getRegulars().thenReturn([joe])
        with patch.object(self.console, "say") as say_mock:
            # WHEN
            self.p.adv()
        # THEN
        say_mock.assert_has_calls([call('^7Regular players online: Joe^7')])

    def test_topstats(self):
        when(self.p._msg).getnext().thenReturn("@topstats")
        self.p._xlrstats_plugin = Mock()
        with patch.object(self.p._xlrstats_plugin, "cmd_xlrtopstats") as xlrtopstats_mock:
            self.p.adv()
            xlrtopstats_mock.assert_has_calls([call(ext=True, cmd=None, data='3', client=None)])

    def test_time(self):
        when(self.p._msg).getnext().thenReturn("@time")
        when(self.console).formatTime(ANY()).thenReturn("f00")
        with patch.object(self.console, "say") as say_mock:
            self.p.adv()
            say_mock.assert_has_calls([call('^2Time: ^3f00')])

    def test_nextmap(self):
        when(self.p._msg).getnext().thenReturn("@nextmap")
        when(self.console).getNextMap().thenReturn("f00")
        with patch.object(self.console, "say") as say_mock:
            self.p.adv()
            say_mock.assert_has_calls([call('^2Next map: ^3f00')])
