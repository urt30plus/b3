from unittest.mock import Mock

from tests.plugins.admin import Admin_functional_test, Admin_TestCase


class Test_parseUserCmd(Admin_TestCase):
    def setUp(self):
        Admin_TestCase.setUp(self)
        self.init()

    def test_clientinfo_bad_arg(self):
        with self.assertRaises(Exception):  # noqa: B017
            self.p.parseUserCmd(None)

    def test_clientinfo_empty_arg(self):
        self.assertIsNone(self.p.parseUserCmd(""))

    def test_clientinfo_only_1_arg(self):
        self.assertEqual(("someone", None), self.p.parseUserCmd("someone"))
        # see https://github.com/xlr8or/big-brother-bot/issues/54
        self.assertIsNone(self.p.parseUserCmd("someone", req=True))

    def test_clientinfo_2_args(self):
        self.assertEqual(("someone", "param1"), self.p.parseUserCmd("someone param1"))
        self.assertEqual(
            ("someone", "param1"), self.p.parseUserCmd("someone param1", req=True)
        )

    def test_clientinfo_3_args(self):
        self.assertEqual(
            ("someone", "param1 param2"), self.p.parseUserCmd("someone param1 param2")
        )
        self.assertEqual(
            ("someone", "param1 param2"),
            self.p.parseUserCmd("someone param1 param2", req=True),
        )

    def test_clientinfo_int(self):
        self.assertEqual(("45", None), self.p.parseUserCmd("45"))
        self.assertEqual(("45", None), self.p.parseUserCmd("'45'"))
        self.assertEqual(("45", "some param"), self.p.parseUserCmd("'45' some param"))


class Test_getGroupLevel(Admin_TestCase):
    def setUp(self):
        Admin_TestCase.setUp(self)
        self.init()

    def test_nominal(self):
        for test_data, expected in {
            "NONE": "none",
            "0": 0,
            "1": 1,
            "guest": 0,
            "user": 1,
            "reg": 2,
            "mod": 20,
            "admin": 40,
            "fulladmin": 60,
            "senioradmin": 80,
            "superadmin": 100,
            "1-20": "1-20",
            "40-20": "40-20",
            "user-admin": "1-40",
        }.items():
            result = self.p.getGroupLevel(test_data)
            if expected != result:
                self.fail(f"{test_data!r}, expecting {expected!r} but got {result!r}")

    def test_failures(self):
        self.p.error = Mock()
        for test_data in ("foo", "mod-foo", "foo-mod"):
            self.assertFalse(self.p.getGroupLevel(test_data))
            assert self.p.error.called


class Test_spell_checker(Admin_functional_test):
    def setUp(self):
        Admin_functional_test.setUp(self)
        self.init()
        self.joe.connects(0)

    def test_existing_command(self):
        self.joe.says("!map")
        self.assertEqual(
            ["You must supply a map to change to"], self.joe.message_history
        )

    def test_misspelled_command(self):
        self.joe.says("!mip")
        self.assertEqual(
            ["Unrecognized command mip. Did you mean !map?"], self.joe.message_history
        )

    def test_unrecognized_command(self):
        self.joe.says("!qfsmlkjazemlrkjazemrlkj")
        self.assertEqual(
            ["Unrecognized command qfsmlkjazemlrkjazemrlkj"], self.joe.message_history
        )

    def test_existing_command_loud(self):
        self.joe.says("@map")
        self.assertEqual(
            ["You must supply a map to change to"], self.joe.message_history
        )

    def test_misspelled_command_loud(self):
        self.joe.says("@mip")
        self.assertEqual(
            ["Unrecognized command mip. Did you mean @map?"], self.joe.message_history
        )

    def test_unrecognized_command_loud(self):
        self.joe.says("@qfsmlkjazemlrkjazemrlkj")
        self.assertEqual(
            ["Unrecognized command qfsmlkjazemlrkjazemrlkj"], self.joe.message_history
        )

    def test_existing_command_private(self):
        self.joe.says("/map")
        self.assertEqual(
            ["You must supply a map to change to"], self.joe.message_history
        )

    def test_misspelled_command_private(self):
        self.joe.says("/mip")
        self.assertEqual(
            ["Unrecognized command mip. Did you mean /map?"], self.joe.message_history
        )

    def test_unrecognized_command_private(self):
        self.joe.says("/qfsmlkjazemlrkjazemrlkj")
        self.assertEqual(
            ["Unrecognized command qfsmlkjazemlrkjazemrlkj"], self.joe.message_history
        )
