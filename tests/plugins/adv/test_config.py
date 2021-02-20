from tests.plugins.adv import AdvTestCase


class Test_config(AdvTestCase):

    def test_default_config(self):
        self.init_plugin()
        self.assertEqual('1', self.p._rate)
        self.assertIsNone(self.p._file_name)
        self.assertIsNotNone(self.p._crontab)
        self.assertTupleEqual((list(range(0, 60)), -1, -1, -1, -1),
                              (self.p._crontab.minute, self.p._crontab.hour,
                               self.p._crontab.day, self.p._crontab.month, self.p._crontab.dow))
        self.assertEqual(7, len(self.p.ad_list))
        self.assertListEqual([
            '^2Visit us at www.urt-30plus.org',
            '^2Public Teamspeak server: ts3urt30.ts.nfoservers.com',
            '^2Type !register to register as a user',
            '^2Type !fa in chat to forgive team damage',
            '^2Send demos to urt30plus@gmail.com',
            '^3Rule #8: No profanity or offensive language (in any language)',
            '@nextmap',
        ], self.p.ad_list)

    def test_empty(self):
        self.init_plugin("""<configuration plugin="adv" />""")
        self.assertEqual(self.p._rate, '2')
        self.assertIsNone(self.p._file_name)
        self.assertEqual(0, len(self.p.ad_list))
        self.assertIsNotNone(self.p._crontab)

    def test_rate_nominal(self):
        self.init_plugin("""\
<configuration plugin="adv">
    <settings name="settings">
        <set name="rate">1</set>
    </settings>
</configuration>
""")
        self.assertEqual('1', self.p._rate)
        self.assertIsNotNone(self.p._crontab)
        self.assertTupleEqual((list(range(60)), -1, -1, -1, -1),
                              (self.p._crontab.minute, self.p._crontab.hour,
                               self.p._crontab.day, self.p._crontab.month, self.p._crontab.dow))

    def test_rate_nominal_second(self):
        self.init_plugin("""\
<configuration plugin="adv">
    <settings name="settings">
        <set name="rate">40s</set>
    </settings>
</configuration>
""")
        self.assertEqual('40s', self.p._rate)
        self.assertIsNotNone(self.p._crontab)
        self.assertTupleEqual((-1, -1, -1, -1, -1),
                              (self.p._crontab.minute, self.p._crontab.hour,
                               self.p._crontab.day, self.p._crontab.month, self.p._crontab.dow))

    def test_rate_junk(self):
        try:
            self.init_plugin("""\
<configuration plugin="adv">
    <settings name="settings">
        <set name="rate">f00</set>
    </settings>
</configuration>
""")
        except TypeError as err:
            print(err)
        except Exception:
            raise
        self.assertEqual('f00', self.p._rate)
        self.assertIsNone(self.p._crontab)
