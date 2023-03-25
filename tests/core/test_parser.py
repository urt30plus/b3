import logging
import unittest

from b3.clients import Client
from b3.parser import Parser


class DummyParser(Parser):
    gameName = "dummy"

    def __init__(self):
        pass  # skip parent class constructor
        self.log = logging.getLogger("output")


class Test_getMessage(unittest.TestCase):
    def setUp(self):
        self.parser = DummyParser()
        self.parser._messages = {}

    def test_unknown_msg__falls_back_on_default(self):
        self.parser._messages = {}
        self.parser._messages_default = {"f00": "lorem ipsum"}
        self.assertEqual("lorem ipsum", self.parser.getMessage("f00"))

    def test_no_parameter(self):
        self.parser._messages["f00"] = "bar"
        self.assertEqual("bar", self.parser.getMessage("f00"))

    def test_with_parameter(self):
        self.parser._messages["f00"] = "bar %s"
        self.assertEqual("bar joe", self.parser.getMessage("f00", "joe"))

    def test_with_unexpected_parameter(self):
        self.parser._messages["f00"] = "bar"
        self.assertRaises(TypeError, self.parser.getMessage, "f00", "joe")

    def test_with_dict_parameter(self):
        self.parser._messages["f00"] = "bar %(p1)s"
        self.assertEqual("bar joe", self.parser.getMessage("f00", {"p1": "joe"}))

    def test_with_missing_dict_parameter(self):
        self.parser._messages["f00"] = "bar %(p1)s"
        self.assertRaises(KeyError, self.parser.getMessage, "f00", {"p2": "joe"})

    def test_with_unicode_dict_parameter(self):
        self.parser._messages["f00"] = "bar %(p1)s"
        self.assertEqual("bar joéÄ", self.parser.getMessage("f00", {"p1": "joéÄ"}))


class Test_getMessageVariables(unittest.TestCase):
    def setUp(self):
        self.parser = DummyParser()

    def assertDictIsSubset(self, subset, superset, *args):
        compare_sub = {k: superset[k] for k in subset.keys() if k in superset.keys()}
        self.assertEqual(subset, compare_sub)

    def test_with_parameters(self):
        client = Client(name="Jack")
        rv = self.parser.getMessageVariables(client)
        self.assertDictIsSubset({"name": client.name}, rv, rv)

    def test_with_named_parameters(self):
        client = Client(name="Jack")
        self.assertDictIsSubset(
            {"clientname": client.name, "reason": "this is a good reason"},
            self.parser.getMessageVariables(
                client=client, reason="this is a good reason"
            ),
        )

    def test_with_named_parameters__unicode(self):
        client = Client(name="ÄÖé")
        self.assertDictIsSubset(
            {"clientname": client.name, "reason": "this is a good reason"},
            self.parser.getMessageVariables(
                client=client, reason="this is a good reason"
            ),
        )


class Test_getWrap(unittest.TestCase):
    def setUp(self):
        self.parser = DummyParser()

    def test_wrapped_initialized(self):
        self.parser._use_color_codes = False
        self.parser._line_length = 40
        self.parser._line_color_prefix = ""
        self.assertIsNotNone(self.parser.wrapper)

    def test_with_invalid_input(self):
        self.parser._use_color_codes = False
        self.parser._line_length = 40
        self.parser._line_color_prefix = ""
        wrapped_text = self.parser.getWrap(None)
        self.assertListEqual(wrapped_text, [])

    def test_with_empty_string(self):
        self.parser._use_color_codes = False
        self.parser._line_length = 40
        self.parser._line_color_prefix = ""
        wrapped_text = self.parser.getWrap(None)
        self.assertListEqual(wrapped_text, [])

    def test_no_color_codes(self):
        self.parser._use_color_codes = False
        self.parser._line_length = 40
        self.parser._line_color_prefix = ""
        wrapped_text = self.parser.getWrap(
            "Lorem ipsum dolor sit amet, consectetur adipisci elit, sed eiusmod tempor incidunt ut labore et dolore magna aliqua."
        )
        self.assertIsInstance(wrapped_text, list)
        self.assertListEqual(
            wrapped_text,
            [
                "Lorem ipsum dolor sit amet, consectetur",
                ">adipisci elit, sed eiusmod tempor",
                ">incidunt ut labore et dolore magna",
                ">aliqua.",
            ],
        )

    def test_no_color_codes_with_color_prefix_set(self):
        self.parser._use_color_codes = False
        self.parser._line_length = 40
        self.parser._line_color_prefix = "^5"
        wrapped_text = self.parser.getWrap(
            "Lorem ipsum dolor sit amet, consectetur adipisci elit, sed eiusmod tempor incidunt ut labore et dolore magna aliqua."
        )
        self.assertIsInstance(wrapped_text, list)
        self.assertListEqual(
            wrapped_text,
            [
                "Lorem ipsum dolor sit amet, consectetur",
                ">adipisci elit, sed eiusmod tempor",
                ">incidunt ut labore et dolore magna",
                ">aliqua.",
            ],
        )

    def test_with_color_codes_and_color_prefix(self):
        self.parser._use_color_codes = True
        self.parser._line_length = 40
        self.parser._line_color_prefix = "^7"
        wrapped_text = self.parser.getWrap(
            "Lorem ipsum dolor sit ^2amet, consectetur adipisci elit, ^1sed eiusmod ^7tempor incidunt ut ^8labore et dolore magna ^2aliqua."
        )
        self.assertIsInstance(wrapped_text, list)
        self.assertListEqual(
            wrapped_text,
            [
                "^7Lorem ipsum dolor sit ^2amet,",
                "^3>^2consectetur adipisci elit, ^1sed eiusmod",
                "^3>^1^7tempor incidunt ut ^8labore et dolore",
                "^3>^8magna ^2aliqua.",
            ],
        )

    def test_with_color_codes_and_no_color_prefix(self):
        self.parser._use_color_codes = True
        self.parser._line_length = 40
        self.parser._line_color_prefix = ""
        wrapped_text = self.parser.getWrap(
            "Lorem ipsum dolor sit ^2amet, consectetur adipisci elit, ^1sed eiusmod ^7tempor incidunt ut ^8labore et dolore magna ^2aliqua."
        )
        self.assertIsInstance(wrapped_text, list)
        self.assertListEqual(
            wrapped_text,
            [
                "Lorem ipsum dolor sit ^2amet,",
                "^3>^2consectetur adipisci elit, ^1sed eiusmod",
                "^3>^1^7tempor incidunt ut ^8labore et dolore",
                "^3>^8magna ^2aliqua.",
            ],
        )

    def test_with_short_message_length(self):
        self.parser._use_color_codes = False
        self.parser._line_length = 40
        self.parser._line_color_prefix = ""
        wrapped_text = self.parser.getWrap("Lorem ipsum dolor sit amet")
        self.assertIsInstance(wrapped_text, list)
        self.assertListEqual(wrapped_text, ["Lorem ipsum dolor sit amet"])


if __name__ == "__main__":
    unittest.main()
