import atexit
import datetime
import functools
import glob
import importlib
import os
import queue
import re
import socket
import sys
import threading
import time
from collections import defaultdict, OrderedDict
from textwrap import TextWrapper
from traceback import extract_tb

import b3
import b3.config
import b3.cron
import b3.events
import b3.game
import b3.output
import b3.rcon
import b3.storage
from b3 import __version__ as currentVersion
from b3.clients import Clients
from b3.clients import Group
from b3.functions import getModule
from b3.functions import splitDSN
from b3.functions import start_daemon_thread
from b3.functions import topological_sort
from b3.functions import vars2printf
from b3.plugin import PluginData
from b3.update import B3version

__author__ = 'ThorN, Courgette, xlr8or, Bakes, Ozon, Fenix'
__version__ = '1.43.6'


class Parser:
    _commands = {}  # will hold RCON commands for the current game
    _cron = None  # cron instance
    _events = {}  # available events (K=>EVENT)
    _event_handling_thread = None
    _cron_stats_events = None  # crontab used to log event statistics
    _cron_stats_crontab = None  # crontab used to log cron run statistics
    _timezone_crontab = None  # force recache of timezone info
    _handlers = defaultdict(list)  # event handlers
    _lineTime = re.compile(r'^(?P<minutes>[0-9]+):(?P<seconds>[0-9]+).*')  # used to track log file time changes
    _lineFormat = re.compile('^([a-z ]+): (.*?)', re.IGNORECASE)
    _lineClear = re.compile(r'^(?:[0-9:]+\s?)?')
    _line_color_prefix = ''  # a color code prefix to be added to every line resulting from getWrap
    _line_length = 80  # max wrap length
    _messages = {}  # message template cache
    _multiline = False  # whether linebreaks \n can be manually used in messages
    _multiline_noprefix = False  # whether B3 adds > to multiline messages
    _paused = False  # set to True when B3 is paused
    _pauseNotice = False  # whether to notice B3 being paused
    _plugins = OrderedDict()  # plugin instances
    _port = 0  # the port used by the gameserver for clients connection
    _publicIp = ''  # game server public ip address
    _rconIp = ''  # the ip address where to forward RCON commands
    _rconPort = None  # the virtual port where to forward RCON commands
    _rconPassword = ''  # the rcon password set on the server
    _reColor = re.compile(r'(\^[0-9a-z])|[\x80-\xff]')
    _timeStart = None  # timestamp when B3 has first started
    _tz_offset = None
    _tz_name = None
    _use_color_codes = True  # whether the game supports color codes or not

    clients = None
    config = None  # parser configuration file instance
    delay = 0.33  # time between each game log lines fetching
    delay2 = 0.02  # time between each game log line processing: max number of lines processed in one second
    encoding = 'latin-1'
    game = None
    gameName = None  # console name
    log = None  # logger instance
    logTime = 0  # time in seconds of epoch of game log
    name = 'b3'  # bot name
    output = None  # used to send data to the game server (default to b3.parsers.q3a.rcon.Rcon)
    privateMsg = True  # will be set to True if the game supports private messages
    queue = None  # event queue
    rconTest = True  # whether to perform RCON testing or not
    screen = None
    storage = None  # storage module instance
    type = None
    stop_parsing_event = threading.Event()
    wrapper = None  # textwrapper instance

    deadPrefix = '[DEAD]^7'  # say dead prefix
    msgPrefix = ''  # say prefix
    pmPrefix = '^8[pm]^7'  # private message prefix
    prefix = '^2%s:^3'  # B3 prefix

    # default messages in case one is missing from config file
    _messages_default = {
        "kicked_by": "$clientname^7 was kicked by $adminname^7 $reason",
        "kicked": "$clientname^7 was kicked $reason",
        "banned_by": "$clientname^7 was banned by $adminname^7 $reason",
        "banned": "$clientname^7 was banned $reason",
        "temp_banned_by": "$clientname^7 was temp banned by $adminname^7 for $banduration^7 $reason",
        "temp_banned": "$clientname^7 was temp banned for $banduration^7 $reason",
        "unbanned_by": "$clientname^7 was un-banned by $adminname^7 $reason",
        "unbanned": "$clientname^7 was un-banned $reason",
    }

    # === Exiting ===
    #
    # The parser runs two threads: main and handler.  The main thread is
    # responsible for the main loop parsing and queuing events, and process
    # termination. The handler thread is responsible for processing queued events
    # including raising ``SystemExit'' when a user-requested exit is needed.
    #
    # The ``SystemExit'' exception bubbles up only as far as the top of the handler
    # thread -- the ``handleEvents'' method.  To expose the exit status to the
    # ``run'' method in the main thread, we store the value in ``exitcode''.
    #
    # Since the teardown steps in ``run'' and ``handleEvents'' would occur in
    # parallel, we use a lock (``exiting'') to ensure that ``run'' waits for
    # ``handleEvents'' to finish before proceeding.
    #
    # How exiting works, in detail:
    #
    #   - the main loop in run() and is terminated only when ``stop_parsing_event``
    #     is set in the ``shutdown`` method.
    #   - die() or restart() invokes shutdown() from the handler thread.
    #   - the handler thread sets the ``stop_parsing_event`` and queues a EVT_STOP
    #     event to initiate it's own shutdown.
    #   - die() or restart() raises SystemExit in the handler thread after
    #     shutdown() and a few seconds delay.
    #   - when SystemExit is caught by handleEvents(), its exit status is
    #     pushed to the main context via exitcode.
    #   - run() waits for the event handling thread to stop before exiting

    exitcode = None

    def __init__(self, conf, options):
        """
        Object contructor.
        :param conf: The B3 configuration file
        :param options: command line options
        """
        self._timeStart = self.time()

        if not self.loadConfig(conf):
            print('CRITICAL ERROR : COULD NOT LOAD CONFIG')
            raise SystemExit(2)

        if self.config.has_option('server', 'encoding'):
            self.encoding = self.config.get('server', 'encoding')
        self.__init_logging()
        self.__init_ipaddress()
        self.__init_print_startmessage()
        self.Events = b3.events.eventManager
        self._eventsStats = b3.events.EventsStats(self)
        self.__init_bot()
        self.__init_serverconfig()
        self.__init_storage()
        self.__init_gamelog()
        self.__init_rcon()
        self.__init_rcon_test()
        self.loadEvents()
        self.screen.write(f'Loading events   : {len(self._events)} events loaded\n')
        self.clients = Clients(self)
        self.loadPlugins()
        self.game = b3.game.Game(self, self.gameName)
        self.__init_eventqueue()
        atexit.register(self.shutdown)

    def __init_logging(self):
        logfile = self.config.getpath('b3', 'logfile')
        log2console = self.config.has_option('devmode', 'log2console') and \
                      self.config.getboolean('devmode', 'log2console')
        logfile = b3.functions.getWritableFilePath(logfile, True)
        log_level = self.config.getint('b3', 'log_level')
        try:
            logsize = b3.functions.getBytes(self.config.get('b3', 'logsize'))
        except (TypeError, b3.config.NoOptionError):
            logsize = b3.functions.getBytes('10MB')
        self.log = b3.output.getInstance(logfile, log_level, logsize, log2console)
        self.screen = sys.stdout
        log_short_path = b3.functions.getShortPath(os.path.abspath(b3.functions.getAbsolutePath(logfile, True)))
        self.screen.write(f'Activating log   : {log_short_path}\n')
        self.screen.flush()
        sys.stdout = b3.output.STDOutLogger(self.log)
        sys.stderr = b3.output.STDErrLogger(self.log)

    def __init_print_startmessage(self):
        self.bot('%s', b3.getB3versionString())
        self.bot('Python: %s', sys.version.replace('\n', ''))
        self.bot('Default encoding: %s', sys.getdefaultencoding())
        self.bot('Starting %s v%s for server %s:%s', self.__class__.__name__,
                 getattr(getModule(self.__module__), '__version__', ' Unknown'),
                 self._rconIp, self._port)

    def __init_ipaddress(self):
        self._publicIp = self.config.get('server', 'public_ip')
        self._port = self.config.getint('server', 'port')
        self._rconPort = self._port  # if rcon port is the same as the game port, rcon_port can be ommited
        self._rconIp = self._publicIp  # if rcon ip is the same as the game port, rcon_ip can be ommited
        if self.config.has_option('server', 'rcon_ip'):
            self._rconIp = self.config.get('server', 'rcon_ip')
        if self.config.has_option('server', 'rcon_port'):
            self._rconPort = self.config.getint('server', 'rcon_port')
        if self.config.has_option('server', 'rcon_password'):
            self._rconPassword = self.config.get('server', 'rcon_password')
        try:
            self._rconIp = socket.gethostbyname(self._rconIp)
        except socket.gaierror:
            pass

    def __init_bot(self):
        self.bot('--------------------------------------------')
        if bot_name := self.config.get('b3', 'bot_name'):
            self.name = bot_name
        if bot_prefix := self.config.get('b3', 'bot_prefix'):
            self.prefix = bot_prefix
        else:
            self.prefix = ''
        self.msgPrefix = self.prefix

    def __init_serverconfig(self):
        if self.config.has_option('server', 'delay'):
            delay = self.config.getfloat('server', 'delay')
            if self.delay > 0:
                self.delay = delay
        if self.config.has_option('server', 'lines_per_second'):
            delay2 = self.config.getfloat('server', 'lines_per_second')
            if delay2 > 0:
                self.delay2 = 1 / delay2
        if self.config.has_option('server', 'max_line_length'):
            self._line_length = self.config.getint('server', 'max_line_length')
            self.bot('Setting line_length to: %s', self._line_length)

        if self.config.has_option('server', 'line_color_prefix'):
            self._line_color_prefix = self.config.get('server', 'line_color_prefix')
            self.bot('Setting line_color_prefix to: "%s"', self._line_color_prefix)

        if self.config.has_option('server', 'multiline'):
            self._multiline = self.config.getboolean('server', 'multiline')
            self.bot('Setting multiline to: %s', self._multiline)

        if self.config.has_option('server', 'multiline_noprefix'):
            self._multiline_noprefix = self.config.getboolean('server', 'multiline_noprefix')
            self.bot('Setting multiline_noprefix to: %s', self._multiline_noprefix)

    def __init_storage(self):
        try:
            dsn = self.config.get('b3', 'database')
            self.storage = b3.storage.getStorage(dsn=dsn, dsnDict=splitDSN(dsn), console=self)
        except (AttributeError, ImportError) as e:
            self.critical('Could not setup storage module: %s', e)
        self.storage.connect()

    def __init_gamelog(self):
        if self.config.has_option('server', 'game_log'):
            game_log = self.config.get('server', 'game_log')
            self.bot('Game log is: %s', game_log)
            f = self.config.getpath('server', 'game_log')
            self.bot('Starting bot reading file: %s', os.path.abspath(f))
            self.screen.write(f'Using gamelog    : {b3.functions.getShortPath(os.path.abspath(f))}\n')
            if os.path.isfile(f):
                self.input = open(f, 'r')
                if self.config.has_option('server', 'seek'):
                    seek = self.config.getboolean('server', 'seek')
                    if seek:
                        self.input.seek(0, os.SEEK_END)
                else:
                    self.input.seek(0, os.SEEK_END)
            else:
                self.screen.write(f">>> Cannot read file: {os.path.abspath(f)}\n")
                self.screen.flush()
                self.critical(f"Cannot read file: {os.path.abspath(f)}")
        else:
            self.screen.write("server > game_log setting is required")
            self.screen.flush()
            self.critical("server > game_log setting is required")

    def __init_rcon(self):
        try:
            self.output = b3.rcon.Rcon(self, (self._rconIp, self._rconPort), self._rconPassword)
        except Exception as err:
            self.screen.write(f">>> Cannot setup RCON: {err}\n")
            self.screen.flush()
            self.critical("Cannot setup RCON: %s", err, exc_info=err)

        if self.config.has_option('server', 'rcon_timeout'):
            custom_socket_timeout = self.config.getfloat('server', 'rcon_timeout')
            self.output.socket_timeout = custom_socket_timeout
            self.bot('Setting rcon socket timeout to: %0.3f sec', custom_socket_timeout)

    def __init_rcon_test(self):
        if self.rconTest:
            res = self.output.write('status')
            self.screen.write('Testing RCON     : ')
            self.screen.flush()
            if res in ['Bad rconpassword.', 'Invalid password.']:
                self.screen.write('>>> Oops: Bad RCON password\n'
                                  '>>> Hint: This will lead to errors and render B3 without any power to interact!\n')
                self.screen.flush()
                time.sleep(2)
            elif res == '':
                self.screen.write('>>> Oops: No response\n'
                                  '>>> Could be something wrong with the rcon connection to the server!\n'
                                  '>>> Hint 1: The server is not running or it is changing maps.\n'
                                  '>>> Hint 2: Check your server-ip and port.\n')
                self.screen.flush()
                time.sleep(2)
            else:
                self.screen.write('OK\n')

    def __init_eventqueue(self):
        try:
            queuesize = self.config.getint('b3', 'event_queue_size')
        except b3.config.NoOptionError:
            queuesize = 50
        except ValueError as err:
            queuesize = 50
            self.warning(err)
        self.info("Creating the event queue with size %s", queuesize)
        self.queue = queue.Queue(queuesize)

    def _reset_timezone_info(self):
        """Causes the timezone offset and name to be re-cached"""
        self._tz_offset = None
        self._tz_name = None

    def start(self):
        """
        Start B3
        """
        self.bot("Starting parser..")
        self.startup()
        self.say(f'{b3.version} ^2[ONLINE]')
        self.call_plugins_onLoadConfig()
        self.bot("Starting plugins")
        self.startPlugins()
        self.schedule_cron_tasks()
        self.bot("All plugins started")
        self.pluginsStarted()
        self.bot("Starting event dispatching thread")
        self._event_handling_thread = start_daemon_thread(
            target=self.handleEvents, name='event_handler'
        )
        self.bot("Start reading game events")
        self.run()

    def _dump_events_stats(self):
        """
        Dump event statistics into the B3 log file.
        """
        self._eventsStats.dump_stats()

    def _dump_cron_stats(self):
        self.info('***** CronTab Stats *****')
        for tab in self.cron.entries():
            if stats := tab.run_stats:
                mean, stdv = b3.functions.meanstdv(stats)
                self.info('%s: min(%0.4f), max(%0.4f), mean(%0.4f), stdv(%0.4f), samples(%i)',
                           tab, min(stats), max(stats), mean, stdv, len(stats))
            else:
                self.info('%s: no stats available', tab)

    def schedule_cron_tasks(self):
        if self.log.isEnabledFor(b3.output.DEBUG):
            self._cron_stats_events = b3.cron.CronTab(self._dump_events_stats, minute='15')
            self.cron.add(self._cron_stats_events)

            self._cron_stats_crontab = b3.cron.CronTab(self._dump_cron_stats, minute='30')
            self.cron.add(self._cron_stats_crontab)

        tz_offset, tz_name = self.tz_offset_and_name()
        if tz_name not in ("UTC", "GMT"):
            hour = self.to_utc_hour(2)
            self._timezone_crontab = b3.cron.CronTab(self._reset_timezone_info, minute=1, hour=hour)
            self.bot("Timezone reset scheduled daily at UTC %s:%s", hour, "01")
            self.cron.add(self._timezone_crontab)

    def die(self):
        """
        Stop B3 with the die exit status (0)
        """
        self.exitcode = 0
        self.shutdown()
        self.finalize()

    def restart(self):
        """
        Stop B3 with the restart exit status (221)
        """
        self.exitcode = 4
        self.bot('Restarting...')
        self.shutdown()
        self.finalize()

    def upTime(self):
        """
        Amount of time B3 has been running
        """
        return self.time() - self._timeStart

    def loadConfig(self, conf):
        """
        Set the config file to load
        """
        if not conf:
            return False

        self.config = conf
        """:type : MainConfig"""
        return True

    def saveConfig(self):
        """
        Save configration changes
        """
        self.bot('Saving config: %s', self.config.fileName)
        return self.config.save()

    def startup(self):
        """
        Called after the parser is created before run(). Overwrite this
        for anything you need to initialize you parser with.
        """
        pass

    def pluginsStarted(self):
        """
        Called after the parser loaded and started all plugins. 
        Overwrite this in parsers to take actions once plugins are ready
        """
        pass

    def pause(self):
        """
        Pause B3 log parsing
        """
        self.bot('PAUSING')
        self._paused = True

    def unpause(self):
        """
        Unpause B3 log parsing
        """
        self._paused = False
        self._pauseNotice = False
        self.input.seek(0, os.SEEK_END)

    def loadEvents(self):
        """
        Load events from event manager
        """
        self._events = self.Events.events

    def createEvent(self, key, name=None):
        """
        Create a new event
        """
        self.Events.createEvent(key, name)
        self._events = self.Events.events
        return self._events[key]

    def getEventID(self, key):
        """
        Get the numeric ID of an event key
        """
        return self.Events.getId(key)

    def getEvent(self, key, data=None, client=None, target=None):
        """
        Return a new Event object for an event name
        """
        return b3.events.Event(self.Events.getId(key), data, client, target)

    def getEventName(self, key):
        """
        Get the name of an event by its key
        """
        return self.Events.getName(key)

    def getEventKey(self, event_id):
        """
        Get the key of a given event ID
        """
        return self.Events.getKey(event_id)

    def getPlugin(self, plugin):
        """
        Get a reference to a loaded plugin
        """
        return self._plugins.get(plugin)

    def reloadConfigs(self):
        """
        Reload all config files
        """
        # reload main config
        self.config.load(self.config.fileName)
        for plugin_name, plugin in self._plugins.items():
            self.bot('Reload configuration file for plugin %s', plugin_name)
            plugin.loadConfig()

    def loadPlugins(self):
        """
        Load plugins specified in the config
        """
        self.screen.write('Loading plugins  : ')
        self.screen.flush()

        extplugins_dir = self.config.get_external_plugins_dir()
        self.bot('Loading plugins (external plugin directory: %s)', extplugins_dir)

        def _get_plugin_config(p_name, p_clazz, p_config_path=None):
            """
            Helper that load and return a configuration file for the given Plugin
            :param p_name: The plugin name
            :param p_clazz: The class implementing the plugin
            :param p_config_path: The plugin configuration file path
            """

            def _search_config_file(match):
                """
                Helper that returns a list of configuration files.
                :param match: The plugin name
                """
                # first look in the built-in plugins directory
                search = '%s%s*%s*' % (b3.functions.getAbsolutePath('@conf\\', decode=True), os.path.sep, match)
                self.debug('Searching for configuration file(s) matching: %s', search)
                collection = glob.glob(search)
                if len(collection) > 0:
                    return collection
                # if none is found, then search in the extplugins directory
                search = '%s%s*%s*' % (
                    os.path.join(b3.functions.getAbsolutePath(extplugins_dir, decode=True), match, 'conf'), os.path.sep, match)
                self.debug('Searching for configuration file(s) matching: %s', search)
                collection = glob.glob(search)
                return collection

            if p_config_path is None:
                # no plugin configuration file path specified: we can still load the plugin
                # if there is non need for a configuration file, otherwise we will lookup one
                if not p_clazz.requiresConfigFile:
                    self.debug('No configuration file specified for plugin %s: '
                               'is not required either', p_name)
                    return None

                # lookup a configuration file for this plugin
                self.warning('No configuration file specified for plugin %s: '
                             'searching a valid configuration file...', p_name)

                search_path = _search_config_file(p_name)
                if len(search_path) == 0:
                    # raise an exception so the plugin will not be loaded (since we miss the needed config file)
                    raise b3.config.ConfigFileNotFound(f'could not find any configuration file for plugin {p_name}')
                if len(search_path) > 1:
                    # log all the configuration files found so users can decide to remove some of them on the next B3 startup
                    self.warning('Multiple configuration files found for plugin %s: %s', p_name, ', '.join(search_path))

                # if the load fails, an exception is raised and the plugin won't be loaded
                self.warning('Using %s as configuration file for plugin %s', search_path[0], p_name)
                self.bot('Loading configuration file %s for plugin %s', search_path[0], p_name)
                return b3.config.load(search_path[0])
            else:
                # configuration file specified: load it if it's found. If we are not able to find the configuration
                # file, then keep loading the plugin if such a plugin doesn't require a configuration file (optional)
                # otherwise stop loading the plugin and loag an error message.
                p_config_absolute_path = b3.functions.getAbsolutePath(p_config_path, decode=True)
                if os.path.exists(p_config_absolute_path):
                    self.bot('Loading configuration file %s for plugin %s', p_config_absolute_path, p_name)
                    return b3.config.load(p_config_absolute_path)

                # notice missing configuration file
                self.warning('Could not find specified configuration file %s for plugin %s',
                             p_config_absolute_path, p_name)

                if p_clazz.requiresConfigFile:
                    # stop loading the plugin
                    raise b3.config.ConfigFileNotFound(f'plugin {p_name} cannot be '
                                                       'loaded without a configuration file')

                self.warning('Not loading a configuration file for plugin %s: '
                             'plugin %s can work also without a configuration file',
                             p_name, p_name)
                self.info('NOTE: plugin %s may behave differently from what '
                          'expected since no user configuration file has '
                          'been loaded', p_name)
                return None

        plugin_list = []  # hold an unsorted plugins list used to filter plugins that needs to be excluded
        plugin_required = []  # hold a list of required plugin names which have not been specified in b3.ini
        sorted_plugin_list = []  # hold the list of plugins sorted according requirements
        plugins = OrderedDict()  # no need for OrderedDict anymore but keep for backwards compatibility!

        # here below we will parse the plugins section of b3.ini, looking for plugins to be loaded.
        # we will import needed python classes and generate configuration file instances for plugins.
        for p in self.config.get_plugins():

            if p['name'] in [plugins[i].name for i in plugins if plugins[i].name == p['name']]:
                # do not load a plugin multiple times
                self.warning('Plugin %s already loaded: avoid multiple entries of the same plugin', p['name'])
                continue

            try:
                mod = self.pluginImport(p['name'], p['path'])
                clz = getattr(mod, '%sPlugin' % p['name'].title())
                cfg = _get_plugin_config(p['name'], clz, p['conf'])
                plugins[p['name']] = PluginData(name=p['name'],
                                                module=mod,
                                                clazz=clz,
                                                conf=cfg,
                                                disabled=p['disabled'])
            except Exception as err:
                self.error('Could not load plugin %s', p['name'], exc_info=err)

        # check for AdminPlugin
        if 'admin' not in plugins:
            # critical will exit, admin plugin must be loaded!
            self.critical('Plugin admin is essential and MUST be loaded! '
                          'Cannot continue without admin plugin')

        # at this point we have an OrderedDict of PluginData of plugins listed in b3.ini and which can be loaded correctly:
        # all the plugins which have not been installed correctly, but are specified in b3.ini, have been already excluded.
        # next we build a list of PluginData instances and then we will sort it according to plugin order importance:
        #   - we'll try to load other plugins required by a listed one
        #   - we'll remove plugin that do not meet requirements

        def _get_plugin_data(p_data):
            """
            Return a list of PluginData of plugins needed by the current one
            :param p_data: A PluginData containing plugin information
            :return: list[PluginData] a list of PluginData of plugins needed by the current one
            """
            if p_data.clazz:

                # check for correct B3 version
                if p_data.clazz.requiresVersion and B3version(p_data.clazz.requiresVersion) > B3version(currentVersion):
                    raise b3.config.MissingRequirement(f'plugin {p_data.name} requires B3 version '
                                             f'{p_data.clazz.requiresVersion} (you have version {currentVersion}) '
                                             ': please update your B3 if you want to run this plugin')

                # check if the current game support this plugin (this may actually exclude more than one plugin
                # in case a plugin is built on top of an incompatible one, due to plugin dependencies)
                if p_data.clazz.requiresParsers and self.gameName not in p_data.clazz.requiresParsers:
                    raise b3.config.MissingRequirement(f'plugin {p_data.name} is not compatible with '
                                             f'{self.gameName} parser : supported games are :'
                                             f' {", ".join(p_data.clazz.requiresParsers)}')

                # check if the plugin needs a particular storage protocol to work
                if p_data.clazz.requiresStorage and self.storage.protocol not in p_data.clazz.requiresStorage:
                    raise b3.config.MissingRequirement(
                        f'plugin {p_data.name} is not compatible with the storage protocol being used ({self.storage.protocol}) : '
                        f'supported protocols are : {", ".join(p_data.clazz.requiresStorage)}')

                # check for plugin dependency
                if p_data.clazz.requiresPlugins:
                    # DFS: look first at the whole requirement tree and try to load from ground up
                    collection = [p_data]
                    for r in p_data.clazz.requiresPlugins:
                        if r not in plugins and r not in plugin_required:
                            try:
                                # missing requirement, try to load it
                                self.debug('Plugin %s has unmet dependency : %s : trying to load plugin %s...',
                                           p_data.name, r, r)
                                collection += _get_plugin_data(PluginData(name=r))
                                self.debug('Plugin %s dependency satisfied: %s', p_data.name, r)
                            except Exception as ex:
                                raise b3.config.MissingRequirement(
                                    f'missing required plugin: {r} : {extract_tb(sys.exc_info()[2])}', ex)

                    return collection

            # plugin has not been loaded manually nor a previous automatic load attempt has been done
            if p_data.name not in plugins and p_data.name not in plugin_required:
                # we are at the bottom step where we load a new requirement by importing the
                # plugin module, class and configuration file. If the following generate an exception, recursion
                # will catch it here above and raise it back so we can exclude the first plugin in the list from load
                self.debug('Looking for plugin %s module and configuration file...', p_data.name)
                p_data.module = self.pluginImport(p_data.name)
                p_data.clazz = getattr(p_data.module, f'{p_data.name.title()}Plugin')
                p_data.conf = _get_plugin_config(p_data.name, p_data.clazz)
                plugin_required.append(p_data.name)  # load just once

            return [p_data]

        # construct a list of all the plugins which needs to be loaded
        # here below we will discard all the plugin which have unmet dependency
        for plugin_name, plugin_data in plugins.items():
            try:
                plugin_list += _get_plugin_data(plugin_data)
            except b3.config.MissingRequirement as err:
                self.error('Could not load plugin %s', plugin_name, exc_info=err)

        plugin_dict = {x.name: x for x in plugin_list}  # dict(str, PluginData)
        plugin_data = plugin_dict.pop('admin')  # remove admin plugin from dict
        plugin_list.remove(plugin_data)  # remove admin plugin from unsorted list
        sorted_plugin_list.append(plugin_data)  # put admin plugin as first and discard from the sorting

        # sort remaining plugins according to their inclusion requirements
        self.bot('Sorting plugins according to their dependency tree...')
        sorted_list = [y for y in
                       topological_sort([(x.name, set(x.clazz.requiresPlugins + [z for z in
                                                                                 x.clazz.loadAfterPlugins if
                                                                                 z in plugin_dict])) for x in
                                         plugin_list])]

        for plugin_name in sorted_list:
            sorted_plugin_list.append(plugin_dict[plugin_name])

        # make sure that required plugins are enabled (both if loaded in b3.ini or loaded automatically)
        for plugin_data in sorted_plugin_list:
            if plugin_data.disabled:
                if plugin_data.name == 'admin':
                    plugin_data.enabled = True
                else:
                    if plugin_data.clazz.requiresPlugins:
                        for req in plugin_data.clazz.requiresPlugins:
                            plugin_dict = {x.name: x for x in sorted_plugin_list}
                            if req in plugin_dict and plugin_dict[req].enabled:
                                plugin_data.enabled = True

        # notice in log for later inspection
        self.bot('Ready to create plugin instances: %s', ', '.join([x.name for x in sorted_plugin_list]))

        plugin_num = 1
        self._plugins = OrderedDict()
        for plugin_data in sorted_plugin_list:

            plugin_conf_path = '--' if plugin_data.conf is None else plugin_data.conf.fileName

            try:
                self.bot('Loading plugin #%s : %s [%s]', plugin_num, plugin_data.name, plugin_conf_path)
                self._plugins[plugin_data.name] = plugin_data.clazz(self, plugin_data.conf)
            except Exception as err:
                self.error('Could not load plugin %s', plugin_data.name, exc_info=err)
                self.screen.write('x')
            else:
                if plugin_data.disabled:
                    self.info("Disabling plugin %s", plugin_data.name)
                    self._plugins[plugin_data.name].disable()
                plugin_num += 1
                version = getattr(plugin_data.module, '__version__', 'Unknown Version')
                author = getattr(plugin_data.module, '__author__', 'Unknown Author')
                self.bot('Plugin %s (%s - %s) loaded', plugin_data.name, version, author)
                self.screen.write('.')
            finally:
                self.screen.flush()

        self.screen.write(' (%s)\n' % len(self._plugins))
        self.screen.flush()

    def call_plugins_onLoadConfig(self):
        """
        For each loaded plugin, call the onLoadConfig hook.
        """
        for _, plugin in self._plugins.items():
            plugin.onLoadConfig()

    def pluginImport(self, name, path=None):
        """
        Import a single plugin.
        :param name: The plugin name
        :param path: The path to the plugin
        """
        if path:
            # import error is being handled in loadPlugins already
            self.info('Loading plugin from specified path: %s', path)
            if path not in sys.path:
                self.warning('Appending path %s to sys.path', path)
                sys.path.append(path)
            return importlib.import_module(name)

        try:
            return importlib.import_module(f'b3.plugins.{name}')
        except ImportError as m:
            ext_plugin_dir = self.config.get_external_plugins_dir()
            self.info('%s is not a built-in plugin (%s)', name.title(), m)
            self.info('Trying external plugin directory : %s', ext_plugin_dir)
            if ext_plugin_dir not in sys.path:
                self.warning('Appending external directory %s to sys.path',
                             ext_plugin_dir)
                sys.path.append(ext_plugin_dir)
            return importlib.import_module(name)

    def startPlugins(self):
        """
        Start all loaded plugins.
        """
        self.screen.write('Starting plugins : ')
        self.screen.flush()

        plugin_num = 1
        for plugin_name, plugin in self._plugins.items():

            try:
                self.bot('Starting plugin #%s : %s', plugin_num, plugin_name)
                plugin.onStartup()
                plugin.start()
            except Exception as err:
                self.error("Could not start plugin %s", plugin_name, exc_info=err)
                self.screen.write('x')
            else:
                self.screen.write('.')
                plugin_num += 1
            finally:
                self.screen.flush()

        self.screen.write(f' ({str(plugin_num - 1)})\n')

    def disablePlugins(self):
        """
        Disable all plugins except for 'admin'
        """
        for plugin_name, plugin in self._plugins.items():
            if plugin_name != 'admin':
                self.bot('Disabling plugin: %s', plugin_name)
                plugin.disable()

    def enablePlugins(self):
        """
        Enable all plugins except for 'admin'
        """
        for plugin_name, plugin in self._plugins.items():
            if plugin_name != 'admin':
                self.bot('Enabling plugin: %s', plugin_name)
                plugin.enable()

    def getMessage(self, msg, *args):
        """
        Return a message from the config file
        """
        try:
            msg = self._messages[msg]
        except KeyError:
            try:
                msg = self._messages[msg] = self.config.getTextTemplate('messages', msg)
            except Exception as err:
                self.warning("Falling back on default message for '%s': %s", msg, err)
                msg = vars2printf(self._messages_default.get(msg, '')).strip()

        if args:
            if type(args[0]) == dict:
                return msg % args[0]
            else:
                return msg % args
        else:
            return msg

    @staticmethod
    def getMessageVariables(*args, **kwargs):
        """
        Dynamically generate a dictionary of fields available for messages in config file.
        """
        variables = {}
        for obj in args:
            if obj is None:
                continue
            if type(obj).__name__ in ('str', 'unicode'):
                if obj not in variables:
                    variables[obj] = obj
            else:
                for attr in vars(obj):
                    pattern = re.compile(r'[\W_]+')
                    cleanattr = pattern.sub('', attr)  # trim any underscore or any non alphanumeric character
                    variables[cleanattr] = getattr(obj, attr)

        for key, obj in kwargs.items():
            # self.debug('Type of kwarg %s: %s' % (key, type(obj).__name__))
            if obj is None:
                continue
            if type(obj).__name__ in ('str', 'unicode'):
                if key not in variables:
                    variables[key] = obj
            # elif type(obj).__name__ == 'instance':
            # self.debug('Classname of object %s: %s' % (key, obj.__class__.__name__))
            else:
                for attr in vars(obj):
                    pattern = re.compile(r'[\W_]+')
                    cleanattr = pattern.sub('', attr)  # trim any underscore or any non alphanumeric character
                    currkey = ''.join([key, cleanattr])
                    variables[currkey] = getattr(obj, attr)

        return variables

    def getCommand(self, cmd, **kwargs):
        """
        Return a reference to a loaded command
        """
        if cmd := self._commands.get(cmd):
            return cmd % kwargs

    @functools.lru_cache(maxsize=None)
    def getGroup(self, data):
        """
        Return a valid Group from storage.
        <data> can be either a group keyword or a group level.
        Raises KeyError if group is not found.
        """
        if type(data) is int or isinstance(data, str) and data.isdigit():
            g = Group(level=data)
        else:
            g = Group(keyword=data)
        return self.storage.getGroup(g)

    def getGroupLevel(self, data):
        """
        Return a valid Group level.
        <data> can be either a group keyword or a group level.
        Raises KeyError if group is not found.
        """
        return self.getGroup(data).level

    def to_utc_hour(self, hour):
        """
        :param hour: an hour (0-23)
        :return: hour adjusted to UTC using detected timezone offset
        """
        tz_offset, _ = self.tz_offset_and_name()
        return (hour - tz_offset) % 24

    def tz_offset_and_name(self):
        """
        Returns the timezone offset and name configured for this console
        :return: tuple(tzoffset, tzname)
        """
        tz_offset = self._tz_offset
        tz_name = self._tz_name
        if tz_name and tz_offset is not None:
            return tz_offset, tz_name

        if self.config.has_option("b3", "time_zone"):
            tz_name = self.config.get("b3", "time_zone").strip().upper()
        else:
            tz_name = "LOCAL"

        if tz_name in ("UTC", "GMT"):
            self._tz_name = tz_name = "UTC"
            self._tz_offset = tz_offset = 0
        else:
            local_dt = datetime.datetime.now().astimezone()
            tz_offset = int(local_dt.utcoffset().total_seconds() / 3600)
            tz_name = local_dt.strftime("%Z")
            if " " in tz_name:
                tz_name = "".join([x[:1] for x in tz_name.split()])
            self._tz_name = tz_name
            self._tz_offset = tz_offset

        self.info("Using timezone: %s offset (%s)", tz_name, tz_offset)
        return tz_offset, tz_name

    def formatTime(self, gmttime, tz_name=None):
        """
        Return a time string formatted to local time in the b3 config time_format
        :param gmttime: The current GMT time
        :param tz_name: The timezone name to be used for time formatting
        """
        if tz_name:
            # if a timezone name has been specified try to use it to format the given gmttime
            tz_name = str(tz_name).strip().upper()
            try:
                # used when the user manually specifies the offset (i.e: !time +4)
                tz_offset = float(tz_name)
            except ValueError:
                # treat it as a timezone name (can potentially fallback to autodetection mode)
                tz_offset, tz_name = self.tz_offset_and_name()
        else:
            # use the timezone name specified in b3 main configuration file (if specified),
            # or make use of the timezone offset autodetection
            tz_offset, tz_name = self.tz_offset_and_name()

        time_format = self.config.get('b3', 'time_format').replace('%Z', tz_name).replace('%z', tz_name)
        return time.strftime(time_format, time.gmtime(gmttime + int(tz_offset * 3600)))

    def run(self):
        """
        Main worker thread for B3
        """
        self.screen.write(
            "Startup complete : B3 is running! Let's get to work!\n\n"
        )
        self.screen.write(
            'If you run into problems check your B3 log file for '
            'more information\n'
        )
        self.screen.flush()

        stop_parsing_event_wait = self.stop_parsing_event.wait
        read_lines = self.read
        parse_line = self.parseLine

        while True:
            if self._paused:
                if not self._pauseNotice:
                    self.bot('PAUSED - not parsing any lines')
                    self._pauseNotice = True
                if stop_parsing_event_wait(timeout=self.delay):
                    break
                continue
            for line in read_lines():
                if line := line.strip():
                    try:
                        parse_line(line)
                    except Exception as msg:
                        self.error('Could not parse line %s - (%s) %s',
                                   line, msg, extract_tb(sys.exc_info()[2]))
                    if stop_parsing_event_wait(timeout=self.delay2):
                        break

            if stop_parsing_event_wait(timeout=self.delay):
                break

        self.bot('Stopped parsing')
        self.bot('Closing games log file')
        self.input.close()
        self.bot('Awaiting Event Handling Thread stop')
        self._event_handling_thread.join(timeout=15.0)
        self.bot('Event Handling Thread stopped')
        if self.exitcode:
            sys.exit(self.exitcode)

    def parseLine(self, line):
        """
        Parse a single line from the log file
        """
        if m := re.match(self._lineFormat, line):
            self.queueEvent(b3.events.Event(self.getEventID('EVT_UNKNOWN'), m.group(2)[:1]))

    def registerHandler(self, event_name, event_handler):
        """
        Register an event handler.
        """
        self.debug('%s: register event <%s>',
                   event_handler.__class__.__name__, self.getEventName(event_name))
        if event_handler not in self._handlers[event_name]:
            self._handlers[event_name].append(event_handler)

    def unregisterHandler(self, event_handler):
        """
        Unregister an event handler.
        """
        for event_name, handlers in self._handlers.items():
            if event_handler in handlers:
                self.debug('%s: unregister event <%s>',
                           event_handler.__class__.__name__, self.getEventName(event_name))
                handlers.remove(event_handler)

    def queueEvent(self, event, expire=15):
        try:
            if event.type in self._handlers:
                time.sleep(0.001)  # wait a bit so event doesnt get jumbled
                current_time = self.time()
                self.queue.put((current_time, current_time + expire, event), timeout=2)
                return True
        except queue.Full:
            self.error('**** Event queue was full (%s)', self.queue.qsize())
        except AttributeError:
            self.error('*** Event has no type: %s', event)
        return False

    def handleEvents(self):
        """
        Event handler thread.
        """
        console_time = self.time
        event_queue_get = self.queue.get
        stop_events = (self.getEventID('EVT_EXIT'), self.getEventID('EVT_STOP'))
        while True:
            added, expire, event = event_queue_get()
            current_time = console_time()
            if event.type in stop_events:
                break
            event_name = self.getEventName(event.type)
            if current_time > expire:
                self.error('**** Event sat in queue too long: %s '
                           'created %s, added %s, current %s, '
                           'expired %s, total (%s)',
                           event_name, event.time, added, current_time,
                           expire, current_time - added)
                continue

            for hfunc in self._handlers[event.type]:
                if not hfunc.isEnabled():
                    continue
                timer_plugin_begin = time.perf_counter()
                thread_plugin_begin = time.thread_time()
                try:
                    hfunc.parseEvent(event)
                    time.sleep(0.001)
                except b3.events.VetoEvent:
                    # plugin called for a halt to event processing
                    self.bot('Event %s vetoed by %s', event_name, str(hfunc))
                    break
                except Exception as msg:
                    self.error('Handler %s could not handle event %s: %s: %s %s',
                               hfunc.__class__.__name__,
                               event_name, msg.__class__.__name__,
                               msg,
                               extract_tb(sys.exc_info()[2]))
                finally:
                    if (elapsed := time.perf_counter() - timer_plugin_begin) > 2.0:
                        elapsed_thread = time.thread_time() - thread_plugin_begin
                        self.warning('Handler %s took more that 2 seconds '
                                     'to handle %s: total %0.4f / thread %0.4f',
                                     hfunc.__class__.__name__, event_name, elapsed, elapsed_thread)
                    self._eventsStats.add_event_handled(hfunc.__class__.__name__,
                                                        event_name, elapsed)

        self.handle_events_shutdown()

    def handle_events_shutdown(self):
        self.bot('Shutting down event handler')

        if not self.stop_parsing_event.is_set():
            self.stop_parsing_event.set()

        self.bot('Sending EVT_STOP message to all plugins')
        event = b3.events.Event(self.getEventID('EVT_STOP'), '')
        for plugin in self._plugins.values():
            try:
                plugin.parseEvent(event)
            except Exception as e:
                self.error(e)

        self.bot('Stopping cron')
        try:
            self._cron.stop()
        except Exception as e:
            self.error(e)

        self.bot('Shutting down database connection')
        try:
            self.storage.shutdown()
        except Exception as e:
            self.error(e)

        self.bot('Shutting down RCON connection')
        try:
            self.output.close()
        except Exception as e:
            self.error(e)

    def write(self, msg, maxRetries=None, socketTimeout=None):
        """
        Write a message to Rcon/Console
        """
        return self.output.write(msg, maxRetries=maxRetries, socketTimeout=socketTimeout)

    def writelines(self, msg):
        """
        Write a sequence of messages to Rcon/Console. Optimized for speed.
        :param msg: The message to be sent to Rcon/Console.
        """
        if msg:
            return self.output.writelines(msg)

    def read(self):
        """
        Read from game server log file
        """
        if not (lines := self.input.readlines()):
            # No lines found so check to see if we need to reset our position.
            # Compare the current cursor position against the current file size,
            # if the cursor is at a number higher than the game log size, then
            # there's a problem
            filestats = os.fstat(self.input.fileno())
            if self.input.tell() > filestats.st_size:
                self.warning('Parser: game log is suddenly smaller than it was '
                             f'before ({self.input.tell()} bytes, now {filestats.st_size}), '
                             'the log was probably either rotated or emptied. B3 will now re-adjust to '
                             'the new size of the log')
                self.input.seek(0, os.SEEK_END)
                lines = self.input.readlines()

        return lines

    def shutdown(self):
        """
        Shutdown B3.
        """
        self.bot('Shutting down...')
        self.stop_parsing_event.set()
        self.queueEvent(b3.events.Event(self.getEventID('EVT_STOP'), ''))

    def finalize(self):
        """
        Commons operation to be done on B3 shutdown.
        Called internally by b3.parser.die()
        """
        pass

    def getWrap(self, text):
        """
        Returns a sequence of lines for text that fits within the limits.
        And wrap if \n character encountered.
        :param text: The text that needs to be splitted.
        """
        if not text:
            return []

        # remove all color codes if not needed
        if not self._use_color_codes:
            text = self.stripColors(text)

        if not self.wrapper:
            # initialize the text wrapper if not already instantiated
            self.wrapper = TextWrapper(width=self._line_length, drop_whitespace=True,
                                       break_long_words=True, break_on_hyphens=False)

        # Apply wrap + manual linebreak
        if self._multiline:
            wrapped_text = []
            for line in text.split(r'\n'):
                if line.strip() != '':
                    wrapped_text.extend(self.wrapper.wrap(line))
        # Apply only wrap
        else:
            wrapped_text = self.wrapper.wrap(text)

        if self._use_color_codes:
            lines = []
            color = self._line_color_prefix
            for line in wrapped_text:
                if not lines or self._multiline_noprefix:
                    lines.append(f'{color}{line}')
                else:
                    lines.append(f'^3>{color}{line}')
                match = re.findall(self._reColor, line)
                if match:
                    color = match[-1]
            return lines
        else:
            if self._multiline_noprefix:
                lines = wrapped_text
            else:
                # we still need to add the > prefix w/o color codes
                # to all the lines except the first one
                lines = [wrapped_text[0]]
                if len(wrapped_text) > 1:
                    for line in wrapped_text[1:]:
                        lines.append(f'>{line}')
            return lines

    def error(self, msg, *args, **kwargs):
        """
        Log an ERROR message.
        """
        self.log.error(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        """
        Log a DEBUG message.
        """
        self.log.debug(msg, *args, **kwargs)

    def bot(self, msg, *args, **kwargs):
        """
        Log a BOT message.
        """
        self.log.bot(msg, *args, **kwargs)

    def verbose(self, msg, *args, **kwargs):
        """
        Log a VERBOSE message.
        """
        self.log.verbose(msg, *args, **kwargs)

    def verbose2(self, msg, *args, **kwargs):
        """
        Log an EXTRA VERBOSE message.
        """
        self.log.verbose2(msg, *args, **kwargs)

    def console(self, msg, *args, **kwargs):
        """
        Log a CONSOLE message.
        """
        self.log.console(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """
        Log a WARNING message.
        """
        self.log.warning(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """
        Log an INFO message.
        """
        self.log.info(msg, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        """
        Log an EXCEPTION message.
        """
        self.log.exception(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        """
        Log a CRITICAL message and shutdown B3.
        """
        self.log.critical(msg, *args, **kwargs)
        self.exitcode = 2
        self.shutdown()
        self.finalize()

    @staticmethod
    def time():
        """
        Return the current time in GMT/UTC.
        """
        return int(time.time())

    def _get_cron(self):
        """
        Instantiate the main Cron object.
        """
        if not self._cron:
            self._cron = b3.cron.Cron(self)
            self._cron.start()
        return self._cron

    cron = property(_get_cron)

    def stripColors(self, text):
        """
        Remove color codes from the given text.
        :param text: the text to clean from color codes.
        :return: str
        """
        return re.sub(self._reColor, '', text).strip()

    # INHERITING CLASSES MUST IMPLEMENTS THE FOLLOWING METHODS
    # PLUGINS THAT ARE GAME INDEPENDENT ASSUME THESE METHODS EXIST
    def getPlayerList(self):
        """
        Query the game server for connected players.
        return a dict having players' id for keys and players' data as another dict for values
        """
        raise NotImplementedError

    def authorizeClients(self):
        """
        For all connected players, fill the client object with properties allowing to find 
        the user in the database (usualy guid, or ip) and call the
        Client.auth() method 
        """
        raise NotImplementedError

    def sync(self):
        """
        For all connected players returned by self.getPlayerList(), get the matching Client
        object from self.clients (with self.clients.getByCID(cid) or similar methods) and
        look for inconsistencies. If required call the client.disconnect() method to remove
        a client from self.clients.
        This is mainly useful for games where clients are identified by the slot number they
        occupy. On map change, a player A on slot 1 can leave making room for player B who
        connects on slot 1.
        """
        raise NotImplementedError

    def say(self, msg, *args):
        """
        Broadcast a message to all players
        """
        raise NotImplementedError

    def saybig(self, msg, *args):
        """
        Broadcast a message to all players in a way that will catch their attention.
        """
        raise NotImplementedError

    def message(self, client, text, *args):
        """
        Display a message to a given player
        """
        raise NotImplementedError

    def kick(self, client, reason='', admin=None, silent=False, *kwargs):
        """
        Kick a given player
        """
        raise NotImplementedError

    def ban(self, client, reason='', admin=None, silent=False, *kwargs):
        """
        Ban a given player on the game server and in case of success
        fire the event ('EVT_CLIENT_BAN', data={'reason': reason, 
        'admin': admin}, client=target)
        """
        raise NotImplementedError

    def unban(self, client, reason='', admin=None, silent=False, *kwargs):
        """
        Unban a given player on the game server
        """
        raise NotImplementedError

    def tempban(self, client, reason='', duration=2, admin=None, silent=False, *kwargs):
        """
        Tempban a given player on the game server and in case of success
        fire the event ('EVT_CLIENT_BAN_TEMP', data={'reason': reason, 
        'duration': duration, 'admin': admin}, client=target)
        """
        raise NotImplementedError

    def getMap(self):
        """
        Return the current map/level name
        """
        raise NotImplementedError

    def getNextMap(self):
        """
        Return the next map/level name to be played
        """
        raise NotImplementedError

    def getMaps(self):
        """
        Return the available maps/levels name
        """
        raise NotImplementedError

    def rotateMap(self):
        """
        Load the next map/level
        """
        raise NotImplementedError

    def changeMap(self, map_name):
        """
        Load a given map/level
        Return a list of suggested map names in cases it fails to recognize the map that was provided
        """
        raise NotImplementedError

    def getPlayerPings(self, filter_client_ids=None):
        """
        Returns a dict having players' id for keys and players' ping for values
        :param filter_client_ids: If filter_client_id is an iterable, only return values for the given client ids.
        """
        raise NotImplementedError

    def getPlayerScores(self):
        """
        Returns a dict having players' id for keys and players' scores for values
        """
        raise NotImplementedError

    def inflictCustomPenalty(self, penalty_type, client, reason=None, duration=None, admin=None, data=None):
        """
        Called if b3.admin.penalizeClient() does not know a given penalty type. 
        Overwrite this to add customized penalties for your game like 'slap', 'nuke', 
        'mute', 'kill' or anything you want.
        IMPORTANT: This method must return True if the penalty was inflicted.
        """
        pass

    def queryClientFrozenSandAccount(self, cid):
        pass


class StubParser:
    """
    Parser implementation used when dealing with the Storage module while updating B3 database.
    """

    screen = sys.stdout

    def __init__(self):
        class StubSTDOut:
            def write(self, *args, **kwargs):
                pass

        self.screen = StubSTDOut()

    def bot(self, msg, *args, **kwargs):
        pass

    def info(self, msg, *args, **kwargs):
        pass

    def debug(self, msg, *args, **kwargs):
        pass

    def error(self, msg, *args, **kwargs):
        pass

    def warning(self, msg, *args, **kwargs):
        pass

    def verbose(self, msg, *args, **kwargs):
        pass

    def verbose2(self, msg, *args, **kwargs):
        pass

    def critical(self, msg, *args, **kwargs):
        pass
