from tests.fake import FakeClient
from tests.plugins.adv import AdvTestCase


class Test_commands(AdvTestCase):

    def setUp(self):
        AdvTestCase.setUp(self)
        self.joe = FakeClient(self.console, name="Joe", guid="joeguid", groupBits=128)

    def test_advlist_empty(self):
        self.init_plugin("""
            [settings]
            rate: 3
        """)
        self.joe.clearMessageHistory()
        self.p.cmd_advlist(data=None, client=self.joe)
        self.assertEqual([], self.p.ad_list)
        self.assertEqual(['Adv: no ads loaded'], self.joe.message_history)

    def test_advlist_one_item(self):
        self.init_plugin("""
            [settings]
            rate: 3

            [messages]
            ad1: f00
        """)
        self.joe.clearMessageHistory()
        self.p.cmd_advlist(data=None, client=self.joe)
        self.assertEqual(['f00'], self.p.ad_list)
        self.assertEqual(['Adv: [1] f00'], self.joe.message_history)

    def test_advlist_many_items(self):
        self.init_plugin("""
            [settings]
            rate: 3

            [messages]
            ad1: f00
            ad2: bar
            ad3: test
        """)
        self.joe.clearMessageHistory()
        self.p.cmd_advlist(data=None, client=self.joe)
        self.assertEqual(['f00', 'bar', 'test'], self.p.ad_list)
        self.assertEqual(['Adv: [1] f00', 'Adv: [2] bar', 'Adv: [3] test'], self.joe.message_history)

    def test_advrate_no_arg_3min(self):
        self.init_plugin("""
            [settings]
            rate: 3

            [messages]
            ad1: f00
            ad2: bar
            ad3: test
        """)
        self.joe.clearMessageHistory()
        self.p.cmd_advrate(data='', client=self.joe)
        self.assertEqual('3', self.p._rate)
        self.assertEqual(['Current rate is every 3 minutes'], self.joe.message_history)

    def test_advrate_no_arg_2min(self):
        self.init_plugin("""
            [settings]
            rate: 2

            [messages]
            ad1: f00
            ad2: bar
            ad3: test
        """)
        self.joe.clearMessageHistory()
        self.p.cmd_advrate(data=None, client=self.joe)
        self.assertEqual('2', self.p._rate)
        self.assertEqual(['Current rate is every 2 minutes'], self.joe.message_history)

    def test_advrate_set_2min(self):
        self.init_plugin("""
            [settings]
            rate: 4

            [messages]
            ad1: f00
            ad2: bar
            ad3: test
        """)
        self.assertEqual('4', self.p._rate)
        self.joe.clearMessageHistory()
        self.p.cmd_advrate(data="2", client=self.joe)
        self.assertEqual('2', self.p._rate)
        self.assertEqual(['Adv: rate set to 2 minutes'], self.joe.message_history)

    def test_advrate_set_3min(self):
        self.init_plugin("""
            [settings]
            rate: 4

            [messages]
            ad1: f00
            ad2: bar
            ad3: test
        """)
        self.assertEqual('4', self.p._rate)
        self.joe.clearMessageHistory()
        self.p.cmd_advrate(data="3", client=self.joe)
        self.assertEqual('3', self.p._rate)
        self.assertEqual(['Adv: rate set to 3 minutes'], self.joe.message_history)

    def test_advrem_nominal(self):
        self.init_plugin("""
            [settings]
            rate: 4

            [messages]
            ad1: f00
            ad2: bar
            ad3: test
        """)
        self.assertEqual(['f00', 'bar', 'test'], self.p.ad_list)
        self.joe.clearMessageHistory()
        self.p.cmd_advrem(data="2", client=self.joe)
        self.assertEqual(['f00', 'test'], self.p.ad_list)
        self.assertEqual(['Adv: removed item: bar'], self.joe.message_history)

    def test_advrem_no_arg(self):
        self.init_plugin("""
            [settings]
            rate: 4

            [messages]
            ad1: f00
            ad2: bar
            ad3: test
        """)
        self.assertEqual(['f00', 'bar', 'test'], self.p.ad_list)
        self.joe.clearMessageHistory()
        self.p.cmd_advrem(data=None, client=self.joe)
        self.assertEqual(['f00', 'bar', 'test'], self.p.ad_list)
        self.assertEqual(['Missing data, try !help advrem'], self.joe.message_history)

    def test_advrem_junk(self):
        self.init_plugin("""
            [settings]
            rate: 4

            [messages]
            ad1: f00
            ad2: bar
            ad3: test
        """)
        self.assertEqual(['f00', 'bar', 'test'], self.p.ad_list)
        self.joe.clearMessageHistory()
        self.p.cmd_advrem(data='f00', client=self.joe)
        self.assertEqual(['f00', 'bar', 'test'], self.p.ad_list)
        self.assertEqual(['Invalid data, use the !advlist command to list valid items numbers'],
                         self.joe.message_history)

    def test_advrem_invalid_index(self):
        self.init_plugin("""
            [settings]
            rate: 4

            [messages]
            ad1: f00
            ad2: bar
            ad3: test
        """)
        self.assertEqual(['f00', 'bar', 'test'], self.p.ad_list)
        self.joe.clearMessageHistory()
        self.p.cmd_advrem(data='-18', client=self.joe)
        self.assertEqual(['f00', 'bar', 'test'], self.p.ad_list)
        self.assertEqual(['Invalid data, use the !advlist command to list valid items numbers'],
                         self.joe.message_history)

    def test_advadd_nominal(self):
        self.init_plugin("""
            [settings]
            rate: 4

            [messages]
            ad1: f00
        """)
        self.assertEqual(['f00'], self.p.ad_list)
        self.joe.clearMessageHistory()
        self.p.cmd_advadd(data="bar", client=self.joe)
        self.assertEqual(['f00', 'bar'], self.p.ad_list)
        self.assertEqual(['Adv: "bar" added'], self.joe.message_history)

    def test_advadd_no_arg(self):
        self.init_plugin("""
            [settings]
            rate: 4

            [messages]
            ad1: f00
        """)
        self.assertEqual(['f00'], self.p.ad_list)
        self.joe.clearMessageHistory()
        self.p.cmd_advadd(data=None, client=self.joe)
        self.assertEqual(['f00'], self.p.ad_list)
        self.assertEqual(['Missing data, try !help advadd'], self.joe.message_history)
