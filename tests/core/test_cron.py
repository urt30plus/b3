import time
import unittest
from unittest.mock import Mock, sentinel

from b3.cron import CronTab, DayOfWeek, OneTimeCronTab, PluginCronTab, Cron
from tests import B3TestCase


class Test_Crontab(unittest.TestCase):

    def test_constructor_defaults(self):
        command = sentinel
        tab = CronTab(command)
        self.assertEqual(command, tab.command)
        self.assertEqual(-1, tab.minute)
        self.assertEqual(-1, tab.hour)
        self.assertEqual(-1, tab.day)
        self.assertEqual(-1, tab.month)
        self.assertEqual(-1, tab.dow)
        self.assertEqual(0, tab.maxRuns)

    def test_constructor(self):
        command = sentinel
        tab = CronTab(command, minute=2, hour=3, day=4, month=5, dow=1)
        self.assertEqual(command, tab.command)
        self.assertEqual(2, tab.minute)
        self.assertEqual(3, tab.hour)
        self.assertEqual(4, tab.day)
        self.assertEqual(5, tab.month)
        self.assertEqual(1, tab.dow)

        tab = CronTab(command, minute=2, hour=3, day=4, month=5, dow=DayOfWeek.TUESDAY)
        self.assertEqual(1, tab.dow)

    def test_dow(self):
        tab = CronTab(None)

        tab.dow = '*'  # any day
        self.assertEqual(-1, tab.dow)

        tab.dow = DayOfWeek.MONDAY
        self.assertEqual(0, tab.dow)

        tab.dow = DayOfWeek.TUESDAY
        self.assertEqual(1, tab.dow)

        tab.dow = DayOfWeek.WEDNESDAY
        self.assertEqual(2, tab.dow)

        tab.dow = DayOfWeek.THURSDAY
        self.assertEqual(3, tab.dow)

        tab.dow = DayOfWeek.FRIDAY
        self.assertEqual(4, tab.dow)

        tab.dow = DayOfWeek.SATURDAY
        self.assertEqual(5, tab.dow)

        tab.dow = DayOfWeek.SUNDAY
        self.assertEqual(6, tab.dow)

        try:
            tab.dow = 7
        except ValueError:
            pass
        else:
            self.fail("expecting ValueError when setting dow to 7")

        try:
            tab.dow = -1
        except ValueError:
            pass
        else:
            self.fail("expecting ValueError when setting dow to 7")

    def test_run(self):
        command = Mock(name="command")
        tab = CronTab(command)
        assert not command.called
        tab.run()
        assert command.called

    def test_match(self):
        tab = CronTab(None, minute='*', hour='*', day='*', month='*', dow='*')
        self.assertTrue(tab.match(time.gmtime()))

        tab = CronTab(None, minute='*', hour='*', day='*', month='*', dow='0,1,2,3,4,5,6')
        self.assertTrue(tab.match(time.gmtime()))

        days = DayOfWeek.range(DayOfWeek.MONDAY, DayOfWeek.TUESDAY,
                               DayOfWeek.WEDNESDAY, DayOfWeek.THURSDAY,
                               DayOfWeek.FRIDAY, DayOfWeek.SATURDAY,
                               DayOfWeek.SUNDAY)
        tab = CronTab(None, minute='*', hour='*', day='*', month='*', dow=days)
        self.assertTrue(tab.match(time.gmtime()))


class Test_OneTimeCrontab(unittest.TestCase):

    def test_constructor(self):
        tab = OneTimeCronTab(None)
        self.assertEqual(1, tab.maxRuns)


class Test_PluginCronTab(unittest.TestCase):

    def test(self):
        CronTab.match = Mock(return_value=True)
        mock_command = Mock()
        p = Mock()
        tab = PluginCronTab(plugin=p, command=mock_command)

        mock_command.reset_mock()
        p.isEnabled = Mock(return_value=True)
        self.assertTrue(tab.match(time.gmtime()))
        tab.run()
        self.assertTrue(mock_command.called)

        mock_command.reset_mock()
        p.isEnabled = Mock(return_value=False)
        self.assertFalse(tab.match(time.gmtime()))
        tab.run()
        self.assertFalse(mock_command.called)


class Test_Crontab_getRate(unittest.TestCase):

    def setUp(self):
        self._t = CronTab(None)

    def tearDown(self):
        pass

    def t(self, param):
        return self._t._getRate(param, 60)

    def test_None(self):
        self.assertRaises(TypeError, self.t, None)

    def test_getRate_int(self):
        self.assertEqual(0, self.t(0))
        self.assertEqual(1, self.t(1))
        self.assertEqual(59, self.t(59))
        self.assertRaises(ValueError, self.t, 60)
        self.assertRaises(ValueError, self.t, -1)

    def test_float(self):
        self.assertEqual(0, self.t(0.0))
        self.assertEqual(1, self.t(1.0))
        self.assertEqual(59, self.t(59.0))
        self.assertRaises(ValueError, self.t, 60.0)
        self.assertRaises(ValueError, self.t, -1.0)

    def test_str_every(self):
        self.assertEqual(-1, self.t('*'))

    def test_str_everySo(self):
        self.assertEqual(list(range(0, 60, 2)), self.t('*/2'))
        self.assertEqual(list(range(0, 60, 17)), self.t('*/17'))
        self.assertEqual([0, 59], self.t('*/59'))
        self.assertEqual([0], self.t('*/60'))
        self.assertRaises(ValueError, self.t, ('*/61'))
        self.assertRaises(TypeError, self.t, ('*/-1'))
        self.assertRaises(ValueError, self.t, ('*/80'))

    def test_str_range(self):
        self.assertEqual(list(range(5, 12)), self.t('5-11'))
        self.assertRaises(TypeError, self.t, ('-5-11'))
        self.assertRaises(ValueError, self.t, ('35-11'))
        self.assertRaises(TypeError, self.t, ('5--11'))
        self.assertRaises(ValueError, self.t, ('5-80'))

    def test_str_range_with_step(self):
        self.assertEqual(list(range(5, 12, 2)), self.t('5-11/2'))
        self.assertEqual([5], self.t('5-11/60'))
        self.assertRaises(ValueError, self.t, ('5-11/80'))
        self.assertRaises(TypeError, self.t, ('5-11/'))
        self.assertRaises(TypeError, self.t, ('5-11/-1'))

    def test_str_other(self):
        self.assertRaises(TypeError, self.t, (''))
        self.assertRaises(TypeError, self.t, ('test'))

    def test_list(self):
        self.assertEqual([5, 11, 32, 45], self.t('5,11,45,32'))
        self.assertEqual([0, 1, 2, 5, 6, 7, 8], self.t('5-8,0-2'))
        self.assertEqual([5, 6, 7, 20, 30], self.t('5-7, 20, 30'))
        self.assertEqual([5, 6, 7, 30, 40], self.t('5-7,40,30'))
        self.assertEqual([0, 5, 6, 7, 40], self.t('5-7,40,0'))
        self.assertEqual([5, 7, 9, 11, 30, 40, 41, 42], self.t('5-12/2, 30, 40-42'))
        self.assertRaises(TypeError, self.t, ('5-12/2, -5, 40-42'))


class Test_Cron(B3TestCase):

    def setUp(self):
        B3TestCase.setUp(self)
        self.cron = Cron(self.console)
        # self.console.verbose = lambda *args: sys.stdout.write(str(args) + "\n")

    def test_add(self):
        mock_tab = Mock(spec=CronTab)
        res = self.cron.add(mock_tab)
        self.assertEqual(1, len(self.cron._tabs))
        self.assertEqual(id(mock_tab), res)
        self.assertIn(id(mock_tab), self.cron._tabs)

    def test_add_operator(self):
        mock_tab = Mock(spec=CronTab)
        self.cron + mock_tab
        self.assertEqual(1, len(self.cron._tabs))
        self.assertIn(id(mock_tab), self.cron._tabs)

    def test_iadd_operator(self):
        mock_tab = Mock(spec=CronTab)
        self.cron += mock_tab
        self.assertEqual(1, len(self.cron._tabs))
        self.assertIn(id(mock_tab), self.cron._tabs)

    def test_cancel(self):
        mock_tab = Mock(spec=CronTab)
        res = self.cron.add(mock_tab)
        self.assertEqual(1, len(self.cron._tabs))

        self.cron.cancel(-1)
        self.assertEqual(1, len(self.cron._tabs))

        self.cron.cancel(id(mock_tab))
        self.assertNotIn(id(mock_tab), self.cron._tabs)
        self.assertEqual(0, len(self.cron._tabs))

    def test_sub_operator(self):
        mock_tab = Mock(spec=CronTab)
        res = self.cron.add(mock_tab)
        self.assertEqual(1, len(self.cron._tabs))
        self.cron - mock_tab
        self.assertNotIn(res, self.cron._tabs)
        self.assertEqual(0, len(self.cron._tabs))

    def test_isub_operator(self):
        mock_tab = Mock(spec=CronTab)
        res = self.cron.add(mock_tab)
        self.assertEqual(1, len(self.cron._tabs))
        self.cron -= mock_tab
        self.assertNotIn(res, self.cron._tabs)
        self.assertEqual(0, len(self.cron._tabs))

    def test_create(self):
        crontab_id = self.cron.create(None)
        self.assertEqual(1, len(self.cron._tabs))
        self.assertIn(crontab_id, self.cron._tabs)
        self.assertEqual(CronTab, type(self.cron._tabs[crontab_id]))


if __name__ == '__main__':
    unittest.main()
