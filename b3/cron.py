import enum
import re
import sys
import threading
import time
import traceback
from collections import deque

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
        return ','.join([str(x.value) for x in args])


class ReMatcher:

    def __init__(self):
        self._re = None

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

    def __init__(self, command, minute='*', hour='*', day='*', month='*', dow='*'):
        """
        Object constructor.
        """
        self._minute = CronTab._getRate(minute, 60)
        self._hour = CronTab._getRate(hour, 24)
        self._day = CronTab._getRate(day, 31)
        self._month = CronTab._getRate(month, 12)
        self._dow = CronTab._getRate(dow, 7)
        self.command = command
        self.run_stats = deque(maxlen=20)
        self.maxRuns = 0
        self.numRuns = 0

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(command={self.command.__qualname__}, "
            f"minute={self.minute}, hour={self.hour}, "
            f"day={self.day}, month={self.month}, dow={self.dow})"
        )

    def run(self):
        """
        Execute the command saved in this crontab.
        """
        start_tick = time.perf_counter()
        self.command()
        self.run_stats.append((time.perf_counter() - start_tick) * 1000)

    @property
    def second(self):
        return 0

    @second.setter
    def second(self, value):
        pass

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

    @staticmethod
    def _getRate(rate, maxrate=None):
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
                myset = set()
                for fragment in rate.split(','):
                    result = CronTab._getRateFromFragment(fragment.strip(), maxrate)
                    if isinstance(result, int):
                        myset.add(result)
                    else:
                        # must be a list
                        for val in result:
                            myset.add(int(val))

                return sorted(myset)
            else:
                return CronTab._getRateFromFragment(rate, maxrate)
        elif isinstance(rate, int):
            if rate < 0 or rate >= maxrate:
                raise ValueError(f'accepted range is 0-{(maxrate - 1)}')
            return rate
        elif isinstance(rate, float):
            if int(rate) < 0 or int(rate) >= maxrate:
                raise ValueError(f'accepted range is 0-{(maxrate - 1)}')
            return int(rate)

        raise TypeError(f'"{rate}" is not a known cron rate type')

    @staticmethod
    def _getRateFromFragment(rate, maxrate):
        if rate == '*':
            return -1

        r = ReMatcher()
        if r.match(r'^([0-9]+)$', rate):
            if int(rate) >= maxrate:
                raise ValueError(f'{rate} cannot be over {maxrate - 1}')
            return int(rate)
        elif r.match(r'^\*/([0-9]+)$', rate):
            # */10 = [0, 10, 20, 30, 40, 50]
            step = int(r.results.group(1))
            if step > maxrate:
                raise ValueError(f'{rate} cannot be over every {maxrate - 1}')
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
                raise ValueError(f'{step} is out of accepted range 0-{maxrate}')
            if lmin < 0 or lmax > maxrate:
                raise ValueError(f'{rate} is out of accepted range 0-{maxrate - 1}')
            if lmin > lmax:
                raise ValueError(f'{lmin} cannot be greater than {lmax} in {rate}')
            return list(range(lmin, lmax + 1, step))

        raise TypeError(f'"{rate}" is not a known cron rate type')

    @staticmethod
    def _match(unit, value):
        if isinstance(unit, int):
            return unit == -1 or unit == value
        return value in unit

    def match(self, timetuple):
        return (
            self._match(self.minute, timetuple[4])
            and self._match(self.hour, timetuple[3])
            and self._match(self.day, timetuple[2])
            and self._match(self.month, timetuple[1])
            and self._match(self.dow, timetuple[6])
        )


class OneTimeCronTab(CronTab):

    def __init__(self, command, minute='*', hour='*', day='*', month='*', dow='*'):
        """
        Object constructor.
        """
        super().__init__(command, minute, hour, day, month, dow)
        self.maxRuns = 1


class PluginCronTab(CronTab):

    def __init__(self, plugin, command, minute='*', hour='*', day='*', month='*', dow='*'):
        """
        Object constructor.
        """
        super().__init__(command, minute, hour, day, month, dow)
        self.plugin = plugin

    def match(self, timetuple):
        """
        Check whether the cron entry matches the current time.
        Will return False if the plugin is disabled.
        """
        if self.plugin.isEnabled():
            return super().match(timetuple)
        return False

    def run(self):
        """
        Execute the command saved in this crontab.
        Will do nothing if the plugin is disabled.
        """
        if self.plugin.isEnabled():
            super().run()


class Cron:

    def __init__(self, console):
        """
        Object constructor.
        """
        self._tabs = {}
        self.console = console

        # thread will stop if this event gets set
        self._stopEvent = threading.Event()
        self._cron_thread = None

    def create(self, command, minute='*', hour='*', day='*', month='*', dow='*'):
        """
        Create a new CronTab and add it to the active cron tabs.
        """
        t = CronTab(command, minute, hour, day, month, dow)
        return self.add(t)

    def add(self, tab):
        """
        Add a CronTab to the list of active cron tabs.
        """
        tab_id = id(tab)
        self._tabs[tab_id] = tab
        self.console.verbose('Added crontab %s', tab)
        return tab_id

    def entries(self):
        return list(self._tabs.values())

    def cancel(self, tab_id):
        """
        Remove a CronTab from the list of active cron tabs.
        """
        try:
            del self._tabs[tab_id]
            self.console.verbose('Removed crontab %s', tab_id)
        except KeyError:
            self.console.verbose('Crontab %s not found', tab_id)

    def __add__(self, tab):
        self.add(tab)

    def __sub__(self, tab):
        self.cancel(id(tab))

    def start(self):
        """
        Start the cron scheduler in a separate thread.
        """
        self._cron_thread = b3.functions.start_daemon_thread(
            target=self.run, name='crontab'
        )

    def stop(self):
        """
        Stop the cron scheduler.
        """
        self._stopEvent.set()
        if self._cron_thread:
            self._cron_thread.join(timeout=5.0)

    def run(self):
        """
        Main cron loop.
        Will terminate when stop event is set.
        """
        self.console.info("Cron scheduler started")
        while True:
            t = time.gmtime()
            for c in self.entries():
                if c.match(t):
                    c.numRuns += 1
                    try:
                        c.run()
                    except Exception as msg:
                        self.console.error('Exception raised while executing crontab %s: %s\n%s',
                                           c, msg, traceback.extract_tb(sys.exc_info()[2]))
                    if 0 < c.maxRuns <= c.numRuns:
                        # reached max executions, remove tab
                        self.__sub__(c)
                    if self._stopEvent.wait(timeout=0.075):
                        break

            # calculate wait until the next minute
            t2 = time.gmtime()
            if t2.tm_min == t.tm_min:
                delay = 62 - t2.tm_sec
            else:
                self.console.warning('Cron run crossed the minute mark: '
                                     'start %s:%s / end %s:%s',
                                     t.tm_min, t.tm_sec, t2.tm_min, t2.tm_sec)
                # since the next minute has arrived we only add a small delay
                delay = 0.1

            if self._stopEvent.wait(timeout=delay):
                break

        self.console.info("Cron scheduler ended")
