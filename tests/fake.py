"""
This module make plugin testing simple. It provides you
with fakeConsole and joe which can be used to say commands
as if it where a player.
"""
import logging
import re
import sys
import time
import traceback
from collections import defaultdict
from io import StringIO
from sys import stdout

import b3.config
import b3.events
import b3.output
import b3.parser
from b3.clients import Clients
from b3.clients import Cvar
from b3.functions import splitDSN
from b3.game import Game
from b3.plugins.admin import AdminPlugin
from b3.storage.sqlite import SqliteStorage

__version__ = '1.18'


class FakeConsole(b3.parser.Parser):
    """
    Console implementation to be used with automated tests.
    """
    Events = b3.events.eventManager = b3.events.Events()
    screen = stdout
    noVerbose = False
    input = None

    def __init__(self, config):
        """
        Object constructor.
        :param config: The main configuration file
        """
        b3.console = self
        self._timeStart = self.time()
        logging.basicConfig(level=b3.output.VERBOSE2, format='%(asctime)s\t%(levelname)s\t%(message)s')
        self.log = logging.getLogger('output')
        self.config = config

        if isinstance(config, b3.config.CfgConfigParser):
            self.config = b3.config.MainConfig(config)
        elif isinstance(config, b3.config.MainConfig):
            self.config = config
        else:
            self.config = b3.config.MainConfig(b3.config.load(config))

        self.storage = SqliteStorage("sqlite://:memory:", splitDSN("sqlite://:memory:"), self)
        self.storage.connect()
        self.clients = b3.clients.Clients(self)
        self.game = b3.game.Game(self, "fakeGame")
        self.game.mapName = 'ut4_turnpike'
        self.cvars = {}
        self._handlers = defaultdict(list)

        self.input = StringIO()

    def run(self):
        pass

    def queueEvent(self, event, expire=10):
        """
        Queue an event for processing.
        NO QUEUE, NO THREAD for faking speed up
        """
        if not hasattr(event, 'type'):
            return False
        elif event.type in self._handlers:
            self.verbose('Queueing event %s %s', self.Events.getName(event.type), event.data)
            self._handleEvent(event)
            return True
        return False

    def _handleEvent(self, event):
        """
        NO QUEUE, NO THREAD for faking speed up
        """
        if event.type == self.getEventID('EVT_EXIT') or event.type == self.getEventID('EVT_STOP'):
            self.working = False

        for hfunc in self._handlers[event.type]:
            if not hfunc.isEnabled():
                continue

            self.verbose('parsing event: %s: %s', self.Events.getName(event.type), hfunc.__class__.__name__)

            try:
                hfunc.parseEvent(event)
                time.sleep(0.001)
            except b3.events.VetoEvent:
                # plugin called for event hault, do not continue processing
                self.bot('Event %s vetoed by %s', self.Events.getName(event.type), str(hfunc))
                break
            except SystemExit as e:
                self.exitcode = e.code
                break
            except Exception as msg:
                self.error('handler %s could not handle event %s: %s: %s %s',
                           hfunc.__class__.__name__, self.Events.getName(event.type),
                           msg.__class__.__name__, msg, traceback.extract_tb(sys.exc_info()[2]))

    def shutdown(self):
        """
        Shutdown B3 - needed to be changed in FakeConsole due to no thread for dispatching events.
        """
        try:
            self.bot('shutting down...')
            self.working = False
            self._handleEvent(self.getEvent('EVT_STOP'))
            if self._cron:
                self._cron.stop()
            self.bot('shutting down database connections...')
            self.storage.shutdown()
        except Exception as e:
            self.error(e)

    def getPlugin(self, name):
        if name == 'admin':
            return fakeAdminPlugin
        else:
            return b3.parser.Parser.getPlugin(self, name)

    def sync(self):
        return {}

    def getNextMap(self):
        return "ut4_theNextMap"

    def getPlayerScores(self):
        return {0: 5, 1: 4}

    def say(self, msg, *args):
        """
        Send text to the server.
        """
        print(">>> %s" % re.sub(re.compile(r'\^[0-9]'), '', msg % args).strip())

    def saybig(self, msg, *args):
        """
        Send bigtext to the server.
        """
        print("+++ %s" % re.sub(re.compile(r'\^[0-9]'), '', msg % args).strip())

    def write(self, msg, maxRetries=0, socketTimeout=None):
        """
        Send text to the console.
        """
        if type(msg) == str:
            print("### %s" % re.sub(re.compile(r'\^[0-9]'), '', msg).strip())
        else:
            print("### %s" % msg)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def authorizeClients(self):
        pass

    def ban(self, client, reason='', admin=None, silent=False, *kwargs):
        """
        Permban a client.
        """
        print('>>>permbanning %s (%s)' % (client.name, reason))
        self.queueEvent(self.getEvent('EVT_CLIENT_BAN', {'reason': reason, 'admin': admin}, client))
        client.disconnect()

    def tempban(self, client, reason='', duration=2, admin=None, silent=False, *kwargs):
        """
        Tempban a client.
        """
        from b3.functions import minutesStr
        print('>>>tempbanning %s for %s (%s)' % (client.name, reason, minutesStr(duration)))
        data = {'reason': reason, 'duration': duration, 'admin': admin}
        self.queueEvent(self.getEvent('EVT_CLIENT_BAN_TEMP', data=data, client=client))
        client.disconnect()

    def unban(self, client, reason='', admin=None, silent=False, *kwargs):
        """
        Unban a client.
        """
        print('>>>unbanning %s (%s)' % (client.name, reason))
        self.queueEvent(self.getEvent('EVT_CLIENT_UNBAN', reason, client))

    def kick(self, client, reason='', admin=None, silent=False, *kwargs):
        """
        Kick a client.
        """
        print('>>>kick %s for %s' % (client.name, reason))
        self.queueEvent(self.getEvent('EVT_CLIENT_KICK', data={'reason': reason, 'admin': admin}, client=client))
        client.disconnect()

    def message(self, client, text, *args):
        """
        Send a message to a client.
        """
        if client is None:
            self.say(text % args)
        elif client.cid is None:
            pass
        else:
            print("sending msg to %s: %s" % (client.name, re.sub(re.compile(r'\^[0-9]'), '', text % args).strip()))

    def getCvar(self, key):
        """
        Get a server variable.
        """
        print("get cvar %s" % key)
        return self.cvars.get(key)

    def setCvar(self, key, value):
        """
        Set a server variable.
        """
        print("set cvar %s" % key)
        c = Cvar(name=key, value=value)
        self.cvars[key] = c

    def queryClientFrozenSandAccount(self, cid):
        return {}


class FakeClient(b3.clients.Client):
    """
    Client object implementation to be used in automated tests.
    """
    console = None

    def __init__(self, console, **kwargs):
        """
        Object constructor.
        :param console: The console implementation
        """
        self.console = console
        self.message_history = []  # this allows unittests to check if a message was sent to the client
        super().__init__(**kwargs)

    def clearMessageHistory(self):
        self.message_history = []

    def getMessageHistoryLike(self, needle):
        clean_needle = re.sub(re.compile(r'\^[0-9]'), '', needle).strip()
        for m in self.message_history:
            if clean_needle in m:
                return m

    def getAllMessageHistoryLike(self, needle):
        clean_needle = re.sub(re.compile(r'\^[0-9]'), '', needle).strip()
        return [m for m in self.message_history if clean_needle in m]

    def message(self, msg, *args):
        msg = msg % args
        cleanmsg = re.sub(re.compile(r'\^[0-9]'), '', msg).strip()
        self.message_history.append(cleanmsg)
        print("sending msg to %s: %s" % (self.name, cleanmsg))

    def warn(self, duration, warning, keyword=None, admin=None, data=''):
        w = super().warn(duration, warning, keyword=None, admin=None, data='')
        print(">>>>%s gets a warning : %s" % (self, w))

    def connects(self, cid):
        print("\n%s connects to the game on slot #%s" % (self.name, cid))
        self.cid = cid
        self.timeAdd = self.console.time()
        # self.console.clients.newClient(cid)
        clients = self.console.clients
        clients[self.cid] = self
        clients.resetIndex()

        self.console.debug('client connected: [%s] %s - %s (%s)', clients[self.cid].cid,
                           clients[self.cid].name, clients[self.cid].guid, clients[self.cid].data)

        self.console.queueEvent(self.console.getEvent('EVT_CLIENT_CONNECT', data=self, client=self))

        if self.guid:
            self.auth()
        elif not self.authed:
            clients._authorizeClients()

    def disconnects(self):
        print(f"\n{self.name} disconnects from slot #{self.cid}")
        self.console.clients.disconnect(self)
        self.cid = None
        self.authed = False
        self._pluginData = {}
        self.state = b3.STATE_UNKNOWN

    def says(self, msg):
        print(f"\n{self.name} says \"{msg}\"")
        self.console.queueEvent(self.console.getEvent('EVT_CLIENT_SAY', data=msg, client=self))

    def says2team(self, msg):
        print(f"\n{self.name} says to team \"{msg}\"")
        self.console.queueEvent(self.console.getEvent('EVT_CLIENT_TEAM_SAY', data=msg, client=self))

    def says2squad(self, msg):
        print(f"\n{self.name} says to squad \"{msg}\"")
        self.console.queueEvent(self.console.getEvent('EVT_CLIENT_SQUAD_SAY', data=msg, client=self))

    def says2private(self, msg):
        print(f"\n{self.name} says privately \"{msg}\"")
        self.console.queueEvent(self.console.getEvent('EVT_CLIENT_PRIVATE_SAY', data=msg, client=self, target=self))

    def damages(self, victim, points=34.0):
        print(f"\n{self.name} damages {victim.name} for {points} points")
        if self == victim:
            eventkey = 'EVT_CLIENT_DAMAGE_SELF'
        elif self.team != b3.TEAM_UNKNOWN and self.team == victim.team:
            eventkey = 'EVT_CLIENT_DAMAGE_TEAM'
        else:
            eventkey = 'EVT_CLIENT_DAMAGE'

        data = (points, 1, 1, 1)
        self.console.queueEvent(self.console.getEvent(eventkey, data=data, client=self, target=victim))

    def kills(self, victim, weapon=1, hit_location=1):
        print(f"\n{self.name} kills {victim.name}")
        if self == victim:
            self.suicides()
            return
        elif self.team != b3.TEAM_UNKNOWN and self.team == victim.team:
            eventkey = 'EVT_CLIENT_KILL_TEAM'
        else:
            eventkey = 'EVT_CLIENT_KILL'

        data = (100, weapon, hit_location, 1)
        self.console.queueEvent(self.console.getEvent(eventkey, data=data, client=self, target=victim))

    def suicides(self):
        print(f"\n{self.name} kills himself")
        data = (100, 1, 1, 1)
        self.console.queueEvent(self.console.getEvent('EVT_CLIENT_SUICIDE', data=data, client=self, target=self))

    def do_action(self, actiontype):
        self.console.queueEvent(self.console.getEvent('EVT_CLIENT_ACTION', data=actiontype, client=self))

    def trigger_event(self, type, data, target=None):
        print(f"\n{self.name} trigger event {type}")
        self.console.queueEvent(b3.events.Event(type, data, self, target))


print("creating fakeConsole with @b3/conf/b3.distribution.ini")
fakeConsole = FakeConsole('@b3/conf/b3.distribution.ini')

print("creating fakeAdminPlugin with @b3/conf/plugin_admin.ini")
fakeAdminPlugin = AdminPlugin(fakeConsole, '@b3/conf/plugin_admin.ini')
fakeAdminPlugin.onLoadConfig()
fakeAdminPlugin.onStartup()
