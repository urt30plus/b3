import enum
import re
import sys
import threading
import time
import traceback

import b3.functions

__author__ = 'ThorN, Courgette'
__version__ = '1.5'


class DayOfWeek(enum.IntEnum):
    MONDAY = 0,
    TUESDAY = 1,
    WEDNESDAY = 2,
    THURSDAY = 3,
    FRIDAY = 4,
    SATURDAY = 5,
    SUNDAY = 6

    @staticmethod
    def range(*args):
        return ",".join([str(x.value) for x in args])


class ReMatcher:
    _re = None

    def match(self, regexp, value):
        """
        Match the given value with the given
        regexp and store the result locally.
        :param regexp: The regular expression
        :param value: The value to match
        :return True if the value matches the regexp, False otherwise
        """
        self._re = re.match(regexp, value)
        return self._re

    @property
    def results(self):
        return self._re


class CronTab:
    _second = None
    _minute = None
    _hour = None
    _day = None
    _month = None
    _dow = None

    command = None
    maxRuns = 0
    numRuns = 0

    def __init__(self, command, second=0, minute='*', hour='*', day='*', month='*', dow='*'):
        """
        Object constructor.
        """
        self.second = second
        self.minute = minute
        self.hour = hour
        self.day = day
        self.month = month
        self.dow = dow
        self.command = command

    def run(self):
        """
        Execute the command saved in this crontab.
        """
        self.command()

    @property
    def second(self):
        return self._second

    @second.setter
    def second(self, value):
        self._second = self._getRate(value, 60)

    @property
    def minute(self):
        return self._minute

    @minute.setter
    def minute(self, value):
        self._minute = self._getRate(value, 60)

    @property
    def hour(self):
        return self._hour

    @hour.setter
    def hour(self, value):
        self._hour = self._getRate(value, 24)

    @property
    def day(self):
        return self._day

    @day.setter
    def day(self, value):
        self._day = self._getRate(value, 31)

    @property
    def month(self):
        return self._month

    @month.setter
    def month(self, value):
        self._month = self._getRate(value, 12)

    @property
    def dow(self):
        return self._dow

    @dow.setter
    def dow(self, value):
        self._dow = self._getRate(value, 7)

    def _getRate(self, rate, maxrate=None):
        """
        >>> o = CronTab(lambda: None)
        >>> o._getRate('*/5', 60)
        [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]
        >>> o._getRate('*/5', 10)
        [0, 5]
        >>> o._getRate('*/20', 60)
        [0, 20, 40]
        >>> o._getRate('*/90', 60)
        Traceback (most recent call last):
        ValueError: */90 cannot be over every 59
        """
        if isinstance(rate, str):
            if ',' in rate:
                # 10,20,30 = [10, 20, 30]
                # 5,6,7,20,30 = [5-7, 20, 30]
                # 5,7,9,11,30,40,41,42 = [5-12/2, 30, 40-42]
                myset = {}
                for fragment in rate.split(','):
                    result = self._getRateFromFragment(fragment.strip(), maxrate)
                    if isinstance(result, int):
                        myset[result] = None
                    else:
                        # must be a list
                        for val in result:
                            myset[int(val)] = None

                mylist = list(myset.keys())
                mylist.sort()
                return mylist
            else:
                return self._getRateFromFragment(rate, maxrate)
        elif isinstance(rate, int):
            if rate < 0 or rate >= maxrate:
                raise ValueError('accepted range is 0-%s' % (maxrate - 1))
            return rate
        elif isinstance(rate, float):
            if int(rate) < 0 or int(rate) >= maxrate:
                raise ValueError('accepted range is 0-%s' % (maxrate - 1))
            return int(rate)

        raise TypeError('"%s" is not a known cron rate type' % rate)

    @staticmethod
    def _getRateFromFragment(rate, maxrate):
        r = ReMatcher()
        if rate == '*':
            return -1
        elif r.match(r'^([0-9]+)$', rate):
            if int(rate) >= maxrate:
                raise ValueError('%s cannot be over %s' % (rate, maxrate - 1))
            return int(rate)
        elif r.match(r'^\*/([0-9]+)$', rate):
            # */10 = [0, 10, 20, 30, 40, 50]
            step = int(r.results.group(1))
            if step > maxrate:
                raise ValueError('%s cannot be over every %s' % (rate, maxrate - 1))
            return list(range(0, maxrate, step))
        elif r.match(r'^(?P<lmin>[0-9]+)-(?P<lmax>[0-9]+)(/(?P<step>[0-9]+))?$', rate):
            # 10-20 = [0, 10, 20, 30, 40, 50]
            lmin = int(r.results.group('lmin'))
            lmax = int(r.results.group('lmax'))
            step = r.results.group('step')
            if step is None:
                step = 1
            else:
                step = int(step)
            if step > maxrate:
                raise ValueError('%s is out of accepted range 0-%s' % (step, maxrate))
            if lmin < 0 or lmax > maxrate:
                raise ValueError('%s is out of accepted range 0-%s' % (rate, maxrate - 1))
            if lmin > lmax:
                raise ValueError('%s cannot be greater than %s in %s' % (lmin, lmax, rate))
            return list(range(lmin, lmax + 1, step))

        raise TypeError('"%s" is not a known cron rate type' % rate)

    @staticmethod
    def _match(unit, value):
        if isinstance(unit, int):
            if unit == -1 or unit == value:
                return True
        elif value in unit:
            return True
        return False

    def match(self, timetuple):
        # second
        timematch = self._match(self.second, timetuple[5] - (timetuple[5] % 1))
        # minute
        timematch = timematch and self._match(self.minute, timetuple[4])
        # hour
        timematch = timematch and self._match(self.hour, timetuple[3])
        # day
        timematch = timematch and self._match(self.day, timetuple[2])
        # month
        timematch = timematch and self._match(self.month, timetuple[1])
        # weekday (in crontab 0 is Mon)
        timematch = timematch and self._match(self.dow, timetuple[6])
        return timematch


class OneTimeCronTab(CronTab):

    def __init__(self, command, second=0, minute='*', hour='*', day='*', month='*', dow='*'):
        """
        Object constructor.
        """
        CronTab.__init__(self, command, second, minute, hour, day, month, dow)
        self.maxRuns = 1


class PluginCronTab(CronTab):
    plugin = None

    def __init__(self, plugin, command, second=0, minute='*', hour='*', day='*', month='*', dow='*'):
        """
        Object constructor.
        """
        CronTab.__init__(self, command, second, minute, hour, day, month, dow)
        self.plugin = plugin

    def match(self, timetuple):
        """
        Check whether the cron entry matches the current time.
        Will return False if the plugin is disabled.
        """
        if self.plugin.isEnabled():
            return CronTab.match(self, timetuple)
        return False

    def run(self):
        """
        Execute the command saved in this crontab.
        Will do nothing if the plugin is disabled.
        """
        if self.plugin.isEnabled():
            CronTab.run(self)


class Cron:

    def __init__(self, console):
        """
        Object constructor.
        """
        self._tabs = {}
        self.console = console

        # thread will stop if this event gets set
        self._stopEvent = threading.Event()

    def create(self, command, second=0, minute='*', hour='*', day='*', month='*', dow='*'):
        """
        Create a new CronTab and add it to the active cron tabs.
        """
        t = CronTab(command, second, minute, hour, day, month, dow)
        return self.add(t)

    def add(self, tab):
        """
        Add a CronTab to the list of active cron tabs.
        """
        self._tabs[id(tab)] = tab
        self.console.verbose('Added crontab %s (%s) - %ss %sm %sh %sd %sM %sDOW' % (tab.command, id(tab), tab.second,
                                                                                    tab.minute, tab.hour, tab.day,
                                                                                    tab.month, tab.dow))
        return id(tab)

    def cancel(self, tab_id):
        """
        Remove a CronTab from the list of active cron tabs.
        """
        try:
            del self._tabs[tab_id]
            self.console.verbose('Removed crontab %s' % tab_id)
        except KeyError:
            self.console.verbose('Crontab %s not found' % tab_id)

    def __add__(self, tab):
        self.add(tab)

    def __sub__(self, tab):
        self.cancel(id(tab))

    def start(self):
        """
        Start the cron scheduler in a separate thread.
        """
        b3.functions.start_daemon_thread(self.run)

    @staticmethod
    def time():
        """
        Return the current timestamp.
        """
        return time.time()

    def stop(self):
        """
        Stop the cron scheduler.
        """
        self._stopEvent.set()

    def run(self):
        """
        Main cron loop.
        Will terminate when stop event is set.
        """
        self.console.info("Cron scheduler started")
        nexttime = self.getNextTime()
        while not self._stopEvent.isSet():
            now = self.time()
            if now < nexttime:
                self._stopEvent.wait(nexttime - now + .1)

            # Check if the time has changed by more than two minutes. This
            # case arises when the system clock is changed. We must reset the timer.
            if abs(self.time() - nexttime) > 120:
                nexttime = self.getNextTime()

            t = time.gmtime(nexttime)
            for k, c in self._tabs.items():
                if c.match(t):
                    if 0 < c.maxRuns < c.numRuns + 1:
                        # reached max executions, remove tab
                        del self._tabs[k]
                    else:
                        c.numRuns += 1
                        try:
                            c.run()
                        except Exception as msg:
                            self.console.error('Exception raised while executing crontab %s: %s\n%s', c.command,
                                               msg, traceback.extract_tb(sys.exc_info()[2]))
            nexttime += 1

        self.console.info("Cron scheduler ended")

    @staticmethod
    def getNextTime():
        # store the time first, we don't want it to change on us
        t = time.time()
        # current time, minus it's 1 second remainder, plus 1 seconds
        # will round to the next nearest 1 seconds
        return (t - t % 1) + 1
