import logging
import sys
import threading
import time
import unittest
from contextlib import contextmanager
from unittest.mock import Mock, patch

from mockito import unstub

import b3.output  # unused but we need to to add the `bot` log level
from b3.config import CfgConfigParser, MainConfig
from b3.events import Event

logging.raiseExceptions = (
    False  # get rid of 'No handlers could be found for logger output' message
)
log = logging.getLogger("output")
log.setLevel(logging.WARNING)

testcase_lock = (
    threading.Lock()
)  # together with flush_console_streams, helps getting logging output related to the


class logging_disabled:
    """
    context manager that temporarily disable logging.

    USAGE:
        with logging_disabled():
            # do stuff
    """

    DISABLED = False

    def __init__(self):
        self.nested = logging_disabled.DISABLED

    def __enter__(self):
        if not self.nested:
            logging.getLogger("output").propagate = False
            logging_disabled.DISABLED = True

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.nested:
            logging.getLogger("output").propagate = True
            logging_disabled.DISABLED = False


def flush_console_streams():
    sys.stderr.flush()
    sys.stdout.flush()


def _start_daemon_thread(callable, *args, **kwargs):
    callable(*args, **kwargs)


class B3TestCase(unittest.TestCase):
    def setUp(self):
        testcase_lock.acquire()
        flush_console_streams()

        # create a FakeConsole parser
        self.parser_conf = MainConfig(CfgConfigParser(allow_no_value=True))
        self.parser_conf.loadFromString(r"""""")
        with logging_disabled():
            from tests.fake import FakeConsole

            self.console = FakeConsole(self.parser_conf)

        self.console.screen = Mock()
        self.console.time = time.time
        self.console.upTime = Mock(return_value=3)

        self.console.cron.stop()

        def mock_error(msg, *args, **kwargs):
            print(("ERROR: %s" % msg) % args)

        self.console.error = mock_error

    def tearDown(self):
        flush_console_streams()
        unstub()
        testcase_lock.release()

    @contextmanager
    def assertRaiseEvent(
        self, event_type, event_client=None, event_data=None, event_target=None
    ):
        """
        USAGE:
            def test_team_change(self):
            # GIVEN
            self.client._team = TEAM_RED
            # THEN
            with self.assertRaiseEvent(
                event_type='EVT_CLIENT_TEAM_CHANGE',
                event_data=24,
                event_client=self.client,
                event_target=None):
                # WHEN
                self.client.team = 24
        """
        event_type_name = self.console.getEventName(event_type)
        self.assertIsNotNone(
            event_type_name, f"could not find event with name '{event_type}'"
        )

        with patch.object(self.console, "queueEvent") as queueEvent:
            yield
            if event_type is None:
                assert not queueEvent.called
                return
            assert queueEvent.called, "No event was fired"

        def assertEvent(queueEvent_call_args):
            eventraised = queueEvent_call_args[0][0]
            return (
                type(eventraised) == Event
                and self.console.getEventName(eventraised.type) == event_type_name
                and eventraised.data == event_data
                and eventraised.target == event_target
                and eventraised.client == event_client
            )

        if not any(map(assertEvent, queueEvent.call_args_list)):
            raise AssertionError(
                "Event %s(%r) not fired"
                % (
                    self.console.getEventName(event_type),
                    {
                        "event_client": event_client,
                        "event_data": event_data,
                        "event_target": event_target,
                    },
                )
            )


class InstantTimer:
    """Makes threading.Timer behave synchronously

    Usage:

        @patch('threading.Timer', new_callable=lambda: InstantTimer)
        def test_my_code_using_threading_Timer(instant_timer):
            t = threading.Timer(30, print, args=['hi'])
            t.start()  # prints 'hi' instantly and in the same thread
    """

    def __init__(self, interval, function, args=None, kwargs=None):
        self.function = function
        self.args = args or []
        self.kwargs = kwargs or {}

    def cancel(self):
        pass

    def start(self):
        self.run()

    def run(self):
        self.function(*self.args, **self.kwargs)


class InstantThread(threading.Thread):
    """Makes threading.Thread behaves synchronously

    Usage:

        @patch("threading.Thread", new_callable=lambda: InstantThread)
        def test_my_code_using_threading_Timer(instant_thread):
            t = threading.Thread(target=some_func)
            t.start()
    """

    def start(self):
        self.run()
