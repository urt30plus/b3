from unittest.mock import Mock, call

from tests.plugins.spree import SpreeTestCase


class Test_events(SpreeTestCase):
    def test_killing_spree_start_with_5_kills(self):
        # GIVEN
        self.init()
        self.console.say = Mock()
        self.bill.connects("1")
        self.mike.connects("2")
        # WHEN
        for x in range(5):
            self.console.queueEvent(
                self.console.getEvent(
                    "EVT_CLIENT_KILL", client=self.bill, target=self.mike
                )
            )
        # THEN
        self.console.say.assert_called_with(
            "Bill is on a killing spree (5 kills in a row)"
        )

    def test_killing_spree_end_with_5_kills(self):
        # GIVEN
        self.init()
        self.console.say = Mock()
        self.bill.connects("1")
        self.mike.connects("2")
        # WHEN
        for x in range(5):
            self.console.queueEvent(
                self.console.getEvent(
                    "EVT_CLIENT_KILL", client=self.bill, target=self.mike
                )
            )
        self.console.queueEvent(
            self.console.getEvent("EVT_CLIENT_KILL", client=self.mike, target=self.bill)
        )
        # THEN
        self.console.say.assert_has_calls(
            [
                call("Bill is on a killing spree (5 kills in a row)"),
                call("Mike stopped the spree of Bill"),
            ]
        )

    def test_killing_spree_start_with_10_kills(self):
        # GIVEN
        self.init()
        self.console.say = Mock()
        self.bill.connects("1")
        self.mike.connects("2")
        # WHEN
        for x in range(10):
            self.console.queueEvent(
                self.console.getEvent(
                    "EVT_CLIENT_KILL", client=self.bill, target=self.mike
                )
            )
        # THEN
        self.console.say.assert_called_with("Bill is on fire! (10 kills in a row)")

    def test_killing_spree_end_with_10_kills(self):
        # GIVEN
        self.init()
        self.console.say = Mock()
        self.bill.connects("1")
        self.mike.connects("2")
        # WHEN
        for x in range(10):
            self.console.queueEvent(
                self.console.getEvent(
                    "EVT_CLIENT_KILL", client=self.bill, target=self.mike
                )
            )
        self.console.queueEvent(
            self.console.getEvent("EVT_CLIENT_KILL", client=self.mike, target=self.bill)
        )
        # THEN
        self.console.say.assert_has_calls(
            [call("Bill is on fire! (10 kills in a row)"), call("Mike iced Bill")],
            any_order=True,
        )

    def test_losing_spree_start_with_12_kills(self):
        # GIVEN
        self.init()
        self.console.say = Mock()
        self.bill.connects("1")
        self.mike.connects("2")
        # WHEN
        for x in range(12):
            self.console.queueEvent(
                self.console.getEvent(
                    "EVT_CLIENT_KILL", client=self.bill, target=self.mike
                )
            )
        # THEN
        self.console.say.assert_has_calls(
            [
                call("Bill is on fire! (10 kills in a row)"),
                call("Keep it up Mike, it will come eventually"),
            ]
        )

    def test_losing_spree_end_with_12_kills(self):
        # GIVEN
        self.init()
        self.console.say = Mock()
        self.bill.connects("1")
        self.mike.connects("2")
        # WHEN
        for x in range(12):
            self.console.queueEvent(
                self.console.getEvent(
                    "EVT_CLIENT_KILL", client=self.bill, target=self.mike
                )
            )
        self.console.queueEvent(
            self.console.getEvent("EVT_CLIENT_KILL", client=self.mike, target=self.bill)
        )
        # THEN
        self.console.say.assert_has_calls(
            [
                call("Bill is on fire! (10 kills in a row)"),
                call("Keep it up Mike, it will come eventually"),
                call("You're back in business Mike"),
                call("Mike iced Bill"),
            ]
        )
