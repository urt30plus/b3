import functools
import random
import re
import os
import threading
import time

import b3
import b3.config
import b3.cron
import b3.events
import b3.plugin
from b3.functions import clamp
from . import __author__
from . import __version__


class Poweradminurt43Plugin(b3.plugin.Plugin):
    requiresParsers = ['iourt43']

    # ClientUserInfo and ClientUserInfoChanged lines return different names, unsanitized and sanitized
    # this regexp designed to make sure either one is sanitized before namecomparison in onNameChange()
    _reClean = re.compile(r'(\^.)|[\x00-\x20]|[\x7E-\xff]', re.I)

    _adminPlugin = None
    _ignoreTill = 0
    _checkdupes = True
    _checkunknown = True
    _checkbadnames = True
    _checkchanges = True
    _checkallowedchanges = 7
    _ncronTab = None
    _tcronTab = None
    _scronTab = None
    _skcronTab = None
    _ninterval = 0
    _tinterval = 0
    _sinterval = 0
    _skinterval = 0
    _minbalinterval = 2  # minimum time in minutes between !bal or !sk for non-mods
    _lastbal = 0  # time since last !bal or !sk
    _oldadv = (None, None, None)
    _teamred = 0
    _teamblue = 0
    _teamdiff = 1
    _skilldiff = 0.5
    _skill_balance_mode = 0
    _balancing = False
    _origvote = 0
    _lastvote = 0
    _votedelay = 0
    _tmaxlevel = 20
    _announce = 2
    _smaxspectime = 0
    _smaxlevel = 0
    _smaxplayers = 0
    _sv_maxclients = 0
    _g_maxGameClients = 0
    _teamsbalanced = False
    _matchmode = False
    _botenable = False
    _botskill = 4
    _botminplayers = 4
    _botmaps = []
    _hsenable = False
    _hsresetvars = 'map'
    _hsbroadcast = True
    _hsall = True
    _hspercent = True
    _hspercentmin = 20
    _hswarnhelmet = True
    _hswarnhelmetnr = 7
    _hswarnkevlar = True
    _hswarnkevlarnr = 50
    _rmenable = False
    _dontcount = 0
    _mapchanged = False
    _playercount = -1
    _oldplayercount = None
    _currentrotation = 0
    _switchcount1 = 12
    _switchcount2 = 24
    _hysteresis = 0
    _rotation_small = ''
    _rotation_medium = ''
    _rotation_large = ''
    _gamepath = ''
    _origgear = 0
    _randnum = 0
    _pass_lines = None
    _papublic_password = None
    _match_plugin_disable = []
    _gameconfig = {}
    _team_change_force_balance_enable = True
    _teamLocksPermanent = False
    _autobalance_gametypes = 'tdm'
    _autobalance_gametypes_array = []
    _max_dic_size = 512000  # max dictionary size in bytes
    _moon_on_gravity = 100
    _moon_off_gravity = 800
    _slapSafeLevel = 60
    _ignorePlus = 30
    _full_ident_level = 60
    _killhistory = []
    _hitlocations = {}

    _round_based_gametypes = ('ts', 'bm', 'freeze')
    _is_round_end = False
    _pending_teambalance = False
    _pending_skillbalance = False
    _skillbalance_func = None

    # https://www.urbanterror.info/support/180-server-cvars/#2
    _weapons = {
        'ber': 'F',
        'mp5': 'I',
        'lr': 'L',
        'sr8': 'Z',
        'm4': 'e',
        'mac': 'h',
        'p90': 'k',
        'smo': 'Q',
        'med': 'T',
        'hel': 'W',
        'de': 'G',
        'ump': 'J',
        'g36': 'M',
        'ak': 'a',
        'glo': 'f',
        'frf1': 'i',
        'mag': 'l',
        'vest': 'R',
        'sil': 'U',
        'ammo': 'X',
        'spas': 'H',
        'hk': 'K',
        'psg': 'N',
        'neg': 'c',
        'colt': 'g',
        'ben': 'j',
        'he': 'O',
        'nvg': 'S',
        'las': 'V',
    }

    # less likely weapon names to check if we fail
    # to recognize a weapon with the _weapon lists
    _weapon_aliases = {
        '.50': 'de',
        'eag': 'de',
        'mp': 'mp5',
        'sr': 'sr8',
        '1911': 'colt',
        'kev': 'vest',
        'gog': 'nvg',
        'ext': 'ammo',
        'amm': 'ammo',
        'nail': 'p90',
        'fr': 'frf1',
        'frf': 'frf1',
        '44': 'mag',
        '.44': 'mag',
        'slug': 'ben',
    }

    _weapon_groups = {
        'all_nades': 'KO',
        'all_snipers': 'NZi',
        'all_pistols': 'FGfgl',
        'all_autos': 'IJLMacehk',
        'all_shotguns': 'Hj',
        'all_secondaries': 'HIJhjk',
        'all_items': 'RTUVWX',
    }

    _gears = {
        'none': ''.join(_weapons.values()),
        'all': '',
        'reset': '',
    }

    # radio spam protection
    _rsp_enable = False
    _rsp_mute_duration = 2
    _rsp_maxlevel = 20
    _rsp_falloffRate = 2  # spam points will fall off by 1 point every 4 seconds
    _rsp_maxSpamins = 10

    def onStartup(self):
        """
        Initialize plugin settings
        """
        # get the admin plugin so we can register commands
        self._adminPlugin = self.console.getPlugin('admin')

        try:
            self._hitlocations['HL_HEAD'] = self.console.HL_HEAD
        except AttributeError as e:
            self._hitlocations['HL_HEAD'] = '0'
            self.warning("could not get HL_HEAD value from B3 parser: %s", e)

        try:
            self._hitlocations['HL_HELMET'] = self.console.HL_HELMET
        except AttributeError as e:
            self._hitlocations['HL_HELMET'] = '1'
            self.warning("could not get HL_HELMET value from B3 parser: %s", e)

        try:
            self._hitlocations['HL_TORSO'] = self.console.HL_TORSO
        except AttributeError as e:
            self._hitlocations['HL_TORSO'] = '2'
            self.warning("could not get HL_TORSO value from B3 parser: %s", e)

        self.debug("HL_HEAD is %s", self._hitlocations['HL_HEAD'])
        self.debug("HL_HELMET is %s", self._hitlocations['HL_HELMET'])
        self.debug("HL_TORSO is %s", self._hitlocations['HL_TORSO'])

        self.register_commands_from_config()
        self._adminPlugin.registerCommand(self, 'paversion', 0, self.cmd_paversion, 'paver')

        # register our events
        self.registerEvents()

        # create event
        self.createEvent('EVT_CLIENT_PUBLIC', 'Server Public Mode Changed')

        # don't run cron-checks on startup
        self.ignoreSet(self._ignorePlus)
        self._balancing = False
        self._killhistory = []

        try:
            # save original vote settings
            self._origvote = self.console.getCvar('g_allowvote').getInt()
        except ValueError as e:
            self.warning("could not retrieve g_allowvote CVAR value: %s", e)
            self._origvote = 0  # no votes

        # if by any chance on botstart g_allowvote is 0
        # we'll use the default UrT value
        if self._origvote == 0:
            self._origvote = 536871039

        self._lastvote = self._origvote

        # how many players are allowed and if g_maxGameClients != 0 we will disable specchecking
        self._sv_maxclients = self.console.getCvar('sv_maxclients').getInt()
        self._g_maxGameClients = self.console.getCvar('g_maxGameClients').getInt()

        self.installCrontabs()

        self._gears['reset'] = self.console.getCvar('g_gear').getString()
        self._gears['none'] = ''.join(self._weapons.values())

        self.debug('plugin started')

    def registerEvents(self):
        """
        Register events needed
        """
        self.verbose('registering events')
        self.registerEvent('EVT_GAME_ROUND_START', self.onGameRoundStart)
        self.registerEvent('EVT_GAME_ROUND_END', self.onGameRoundEnd)
        self.registerEvent('EVT_GAME_EXIT', self.onGameExit)
        self.registerEvent('EVT_CLIENT_AUTH', self.onClientAuth)
        self.registerEvent('EVT_CLIENT_DISCONNECT', self.onClientDisconnect)
        self.registerEvent('EVT_CLIENT_TEAM_CHANGE', self.onTeamChange)
        self.registerEvent('EVT_CLIENT_DAMAGE', self.headshotcounter)
        self.registerEvent('EVT_CLIENT_NAME_CHANGE', self.onNameChange)
        self.registerEvent('EVT_CLIENT_KILL', self.onKill)
        self.registerEvent('EVT_CLIENT_KILL_TEAM', self.onKillTeam)
        self.registerEvent('EVT_CLIENT_ACTION', self.onAction)
        self.registerEvent('EVT_GAME_MAP_CHANGE', self.onGameMapChange)
        self.registerEvent('EVT_CLIENT_RADIO', self.onRadio)

    def installCrontabs(self):
        """
        CRONTABS INSTALLATION
        Cleanup and Create the crontabs
        """
        if self._ncronTab:
            # remove existing crontab
            self.console.cron - self._ncronTab
        if self._tcronTab:
            # remove existing crontab
            self.console.cron - self._tcronTab
        if self._scronTab:
            # remove existing crontab
            self.console.cron - self._scronTab
        if self._skcronTab:
            # remove existing crontab
            self.console.cron - self._skcronTab
        if self._ninterval > 0:
            self._ncronTab = b3.cron.PluginCronTab(self, self.namecheck, minute=f'*/{self._ninterval}')
            self.console.cron + self._ncronTab
        if self._tinterval > 0:
            self._tcronTab = b3.cron.PluginCronTab(self, self.teamcheck, minute=f'*/{self._tinterval}')
            self.console.cron + self._tcronTab
        if self._sinterval > 0:
            self._scronTab = b3.cron.PluginCronTab(self, self.speccheck, minute=f'*/{self._sinterval}')
            self.console.cron + self._scronTab
        if self._skinterval > 0:
            self._skcronTab = b3.cron.PluginCronTab(self, self.skillcheck, minute=f'*/{self._skinterval}')
            self.console.cron + self._skcronTab

    def onLoadConfig(self):
        """
        Load plugin configuration
        """
        self.loadNameChecker()
        self.loadTeamBalancer()
        self.loadVoteDelayer()
        self.loadSpecChecker()
        self.loadSkillBalancer()
        self.loadMoonMode()
        self.loadPublicMode()
        self.loadMatchMode()
        self.loadBotSupport()
        self.loadHeadshotCounter()
        self.loadRotationManager()
        self.loadSpecial()
        self.loadRadioSpamProtection()

    def loadNameChecker(self):
        """
        Setup the name checker
        """
        self._ninterval = self.getSetting('namechecker', 'ninterval', b3.INT, self._ninterval,
                                          lambda x: clamp(x, maxv=59))
        self._checkdupes = self.getSetting('namechecker', 'checkdupes', b3.BOOL, self._checkdupes)
        self._checkunknown = self.getSetting('namechecker', 'checkunknown', b3.BOOL, self._checkunknown)
        self._checkbadnames = self.getSetting('namechecker', 'checkbadnames', b3.BOOL, self._checkbadnames)
        self._checkchanges = self.getSetting('namechecker', 'checkchanges', b3.BOOL, self._checkchanges)
        self._checkallowedchanges = self.getSetting('namechecker', 'checkallowedchanges', b3.INT,
                                                    self._checkallowedchanges, lambda x: clamp(x, minv=1))

    def loadTeamBalancer(self):
        """
        Setup the teambalancer
        """
        self._tinterval = self.getSetting('teambalancer', 'tinterval', b3.INT, self._tinterval,
                                          lambda x: clamp(x, maxv=59))
        self._teamdiff = self.getSetting('teambalancer', 'teamdifference', b3.INT, self._teamdiff,
                                         lambda x: clamp(x, minv=1, maxv=9))
        self._tmaxlevel = self.getSetting('teambalancer', 'maxlevel', b3.LEVEL, self._tmaxlevel)
        self._announce = self.getSetting('teambalancer', 'announce', b3.INT, self._announce)
        # 10/21/2008 - 1.4.0b9 - mindriot
        self._team_change_force_balance_enable = self.getSetting('teambalancer', 'team_change_force_balance_enable',
                                                                 b3.BOOL, self._team_change_force_balance_enable)
        # 10/22/2008 - 1.4.0b10 - mindriot
        self._autobalance_gametypes = self.getSetting('teambalancer', 'autobalance_gametypes', b3.STR,
                                                      self._autobalance_gametypes, lambda x: x.lower())
        self._autobalance_gametypes_array = re.split(r'[\s,]+', self._autobalance_gametypes)
        self._teamLocksPermanent = self.getSetting('teambalancer', 'teamLocksPermanent', b3.BOOL,
                                                   self._teamLocksPermanent)
        self._ignorePlus = self.getSetting('teambalancer', 'timedelay', b3.INT, self._ignorePlus)

    def loadSkillBalancer(self):
        """
        Setup the skill balancer
        """
        self._skinterval = self.getSetting('skillbalancer', 'interval', b3.INT, self._skinterval,
                                           lambda x: clamp(x, maxv=59))
        self._skilldiff = self.getSetting('skillbalancer', 'difference', b3.FLOAT, self._skilldiff,
                                          lambda x: clamp(x, minv=0.1, maxv=9.0))
        self._skill_balance_mode = self.getSetting('skillbalancer', 'mode', b3.INT, self._skill_balance_mode)
        self._minbalinterval = self.getSetting('skillbalancer', 'min_bal_interval', b3.INT, self._minbalinterval)

    def loadVoteDelayer(self):
        """
        Setup the vote delayer
        """
        self._votedelay = self.getSetting('votedelay', 'votedelay', b3.INT, self._votedelay)
        # set a max delay, setting it larger than timelimit would be foolish
        timelimit = self.console.getCvar('timelimit').getInt()
        if timelimit == 0 and self._votedelay != 0:
            # endless map or frag limited settings
            self._votedelay = 10
        elif self._votedelay >= timelimit - 1:
            # don't overlap rounds
            self._votedelay = timelimit - 1

    def loadSpecChecker(self):
        """
        Setup the spec checker
        """
        self._sinterval = self.getSetting('speccheck', 'sinterval', b3.INT, self._sinterval,
                                          lambda x: clamp(x, maxv=59))
        self._smaxspectime = self.getSetting('speccheck', 'maxspectime', b3.INT, self._smaxspectime)
        self._smaxlevel = self.getSetting('speccheck', 'maxlevel', b3.LEVEL, self._smaxlevel)
        maxclients = self.console.getCvar('sv_maxclients').getInt()
        pvtclients = self.console.getCvar('sv_privateClients').getInt()
        smaxplayers = maxclients - pvtclients
        self._smaxplayers = self.getSetting('speccheck', 'maxplayers', b3.INT, smaxplayers)

    def loadMoonMode(self):
        """
        Setup the moon mode
        """
        self._moon_on_gravity = self.getSetting('moonmode', 'gravity_on', b3.INT, self._moon_on_gravity)
        self._moon_off_gravity = self.getSetting('moonmode', 'gravity_off', b3.INT, self._moon_off_gravity)

    def loadPublicMode(self):
        """
        Setup the public mode
        """
        self._randnum = self.getSetting('publicmode', 'randnum', b3.INT, self._randnum)

        try:

            padic = self.getSetting('publicmode', 'usedic', b3.BOOL, False)
            if padic:
                padicfile = self.config.getpath('publicmode', 'dicfile')
                self.debug('trying to use password dictionnary %s' % padicfile)
                if os.path.exists(padicfile):
                    stinfo = os.stat(padicfile)
                    if stinfo.st_size > self._max_dic_size:
                        self.warning('dictionary file is too big: switching to default')
                    else:
                        dicfile = open(padicfile)
                        text = dicfile.read().strip()
                        dicfile.close()
                        if text == "":
                            self.warning('dictionary file is empty: switching to default')
                        else:
                            self._pass_lines = text.splitlines()
                    self.debug('using dictionary password')
                else:
                    self.warning('dictionary is enabled but the file doesn\'t exists: switching to default')

        except Exception as e:
            self.error('could not load dictionary config: %s' % e)
            self.debug('using default dictionary')

        self._papublic_password = self.getSetting('publicmode', 'g_password', b3.STR, None)
        if self._papublic_password is None:
            self.warning('could not setup papublic command because there is no password set in config')

    def loadMatchMode(self):
        """
        Setup the match mode
        """
        self._match_plugin_disable = self.getSetting('matchmode', 'plugins_disable', b3.LIST, [])

        try:
            # load all the configuration files into a dict
            for key, value in self.config.items('matchmode_configs'):
                self._gameconfig[key] = value
        except (b3.config.NoSectionError, b3.config.NoOptionError, KeyError) as e:
            self.warning('could not read matchmode configs: %s' % e)

    def loadBotSupport(self):
        """
        Setup the bot support
        """
        self._botenable = self.getSetting('botsupport', 'bot_enable', b3.BOOL, self._botenable)
        self._botskill = self.getSetting('botsupport', 'bot_skill', b3.INT, self._botskill,
                                         lambda x: clamp(x, minv=1, maxv=5))
        self._botminplayers = self.getSetting('botsupport', 'bot_minplayers', b3.INT, self._botminplayers,
                                              lambda x: clamp(x, minv=0, maxv=16))
        self._botmaps = self.getSetting('botsupport', 'bot_maps', b3.LIST, [])

        if self._botenable:
            # if it isn't enabled already it takes a mapchange to activate
            self.console.write('set bot_enable 1')

        # set the correct botskill anyway
        self.console.write('set g_spskill %s' % self._botskill)
        # first check for botsupport
        self.botsupport()

    def loadHeadshotCounter(self):
        """
        Setup the headshot counter
        """

        def validate_reset_vars(x):
            acceptable = ('no', 'map', 'round')
            if x.lower() not in acceptable:
                raise ValueError('value must be one of [%s]' % ', '.join(acceptable))
            return x.lower()

        self._hsenable = self.getSetting('headshotcounter', 'hs_enable', b3.BOOL, self._hsenable)
        self._hsresetvars = self.getSetting('headshotcounter', 'reset_vars', b3.STR, self._hsresetvars,
                                            validate_reset_vars)
        self._hsbroadcast = self.getSetting('headshotcounter', 'broadcast', b3.BOOL, self._hsbroadcast)
        self._hsall = self.getSetting('headshotcounter', 'announce_all', b3.BOOL, self._hsall)
        self._hspercent = self.getSetting('headshotcounter', 'announce_percentages', b3.BOOL, self._hspercent)
        self._hspercentmin = self.getSetting('headshotcounter', 'percent_min', b3.INT, self._hspercentmin)
        self._hswarnhelmet = self.getSetting('headshotcounter', 'warn_helmet', b3.BOOL, self._hswarnhelmet)
        self._hswarnhelmetnr = self.getSetting('headshotcounter', 'warn_helmet_nr', b3.INT, self._hswarnhelmetnr)
        self._hswarnkevlar = self.getSetting('headshotcounter', 'warn_kevlar', b3.BOOL, self._hswarnkevlar)
        self._hswarnkevlarnr = self.getSetting('headshotcounter', 'warn_kevlar_nr', b3.INT, self._hswarnkevlarnr)

        # making shure loghits is enabled to count headshots
        if self._hsenable:
            self.console.write('set g_loghits 1')

    def loadRotationManager(self):
        """
        Setup the rotation manager
        """
        self._rmenable = self.getSetting('rotationmanager', 'rm_enable', b3.BOOL, self._rmenable)
        if self._rmenable:
            self._switchcount1 = self.getSetting('rotationmanager', 'switchcount1', b3.INT, self._switchcount1)
            self._switchcount2 = self.getSetting('rotationmanager', 'switchcount2', b3.INT, self._switchcount2)
            self._hysteresis = self.getSetting('rotationmanager', 'hysteresis', b3.INT, self._hysteresis)
            self._rotation_small = self.getSetting('rotationmanager', 'smallrotation', b3.STR, self._rotation_small)
            self._rotation_medium = self.getSetting('rotationmanager', 'mediumrotation', b3.STR, self._rotation_medium)
            self._rotation_large = self.getSetting('rotationmanager', 'largerotation', b3.STR, self._rotation_large)
            self._gamepath = self.getSetting('rotationmanager', 'gamepath', b3.STR, self._gamepath)
        else:
            self.debug('Rotation Manager is disabled')

    def loadSpecial(self):
        """
        Setup special configs
        """
        self._slapSafeLevel = self.getSetting('special', 'slap_safe_level', b3.LEVEL, self._slapSafeLevel)
        self._full_ident_level = self.getSetting('special', 'paident_full_level', b3.LEVEL, self._full_ident_level)

    def loadRadioSpamProtection(self):
        """
        Setup the radio spam protection
        """
        self._rsp_enable = self.getSetting('radio_spam_protection', 'enable', b3.BOOL, self._rsp_enable)
        self._rsp_mute_duration = self.getSetting('radio_spam_protection', 'mute_duration', b3.INT,
                                                  self._rsp_mute_duration, lambda x: clamp(x, minv=1))
        self._rsp_maxlevel = self.getSetting('radio_spam_protection', 'maxlevel', b3.LEVEL, self._rsp_maxlevel)

    def onClientDisconnect(self, _):
        """
        Handle EVT_CLIENT_DISCONNECT.
        """
        if self._rmenable and self.console.time() > self._dontcount and self._mapchanged:
            self._playercount -= 1
            self.adjustrotation(-1)

    def onClientAuth(self, event):
        """
        Handle EVT_CLIENT_AUTH.
        """
        if self._hsenable:
            self.setupVars(event.client)
        if self._rmenable and self.console.time() > self._dontcount and self._mapchanged:
            self._playercount += 1
            self.adjustrotation(+1)

    def onGameRoundStart(self, _):
        """
        Handle EVT_GAME_ROUND_START.
        """
        self._is_round_end = False
        self._forgetTeamContrib()
        self._killhistory = []
        self._lastbal = self.console.time()

        # check for botsupport
        if self._botenable:
            self.botsdisable()
            self.botsupport()

        # reset headshotcounter (per round) if applicable
        if self._hsresetvars == 'round':
            self.resetVars()

        # ignore teambalance checking for 1 minute
        self.ignoreSet(self._ignorePlus)
        self._teamred = 0
        self._teamblue = 0

        # vote delay init
        if self._votedelay > 0 and self.console.getCvar('g_allowvote').getInt() != 0:
            # delay voting
            data = 'off'
            self.votedelay(data)
            # re-enable voting
            tm = self._votedelay * 60
            t1 = threading.Timer(tm, self.votedelay)
            t1.start()

    def onGameExit(self, _):
        """
        Handle EVT_GAME_EXIT.
        """
        self._mapchanged = True
        if self._botenable:
            self.botsdisable()

        self.ignoreSet(self._ignorePlus)

        # reset headshotcounter (per map) if applicable
        if self._hsresetvars == 'map':
            self.resetVars()

        # reset number of name changes per client
        self.resetNameChanges()
        if not self._teamLocksPermanent:
            # release TeamLocks
            self.resetTeamLocks()

        # setup timer for recounting players
        if self._rmenable:
            tm = 60
            self._dontcount = self.console.time() + tm
            t2 = threading.Timer(tm, self.recountplayers)
            t2.start()

    def onGameMapChange(self, _):
        """
        Handle EVT_GAME_MAP_CHANGE.
        """
        if matchmode := self.console.getCvar('g_matchmode'):
            self._matchmode = matchmode.getBoolean()

    def onKill(self, event):
        """
        Handle EVT_CLIENT_KILL.
        """
        killer = event.client
        victim = event.target
        killer.var(self, 'kills', 0).value += 1
        victim.var(self, 'deaths', 0).value += 1
        now = self.console.time()
        killer.var(self, 'teamcontribhist', []).value.append((now, 1))
        victim.var(self, 'teamcontribhist', []).value.append((now, -1))
        self._killhistory.append((now, killer.team))

    def onKillTeam(self, event):
        """
        Handle EVT_CLIENT_KILL_TEA;.
        """
        event.client.var(self, 'teamkills', 0).value += 1

    def onAction(self, event):
        """
        Handle EVT_CLIENT_ACTION.
        """
        if event.data in ('flag_captured', 'flag_dropped', 'flag_returned', 'bomb_planted', 'bomb_defused'):
            event.client.var(self, event.data, 0).value += 1
        if event.data in ('team_CTF_redflag', 'team_CTF_blueflag'):
            event.client.var(self, 'flag_taken', 0).value += 1

    def onRadio(self, event):
        """
        Handle radio events
        """
        if not self._rsp_enable:
            return

        client = event.client

        if client.maxLevel >= self._rsp_maxlevel:
            return

        if client.var(self, 'radio_ignore_till', self.getTime()).value > self.getTime():
            return

        points = 0
        data = repr(event.data)
        last_message_data = client.var(self, 'last_radio_data').value

        now = self.getTime()
        last_radio_time = client.var(self, 'last_radio_time', None).value
        gap = None
        if last_radio_time is not None:
            gap = now - last_radio_time
            if gap < 20:
                points += 1
            if gap < 2:
                points += 1
                if data == last_message_data:
                    points += 3
            if gap < 1:
                points += 3

        spamins = client.var(self, 'radio_spamins', 0).value + points

        # apply natural points decrease due to time
        if gap is not None:
            spamins -= int(gap / self._rsp_falloffRate)

        if spamins < 1:
            spamins = 0

        # set new values
        client.setvar(self, 'radio_spamins', spamins)
        client.setvar(self, 'last_radio_time', now)
        client.setvar(self, 'last_radio_data', data)

        # should we warn ?
        if spamins >= self._rsp_maxSpamins:
            self.console.writelines(["mute %s %s" % (client.cid, self._rsp_mute_duration)])
            client.setvar(self, 'radio_spamins', int(self._rsp_maxSpamins / 2.0))
            client.setvar(self, 'radio_ignore_till', int(self.getTime() + self._rsp_mute_duration - 1))

    def cmd_paadvise(self, data, client, cmd=None):
        """
        Report team skill balance, and give advice if teams are unfair
        """
        avgdiff, diff = self._getTeamScoreDiffForAdvise()
        self.console.say('Avg kill ratio diff is %.2f, skill diff is %.2f' % (avgdiff, diff))
        self._advise(avgdiff, 1)

    def cmd_paunskuffle(self, data, client, cmd=None):
        """
        Create unbalanced teams. Used to test !paskuffle and !pabalance.
        """
        self._balancing = True
        clients = self.console.clients.getList()
        scores = self._getScores(clients)
        decorated = [(scores.get(c.id, 0), c) for c in clients if c.team in (b3.TEAM_BLUE, b3.TEAM_RED)]
        decorated.sort(key=lambda x: x[0])
        players = [c for score, c in decorated]
        n = len(players) // 2
        blue = players[:n]
        red = players[n:]
        self.console.write('bigtext "Unskuffling! Noobs beware!"')
        self._move(blue, red)
        self._forgetTeamContrib()
        self._balancing = False

    def cmd_paskuffle(self, data=None, client=None, cmd=None):
        """
        Skill shuffle. Shuffle players to balanced teams by numbers and skill.
        Locked players are also moved.
        """
        self._shuffle_teams(client=client)

    def cmd_pabalance(self, data=None, client=None, cmd=None):
        """
        Move as few players as needed to create teams balanced by numbers AND skill.
        Locked players are not moved.
        """
        self._shuffle_teams(client=client, maxmovesperc=0.3)

    def _shuffle_teams(self, client=None, maxmovesperc=None):
        now = self.console.time()
        sincelast = now - self._lastbal
        if client and client.maxLevel < 20 and self.ignoreCheck() and sincelast < 60 * self._minbalinterval:
            client.message('Teams changed recently, please wait a while')
            return

        # if we are in the middle of a round in a round based gametype,
        # delay till the end of it
        if self._getGameType() in self._round_based_gametypes and not self._is_round_end:
            self._pending_skillbalance = True
            self._skillbalance_func = self.cmd_pabalance if maxmovesperc else self.cmd_paskuffle
            if client:
                client.message('^7Teams will be balanced at the end of this round')
            return

        self._balancing = True
        olddiff, bestdiff, blue, red, scores = self._randTeams(100, 0.1, maxmovesperc)
        if bestdiff is not None:
            if maxmovesperc:
                self.console.write('bigtext "Balancing teams!"')
            else:
                self.console.write('bigtext "Skill Shuffle in Progress!"')
            moves = self._move(blue, red, scores)
        else:
            moves = 0

        if moves:
            self.console.say('^4Team skill difference was ^1%.2f^4, is now ^1%.2f' % (olddiff, bestdiff))
        elif maxmovesperc is not None:
            # we couldn't beat the previous diff by moving only a few players
            # with a balance so do a full skuffle
            self._shuffle_teams(client)
        else:
            self.console.say('^1Cannot improve team balance!')

        self._forgetTeamContrib()
        self._balancing = False
        self._lastbal = now

    def cmd_paautoskuffle(self, data, client, cmd=None):
        """
        [<mode>] - Set the skill balancer mode.
        """
        modes = ["0-none", "1-advise", "2-autobalance", "3-autoskuffle"]
        if not data:
            mode = modes[self._skill_balance_mode]
            self.console.say("Skill balancer mode is '%s'" % mode)
            self.console.say("Options are %s" % ', '.join(modes))
            return

        mode = None

        try:
            mode = int(data)
        except ValueError:
            for i, m in enumerate(modes):
                if data in m:
                    mode = i

        if mode is not None and 0 <= mode <= 3:
            self._skill_balance_mode = mode
            self.console.say("Skill balancer mode is now '%s'" % modes[mode])
            self.skillcheck()
        else:
            self.console.say("Valid options are %s" % ', '.join(modes))

    def cmd_paswap(self, data, client, cmd=None):
        """
        <player1> [player2] - Swap two teams for 2 clients. If player2 is not specified, the admin
        using the command is swapped with player1. Doesn't work with spectators (exception for calling admin).
        """
        # check for input. If none, exist with a message.
        if args := self._adminPlugin.parseUserCmd(data):
            # check if the first player exists. If none, exit.
            if not (client1 := self._adminPlugin.findClientPrompt(args[0], client)):
                return
        else:
            client.message("Invalid parameters, try !help paswap")
            return

        # if the specified player doesn't exist, exit.
        if args[1] is not None:
            if not (client2 := self._adminPlugin.findClientPrompt(args[1], client)):
                return
        else:
            client2 = client

        if client1.team == b3.TEAM_SPEC:
            client.message("%s is a spectator! - Can't be swapped" % client1.name)
            return

        if client2.team == b3.TEAM_SPEC:
            client.message("%s is a spectator! - Can't be swapped" % client2.name)
            return

        if client1.team == client2.team:
            client.message("%s and %s are on the same team!" % (client1.name, client2.name))
            return

        # /rcon swap <clientA> <clientB>
        self.console.write('swap %s %s' % (client1.cid, client2.cid))

        # No need to send the message twice to the switching admin :-)

        if client1 != client:
            client1.message("^4You were swapped with %s by the admin" % client2.name)

        if client2 != client:
            client2.message("^4You were swapped with %s by the admin" % client1.name)

        client.message("^3Successfully swapped %s and %s" % (client1.name, client2.name))

    def cmd_pateams(self, data, client, cmd=None):
        """
        Force teambalancing (all gametypes!)
        The player with the least time in a team will be switched.
        """
        # if we are in the middle of a round in a round based gametype, delay till the end of it
        if self._getGameType() in self._round_based_gametypes and not self._is_round_end:
            self._pending_teambalance = True
            client.message('^7Teams will be balanced at the end of this round')
        else:
            if self.teambalance():
                if self._teamsbalanced:
                    client.message('^7Teams are already balanced')
                else:
                    client.message('^7Teams are now balanced')
                    self._teamsbalanced = True
            else:
                client.message('^7Teambalancing failed, please try a again in a few moments')

    def cmd_pavote(self, data, client=None, cmd=None):
        """
        <on/off/reset> - Set voting on, off or reset to original value at bot start.
        Setting vote on will set the vote back to the value when it was set off.
        """
        if not data:
            if client:
                client.message('^7Invalid or missing data, try !help pavote')
            return

        if data.lower() in ('on', 'off', 'reset'):
            if client:
                client.message('^7Voting: ^1%s' % data)
        else:
            if client:
                client.message('^7Invalid data, try !help pavote')
            return

        if data.lower() == 'off':
            curvalue = self.console.getCvar('g_allowvote').getInt()
            if curvalue != 0:
                self._lastvote = curvalue
            self.console.setCvar('g_allowvote', '0')
        elif data.lower() == 'on':
            self.console.setCvar('g_allowvote', '%s' % self._lastvote)
        elif data.lower() == 'reset':
            self.console.setCvar('g_allowvote', '%s' % self._origvote)

    def cmd_paversion(self, data, client, cmd=None):
        """
        This command identifies PowerAdminUrt version and creator.
        """
        cmd.sayLoudOrPM(client, 'I am PowerAdminUrt version ^2%s ^7by ^3%s' % (__version__, __author__))

    def cmd_paexec(self, data, client, cmd=None):
        """
        <configfile.cfg> - Execute a server configfile.
        (You must use the command exactly as it is!)
        """
        if not data:
            client.message('^7Missing data, try !help paexec')
            return

        if re.match('^[a-z0-9_.]+.cfg$', data, re.I):
            result = self.console.write('exec %s' % data)
            cmd.sayLoudOrPM(client, result)
        else:
            self.error('%s is not a valid configfile' % data)

    def cmd_pacyclemap(self, data, client, cmd=None):
        """
        Cycle to the next map.
        (You can safely use the command without the 'pa' at the beginning)
        """
        time.sleep(1)
        self.console.write('cyclemap')

    def cmd_pamaprestart(self, data, client, cmd=None):
        """
        Restart the current map.
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.console.write('map_restart')

    def cmd_pamapreload(self, data, client, cmd=None):
        """
        Reload the current map.
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.console.write('reload')

    def cmd_paset(self, data, client, cmd=None):
        """
        <cvar> <value> - Set a server cvar to a certain value.
        (You must use the command exactly as it is!)
        """
        if not data:
            client.message('^7Invalid or missing data, try !help paset')
            return

        # are we still here? Let's write it to console
        args = data.split(' ', 1)
        cvar = args[0]
        value = args[1] if len(args) == 2 else ""
        self.console.setCvar(cvar, value)

    def cmd_paget(self, data, client, cmd=None):
        """
        <cvar> - Returns the value of a servercvar.
        (You must use the command exactly as it is! )
        """
        if not data:
            client.message('^7Invalid or missing data, try !help paget')
            return

        # are we still here? Let's write it to console
        getcvar = data.split(' ')
        getcvarvalue = self.console.getCvar('%s' % getcvar[0])
        cmd.sayLoudOrPM(client, '%s' % getcvarvalue)

    def cmd_pabigtext(self, data, client, cmd=None):
        """
        <message> - Print a Bold message on the center of all screens.
        (You can safely use the command without the 'pa' at the beginning)
        """
        if not data:
            client.message('^7Invalid or missing data, try !help pabigtext')
            return

        # are we still here? Let's write it to console
        self.console.write('bigtext "%s"' % data)

    def cmd_pamute(self, data, client, cmd=None):
        """
        <player> [<duration>] - Mute a player.
        (You can safely use the command without the 'pa' at the beginning)
        """
        # this will split the player name and the message
        if args := self._adminPlugin.parseUserCmd(data):
            # args[0] is the player id
            if not (sclient := self._adminPlugin.findClientPrompt(args[0], client)):
                # a player matchin the name was not found, a list of closest matches will be displayed
                # we can exit here and the user will retry with a more specific player
                return
        else:
            client.message('^7Invalid data, try !help pamute')
            return

        if sclient.maxLevel > client.maxLevel:
            client.message("^7You don't have enough privileges to mute this player")
            return

        if args[1] is not None and re.match(r'^([0-9]+)\s*$', args[1]):
            duration = int(args[1])
        else:
            duration = ''

        # are we still here? Let's write it to console
        self.console.write('mute %s %s' % (sclient.cid, duration))

    def cmd_papause(self, data, client, cmd=None):
        """
        <message> - Pause the game. Type again to resume
        """
        result = self.console.write('pause')
        cmd.sayLoudOrPM(client, result)

    def cmd_paslap(self, data, client, cmd=None):
        """
        <player> [<ammount>] - (multi)Slap a player.
        (You can safely use the command without the 'pa' at the beginning)
        """
        # this will split the player name and the message
        if args := self._adminPlugin.parseUserCmd(data):
            # args[0] is the player id
            if not (sclient := self._adminPlugin.findClientPrompt(args[0], client)):
                # a player matchin the name was not found, a list of closest matches will be displayed
                # we can exit here and the user will retry with a more specific player
                return
        else:
            client.message('^7Invalid data, try !help paslap')
            return

        if sclient.maxLevel >= self._slapSafeLevel and client.maxLevel < 90:
            client.message("^7You don't have enough privileges to slap an Admin")
            return

        if args[1]:

            try:
                x = int(args[1])
            except ValueError:
                client.message('^7Invalid data, try !help paslap')
                return

            if x in range(1, 26):
                self.console.writelines([f'slap {sclient.cid}'] * x)
            else:
                client.message('^7Number of punishments out of range, must be 1 to 25')
        else:
            self.console.write('slap %s' % sclient.cid)

    def cmd_panuke(self, data, client, cmd=None):
        """
        <player> [<ammount>] - (multi)Nuke a player.
        (You can safely use the command without the 'pa' at the beginning)
        """
        # this will split the player name and the message
        if args := self._adminPlugin.parseUserCmd(data):
            # args[0] is the player id
            if not (sclient := self._adminPlugin.findClientPrompt(args[0], client)):
                # a player matchin the name was not found, a list of closest matches will be displayed
                # we can exit here and the user will retry with a more specific player
                return
        else:
            client.message('^7Invalid data, try !help panuke')
            return

        if args[1]:

            try:
                x = int(args[1])
            except ValueError:
                client.message('^7Invalid data, try !help panuke')
                return

            if x in range(1, 26):
                self.console.writelines([f'nuke {sclient.cid}'] * x)
            else:
                client.message('^7Number of punishments out of range, must be 1 to 25')
        else:
            self.console.write('nuke %s' % sclient.cid)

    def cmd_paveto(self, data, client, cmd=None):
        """
        Veto current running Vote.
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.console.write('veto')

    def cmd_paforce(self, data, client, cmd=None):
        """
        <player> <red/blue/spec/free> <lock> - Force a client to red/blue/spec or release the force (free)
        adding 'lock' will lock the player where it is forced to, default this is off.
        using 'all free' will release all locks.
        (You can safely use the command without the 'pa' at the beginning)
        """
        # this will split the player name and the message
        if args := self._adminPlugin.parseUserCmd(data):
            # check if all Locks should be released
            if args[0] == "all" and args[1] == "free":
                self.resetTeamLocks()
                self.console.say('All TeamLocks were released')
                return

            # args[0] is the player id
            if not (sclient := self._adminPlugin.findClientPrompt(args[0], client)):
                # a player matchin the name was not found, a list of closest matches will be displayed
                # we can exit here and the user will retry with a more specific player
                return
        else:
            client.message('^7Invalid data, try !help paforce')
            return

        if not args[1]:
            client.message('^7Missing data, try !help paforce')
            return

        tdata = args[1].split(' ')
        team = tdata[0]

        lock = False
        if len(tdata) > 1 and tdata[1] == 'lock':
            lock = True

        if team == 'spec' or team == 'spectator':
            team = 's'
        if team == 'b':
            team = 'blue'
        if team == 'r':
            team = 'red'

        if team == 's':
            teamname = 'spectator'
        else:
            teamname = team

        if team == 'free':
            if sclient.isvar(self, 'paforced'):
                sclient.message('^3Your have been released by the admin')
                client.message('^7%s ^3has been released' % sclient.name)
                sclient.delvar(self, 'paforced')
                return
            else:
                client.message('^3There was no lock on ^7%s' % sclient.name)

        elif team in ('red', 'blue', 's') and lock:
            sclient.message('^3Your are forced and locked to: ^7%s' % teamname)

        elif team in ('red', 'blue', 's'):
            sclient.message('^3Your are forced to: ^7%s' % teamname)

        else:
            client.message('^7Invalid data, try !help paforce')
            return

        if lock:
            sclient.setvar(self, 'paforced', team)  # s, red or blue
        else:
            sclient.delvar(self, 'paforced')

        # are we still here? Let's write it to console
        self.console.write('forceteam %s %s' % (sclient.cid, team))
        client.message('^3%s ^7forced to ^3%s' % (sclient.name, teamname))

    def cmd_paswapteams(self, data, client, cmd=None):
        """
        Swap current teams.
        (You can safely use the command without the 'pa' at the beginning)
        """
        # ignore automatic checking before giving the command
        self.ignoreSet(30)
        self.console.write('swapteams')

    def cmd_pashuffleteams(self, data, client, cmd=None):
        """
        Shuffle teams.
        (You can safely use the command without the 'pa' at the beginning)
        """
        # Ignore automatic checking before giving the command
        self.ignoreSet(30)
        self.console.write('shuffleteams')

    def cmd_pamoon(self, data, client, cmd=None):
        """
        Set moon mode <on/off>
        (You can safely use the command without the 'pa' at the beginning)
        """
        if not data or data not in ('on', 'off'):
            client.message('^7Invalid or missing data, try !help pamoon')
            return

        if data == 'on':
            self.console.setCvar('g_gravity', self._moon_on_gravity)
            self.console.say('^7Moon mode: ^2ON')
        elif data == 'off':
            self.console.setCvar('g_gravity', self._moon_off_gravity)
            self.console.say('^7Moon mode: ^1OFF')

    def cmd_papublic(self, data, client, cmd=None):
        """
        Set server public mode on/off.
        (You can safely use the command without the 'pa' at the beginning)
        """
        if not data or data not in ('on', 'off'):
            client.message('^7Invalid or missing data, try !help papublic')
            return

        if data == 'on':
            self.console.setCvar('g_password', '')
            self.console.say('^7public mode: ^2ON')
            self.console.queueEvent(self.console.getEvent('EVT_CLIENT_PUBLIC', '', client))

        elif data == 'off':
            newpassword = self._papublic_password
            if self._pass_lines is not None:
                i = random.randint(0, len(self._pass_lines) - 1)
                newpassword = self._pass_lines[i]

            for i in range(0, self._randnum):
                newpassword += str(random.randint(1, 9))

            self.debug('private password set to: %s' % newpassword)

            if newpassword is None:
                client.message('^1ERROR: ^7could not set public mode off because \
                                there is no password specified in the config file')
                return

            self.console.setCvar('g_password', '%s' % newpassword)
            self.console.say('^7public mode: ^1OFF')
            client.message('^7password is \'^4%s^7\'' % newpassword)
            client.message('^7type ^5!mapreload^7 to apply change')
            self.console.write('bigtext "^7Server going ^3PRIVATE ^7soon!!"')
            self.console.queueEvent(self.console.getEvent('EVT_CLIENT_PUBLIC', newpassword, client))

    def cmd_pamatch(self, data, client, cmd=None):
        """
        Set server match mode on/off
        (You can safely use the command without the 'pa' at the beginning)
        """
        if not data or data not in ('on', 'off'):
            client.message('^7Invalid or missing data, try !help pamatch')
            return

        if data == 'on':
            self._matchmode = True
            self.console.setCvar('g_matchmode', '1')
            self.console.say('^7Match mode: ^2ON')
            self.console.write('bigtext "^7MATCH starting soon !!"')
            for e in self._match_plugin_disable:
                self.info('disabling plugin %s' % e)
                if plugin := self.console.getPlugin(e):
                    plugin.disable()
                    client.message('^7plugin %s disabled' % e)
            client.message('^7type ^5!mapreload^7 to apply change')
            self.console.write('bigtext "^7MATCH starting soon !!"')

        elif data == 'off':
            self._matchmode = False
            self.console.setCvar('g_matchmode', '0')
            self.console.say('^7Match mode: ^1OFF')

            for e in self._match_plugin_disable:
                self.info('enabling plugin %s' % e)
                if plugin := self.console.getPlugin(e):
                    plugin.enable()
                    client.message('^7plugin %s enabled' % e)
            client.message('^7type ^5!mapreload^7 to apply change')

        self.set_configmode(None)

    def cmd_paffa(self, data, client, cmd=None):
        """
        Change game type to Free For All
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.console.setCvar('g_gametype', '0')
        if client:
            client.message('^7game type changed to ^4Free For All')

        self.set_configmode('ffa')

    def cmd_patdm(self, data, client, cmd=None):
        """
        Change game type to Team Death Match
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.console.setCvar('g_gametype', '3')
        if client:
            client.message('^7game type changed to ^4Team Death Match')

        self.set_configmode('tdm')

    def cmd_pats(self, data, client, cmd=None):
        """
        Change game type to Team Survivor
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.console.setCvar('g_gametype', '4')
        if client:
            client.message('^7game type changed to ^4Team Survivor')

        self.set_configmode('ts')

    def cmd_paftl(self, data, client, cmd=None):
        """
        Change game type to Follow The Leader
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.console.setCvar('g_gametype', '5')
        if client:
            client.message('^7game type changed to ^4Follow The Leader')

        self.set_configmode('ftl')

    def cmd_pacah(self, data, client, cmd=None):
        """
        Change game type to Capture And Hold
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.console.setCvar('g_gametype', '6')
        if client:
            client.message('^7game type changed to ^4Capture And Hold')

        self.set_configmode('cah')

    def cmd_pactf(self, data, client, cmd=None):
        """
        Change game type to Capture The Flag
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.console.setCvar('g_gametype', '7')
        if client:
            client.message('^7game type changed to ^4Capture The Flag')

        self.set_configmode('ctf')

    def cmd_pabomb(self, data, client, cmd=None):
        """
        Change game type to Bomb
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.console.setCvar('g_gametype', '8')
        if client:
            client.message('^7game type changed to ^4Bomb')

        self.set_configmode('bomb')

    def cmd_paident(self, data, client=None, cmd=None):
        """
        <name> - show the ip and guid and authname of a player
        (You can safely use the command without the 'pa' at the beginning)
        """
        if not (args := self._adminPlugin.parseUserCmd(data)):
            cmd.sayLoudOrPM(client, 'Your id is ^2@%s' % client.id)
            return

        # args[0] is the player id
        if not (sclient := self._adminPlugin.findClientPrompt(args[0], client)):
            # a player matching the name was not found, a list of closest matches will be displayed
            # we can exit here and the user will retry with a more specific player
            return

        if client.maxLevel < self._full_ident_level:
            cmd.sayLoudOrPM(client, '%s ^4@%s ^2%s' % (self.console.formatTime(self.console.time()),
                                                       sclient.id, sclient.exactName))
        else:
            cmd.sayLoudOrPM(client, '%s ^4@%s ^2%s ^2%s ^7[^2%s^7] since ^2%s' % (
                self.console.formatTime(self.console.time()), sclient.id, sclient.exactName, sclient.ip, sclient.pbid,
                self.console.formatTime(sclient.timeAdd)))

    def cmd_paci(self, data, client=None, cmd=None):
        """
        <client> - kick a client that has an interrupted connection
        """
        if not (m := self._adminPlugin.parseUserCmd(data)):
            client.message('^7Missing data, try !help ci')
            return False

        if not (sclient := self._adminPlugin.findClientPrompt(m[0], client)):
            return

        try:
            players = self.console.getPlayerPings()
            if players[str(sclient.cid)] > 500:
                sclient.kick(self._adminPlugin.getReason('ci'), 'ci', client)
            else:
                client.message(f'^7{sclient.exactName} ^7is not CI')
        except KeyError:
            pass

    def onGameRoundEnd(self, _):
        """
        Handle EVT_GAME_ROUND_END.
        """
        self._is_round_end = True
        if self.isEnabled() and self._getGameType() in self._round_based_gametypes:
            if self._pending_skillbalance and self._skillbalance_func:
                self.info('onRoundEnd: executing skill balancing')
                self._skillbalance_func()
            elif self._pending_teambalance:
                self.info('onRoundEnd: executing team balancing')
                self.teambalance()

        self._pending_teambalance = False
        self._pending_skillbalance = False
        self._skillbalance_func = None

    def onTeamChange(self, event):
        """
        Handle EVT_CLIENT_TEAM_CHANGE.
        """
        client = event.client
        team = event.data
        # store the time of teamjoin for autobalancing purposes
        client.setvar(self, 'teamtime', self.console.time())
        # remember current stats so we can tell how the player
        # is performing on the new team
        self._saveTeamvars(client)

        if not self._matchmode and client.isvar(self, 'paforced'):
            forcedteam = client.var(self, 'paforced').value
            if team != b3.TEAM_UNKNOWN and team != self.console.getTeam(forcedteam):
                self.console.write('forceteam %s %s' % (client.cid, forcedteam))
                client.message('^1You are LOCKED! You are NOT allowed to switch!')
            # break out of this function, nothing more to do here
            return None

        # 10/21/2008 - 1.4.0b9 - mindriot
        # 10/23/2008 - 1.4.0b12 - mindriot
        if self._team_change_force_balance_enable and not self._matchmode:

            # if the round just started, don't do anything
            if self.ignoreCheck():
                return None

            if self.isEnabled() and not self._balancing:
                # set balancing flag
                self._balancing = True

                # are we supposed to be balanced?
                if client.maxLevel >= self._tmaxlevel:
                    # done balancing
                    self._balancing = False
                    return None

                # did player join spectators?
                if team == b3.TEAM_SPEC:
                    # done balancing
                    self._balancing = False
                    return None
                elif team == b3.TEAM_UNKNOWN:
                    # done balancing
                    self._balancing = False
                    return None

                # check if player was allowed to join this team
                if not self.countteams():
                    self._balancing = False
                    self.error('aborting teambalance: counting teams failed!')
                    return False
                if abs(self._teamred - self._teamblue) <= self._teamdiff:
                    # teams are balanced
                    self._balancing = False
                    return None
                else:
                    # switch is not allowed, so this should be a client suicide, not a legit switch.
                    # added as anti stats-harvest-exploit measure. One suicide is added as extra penalty for harvesting.
                    if self.console:
                        self.console.queueEvent(self.console.getEvent('EVT_CLIENT_SUICIDE',
                                                                      (100, 'penalty', 'body', 'Team_Switch_Penalty'),
                                                                      client, client))

                        self.console.queueEvent(self.console.getEvent('EVT_CLIENT_SUICIDE',
                                                                      (100, 'penalty', 'body', 'Team_Switch_Penalty'),
                                                                      client, client))

                        plugin = self.console.getPlugin('xlrstats')
                        if plugin:
                            client.message('^7Switching made teams ^1UNFAIR^7! '
                                           'Points where deducted from your stats as a penalty!')

                    if self._teamred > self._teamblue:
                        # join the blue team
                        self.console.write('forceteam %s blue' % client.cid)
                    else:
                        # join the red team
                        self.console.write('forceteam %s red' % client.cid)

                # done balancing
                self._balancing = False

        else:
            self.info('onTeamChange DISABLED')

    def countteams(self):
        """
        Count the amount of players in RED and BLUE team.
        """
        try:
            self._teamred = 0
            self._teamblue = 0
            data = self.console.write('players')
            for line in data.splitlines()[3:]:
                m = re.match(self.console._rePlayerScore, line.strip())
                if m:
                    if m.group('team').upper() == 'RED':
                        self._teamred += 1
                    elif m.group('team').upper() == 'BLUE':
                        self._teamblue += 1
            return True
        except Exception:
            return False

    def _getGameType(self):
        # g_gametype //0 = FreeForAll = dm, 3 = TeamDeathMatch = tdm, 4 = Team Survivor = ts,
        # 5 = Follow the Leader = ftl, 6 = Capture and Hold = cah, 7 = Capture The Flag = ctf, 8 = Bombmode = bm
        return self.console.game.game_type

    def teamcheck(self):
        """
        Teambalancer cronjob.
        """
        gametype = self._getGameType()
        # run teambalance only if current gametype is in autobalance_gametypes list
        if gametype not in self._autobalance_gametypes_array:
            return

        if gametype in self._round_based_gametypes:
            self.info('round based gametype detected (%s) : delaying teambalance till round end', gametype)
            self._pending_teambalance = True
            return

        if self._skill_balance_mode != 0:
            self.debug('skill balancer is active, not performing classic teamcheck')

        if self.console.time() > self._ignoreTill:
            self.teambalance()

    def teambalance(self):
        """
        Balance current teams.
        """
        if not self.isEnabled() or self._balancing or self._matchmode:
            return True

        self._balancing = True

        if not self.countteams():
            self._balancing = False
            self.warning('aborting teambalance: counting teams failed!')
            return False

        if abs(self._teamred - self._teamblue) <= self._teamdiff:
            self._teamsbalanced = True
            self._balancing = False
            return True

        self._teamsbalanced = False
        if self._announce == 1:
            self.console.write('say Autobalancing Teams!')
        elif self._announce == 2:
            self.console.write('bigtext "Autobalancing Teams!"')

        if self._teamred > self._teamblue:
            newteam = 'blue'
            oldteam = b3.TEAM_RED
        else:
            newteam = 'red'
            oldteam = b3.TEAM_BLUE

        count = 25  # endless loop protection
        while abs(self._teamred - self._teamblue) > self._teamdiff and count > 0:
            stime = self.console.upTime()
            now = self.console.time()
            forceclient = None
            for c in self.console.clients.getList():
                if (
                        c.team == oldteam
                        and now - c.var(self, 'teamtime', now).value < stime
                        and not c.isvar(self, 'paforced')
                ):
                    forceclient = c.cid
                    stime = now - c.var(self, 'teamtime').value

            if forceclient:
                self.console.write(f'forceteam {forceclient} {newteam}')

            count -= 1
            # recount the teams... do we need to balance once more?
            if not self.countteams():
                self._balancing = False
                self.error('aborting teambalance: counting teams failed!')
                return False

            if self._teamred > self._teamblue:
                newteam = 'blue'
                oldteam = b3.TEAM_RED
            else:
                newteam = 'red'
                oldteam = b3.TEAM_BLUE

        self._balancing = False

        return True

    def resetTeamLocks(self):
        if self.isEnabled():
            clients = self.console.clients.getList()
            for c in clients:
                if c.isvar(self, 'paforced'):
                    c.delvar(self, 'paforced')
        return None

    def namecheck(self):
        if self._matchmode:
            return None

        d = {}
        if self.isEnabled() and self.console.time() > self._ignoreTill:
            for player in self.console.clients.getList():
                if player.name not in d:
                    d[player.name] = [player.cid]
                else:
                    d[player.name].append(player.cid)

            for pname, cidlist in d.items():
                if self._checkdupes and len(cidlist) > 1:
                    self.warning("warning players %s for using the same name" %
                                (", ".join(["%s <%s> @%s" %
                                (c.exactName, c.cid, c.id) for c in
                                map(self.console.clients.getByCID, cidlist)])))

                    for cid in cidlist:
                        client = self.console.clients.getByCID(cid)
                        self._adminPlugin.warnClient(client, 'badname')

                if self._checkunknown and pname == self.console.stripColors('New UrT Player'):
                    for cid in cidlist:
                        client = self.console.clients.getByCID(cid)
                        self.warning("warning player %s <%s> @%s for using forbidden name 'New UrT Player'" %
                                    (client.exactName, client.cid, client.id))
                        self._adminPlugin.warnClient(client, 'badname')

                if self._checkbadnames and pname == 'all':
                    for cid in cidlist:
                        client = self.console.clients.getByCID(cid)
                        self.warning("warning player %s <%s> @%s for using forbidden name 'all'" %
                                    (client.exactName, client.cid, client.id))
                        self._adminPlugin.warnClient(client, 'badname')

    def onNameChange(self, event):
        """
        Handle EVT_CLIENT_NAME_CHANGE.
        """
        client = event.client
        if self.isEnabled() and self._checkchanges and client.maxLevel < 9:
            if not client.isvar(self, 'namechanges'):
                client.setvar(self, 'namechanges', 0)
                client.setvar(self, 'savedname', self.clean(client.exactName))

            cleanedname = self.clean(client.exactName)
            # also check if the name is ending with '_<slot num>' (happens with clients having deconnections)
            if cleanedname.endswith('_' + str(client.cid)):
                cleanedname = cleanedname[:-len('_' + str(client.cid))]

            if cleanedname != client.var(self, 'savedname').value:
                n = client.var(self, 'namechanges').value + 1
                oldname = client.var(self, 'savedname').value
                client.setvar(self, 'savedname', cleanedname)
                self.debug('%s changed name %s times. His name was %s' % (cleanedname, n, oldname))
                if n > self._checkallowedchanges:
                    client.kick('Too many namechanges!')
                else:
                    client.setvar(self, 'namechanges', n)
                    if self._checkallowedchanges - n < 4:
                        r = self._checkallowedchanges - n
                        client.message('^1WARNING:^7 ^2%s^7 more namechanges allowed during this map!' % r)

    def resetNameChanges(self):
        if self.isEnabled() and self._checkchanges:
            for c in self.console.clients.getList():
                if c.isvar(self, 'namechanges'):
                    c.setvar(self, 'namechanges', 0)

    def votedelay(self, data=None):
        if not data:
            data = 'on'
        self.cmd_pavote(data)

    def speccheck(self):
        if self.isEnabled() and self._g_maxGameClients == 0 and not self._matchmode:
            clients = self.console.clients.getList()
            if len(clients) < self._smaxplayers:
                return

            for c in clients:
                if not c.isvar(self, 'teamtime'):
                    # 10/22/2008 - 1.4.0b11 - mindriot
                    # store the time of teamjoin for autobalancing purposes
                    c.setvar(self, 'teamtime', self.console.time())
                    self.verbose('client variable teamtime set to: %s' % c.var(self, 'teamtime').value)

                if c.maxLevel >= self._smaxlevel:
                    continue
                elif c.isvar(self, 'paforced'):
                    continue
                elif c.team == b3.TEAM_SPEC and (self.console.time() - c.var(self, 'teamtime').value) > \
                        (self._smaxspectime * 60):
                    self._adminPlugin.warnClient(c, 'spec')

    def botsupport(self, data=None):
        """
        Check for bot support on the current map.
        """
        if self.isEnabled() and not self._matchmode:
            try:
                test = self.console.game.mapName
            except AttributeError:
                self.warning('mapName not yet available')
            else:
                if self._botenable:
                    for m in self._botmaps:
                        if m == self.console.game.mapName:
                            # we got ourselves a winner
                            self.botsenable()

    def botsdisable(self):
        self.console.write('set bot_minplayers 0')

    def botsenable(self):
        self.console.write('set bot_minplayers %s' % self._botminplayers)

    def setupVars(self, client):
        if not client.isvar(self, 'totalhits'):
            client.setvar(self, 'totalhits', 0.00)
        if not client.isvar(self, 'totalhitted'):
            client.setvar(self, 'totalhitted', 0.00)
        if not client.isvar(self, 'headhits'):
            client.setvar(self, 'headhits', 0.00)
        if not client.isvar(self, 'headhitted'):
            client.setvar(self, 'headhitted', 0.00)
        if not client.isvar(self, 'helmethits'):
            client.setvar(self, 'helmethits', 0.00)
        if not client.isvar(self, 'torsohitted'):
            client.setvar(self, 'torsohitted', 0.00)

        client.setvar(self, 'hitvars', True)

    def resetVars(self):
        if self.isEnabled() and self._hsenable:
            clients = self.console.clients.getList()
            for c in clients:
                if c.isvar(self, 'hitvars'):
                    c.setvar(self, 'totalhits', 0.00)
                    c.setvar(self, 'totalhitted', 0.00)
                    c.setvar(self, 'headhits', 0.00)
                    c.setvar(self, 'headhitted', 0.00)
                    c.setvar(self, 'helmethits', 0.00)
                    c.setvar(self, 'torsohitted', 0.00)

        return None

    def headshotcounter(self, event):
        """
        Handle EVT_CLIENT_DAMAGE.
        """
        attacker = event.client
        victim = event.target
        data = event.data
        if self.isEnabled() and \
                self._hsenable and \
                attacker.isvar(self, 'hitvars') and \
                victim.isvar(self, 'hitvars') and not self._matchmode:

            hitloc = data[2]

            # set totals
            t = attacker.var(self, 'totalhits').value + 1
            attacker.setvar(self, 'totalhits', t)
            t = victim.var(self, 'totalhitted').value + 1
            victim.setvar(self, 'totalhitted', t)

            # headshots... no helmet!
            if hitloc == self._hitlocations['HL_HEAD']:
                t = attacker.var(self, 'headhits').value + 1
                attacker.setvar(self, 'headhits', t)
                t = victim.var(self, 'headhitted').value + 1
                victim.setvar(self, 'headhitted', t)

            # helmethits
            elif hitloc == self._hitlocations['HL_HELMET']:
                t = attacker.var(self, 'helmethits').value + 1
                attacker.setvar(self, 'helmethits', t)

            # torso... no kevlar!
            elif hitloc == self._hitlocations['HL_TORSO']:
                t = victim.var(self, 'torsohitted').value + 1
                victim.setvar(self, 'torsohitted', t)

            # announce headshots
            if self._hsall and hitloc in (self._hitlocations['HL_HEAD'], self._hitlocations['HL_HELMET']):
                headshots = attacker.var(self, 'headhits').value + attacker.var(self, 'helmethits').value
                hstext = 'headshots'
                if headshots == 1:
                    hstext = 'headshot'

                percentage = int(headshots / attacker.var(self, 'totalhits').value * 100)
                if self._hspercent and headshots > 5 and percentage > self._hspercentmin:
                    message = ('^2%s^7: %s %s! ^7(%s percent)' % (attacker.name, int(headshots), hstext, percentage))
                else:
                    message = ('^2%s^7: %s %s!' % (attacker.name, int(headshots), hstext))

                if self._hsbroadcast:
                    self.console.write(message)
                else:
                    self.console.say(message)

            # wear a helmet!
            if self._hswarnhelmet and \
                    victim.connections < 20 and \
                    victim.var(self, 'headhitted').value == self._hswarnhelmetnr and \
                    hitloc == self._hitlocations['HL_HEAD']:
                victim.message('You were hit in the head %s times! Consider wearing a helmet!' % self._hswarnhelmetnr)

            # wear kevlar!
            if self._hswarnkevlar and \
                    victim.connections < 20 and \
                    victim.var(self, 'torsohitted').value == self._hswarnkevlarnr and \
                    hitloc == self._hitlocations['HL_TORSO']:
                victim.message('You were hit in the torso %s times! Wearing kevlar vest will reduce \
                                your number of deaths!' % self._hswarnkevlarnr)

    def adjustrotation(self, delta):
        # if the round just started, don't do anything
        if self.console.time() < self._dontcount:
            return

        if delta == +1:
            if self._playercount > (self._switchcount2 + self._hysteresis):
                self.setrotation(3)
            elif self._playercount > (self._switchcount1 + self._hysteresis):
                self.setrotation(2)
            else:
                self.setrotation(1)

        elif delta == -1 or delta == 0:
            if self._playercount < (self._switchcount1 + (delta * self._hysteresis)):
                self.setrotation(1)
            elif self._playercount < (self._switchcount2 + (delta * self._hysteresis)):
                self.setrotation(2)
            else:
                self.setrotation(3)

        else:
            self.error('invalid delta passed to adjustrotation')

    def setrotation(self, newrotation):
        if not self._gamepath or \
                not self._rotation_small or \
                not self._rotation_medium or \
                not self._rotation_large or \
                not self._mapchanged:
            return

        if newrotation == self._currentrotation:
            return

        if newrotation == 1:
            rotname = "small"
            rotation = self._rotation_small
        elif newrotation == 2:
            rotname = "medium"
            rotation = self._rotation_medium
        elif newrotation == 3:
            rotname = "large"
            rotation = self._rotation_large
        else:
            self.error('invalid newrotation passed to setrotation')
            return

        self.console.setCvar('g_mapcycle', rotation)
        self._currentrotation = newrotation

    def recountplayers(self):
        # reset, recount and set a rotation
        self._oldplayercount = self._playercount
        self._playercount = len(self.console.clients.getList())

        if self._oldplayercount == -1:
            self.adjustrotation(0)
        elif self._playercount > self._oldplayercount:
            self.adjustrotation(+1)
        elif self._playercount < self._oldplayercount:
            self.adjustrotation(-1)

    def clean(self, data):
        return re.sub(self._reClean, '', data)[:20]

    def ignoreSet(self, data=60):
        """
        Sets the ignoreflag for an amount of seconds
        self._ignoreTill is a plugin flag that holds a time which ignoreCheck checks against
        """
        self._ignoreTill = self.console.time() + data

    def ignoreDel(self):
        self._ignoreTill = 0

    def ignoreCheck(self):
        """
        Tests if the ignore flag is set, to disable certain automatic functions when unwanted
        Returns True if the functionality should be ignored
        """
        return self._ignoreTill - self.console.time() > 0

    def cmd_pawaverespawns(self, data, client, cmd=None):
        """
        <on/off> - Set waverespawns on, or off.
        """
        if not data or data.lower() not in ('on', 'off'):
            client.message('^7Invalid or missing data, try !help pawaverespawns')
            return

        if data.lower() == 'on':
            self.console.setCvar('g_waverespawns', '1')
            self.console.say('^7Wave Respawns: ^2ON')
        elif data.lower() == 'off':
            self.console.setCvar('g_waverespawns', '0')
            self.console.say('^7Wave Respawns: ^1OFF')

    def cmd_pasetnextmap(self, data, client=None, cmd=None):
        """
        <mapname> - Set the nextmap (partial map name works)
        """
        if not data:
            client.message('^7Invalid or missing data, try !help pasetnextmap')
        else:
            match = self.console.getMapsSoundingLike(data)
            if isinstance(match, str):
                mapname = match
                self.console.setCvar('g_nextmap', mapname)
                if client:
                    client.message('^7nextmap set to %s' % mapname)
            elif isinstance(match, list):
                client.message('do you mean : %s ?' % ', '.join(match[:5]))
            else:
                client.message('^7cannot find any map like [^4%s^7]' % data)

    def cmd_parespawngod(self, data, client, cmd=None):
        """
        <seconds> - Set the respawn protection in seconds.
        """
        if not data:
            client.message('^7Missing data, try !help parespawngod')
        else:
            self.console.setCvar('g_respawnProtection', data)

    def cmd_parespawndelay(self, data, client, cmd=None):
        """
        <seconds> - Set the respawn delay in seconds.
        """
        if not data:
            client.message('^7Missing data, try !help parespawndelay')
        else:
            self.console.setCvar('g_respawnDelay', data)

    def cmd_pacaplimit(self, data, client, cmd=None):
        """
        <caps> - Set the ammount of flagcaps before map is over.
        """
        if not data:
            client.message('^7Missing data, try !help pacaplimit')
        else:
            self.console.setCvar('capturelimit', data)

    def cmd_patimelimit(self, data, client, cmd=None):
        """
        <minutes> - Set the minutes before map is over.
        """
        if not data:
            client.message('^7Missing data, try !help patimelimit')
        else:
            self.console.setCvar('timelimit', data)

    def cmd_pafraglimit(self, data, client, cmd=None):
        """
        <frags> - Set the ammount of points to be scored before map is over.
        """
        if not data:
            client.message('^7Missing data, try !help pafraglimit')
        else:
            self.console.setCvar('fraglimit', data)

    def cmd_pabluewave(self, data, client, cmd=None):
        """
        <seconds> - Set the blue wave respawn time.
        """
        if not data:
            client.message('^7Missing data, try !help pabluewave')
        else:
            self.console.setCvar('g_bluewave', data)

    def cmd_paredwave(self, data, client, cmd=None):
        """
        <seconds> - Set the red wave respawn time.
        """
        if not data:
            client.message('^7Missing data, try !help paredwave')
        else:
            self.console.setCvar('g_redwave', data)

    def cmd_pahotpotato(self, data, client, cmd=None):
        """
        <minutes> - Set the flag explode time.
        """
        if not data:
            client.message('^7Missing data, try !help pahotpotato')
        else:
            self.console.setCvar('g_hotpotato', data)

    def cmd_pasetwave(self, data, client, cmd=None):
        """
        <seconds> - Set the wave respawn time for both teams.
        """
        if not data:
            client.message('^7Missing data, try !help pasetwave')
        else:
            self.console.setCvar('g_bluewave', data)
            self.console.setCvar('g_redwave', data)

    def cmd_pasetgravity(self, data, client, cmd=None):
        """
        <value> - Set the gravity value. default = 800 (less means less gravity)
        """
        if not data:
            client.message('^7Missing data, try !help pasetgravity')
        else:
            if data.lower() in ('def', 'reset'):
                data = 800
            self.console.setCvar('g_gravity', data)
            client.message('^7Gravity: %s' % data)

    def set_configmode(self, mode=None):
        if mode:
            modestring = 'mode_%s' % mode
            if modestring in self._gameconfig:
                cfgfile = self._gameconfig.get(modestring)
                filename = os.path.join(self.console.game.fs_homepath, self.console.game.fs_game, cfgfile)
                if os.path.isfile(filename):
                    self.info('executing config file: %s', cfgfile)
                    self.console.write('exec %s' % cfgfile)

        if self._matchmode:
            cfgfile = self._gameconfig.get('matchon', None)
        else:
            cfgfile = self._gameconfig.get('matchoff', None)

        if cfgfile:
            filename = os.path.join(self.console.game.fs_homepath, self.console.game.fs_game, cfgfile)
            if os.path.isfile(filename):
                self.info('executing configfile: %s', cfgfile)
                self.console.write('exec %s' % cfgfile)

    def cmd_pakill(self, data, client, cmd=None):
        """
        <player> - kill a player.
        (You can safely use the command without the 'pa' at the beginning)
        """
        if not data:
            client.message('^7invalid data, try !help pakill')
            return

        if not (sclient := self._adminPlugin.findClientPrompt(data, client)):
            # a player matchin the name was not found, a list of closest matches will be displayed
            # we can exit here and the user will retry with a more specific player
            return

        self.console.write('smite %s' % sclient.cid)

    def cmd_palms(self, data, client, cmd=None):
        """
        Change game type to Last Man Standing
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.console.setCvar('g_gametype', '1')
        if client:
            client.message('^7game type changed to ^4Last Man Standing')
        self.set_configmode('lms')

    def cmd_pajump(self, data, client, cmd=None):
        """
        Change game type to Jump
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.console.setCvar('g_gametype', '9')
        if client:
            client.message('^7game type changed to ^4Jump')
        self.set_configmode('jump')

    def cmd_pafreeze(self, data, client, cmd=None):
        """
        Change game type to Freeze Tag
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.console.setCvar('g_gametype', '10')
        if client:
            client.message('^7game type changed to ^4Freeze Tag')
        self.set_configmode('freeze')

    def cmd_paskins(self, data, client, cmd=None):
        """
        Set the use of client skins <on/off>
        (You can safely use the command without the 'pa' at the beginning)
        """
        if not data or data.lower() not in ('on', 'off'):
            client.message('^7invalid or missing data, try !help paskins')
            return

        if data.lower() == 'on':
            self.console.setCvar('g_skins', '1')
            self.console.say('^7Client skins: ^2ON')
        elif data.lower() == 'off':
            self.console.setCvar('g_skins', '0')
            self.console.say('^7Client skins: ^1OFF')

    def cmd_pafunstuff(self, data, client, cmd=None):
        """
        Set the use of funstuff <on/off>
        (You can safely use the command without the 'pa' at the beginning)
        """
        if not data or data.lower() not in ('on', 'off'):
            client.message('^7invalid or missing data, try !help pafunstuff')
            return

        if data.lower() == 'on':
            self.console.setCvar('g_funstuff', 1)
            self.console.say('^7Funstuff: ^2ON')
        elif data.lower() == 'off':
            self.console.setCvar('g_funstuff', 0)
            self.console.say('^7Funstuff: ^1OFF')

    def cmd_pagoto(self, data, client, cmd=None):
        """
        Set the goto <on/off>
        (You can safely use the command without the 'pa' at the beginning)
        """
        if not data or data.lower() not in ('on', 'off'):
            client.message('^7invalid or missing data, try !help pagoto')
            return

        if data.lower() == 'on':
            self.console.setCvar('g_allowgoto', 1)
            self.console.say('^7Goto: ^2ON')
        elif data.lower() == 'off':
            self.console.setCvar('g_allowgoto', 0)
            self.console.say('^7Goto: ^1OFF')

    def cmd_pastamina(self, data, client, cmd=None):
        """
        Set the stamina behavior <default/regain/infinite>
        (You can safely use the command without the 'pa' at the beginning)
        """
        if not data or data.lower() not in ('default', 'regain', 'infinite'):
            client.message('^7invalid or missing data, try !help pastamina')
            return

        if data.lower() == 'default':
            self.console.setCvar('g_stamina', 0)
            self.console.say('^7Stamina mode: ^3DEFAULT')
        elif data.lower() == 'regain':
            self.console.setCvar('g_stamina', 1)
            self.console.say('^7Stamina mode: ^3REGAIN')
        elif data.lower() == 'infinite':
            self.console.setCvar('g_stamina', 2)
            self.console.say('^7Stamina mode: ^3INFINITE')

    def cmd_pagear(self, data, client=None, cmd=None):
        """
        [<gear>] - set the allowed gear on the server
        (You can safely use the command without the 'pa' at the beginning)
        """
        if not data:
            self.printgear(client=client, cmd=cmd)
            # display help text
            client.message('^7Usage: ^3!^7pagear [+/-][%s]' % '|'.join(sorted(self._weapons.keys())))
            client.message('^7Load weapon groups: ^3!^7pagear [+/-][%s]' % '|'.join(sorted(self._weapon_groups.keys())))
            client.message('^7Load defaults: ^3!^7pagear [%s]' % '|'.join(sorted(self._gears.keys())))
            return

        def update_gear(gear_set, param_data):
            """
            update gear_set given the param_data

            @param gear_set: set of letters representing the g_gear cvar value
            @param param_data: !pagear command parameter representing a weapon/item name/preset/group
            """
            cleaned_data = re.sub(r'\s', "", param_data)

            # set a predefined gear
            if cleaned_data in self._gears:
                gear_set.clear()
                gear_set.update(self._gears[cleaned_data])
                return

            # add a specific weapon to the current gear string
            if cleaned_data[:1] in ('+', '-'):
                opt = cleaned_data[:1]
                weapon_codes = self.get_weapon_code(cleaned_data[1:])

                if not weapon_codes:
                    client.message("could not recognize weapon/item %r" % cleaned_data[1:])
                    return

                for weapon_code in weapon_codes:
                    if opt == '+':
                        gear_set.discard(weapon_code)
                    if opt == '-':
                        gear_set.add(weapon_code)

        current_gear_set = set(self.console.getCvar('g_gear').getString())
        new_gear_set = set(current_gear_set)
        for m in re.finditer(r"(all|none|reset|[+-]\s*[\w.]+)", data.strip().lower()):
            update_gear(new_gear_set, m.group())

        if current_gear_set == new_gear_set:
            client.message('^7gear ^1not ^7changed')
            return

        new_gear_cvar = "".join(sorted(new_gear_set))
        self.console.setCvar('g_gear', new_gear_cvar)
        self.printgear(client=client, cmd=cmd, gearstr=new_gear_cvar)

    def cmd_pacaptain(self, data, client, cmd=None):
        """
        [<player>] - Set the given client as the captain for its team
        (You can safely use the command without the 'pa' at the beginning)
        """
        if not self._matchmode:
            client.message("!pacaptain command is available only in match mode")
            return

        if not data:
            sclient = client
        else:
            if not (sclient := self._adminPlugin.findClientPrompt(data, client)):
                return

        if sclient.team == b3.TEAM_SPEC:
            client.message("%s is a spectator! - Can't set captain status" % sclient.name)
            return

        self.console.write("forcecaptain %s" % sclient.cid)

        # only give  notice if the client is not the admin who issued the command:
        # urban terror already display a server message when the captain flag is changed
        if sclient != client:
            team = "^1RED" if sclient.team == b3.TEAM_RED else "^4BLUE"
            sclient.message("^7You were set as captain for the %s ^7team by the Admin" % team)

    def cmd_pasub(self, data, client, cmd=None):
        """
        [<player>] - set the given client as a substitute for its team
        (You can safely use the command without the 'pa' at the beginning)
        """
        if not self._matchmode:
            client.message("!pasub command is available only in match mode")
            return

        if not data:
            sclient = client
        else:
            if not (sclient := self._adminPlugin.findClientPrompt(data, client)):
                return

        if sclient.team == b3.TEAM_SPEC:
            client.message("%s is a spectator! - Can't set substitute status" % sclient.name)
            return

        self.console.write("forcesub %s" % sclient.cid)

        # only give  notice if the client is not the admin who issued the command:
        # urban terror already display a server message when the substitute flag is changed
        if sclient != client:
            team = "^1RED" if sclient.team == b3.TEAM_RED else "^4BLUE"
            sclient.message("^7You were set as substitute for the %s ^7team by the Admin" % team)

    def cmd_pagungame(self, data, client, cmd=None):
        """
        Change game type to Gun Game
        (You can safely use the command without the 'pa' at the beginning)
        """
        self.console.setCvar('g_gametype', '11')
        if client:
            client.message('^7game type changed to ^4Gun Game')
        self.set_configmode('gungame')

    def cmd_painstagib(self, data, client, cmd=None):
        """
        Turn instagib game mode <on/off>
        (You can safely use the command without the 'pa' at the beginning)
        """
        if not data or data.lower() not in ('on', 'off'):
            client.message('^7You must provide an argument of "on" or "off", try !help painstagib')
            return

        if data.lower() == 'on':
            self.console.setCvar('g_instagib', '1')
            self.console.say('^7Instagib mode: ^2ON')
        elif data.lower() == 'off':
            self.console.setCvar('g_instagib', '0')
            self.console.say('^7Instagib mode: ^1OFF')

    def cmd_pahardcore(self, data, client, cmd=None):
        """
        Set the g_hardcore <on/off>
        (You can safely use the command without the 'pa' at the beginning)
        """
        if not data or data.lower() not in ('on', 'off'):
            client.message('^7You must provide an argument of "on" or "off", try !help pahardcore')
            return

        if data.lower() == 'on':
            self.console.setCvar('g_hardcore', 1)
            self.console.say('^7Hardcore: ^2ON')
        elif data.lower() == 'off':
            self.console.setCvar('g_hardcore', 0)
            self.console.say('^7Hardcore: ^1OFF')

    def printgear(self, client, cmd, gearstr=None):
        """
        Print the current gear in the game chat
        """
        if not gearstr:
            # if not explicitly passed get it form the server
            gearstr = self.console.getCvar('g_gear').getString()

        lines = []
        for key in self._weapons:
            lines.append('%s:%s' % (key, '^2ON' if self._weapons[key] not in gearstr else '^1OFF'))

        cmd.sayLoudOrPM(client, '^3current gear: ^7%s' % '^7, '.join(sorted(lines)))

    def getTime(self):
        """ just to ease automated tests """
        return self.console.time()

    def get_weapon_code(self, name):
        """
        try its best to guess the weapon code given a name.
        If name is a group name, then return multiple weapon codes as a string
        """
        if name in self._weapon_groups:
            return self._weapon_groups[name]
        name_tries = [name[:length] for length in (5, 4, 3, 2)]
        for _name in name_tries:
            if _name in self._weapons:
                return self._weapons[_name]
        for _name in name_tries:
            if _name in self._weapon_aliases:
                key = self._weapon_aliases[_name]
                return self._weapons[key]

    def _teamvar(self, client, var):
        """
        Return how much variable has changed
        since player joined its team
        """
        old = client.var(self, 'prev_' + var, 0).value
        new = client.var(self, var, 0).value
        return new - old

    def _saveTeamvars(self, client):
        for var in ('kills', 'deaths', 'teamkills', 'headhits', 'helmethits',
                    'flag_captured', 'flag_returned', 'bomb_planted', 'bomb_defused'):
            old = client.var(self, var, 0).value
            client.setvar(self, "prev_" + var, old)

    def _getScores(self, clients, usexlrstats=True):
        xlrstats = self.console.getPlugin('xlrstats') if usexlrstats else None
        playerstats = {}
        maxstats = {}
        minstats = {}
        keys = 'hsratio', 'killratio', 'teamcontrib', 'xhsratio', 'xkillratio', 'flagperf', 'bombperf'
        now = self.console.time()
        for c in clients:
            if not c.isvar(self, 'teamtime'):
                c.setvar(self, 'teamtime', now)
            age = (now - c.var(self, 'teamtime', 0).value) / 60.0
            kills = max(0, self._teamvar(c, 'kills'))
            deaths = max(0, self._teamvar(c, 'deaths'))
            teamkills = max(0, self._teamvar(c, 'teamkills'))
            hs = self._teamvar(c, 'headhits') + self._teamvar(c, 'helmethits')
            hsratio = min(1.0, hs / (1.0 + kills))  # hs can be greater than kills
            killratio = kills / (1.0 + deaths + teamkills)
            teamcontrib = (kills - deaths - teamkills) / (age + 1.0)
            flag_taken = int(bool(c.var(self, 'flag_taken', 0).value))  # one-time bonus
            flag_captured = self._teamvar(c, 'flag_captured')
            flag_returned = self._teamvar(c, 'flag_returned')
            flagperf = 10 * flag_taken + 20 * flag_captured + flag_returned
            bomb_planted = self._teamvar(c, 'bomb_planted')
            bomb_defused = self._teamvar(c, 'bomb_defused')
            bombperf = bomb_planted + bomb_defused

            playerstats[c.id] = {
                'age': age,
                'hsratio': hsratio,
                'killratio': killratio,
                'teamcontrib': teamcontrib,
                'flagperf': flagperf,
                'bombperf': bombperf,
            }
            stats = xlrstats.get_PlayerStats(c) if xlrstats else None
            if stats:
                playerstats[c.id]['xkillratio'] = stats.ratio
                head = xlrstats.get_PlayerBody(playerid=c.cid, bodypartid=0).kills
                helmet = xlrstats.get_PlayerBody(playerid=c.cid, bodypartid=1).kills
                xhsratio = min(1.0, (head + helmet) / (1.0 + kills))
                playerstats[c.id]['xhsratio'] = xhsratio
            else:
                playerstats[c.id]['xhsratio'] = 0.0
                playerstats[c.id]['xkillratio'] = 0.8
            for key in keys:
                if key not in maxstats or maxstats[key] < playerstats[c.id][key]:
                    maxstats[key] = playerstats[c.id][key]
                if key not in minstats or minstats[key] > playerstats[c.id][key]:
                    minstats[key] = playerstats[c.id][key]

        scores = {}
        weights = {
            'killratio': 1.0,
            'teamcontrib': 0.5,
            'hsratio': 0.3,
            'xkillratio': 1.0,
            'xhsratio': 0.5,
            # weight score for mission objectives higher
            'flagperf': 3.0,
            'bombperf': 3.0,
        }

        weightsum = sum(weights[key] for key in keys)
        for c in clients:
            score = 0.0
            tm = min(1.0, playerstats[c.id]['age'] / 5.0)  # reduce score for players who just joined
            msg = []
            for key in keys:
                denom = maxstats[key] - minstats[key]
                if denom < 0.0001:  # accurate at ne nimis
                    continue
                msg.append("%s=%.3f" % (key, playerstats[c.id][key]))
                keyscore = weights[key] * (playerstats[c.id][key] - minstats[key]) / denom
                if key in ('killratio', 'teamcontrib', 'hsratio'):
                    score += tm * keyscore
                else:
                    score += keyscore

            score /= weightsum
            scores[c.id] = score

        return scores

    def _getRandomTeams(self, clients, checkforced=False):
        blue = []
        red = []
        nonforced = []
        for c in clients:
            # ignore spectators
            if c.team in (b3.TEAM_BLUE, b3.TEAM_RED):
                if checkforced and c.isvar(self, 'paforced'):
                    if c.team == b3.TEAM_BLUE:
                        blue.append(c)
                    else:
                        red.append(c)
                else:
                    nonforced.append(c)

        # distribute nonforced players
        random.shuffle(nonforced)
        n = (len(nonforced) + len(blue) + len(red)) // 2 - len(blue)
        blue.extend(nonforced[:n])
        red.extend(nonforced[n:])
        return blue, red

    def _getTeamScore(self, team, scores):
        return sum(scores.get(c.id, 0.0) for c in team)

    def _getTeamScoreDiff(self, blue, red, scores):
        bluescore = self._getTeamScore(blue, scores)
        redscore = self._getTeamScore(red, scores)
        return bluescore - redscore

    def _getTeamScoreDiffForAdvise(self, minplayers=None):
        clients = self.console.clients.getList()
        gametype = self._getGameType()
        tdm = (gametype == 'tdm')
        scores = self._getScores(clients, usexlrstats=tdm)
        blue = [c for c in clients if c.team == b3.TEAM_BLUE]
        red = [c for c in clients if c.team == b3.TEAM_RED]

        if minplayers and len(blue) + len(red) < minplayers:
            return None, None

        diff = self._getTeamScoreDiff(blue, red, scores)

        if tdm:
            bs, rs = self._getAvgKillsRatios(blue, red)
            avgdiff = bs - rs
        else:
            # just looking at kill ratios doesn't work well for CTF, so we base
            # the balance diff on the skill diff for now
            sincelast = self.console.time() - self._lastbal
            damping = min(1.0, sincelast / (1.0 + 60.0 * self._minbalinterval))
            avgdiff = 1.21 * diff * damping

        return avgdiff, diff

    def _getRecentKills(self, tm):
        t0 = self.console.time() - tm
        i = len(self._killhistory) - 1
        while i >= 0:
            t, team = self._killhistory[i]
            if t < t0:
                break

            i -= 1
            yield t, team

    def _getAvgKillsRatios(self, blue, red):
        if not blue or not red:
            return 0.0, 0.0

        tmin = 2.0
        tmax = 4.0
        totkpm = len(list((self._getRecentKills(60))))
        tm = max(tmin, tmax - 0.1 * totkpm)
        recentcontrib = {}
        t0 = self.console.time() - tm * 60
        for c in blue + red:
            hist = c.var(self, 'teamcontribhist', []).value
            k = 0
            d = 0
            for t, s in hist:
                if t0 < t:
                    if s > 0:
                        k += 1
                    elif s < 0:
                        d += 1
            recentcontrib[c.id] = k / (1.0 + d)

        def contribcmp(a, b):
            return b3.functions.cmp(recentcontrib[b.id], recentcontrib[a.id])

        blue = sorted(blue, key=functools.cmp_to_key(contribcmp))
        red = sorted(red, key=functools.cmp_to_key(contribcmp))
        n = min(len(blue), len(red))
        if n > 3:
            n = 3 + int((n - 3) / 2)

        bs = float(sum(recentcontrib[c.id] for c in blue[:n])) / n / tm
        rs = float(sum(recentcontrib[c.id] for c in red[:n])) / n / tm
        self.debug('recent: n=%d tm=%.2f %.2f %.2f' % (n, tm, bs, rs))
        return bs, rs

    def _forgetTeamContrib(self):
        self._oldadv = (None, None, None)
        clients = self.console.clients.getList()
        for c in clients:
            c.setvar(self, 'teamcontribhist', [])
            self._saveTeamvars(c)

    def _countSnipers(self, team):
        n = 0
        for c in team:
            kills = max(0, c.var(self, 'kills', 0).value)
            deaths = max(0, c.var(self, 'deaths', 0).value)
            ratio = kills / (1.0 + deaths)
            if ratio < 1.2:
                # Ignore sniper noobs
                continue
                # Count players with SR8 and PSG1
            gear = getattr(c, 'gear', '')
            if self._gear_contains_sniper(gear):
                n += 1

        return n

    def _gear_contains_sniper(self, gear):
        return 'Z' in gear or 'N' in gear or 'i' in gear

    def _move(self, blue, red, scores=None):
        # Filter out players already in correct team
        blue = [c for c in blue if c.team != b3.TEAM_BLUE]
        red = [c for c in red if c.team != b3.TEAM_RED]

        if not blue and not red:
            return 0

        clients = self.console.clients.getList()
        numblue = len([c for c in clients if c.team == b3.TEAM_BLUE])
        numred = len([c for c in clients if c.team == b3.TEAM_RED])
        self.ignoreSet(30)

        # We have to make sure we don't get a "too many players" error from the
        # server when we move the players. Start moving from the team with most
        # players. If the teams are equal in numbers, temporarily put one
        # player in spec mode.
        moves = len(blue) + len(red)
        if blue and numblue == numred:
            spec = blue.pop()
            self.console.write(f'forceteam {spec.cid} spectator')
            numred -= 1
            moves -= 1
        else:
            spec = None

        queue = []
        for _ in range(moves):
            if (blue and numblue < numred) or (blue and not red):
                c = blue.pop()
                newteam = 'blue'
                self.console.write(f'forceteam {c.cid} {newteam}')
                numblue += 1
                numred -= 1
            elif red:
                c = red.pop()
                newteam = 'red'
                self.console.write(f'forceteam {c.cid} {newteam}')
                numblue -= 1
                numred += 1
            else:
                c = None
                newteam = None

            if newteam and scores:
                colorpfx = '^1' if newteam == 'red' else '^4'
                msg = f"{colorpfx}You were moved to {newteam} team for balance."

                # send private msg after all joins, seem like we can lose the
                # msg otherwise...
                queue.append((c, msg))

        if spec:
            self.console.write(f'forceteam {spec.cid} blue')

        for c, msg in queue:
            c.message(msg)

        return moves

    def _randTeams(self, times, slack, maxmovesperc=None):
        """
        Randomize teams a few times and pick the most balanced
        """
        clients = self.console.clients.getList()
        scores = self._getScores(clients)
        oldblue = [c for c in clients if c.team == b3.TEAM_BLUE]
        oldred = [c for c in clients if c.team == b3.TEAM_RED]
        n = len(oldblue) + len(oldred)
        olddiff = self._getTeamScoreDiff(oldblue, oldred, scores)
        bestdiff = None  # best balance diff so far when diff > slack
        sbestdiff = None  # best balance diff so far when diff < slack
        bestnumdiff = None  # best difference in number of snipers so far
        bestblue = bestred = None  # best teams so far when diff > slack
        sbestblue = sbestred = None  # new teams so far when diff < slack
        epsilon = 0.0001

        for _ in range(times):
            blue, red = self._getRandomTeams(clients, checkforced=True)
            if maxmovesperc:
                m = (self._countMoves(oldblue, blue) +
                     self._countMoves(oldred, red))
                if m > max(2, int(round(maxmovesperc * n))):
                    continue

            diff = self._getTeamScoreDiff(blue, red, scores)

            if abs(diff) <= slack:
                # balance below slack, try to distribute the snipers instead
                numdiff = abs(self._countSnipers(blue) - self._countSnipers(red))
                if bestnumdiff is None or numdiff < bestnumdiff:
                    # got better sniper num diff
                    sbestblue, sbestred = blue, red
                    sbestdiff, bestnumdiff = diff, numdiff

                elif numdiff == bestnumdiff and abs(diff) < abs(sbestdiff) - epsilon:
                    # same number of snipers but better balance diff
                    sbestblue, sbestred = blue, red
                    sbestdiff = diff

            elif bestdiff is None or abs(diff) < abs(bestdiff) - epsilon:
                # balance above slack threshold
                bestblue, bestred = blue, red
                bestdiff = diff

        if sbestdiff is not None:
            return olddiff, sbestdiff, sbestblue, sbestred, scores

        return olddiff, bestdiff, bestblue, bestred, scores

    def _countMoves(self, old, new):
        i = 0
        newnames = [c.name for c in new]
        for c in old:
            if c.name not in newnames:
                i += 1
        return i

    def skillcheck(self):
        """
        Skill balancer cronjob.
        """
        if self._balancing or self.ignoreCheck():
            return

        gametype = self._getGameType()

        # run skillbalancer only if current
        # gametype is in autobalance_gametypes list
        if gametype not in self._autobalance_gametypes_array:
            return

        # skill balance disabled
        if self._skill_balance_mode == 0:
            return

        avgdiff, diff = self._getTeamScoreDiffForAdvise(minplayers=3)
        if avgdiff is None:
            return

        absdiff = abs(avgdiff)
        unbalanced = False

        if absdiff >= self._skilldiff:
            unbalanced = True

        if unbalanced or self._skill_balance_mode == 1:
            if absdiff > 0.2:
                self.console.say('Avg kill ratio diff is %.2f, skill diff is %.2f' % (avgdiff, diff))
                if self._skill_balance_mode == 1:
                    # give advice if teams are unfair
                    self._advise(avgdiff, 2)
                else:
                    # only report stronger team, we will balance/skuffle below
                    self._advise(avgdiff, 0)

        if unbalanced and 2 <= self._skill_balance_mode <= 3:
            if self._skill_balance_mode == 2:
                func = self.cmd_pabalance
            else:
                func = self.cmd_paskuffle

            # if we are in the middle of a round in a round based gametype, delay till the end of it
            if gametype in self._round_based_gametypes and not self._is_round_end:
                self._pending_skillbalance = True
                self._skillbalance_func = func
            else:
                # execute it now
                func()

    def _advise(self, avgdiff, mode):
        # mode 0: no advice
        # mode 1: give advice
        # mode 2: give advice if teams are unfair
        absdiff = 5 * abs(avgdiff)
        unfair = absdiff > 2.31  # constant carefully reviewed by an eminent team of trained Swedish scientistians :)
        word = None
        same = 'remains '
        stronger = 'has become '
        if 1 <= absdiff < 2:
            word = 'stronger'
        elif 2 <= absdiff < 4:
            word = 'dominating'
        elif 4 <= absdiff < 6:
            word = 'overpowering'
        elif 6 <= absdiff < 8:
            word = 'supreme'
        elif 8 <= absdiff < 10:
            word = 'Godlike!'
        elif 10 <= absdiff:
            word = 'probably cheating :P'
            same = 'is '
            stronger = 'is '

        if word:
            oldteam, oldword, oldabsdiff = self._oldadv
            team = avgdiff < 0 and 'Red' or 'Blue'
            if team == oldteam:
                if word == oldword:
                    msg = '%s team %s%s' % (team, same, word)
                elif absdiff > oldabsdiff:
                    # stronger team is becoming even stronger
                    msg = '%s team %s%s' % (team, stronger, word)
                elif absdiff < oldabsdiff:
                    # stronger team is becoming weaker
                    msg = '%s team is just %s' % (team, word)
                    if absdiff < 4:
                        # difference not too big, teams may soon be fair
                        unfair = False
                else:
                    # FIXME (Fenix): here 'msg' is not initialized thus it produces a warning
                    return
            else:
                msg = '%s team is now %s' % (team, word)

            if unfair and (mode == 1 or mode == 2):
                msg += ', use !bal to balance the teams'

            if not unfair and mode == 1:
                msg += ', but no action necessary yet'

            self._oldadv = (team, word, absdiff)

        else:
            msg = 'Teams seem fair'
            self._oldadv = (None, None, None)

        self.console.say(msg)
