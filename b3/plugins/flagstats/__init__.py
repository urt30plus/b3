import b3, time
import b3.events
import b3.plugin

__version__ = '0.6.9'
__author__ = 'Beber888, GrosBedo'


class TeamData():
    name = 'UnknownTeam'
    maxFlag = 0
    maxFlagClients = None
    Time = 0
    minTime = -1
    minTimeClient = None
    TakenTime = 0
    FlagTaken = 0


class RedTeamData(TeamData):
    name = 'Red'


class BlueTeamData(TeamData):
    name = 'Blue'


class FlagstatsPlugin(b3.plugin.Plugin):
    _adminPlugin = None
    _reset_flagstats_stats = None
    _min_level_flagstats_cmd = None
    _clientvar_name = 'flagstats_info'
    _show_awards = None
    GameType = 0

    def onLoadConfig(self):

        try:
            self._min_level_flagstats_cmd = self.config.getint('commands', 'flagstats')
        except:
            self._min_level_flagstats_cmd = 1
            self.debug('Using default value (%i) for commands::flagstats', self._min_level_flagstats_cmd)

        try:
            self._min_level_topflags_cmd = self.config.getint('commands', 'topflags')
        except:
            self._min_level_topflags_cmd = 1
            self.debug('Using default value (%i) for commands::topflags', self._min_level_topflags_cmd)

        try:
            self._reset_flagstats_stats = self.config.getboolean('settings', 'reset_flagstats')
        except:
            self._reset_flagstats_stats = False
            self.debug('Using default value (%s) for settings::reset_flagstats', self._reset_flagstats_stats)

        try:
            self._show_awards = self.config.getboolean('settings', 'show_awards')
        except:
            self._show_awards = False
            self.debug('Using default value (%s) for settings::show_awards', self._show_awards)

        try:
            self._show_personal_best = self.config.getboolean('settings', 'show_personal_best')
        except:
            self._show_personal_best = False
            self.debug('Using default value (%s) for settings::show_personal_best', self._show_personal_best)

        try:
            self._separate_awards = self.config.getboolean('settings', 'separate_awards')
        except:
            self._separate_awards = False
            self.debug('Using default value (%s) for settings::separate_awards', self._separate_awards)

        return

    def onStartup(self):
        self.registerEvent('EVT_CLIENT_ACTION')
        try:
            self.registerEvent('EVT_GAME_FLAG_RETURNED')
        except:
            pass
        self.registerEvent('EVT_GAME_EXIT')  # used to show awards at the end of round
        # self.registerEvent(b3.events.EVT_GAME_ROUND_END) # used to show awards at the end of round
        self.registerEvent(
            'EVT_GAME_ROUND_START')  # better to reinit stats at round start than round end, so that players can still query their stats at the end

        # Initialize the teams' flag stats
        self.BlueTeamData = BlueTeamData()
        self.RedTeamData = RedTeamData()

        # Load admin plugin
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('Could not find admin plugin')
            return False

        self.register_commands_from_config()

    def onEvent(self, event):
        """\
        Handle intercepted events
        """
        if self.console.game.gameType == 'ctf':
            try:
                if event.type == self.console.getEventID('EVT_GAME_FLAG_RETURNED'):
                    self.FlagReturn(event)
                    return
            except:
                pass

            if event.type == self.console.getEventID('EVT_CLIENT_ACTION'):
                self.FlagCounter(event)
            elif event.type == self.console.getEventID('EVT_GAME_EXIT'):
                if self._show_awards:
                    self.flag_awards_show()
            elif event.type == self.console.getEventID('EVT_GAME_ROUND_START'):
                self.game_reinit(event)
        return

    def init_flagstats_stats(self, client):
        # initialize the clients' flag stats
        client.setvar(self, 'flagtaken', 0)
        client.setvar(self, 'flagreturned', 0)
        client.setvar(self, 'flagcaptured', 0)
        client.setvar(self, 'flagcarrierkill', 0)
        client.setvar(self, 'flagbesttime', -1)

    def FlagCounter(self, event):
        """\
        A Event was made.
        """

        # VARS INITIAZITATION
        client = event.client
        self.teamdatas = None

        # TEAMS INITIALIZATION
        if client.team == b3.TEAM_BLUE or event.data == 'team_CTF_redflag':
            self.teamdatas = self.BlueTeamData
            self.oppositeteamdatas = self.RedTeamData
        elif client.team == b3.TEAM_RED or event.data == 'team_CTF_blueflag':
            self.teamdatas = self.RedTeamData
            self.oppositeteamdatas = self.BlueTeamData
        else:  # this is not a CTF event and no player is acting in this event, so we just pass
            return False

        # FLAG MANAGEMENT
        # Flag taken
        if (
                event.data == 'team_CTF_redflag' or event.data == 'team_CTF_blueflag' or event.data == 'flag_taken') and self.oppositeteamdatas.FlagTaken == 0:  # and self.teamdatas.PorteurRed == 0:
            self.oppositeteamdatas.FlagTaken = 1
            self.oppositeteamdatas.TakenTime = time.time()
            client.var(self, 'flagtaken', 0).value += 1

        # Flag returned
        elif event.data == 'flag_returned' and self.teamdatas.FlagTaken == 1:
            self.teamdatas.FlagTaken = 0
            client.var(self, 'flagreturned', 0).value += 1

        # Flag captured
        elif event.data == 'flag_captured' and self.oppositeteamdatas.FlagTaken == 1:  # and client ==  self.PorteurRed:
            self.oppositeteamdatas.FlagTaken = 0
            timeCapture = time.time() - self.oppositeteamdatas.TakenTime

            if client:
                client.var(self, 'flagcaptured', 0).value += 1
                flagcaptures = client.var(self, 'flagcaptured', 0).value
                if self.teamdatas.maxFlag < flagcaptures:
                    self.teamdatas.maxFlag = flagcaptures
                    self.teamdatas.maxFlagClients = client
                if self.teamdatas.minTime > timeCapture or self.teamdatas.minTime == -1:
                    self.teamdatas.minTime = timeCapture
                    self.teamdatas.minTimeClient = client
                if client.var(self, 'flagbesttime', -1).value > timeCapture or client.var(self, 'flagbesttime',
                                                                                          -1).value == -1:
                    # new personal record !
                    client.setvar(self, 'flagbesttime', timeCapture)
                    self.show_messageToClient(client, timeCapture, bestTime=True)
                else:
                    self.show_messageToClient(client, timeCapture)

        # Flag carrier killed
        elif event.data == 'flag_carrier_kill':
            client.var(self, 'flagcarrierkill', 0).value += 1

        return

    def FlagReturn(self, event):
        if event.data == 'RED':
            self.RedTeamData.FlagTaken = 0
        if event.data == 'BLUE':
            self.BlueTeamData.FlagTaken = 0

    def show_messageToClient(self, client, timeCapture, bestTime=False):
        """\
        display the message
        """
        flagcaptured = client.var(self, 'flagcaptured', 0).value
        if flagcaptured > 1:
            Plurial = 's'
        else:
            Plurial = ''
        self.console.write(
            '%s^3 captured ^5%s^3 flag%s in ^5%s^3' % (client.name, flagcaptured, Plurial, self.show_time(timeCapture)))
        if bestTime and self._show_personal_best:
            client.message(
                '^3%s: New personnal record for flag capture ! (^5%s^3)' % (client.name, self.show_time(timeCapture)))

    def cmd_flagstats(self, data, client, cmd=None):
        """\
        [player] - Show a players number of flag captured
        """
        if data is None or data == '':
            if client is not None:
                client.message(
                    '^7You took ^5%s ^7flags, returned ^5%s^7, captured ^5%s^7, def ^5%s^7, best capture time ^5%s ^7' % (
                        client.var(self, 'flagtaken', 0).value, client.var(self, 'flagreturned', 0).value,
                        client.var(self, 'flagcaptured', 0).value,
                        (client.var(self, 'flagreturned', 0).value + client.var(self, 'flagcarrierkill', 0).value),
                        self.show_time(client.var(self, 'flagbesttime', -1).value)))
        else:
            input = self._adminPlugin.parseUserCmd(data)
            if input:
                # input[0] is the player id
                sclient = self._adminPlugin.findClientPrompt(input[0], client)
                if not sclient:
                    # a player matchin the name was not found, a list of closest matches will be displayed
                    # we can exit here and the user will retry with a more specific player
                    client.message('^7Invalid data, can\'t find player %s' % data)
                    return False
            else:
                client.message('^7Invalid data, try !help flag')
                return False

            client.message(
                '^7%s took ^5%s ^7flags returned ^5%s^7 captured ^5%s^7, def ^5%s^7, best capture time ^5%s ^7' % (
                    sclient.name, sclient.var(self, 'flagtaken', 0).value, sclient.var(self, 'flagreturned', 0).value,
                    sclient.var(self, 'flagcaptured', 0).value,
                    (sclient.var(self, 'flagreturned', 0).value + sclient.var(self, 'flagcarrierkill', 0).value),
                    self.show_time(sclient.var(self, 'flagbesttime', -1).value)))

    def game_reinit(self, event):

        if self._reset_flagstats_stats:
            for c in self.console.clients.getList():
                self.init_flagstats_stats(c)

        self.RedTeamData = RedTeamData()
        self.BlueTeamData = BlueTeamData()

    def cmd_topflags(self, data, client, cmd=None):
        """\
        Show the flag awards of the current map
        """
        self.flag_awards_show(client)
        return

    def show_time(self, sec):
        """
        Convert a time in seconds into minutes and hours
        """
        result = ''

        if sec < 0:
            result = 'None'
        else:
            hrs = int(sec / 3600)
            sec -= hrs * 3600
            min = int(sec / 60)
            sec -= min * 60
            if hrs > 0: result = ''.join([result, '%s h ' % hrs])
            if min > 0: result = ''.join([result, '%s m ' % min])
            result = ''.join([result, '%0.2f s' % sec])

        return result

    def flag_awards_show(self, client=None):
        msg = ''
        msgblue = ''
        msgred = ''
        plurial = ''

        if not self._separate_awards:
            # MOST FLAGS
            if self.BlueTeamData.maxFlag > self.RedTeamData.maxFlag:
                if self.BlueTeamData.maxFlag > 1:
                    plurial = 's'
                msg = ''.join([msg, 'Most Flags: %s [^4Blue^3] (^5%s^3 flag%s) - ' % (
                    self.BlueTeamData.maxFlagClients.name, self.BlueTeamData.maxFlag, plurial)])
            elif self.BlueTeamData.maxFlag < self.RedTeamData.maxFlag:
                if self.RedTeamData.maxFlag > 1:
                    plurial = 's'
                msg = ''.join([msg, 'Most Flags: %s [^1Red^3] (^5%s^3 flag%s) - ' % (
                    self.RedTeamData.maxFlagClients.name, self.RedTeamData.maxFlag, plurial)])
            elif self.BlueTeamData.maxFlag == self.RedTeamData.maxFlag and self.BlueTeamData.maxFlagClients is not None:
                msg = ''.join([msg, 'Most Flags: %s [^4Blue^3] and %s [^1Red^3] (^5%s^3 flags) - ' % (
                    self.BlueTeamData.maxFlagClients.name, self.RedTeamData.maxFlagClients.name,
                    self.RedTeamData.maxFlag)])
            else:  # both are None
                msg = ''

            # BEST DEFENDER
            clientmaxdef = None
            for c in self.console.clients.getList():
                if clientmaxdef is None or (
                        (c.var(self, 'flagcarrierkill', 0).value + c.var(self, 'flagreturned', 0).value) > (
                        clientmaxdef.var(self, 'flagcarrierkill', 0).value + clientmaxdef.var(self, 'flagreturned',
                                                                                              0).value)):
                    clientmaxdef = c
            if clientmaxdef is not None and (
                    clientmaxdef.var(self, 'flagcarrierkill', 0).value + clientmaxdef.var(self, 'flagreturned',
                                                                                          0).value) > 0:
                if clientmaxdef.team == b3.TEAM_BLUE:
                    tmpteam = '^4Blue'
                elif clientmaxdef.team == b3.TEAM_RED:
                    tmpteam = '^1Red'
                else:
                    tmpteam = '^1Free'
                msg = ''.join([msg, 'Best Defender: %s [%s^3] (def ^5%s^3) - ' % (clientmaxdef.name, tmpteam,
                                                                                  clientmaxdef.var(self,
                                                                                                   'flagcarrierkill',
                                                                                                   0).value + clientmaxdef.var(
                                                                                      self, 'flagreturned', 0).value)])

            # FASTEST CAPTURE
            if (self.BlueTeamData.minTime < self.RedTeamData.minTime and self.BlueTeamData.minTime != -1) or (
                    self.BlueTeamData.minTime > 0 and self.RedTeamData.minTime == -1):  # If blue team's fastest cap time is smaller than red team's, we take blue's score. Another case : blue team captured, red did not, so red time is -1 by default, but in this case blue team's fastest cap time is taken.
                msg = ''.join([msg, 'Fastest Cap: %s [^4Blue^3] (^5%s^3)' % (
                    self.BlueTeamData.minTimeClient.name, self.show_time(self.BlueTeamData.minTime))])
            elif (self.BlueTeamData.minTime > self.RedTeamData.minTime and self.RedTeamData.minTime != -1) or (
                    self.RedTeamData.minTime > 0 and self.BlueTeamData.minTime == -1):  # opposite of the previous conditionnal test (in favor of red team)
                msg = ''.join([msg, 'Fastest Cap: %s [^1Red^3] (^5%s^3)' % (
                    self.RedTeamData.minTimeClient.name, self.show_time(self.RedTeamData.minTime))])
            elif self.BlueTeamData.minTime == self.RedTeamData.minTime and self.BlueTeamData.minTimeClient is not None:  # if both teams equal and are not null
                msg = ''.join([msg, 'Fastest Cap: %s [^4Blue^3] and %s [^1Red^3] (^5%s^3)' % (
                    self.BlueTeamData.minTimeClient.name, self.RedTeamData.minTimeClient.name,
                    self.show_time(self.BlueTeamData.minTime))])

            # PRINT AWARDS
            if client:
                if msg == '':
                    client.message('There is no flag stats recorded yet, please wait for a capture to happen.')
                else:
                    client.message('^3CTF Awards: %s' % msg)
            else:
                if msg != '':
                    self.console.say('^3CTF Awards: %s' % msg)

        else:
            # BLUE TEAM AWARDS
            # - most flags
            if self.BlueTeamData.maxFlagClients is not None:
                plurial = ''
                if self.BlueTeamData.maxFlag > 1:
                    plurial = 's'
                msgblue = ''.join([msgblue, 'Most Flags: %s (^5%s^3 flag%s) - ' % (
                    self.BlueTeamData.maxFlagClients.name, self.BlueTeamData.maxFlag, plurial)])
            # - best defender
            clientmaxdef = None
            for c in self.console.clients.getList():
                if c.team == b3.TEAM_BLUE and (clientmaxdef is None or (
                        (c.var(self, 'flagcarrierkill', 0).value + c.var(self, 'flagreturned', 0).value) > (
                        clientmaxdef.var(self, 'flagcarrierkill', 0).value + clientmaxdef.var(self, 'flagreturned',
                                                                                              0).value))):
                    clientmaxdef = c
            if clientmaxdef is not None and ((clientmaxdef.var(self, 'flagcarrierkill', 0).value + clientmaxdef.var(
                    self, 'flagreturned', 0).value) > 0):
                tmpteam = '^4Blue'
                msgblue = ''.join([msgblue, 'Best Defender: %s [%s^3] (def ^5%s^3) - ' % (clientmaxdef.name, tmpteam,
                                                                                          clientmaxdef.var(self,
                                                                                                           'flagcarrierkill',
                                                                                                           0).value + clientmaxdef.var(
                                                                                              self, 'flagreturned',
                                                                                              0).value)])
            # - fastest capture
            if self.BlueTeamData.minTimeClient is not None:
                msgblue = ''.join([msgblue, 'Fastest Cap: %s (^5%s^3)' % (
                    self.BlueTeamData.minTimeClient.name, self.show_time(self.BlueTeamData.minTime))])

            # RED TEAM AWARDS
            # - most flags
            if self.RedTeamData.maxFlagClients is not None:
                plurial = ''
                if self.RedTeamData.maxFlag > 1:
                    plurial = 's'
                msgred = ''.join([msgred, 'Most Flags: %s (^5%s^3 flag%s) - ' % (
                    self.RedTeamData.maxFlagClients.name, self.RedTeamData.maxFlag, plurial)])
            # - best defender
            clientmaxdef = None
            for c in self.console.clients.getList():
                if c.team == b3.TEAM_RED and (clientmaxdef is None or (
                        (c.var(self, 'flagcarrierkill', 0).value + c.var(self, 'flagreturned', 0).value) > (
                        clientmaxdef.var(self, 'flagcarrierkill', 0).value + clientmaxdef.var(self, 'flagreturned',
                                                                                              0).value))):
                    clientmaxdef = c
            if clientmaxdef is not None and ((clientmaxdef.var(self, 'flagcarrierkill', 0).value + clientmaxdef.var(
                    self, 'flagreturned', 0).value) > 0):
                tmpteam = '^1Red'
                msgred = ''.join([msgred, 'Best Defender: %s [%s^3] (def ^5%s^3) - ' % (clientmaxdef.name, tmpteam,
                                                                                        clientmaxdef.var(self,
                                                                                                         'flagcarrierkill',
                                                                                                         0).value + clientmaxdef.var(
                                                                                            self, 'flagreturned',
                                                                                            0).value)])
            # - fastest capture
            if self.RedTeamData.minTimeClient is not None:
                msgred = ''.join([msgred, 'Fastest Cap: %s (^5%s^3)' % (
                    self.RedTeamData.minTimeClient.name, self.show_time(self.RedTeamData.minTime))])

            # PRINT AWARDS
            if client:
                if msgred == '' and msgblue == '':
                    client.message('There is no flag stats recorded yet, please wait for a capture to happen.')
                else:
                    if msgblue != '':
                        client.message('^4Blue Awards: ^3%s' % msgblue)
                    if msgred != '':
                        client.message('^1Red Awards: ^3%s' % msgred)
            else:
                if msgred == '' and msgblue == '':
                    self.console.say('There is no flag stats recorded yet, please wait for a capture to happen.')
                else:
                    if msgblue != '':
                        self.console.say('^4Blue Awards: ^3%s' % msgblue)
                    if msgred != '':
                        self.console.say('^1Red Awards: ^3%s' % msgred)
        return
