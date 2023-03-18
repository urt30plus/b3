from . import FlagstatsPluginTestCase


class Test_events(FlagstatsPluginTestCase):
    def test_first_kill(self):
        self.console.queueEvent(
            self.console.getEvent(
                "EVT_CLIENT_ACTION",
                client=self.mike,
                target=self.bill,
                data="flag_carrier_kill",
            )
        )
        self.assertEqual(self.mike.var(self.p, "flagcarrierkill").value, 1)
