import time

import b3
import b3.config
import b3.events
import b3.plugin
from b3.clients import Client

__version__ = '0.6.9'
__author__ = 'Beber888, GrosBedo'


class TeamData:
    def __init__(self, team=b3.TEAM_UNKNOWN):
        self.team = team
        if team == b3.TEAM_RED:
            self.name = 'Red'
        elif team == b3.TEAM_BLUE:
            self.name = 'Blue'
        else:
            self.name = 'UnknownTeam'
        self.max_flag = 0
        self.max_flag_client = None
        self.time = 0
        self.min_time = -1
        self.min_time_client = None
        self.taken_time = 0
        self.flag_taken = 0


class FlagstatsPlugin(b3.plugin.Plugin):
    CONFIG_ERRORS = (ValueError, b3.config.NoOptionError, b3.config.NoSectionError)
    FLAG_TAKEN_ACTIONS = ('team_CTF_redflag', 'team_CTF_blueflag', 'flag_taken')

    def __init__(self, console, config=None):
        super().__init__(console, config)
        self._adminPlugin = None
        self._reset_flagstats_stats = False
        self._min_level_flagstats_cmd = 1
        self._min_level_topflags_cmd = 1
        self._clientvar_name = 'flagstats_info'
        self._show_awards = False
        self._separate_awards = False
        self._show_personal_best = False
        self.blue_team = TeamData(b3.TEAM_BLUE)
        self.red_team = TeamData(b3.TEAM_RED)

    def onLoadConfig(self):
        try:
            self._min_level_flagstats_cmd = self.config.getint('commands', 'flagstats')
        except self.CONFIG_ERRORS:
            self.debug('Using default value (%i) for commands::flagstats', self._min_level_flagstats_cmd)

        try:
            self._min_level_topflags_cmd = self.config.getint('commands', 'topflags')
        except self.CONFIG_ERRORS:
            self.debug('Using default value (%i) for commands::topflags', self._min_level_topflags_cmd)

        try:
            self._reset_flagstats_stats = self.config.getboolean('settings', 'reset_flagstats')
        except self.CONFIG_ERRORS:
            self.debug('Using default value (%s) for settings::reset_flagstats', self._reset_flagstats_stats)

        try:
            self._show_awards = self.config.getboolean('settings', 'show_awards')
        except self.CONFIG_ERRORS:
            self.debug('Using default value (%s) for settings::show_awards', self._show_awards)

        try:
            self._show_personal_best = self.config.getboolean('settings', 'show_personal_best')
        except self.CONFIG_ERRORS:
            self.debug('Using default value (%s) for settings::show_personal_best', self._show_personal_best)

        try:
            self._separate_awards = self.config.getboolean('settings', 'separate_awards')
        except self.CONFIG_ERRORS:
            self.debug('Using default value (%s) for settings::separate_awards', self._separate_awards)

    def onStartup(self):
        # reset stats at round start so that players can still query their stats at the end
        self.registerEvent('EVT_GAME_ROUND_START', self.on_round_start)
        self.registerEvent('EVT_CLIENT_ACTION', self.on_client_action)
        self.registerEvent('EVT_GAME_FLAG_RETURNED', self.on_flag_return)
        # used to show awards at the end of round
        self.registerEvent('EVT_GAME_EXIT', self.on_game_exit)

        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.error('Could not find admin plugin')
            return False

        self.register_commands_from_config()

    def on_round_start(self, event):
        if self.console.game.gameType == 'ctf':
            self.game_reinit(event)

    def on_game_exit(self, event):
        if self._show_awards and self.console.game.gameType == 'ctf':
            self.flag_awards_show()

    def on_client_action(self, event):
        if not self.console.game.gameType == 'ctf':
            return

        client = event.client
        action = event.data

        if client.team == b3.TEAM_BLUE or action == 'team_CTF_redflag':
            teamdatas = self.blue_team
            oppositeteamdatas = self.red_team
        elif client.team == b3.TEAM_RED or action == 'team_CTF_blueflag':
            teamdatas = self.red_team
            oppositeteamdatas = self.blue_team
        else:  # this is not a CTF event and no player is acting in this event, so we just pass
            return

        # Flag taken
        if action in self.FLAG_TAKEN_ACTIONS and oppositeteamdatas.flag_taken == 0:
            oppositeteamdatas.flag_taken = 1
            oppositeteamdatas.taken_time = time.time()
            client.var(self, 'flagtaken', 0).value += 1

        # Flag returned
        elif action == 'flag_returned' and teamdatas.flag_taken == 1:
            teamdatas.flag_taken = 0
            client.var(self, 'flagreturned', 0).value += 1

        # Flag captured
        elif action == 'flag_captured' and oppositeteamdatas.flag_taken == 1:
            oppositeteamdatas.flag_taken = 0
            time_capture = time.time() - oppositeteamdatas.taken_time
            if client:
                client.var(self, 'flagcaptured', 0).value += 1
                flagcaptures = client.var(self, 'flagcaptured', 0).value
                if teamdatas.max_flag < flagcaptures:
                    teamdatas.max_flag = flagcaptures
                    teamdatas.max_flag_client = client
                if teamdatas.min_time > time_capture:
                    teamdatas.min_time = time_capture
                    teamdatas.min_time_client = client
                if client.var(self, 'flagbesttime', -1).value < time_capture:
                    # new personal record !
                    client.setvar(self, 'flagbesttime', time_capture)
                    self.show_message_to_client(client, time_capture, best_time=True)
                else:
                    self.show_message_to_client(client, time_capture)

        # Flag carrier killed
        elif action == 'flag_carrier_kill':
            client.var(self, 'flagcarrierkill', 0).value += 1

    def on_flag_return(self, event):
        if event.data == 'RED':
            self.red_team.flag_taken = 0
        elif event.data == 'BLUE':
            self.blue_team.flag_taken = 0
        else:
            self.warning('on_flag_return: unhandled value [%s]', event.data)

    def show_message_to_client(self, client, time_capture, best_time=False):
        """\
        display the message
        """
        flagcaptured = client.var(self, 'flagcaptured', 0).value
        plural = 's' if flagcaptured > 1 else ''
        self.console.write('%s^3 captured ^5%s^3 flag%s in ^5%s^3' %
                           (client.name, flagcaptured, plural, self.show_time(time_capture)))
        if best_time and self._show_personal_best:
            client.message('^3%s: New personnal record for flag capture ! (^5%s^3)' %
                           (client.name, self.show_time(time_capture)))

    def cmd_flagstats(self, data, client, cmd=None):
        """\
        [player] - Show a players number of flag captured
        """
        sclient = client
        if data:
            if args := self._adminPlugin.parseUserCmd(data):
                if not (sclient := self._adminPlugin.findClientPrompt(args[0], client)):
                    return
            else:
                client.message('^7Invalid data, try !help flag')
                return

        msg = self.format_client_stats(sclient)
        client.message(msg)

    def format_client_stats(self, client: Client) -> str:
        return '^7%s took ^5%s ^7flags, returned ^5%s^7, captured ^5%s^7, def ^5%s^7, best capture time ^5%s ^7' % (
            client.name, client.var(self, 'flagtaken', 0).value, client.var(self, 'flagreturned', 0).value,
            client.var(self, 'flagcaptured', 0).value,
            (client.var(self, 'flagreturned', 0).value + client.var(self, 'flagcarrierkill', 0).value),
            self.show_time(client.var(self, 'flagbesttime', -1).value))

    def game_reinit(self, event):
        if self._reset_flagstats_stats:
            for c in self.console.clients.getList():
                self.init_flagstats_stats(c)

        self.red_team = TeamData(b3.TEAM_RED)
        self.blue_team = TeamData(b3.TEAM_BLUE)

    def init_flagstats_stats(self, client):
        # initialize the clients' flag stats
        client.setvar(self, 'flagtaken', 0)
        client.setvar(self, 'flagreturned', 0)
        client.setvar(self, 'flagcaptured', 0)
        client.setvar(self, 'flagcarrierkill', 0)
        client.setvar(self, 'flagbesttime', -1)

    def cmd_topflags(self, data, client, cmd=None):
        """\
        Show the flag awards of the current map
        """
        self.flag_awards_show(client)

    @staticmethod
    def show_time(sec):
        """
        Convert a time in seconds into minutes and hours
        """
        if sec < 0:
            result = 'None'
        else:
            hrs = int(sec / 3600)
            sec -= hrs * 3600
            minute = int(sec / 60)
            sec -= minute * 60
            result = ''
            if hrs > 0:
                result = ''.join([result, '%s h ' % hrs])
            if minute > 0:
                result = ''.join([result, '%s m ' % minute])
            result = ''.join([result, '%0.2f s' % sec])

        return result

    def flag_awards_show(self, client=None):
        message_func = client.message if client else self.console.say
        if self._separate_awards:
            msgblue = self.team_awards_message(self.blue_team)
            msgred = self.team_awards_message(self.red_team)
            if not msgred and not msgblue:
                message_func('There is no flag stats recorded yet, please wait for a capture to happen.')
            else:
                if msgblue:
                    message_func('^4Blue Awards: ^3%s' % msgblue)
                if msgred:
                    message_func('^4Red Awards: ^3%s' % msgred)
        else:
            if msg := self.merged_awards_message():
                message_func('^3CTF Awards: %s' % msg)
            else:
                if client:
                    message_func('There is no flag stats recorded yet, please wait for a capture to happen.')

    def merged_awards_message(self):
        msg = ''

        # Most Flags
        if self.blue_team.max_flag > self.red_team.max_flag:
            plural = 's' if self.blue_team.max_flag > 1 else ''
            msg = ''.join([msg, 'Most Flags: %s [^4Blue^3] (^5%s^3 flag%s) - ' % (
                self.blue_team.max_flag_client.name, self.blue_team.max_flag, plural)])
        elif self.blue_team.max_flag < self.red_team.max_flag:
            plural = 's' if self.red_team.max_flag > 1 else ''
            msg = ''.join([msg, 'Most Flags: %s [^1Red^3] (^5%s^3 flag%s) - ' % (
                self.red_team.max_flag_client.name, self.red_team.max_flag, plural)])
        elif self.blue_team.max_flag == self.red_team.max_flag and self.blue_team.max_flag_client is not None:
            msg = ''.join([msg, 'Most Flags: %s [^4Blue^3] and %s [^1Red^3] (^5%s^3 flags) - ' % (
                self.blue_team.max_flag_client.name, self.red_team.max_flag_client.name,
                self.red_team.max_flag)])
        else:  # both are None
            msg = ''

        # BEST DEFENDER
        clientmaxdef = None
        for c in self.console.clients.getList():
            if self.defensive_score(clientmaxdef) < self.defensive_score(c):
                clientmaxdef = c

        if (score := self.defensive_score(clientmaxdef)) > 0:
            if clientmaxdef.team == b3.TEAM_BLUE:
                tmpteam = '^4Blue'
            elif clientmaxdef.team == b3.TEAM_RED:
                tmpteam = '^1Red'
            else:
                tmpteam = '^1Free'
            msg = ''.join([msg, 'Best Defender: %s [%s^3] (def ^5%s^3) - ' % (clientmaxdef.name, tmpteam, score)])

        # FASTEST CAPTURE
        # If blue team's fastest cap time is smaller than red team's, we take blue's score.
        # Another case : blue team captured, red did not, so red time is -1 by default, but
        # in this case blue team's fastest cap time is taken.
        if (self.blue_team.min_time < self.red_team.min_time and self.blue_team.min_time != -1) \
                or (self.blue_team.min_time > 0 and self.red_team.min_time == -1):
            msg = ''.join([msg, 'Fastest Cap: %s [^4Blue^3] (^5%s^3)' % (
                self.blue_team.min_time_client.name, self.show_time(self.blue_team.min_time))])
        elif (self.blue_team.min_time > self.red_team.min_time != -1) \
                or (self.red_team.min_time > 0 and self.blue_team.min_time == -1):
            msg = ''.join([msg, 'Fastest Cap: %s [^1Red^3] (^5%s^3)' % (
                self.red_team.min_time_client.name, self.show_time(self.red_team.min_time))])
        elif self.blue_team.min_time == self.red_team.min_time and self.blue_team.min_time_client is not None:
            msg = ''.join([msg, 'Fastest Cap: %s [^4Blue^3] and %s [^1Red^3] (^5%s^3)' % (
                self.blue_team.min_time_client.name, self.red_team.min_time_client.name,
                self.show_time(self.blue_team.min_time))])

        return msg

    def team_awards_message(self, team: TeamData) -> str:
        msg = ''

        if team.max_flag_client is not None:
            plural = 's' if team.max_flag > 1 else ''
            msg = ''.join([msg, 'Most Flags: %s (^5%s^3 flag%s) - ' % (
                team.max_flag_client.name, team.max_flag, plural)])

        clientmaxdef = None
        for c in self.console.clients.getList():
            if c.team != team.team:
                continue
            if self.defensive_score(clientmaxdef) < self.defensive_score(c):
                clientmaxdef = c

        if (score := self.defensive_score(clientmaxdef)) > 0:
            tmpteam = f'^4{team.name}'
            msg = ''.join(
                [msg, 'Best Defender: %s [%s^3] (def ^5%s^3) - ' % (clientmaxdef.name, tmpteam, score)])

        if team.min_time_client is not None:
            msg = ''.join([msg, 'Fastest Cap: %s (^5%s^3)' % (
                team.min_time_client.name, self.show_time(team.min_time))])

        return msg

    def defensive_score(self, client: Client) -> int:
        if not client:
            return -1
        return (
                client.var(self, 'flagcarrierkill', 0).value +
                client.var(self, 'flagreturned', 0).value
        )
