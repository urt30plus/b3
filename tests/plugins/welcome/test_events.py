from unittest.mock import call, patch

from b3.plugins.welcome import (
    F_ANNOUNCE_FIRST,
    F_ANNOUNCE_USER,
    F_CUSTOM_GREETING,
    F_FIRST,
    F_NEWB,
    F_USER,
)
from tests.fake import FakeClient
from tests.plugins.welcome import Welcome_functional_test


class Test_welcome(Welcome_functional_test):
    def setUp(self):
        Welcome_functional_test.setUp(self)
        self.load_config()
        # disabled event handling (spawns threads and is of no use for that test)
        self.p.onEvent = lambda *args, **kwargs: None

        self.client = FakeClient(console=self.console, name="Jack", guid="JackGUID")
        self.client._connections = 0
        self.client.greeting = "hi everyone :)"
        self.client.connects("0")
        self.superadmin.connects("1")

        self.say_patcher = patch.object(self.console, "say")
        self.say_mock = self.say_patcher.start()

    def tearDown(self):
        Welcome_functional_test.tearDown(self)
        self.say_patcher.stop()

    def Test_get_client_info(self):
        self.parser_conf.add_section("b3")
        self.parser_conf.set("b3", "time_zone", "UTC")
        self.parser_conf.set("b3", "time_format", "%I:%M%p %Z %m/%d/%y")
        self.assertDictEqual(
            {
                "connections": "1",
                "group": "Super Admin",
                "id": "2",
                "lastVisit": "Unknown",
                "level": "100",
                "name": "SuperAdmin^7",
            },
            self.p.get_client_info(self.superadmin),
        )
        # WHEN
        self.superadmin.lastVisit = 1364821993
        self.superadmin._connections = 2
        # THEN
        self.assertDictEqual(
            {
                "connections": "2",
                "group": "Super Admin",
                "id": "2",
                "lastVisit": "02:13PM CET 04/01/13",
                "level": "100",
                "name": "SuperAdmin^7",
            },
            self.p.get_client_info(self.superadmin),
        )
        # WHEN
        self.superadmin.says("!mask mod")
        # THEN
        self.assertDictEqual(
            {
                "connections": "2",
                "group": "Moderator",
                "id": "2",
                "lastVisit": "02:13PM CET 04/01/13",
                "level": "20",
                "name": "SuperAdmin^7",
            },
            self.p.get_client_info(self.superadmin),
        )

    def test_0(self):
        # GIVEN
        self.p._welcomeFlags = 0
        # WHEN
        self.p.welcome(self.superadmin)
        # THEN
        self.assertListEqual([], self.say_mock.mock_calls)
        self.assertListEqual([], self.superadmin.message_history)

    def test_first(self):
        # GIVEN
        self.client._connections = 0
        self.p._welcomeFlags = F_FIRST
        # WHEN
        self.p.welcome(self.client)
        # THEN
        self.assertListEqual([], self.say_mock.mock_calls)
        self.assertListEqual(
            [
                "Welcome Jack, this must be your first visit, you are player #1. Type !help for "
                "help"
            ],
            self.client.message_history,
        )

    def test_newb(self):
        # GIVEN
        self.client._connections = 2
        self.p._welcomeFlags = F_NEWB
        # WHEN
        self.p.welcome(self.client)
        # THEN
        self.assertListEqual([], self.say_mock.mock_calls)
        self.assertListEqual(
            [
                "[Authed] Welcome back Jack [@1], last visit Unknown. Type !register in chat to register."
                " Type !help for help"
            ],
            self.client.message_history,
        )

    def test_user(self):
        # GIVEN
        self.client._connections = 2
        self.p._welcomeFlags = F_USER
        self.client.says("!register")
        self.client.clearMessageHistory()
        # WHEN
        self.p.welcome(self.client)
        # THEN
        self.assertListEqual(
            [call("^7Jack^7 ^7put in group User")], self.say_mock.mock_calls
        )
        self.assertListEqual(
            [
                "[Authed] Welcome back Jack [@1], last visit Unknown, you're a User, played 2 times"
            ],
            self.client.message_history,
        )

    def test_announce_first(self):
        # GIVEN
        self.client._connections = 0
        self.p._welcomeFlags = F_ANNOUNCE_FIRST
        # WHEN
        self.p.welcome(self.client)
        # THEN
        self.assertListEqual(
            [call("^7Everyone welcome Jack^7^7, player number ^3#1^7, to the server")],
            self.say_mock.mock_calls,
        )
        self.assertListEqual([], self.client.message_history)

    def test_announce_user(self):
        # GIVEN
        self.client._connections = 2
        self.p._welcomeFlags = F_ANNOUNCE_USER
        self.client.says("!register")
        self.client.clearMessageHistory()
        # WHEN
        self.p.welcome(self.client)
        # THEN
        self.assertListEqual(
            [
                call("^7Jack^7 ^7put in group User"),
                call(
                    "^7Everyone welcome back Jack^7^7, player number ^3#1^7, to the server, played 2 "
                    "times"
                ),
            ],
            self.say_mock.mock_calls,
        )
        self.assertListEqual([], self.client.message_history)

    def test_custom_greeting(self):
        # GIVEN
        self.client._connections = 2
        self.p._welcomeFlags = F_CUSTOM_GREETING
        self.client.says("!register")
        self.client.clearMessageHistory()
        # WHEN
        self.p.welcome(self.client)
        # THEN
        self.assertListEqual(
            [
                call("^7Jack^7 ^7put in group User"),
                call("^7Jack^7^7 joined: hi everyone :)"),
            ],
            self.say_mock.mock_calls,
        )
        self.assertListEqual([], self.client.message_history)
