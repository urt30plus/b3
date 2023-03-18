from unittest.mock import patch, call, Mock

from mockito import when, any as ANY

from tests.fake import FakeClient
from tests.plugins.adv import AdvTestCase


class Test_keywords(AdvTestCase):
    def setUp(self):
        AdvTestCase.setUp(self)
        self.init_plugin()

    def test_admins(self):
        # GIVEN
        joe = FakeClient(self.console, name="Joe", guid="joeguid", groupBits=128)
        joe.connects(0)
        when(self.p.admin_plugin).getAdmins().thenReturn([joe])
        with patch.object(self.console, "say") as say_mock:
            # WHEN
            self.p.print_ad("@admins")
        # THEN
        say_mock.assert_has_calls([call("^7Admins online: Joe^7^7 [^3100^7]")])

    def test_regulars(self):
        # GIVEN
        joe = FakeClient(self.console, name="Joe", guid="joeguid", groupBits=2)
        joe.connects(0)
        when(self.p.admin_plugin).getRegulars().thenReturn([joe])
        with patch.object(self.console, "say") as say_mock:
            # WHEN
            self.p.print_ad("@regulars")
        # THEN
        say_mock.assert_has_calls([call("^7Regular players online: Joe^7")])

    def test_time(self):
        when(self.console).formatTime(ANY()).thenReturn("f00")
        joe = FakeClient(self.console, name="Joe", guid="joeguid", groupBits=128)
        joe.connects(0)
        with patch.object(self.console, "say") as say_mock:
            # WHEN
            self.p.print_ad("@time")
        # THEN
        say_mock.assert_has_calls([call("^2Time: ^3f00")])

    def test_nextmap(self):
        when(self.console).getNextMap().thenReturn("f00")
        joe = FakeClient(self.console, name="Joe", guid="joeguid", groupBits=128)
        joe.connects(0)
        with patch.object(self.console, "say") as say_mock:
            # WHEN
            self.p.print_ad("@nextmap")
        # THEN
        say_mock.assert_has_calls([call("^2Next map: ^3f00")])
