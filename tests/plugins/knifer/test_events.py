from . import KniferPluginTestCase


class Test_events(KniferPluginTestCase):

    def test_first_kill(self):
        self.console.queueEvent(self.console.getEvent('EVT_CLIENT_KILL',
                                                      client=self.mike,
                                                      target=self.bill,
                                                      data=(100, self.console.UT_MOD_KNIFE)))
        self.assertDictEqual(self.p._killers, {self.mike.cid: self.mike})
