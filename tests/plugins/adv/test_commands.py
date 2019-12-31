from tests.fake import FakeClient
from tests.plugins.adv import AdvTestCase


class Test_commands(AdvTestCase):

    def setUp(self):
        AdvTestCase.setUp(self)
        self.joe = FakeClient(self.console, name="Joe", guid="joeguid", groupBits=128)

    def test_advlist_empty(self):
        self.init_plugin("""
            <configuration>
                <settings name="settings">
                    <set name="rate">30s</set>
                </settings>
                <ads>
                </ads>
            </configuration>
        """)
        self.joe.clearMessageHistory()
        self.p.cmd_advlist(data=None, client=self.joe)
        self.assertEqual([], self.p._msg.items)
        self.assertEqual(['Adv: no ads loaded'], self.joe.message_history)

    def test_advlist_one_item(self):
        self.init_plugin("""
            <configuration>
                <settings name="settings">
                    <set name="rate">30s</set>
                </settings>
                <ads>
                    <ad>f00</ad>
                </ads>
            </configuration>
        """)
        self.joe.clearMessageHistory()
        self.p.cmd_advlist(data=None, client=self.joe)
        self.assertEqual(['f00'], self.p._msg.items)
        self.assertEqual(['Adv: [1] f00'], self.joe.message_history)

    def test_advlist_many_items(self):
        self.init_plugin("""
            <configuration>
                <settings name="settings">
                    <set name="rate">30s</set>
                </settings>
                <ads>
                    <ad>f00</ad>
                    <ad>bar</ad>
                    <ad>test</ad>
                </ads>
            </configuration>
        """)
        self.joe.clearMessageHistory()
        self.p.cmd_advlist(data=None, client=self.joe)
        self.assertEqual(['f00', 'bar', 'test'], self.p._msg.items)
        self.assertEqual(['Adv: [1] f00', 'Adv: [2] bar', 'Adv: [3] test'], self.joe.message_history)

    def test_advrate_no_arg_30s(self):
        self.init_plugin("""
            <configuration>
                <settings name="settings">
                    <set name="rate">30s</set>
                </settings>
                <ads>
                    <ad>f00</ad>
                    <ad>bar</ad>
                    <ad>test</ad>
                </ads>
            </configuration>
        """)
        self.joe.clearMessageHistory()
        self.p.cmd_advrate(data='', client=self.joe)
        self.assertEqual('30s', self.p._rate)
        self.assertEqual(['Current rate is every 30 seconds'], self.joe.message_history)

    def test_advrate_no_arg_2min(self):
        self.init_plugin("""
            <configuration>
                <settings name="settings">
                    <set name="rate">2</set>
                </settings>
                <ads>
                    <ad>f00</ad>
                    <ad>bar</ad>
                    <ad>test</ad>
                </ads>
            </configuration>
        """)
        self.joe.clearMessageHistory()
        self.p.cmd_advrate(data=None, client=self.joe)
        self.assertEqual('2', self.p._rate)
        self.assertEqual(['Current rate is every 2 minutes'], self.joe.message_history)

    def test_advrate_set_20s(self):
        self.init_plugin("""
            <configuration>
                <settings name="settings">
                    <set name="rate">45s</set>
                </settings>
                <ads>
                    <ad>f00</ad>
                    <ad>bar</ad>
                    <ad>test</ad>
                </ads>
            </configuration>
        """)
        self.assertEqual('45s', self.p._rate)
        self.joe.clearMessageHistory()
        self.p.cmd_advrate(data="20s", client=self.joe)
        self.assertEqual('20s', self.p._rate)
        self.assertEqual(['Adv: rate set to 20 seconds'], self.joe.message_history)

    def test_advrate_set_3min(self):
        self.init_plugin("""
            <configuration>
                <settings name="settings">
                    <set name="rate">45s</set>
                </settings>
                <ads>
                    <ad>f00</ad>
                    <ad>bar</ad>
                    <ad>test</ad>
                </ads>
            </configuration>
        """)
        self.assertEqual('45s', self.p._rate)
        self.joe.clearMessageHistory()
        self.p.cmd_advrate(data="3", client=self.joe)
        self.assertEqual('3', self.p._rate)
        self.assertEqual(['Adv: rate set to 3 minutes'], self.joe.message_history)

    def test_advrem_nominal(self):
        self.init_plugin("""
            <configuration>
                <settings name="settings">
                    <set name="rate">45s</set>
                </settings>
                <ads>
                    <ad>f00</ad>
                    <ad>bar</ad>
                    <ad>test</ad>
                </ads>
            </configuration>
        """)
        self.assertEqual(['f00', 'bar', 'test'], self.p._msg.items)
        self.joe.clearMessageHistory()
        self.p.cmd_advrem(data="2", client=self.joe)
        self.assertEqual(['f00', 'test'], self.p._msg.items)
        self.assertEqual(['Adv: removed item: bar'], self.joe.message_history)

    def test_advrem_no_arg(self):
        self.init_plugin("""
            <configuration>
                <settings name="settings">
                    <set name="rate">45s</set>
                </settings>
                <ads>
                    <ad>f00</ad>
                    <ad>bar</ad>
                    <ad>test</ad>
                </ads>
            </configuration>
        """)
        self.assertEqual(['f00', 'bar', 'test'], self.p._msg.items)
        self.joe.clearMessageHistory()
        self.p.cmd_advrem(data=None, client=self.joe)
        self.assertEqual(['f00', 'bar', 'test'], self.p._msg.items)
        self.assertEqual(['Missing data, try !help advrem'], self.joe.message_history)

    def test_advrem_junk(self):
        self.init_plugin("""
            <configuration>
                <settings name="settings">
                    <set name="rate">45s</set>
                </settings>
                <ads>
                    <ad>f00</ad>
                    <ad>bar</ad>
                    <ad>test</ad>
                </ads>
            </configuration>
        """)
        self.assertEqual(['f00', 'bar', 'test'], self.p._msg.items)
        self.joe.clearMessageHistory()
        self.p.cmd_advrem(data='f00', client=self.joe)
        self.assertEqual(['f00', 'bar', 'test'], self.p._msg.items)
        self.assertEqual(['Invalid data, use the !advlist command to list valid items numbers'],
                         self.joe.message_history)

    def test_advrem_invalid_index(self):
        self.init_plugin("""
            <configuration>
                <settings name="settings">
                    <set name="rate">45s</set>
                </settings>
                <ads>
                    <ad>f00</ad>
                    <ad>bar</ad>
                    <ad>test</ad>
                </ads>
            </configuration>
        """)
        self.assertEqual(['f00', 'bar', 'test'], self.p._msg.items)
        self.joe.clearMessageHistory()
        self.p.cmd_advrem(data='-18', client=self.joe)
        self.assertEqual(['f00', 'bar', 'test'], self.p._msg.items)
        self.assertEqual(['Invalid data, use the !advlist command to list valid items numbers'],
                         self.joe.message_history)

    def test_advadd_nominal(self):
        self.init_plugin("""
            <configuration>
                <settings name="settings">
                    <set name="rate">45s</set>
                </settings>
                <ads>
                    <ad>f00</ad>
                </ads>
            </configuration>
        """)
        self.assertEqual(['f00'], self.p._msg.items)
        self.joe.clearMessageHistory()
        self.p.cmd_advadd(data="bar", client=self.joe)
        self.assertEqual(['f00', 'bar'], self.p._msg.items)
        self.assertEqual(['Adv: "bar" added'], self.joe.message_history)

    def test_advadd_no_arg(self):
        self.init_plugin("""
            <configuration>
                <settings name="settings">
                    <set name="rate">45s</set>
                </settings>
                <ads>
                    <ad>f00</ad>
                </ads>
            </configuration>
        """)
        self.assertEqual(['f00'], self.p._msg.items)
        self.joe.clearMessageHistory()
        self.p.cmd_advadd(data=None, client=self.joe)
        self.assertEqual(['f00'], self.p._msg.items)
        self.assertEqual(['Missing data, try !help advadd'], self.joe.message_history)
