import functools
import time
from typing import Optional

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

    FLAG_TAKEN_ACTIONS = (
        'team_CTF_redflag',
        'team_CTF_blueflag',
        'flag_taken',
    )

    def __init__(self, console, config=None):
        super().__init__(console, config)
        self._adminPlugin = None
        self._reset_flagstats_stats = False
        self._show_awards = False
        self._separate_awards = False
        self._show_personal_best = False
        self.blue_team = TeamData(b3.TEAM_BLUE)
        self.red_team = TeamData(b3.TEAM_RED)

    def onLoadConfig(self):
        self._reset_flagstats_stats = self.getSetting(
            'settings',
            'reset_flagstats',
            b3.BOOLEAN,
            self._reset_flagstats_stats,
        )
        self._show_awards = self.getSetting(
            'settings',
            'show_awards',
            b3.BOOLEAN,
            self._show_awards,
        )
        self._show_personal_best = self.getSetting(
            'settings',
            'show_personal_best',
            b3.BOOLEAN,
            self._show_personal_best,
        )
        self._separate_awards = self.getSetting(
            'settings',
            'separate_awards',
            b3.BOOLEAN,
            self._separate_awards,
        )

    def onStartup(self):
        self.registerEvent('EVT_GAME_ROUND_START', self.on_round_start)
        self.registerEvent('EVT_CLIENT_ACTION', self.on_client_action)
        self.registerEvent('EVT_GAME_FLAG_RETURNED', self.on_flag_return)
        if self._show_awards:
            self.registerEvent('EVT_GAME_EXIT', self.on_game_exit)

        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.error('Could not find admin plugin')
            return False

        self.register_commands_from_config()

    def isEnabled(self):
        return self.console.game.game_type == 'ctf' and super().isEnabled()

    def on_round_start(self, event):
        self.game_reinit(event)

    def on_game_exit(self, event):
        self.flag_awards_show()

    def on_client_action(self, event):
        client = event.client
        action = event.data

        if action == 'team_CTF_redflag' or client.team == b3.TEAM_BLUE:
            team = self.blue_team
            other_team = self.red_team
        elif action == 'team_CTF_blueflag' or client.team == b3.TEAM_RED:
            team = self.red_team
            other_team = self.blue_team
        else:
            # this is not a CTF event and no player is acting in this event,
            # so we just pass
            return

        if action in self.FLAG_TAKEN_ACTIONS and other_team.flag_taken == 0:
            other_team.flag_taken = 1
            other_team.taken_time = time.time()
            client.var(self, 'flagtaken', 0).value += 1
        elif action == 'flag_returned' and team.flag_taken == 1:
            team.flag_taken = 0
            client.var(self, 'flagreturned', 0).value += 1
        elif action == 'flag_captured' and other_team.flag_taken == 1:
            other_team.flag_taken = 0
            time_capture = time.time() - other_team.taken_time
            if client:
                client.var(self, 'flagcaptured', 0).value += 1
                flagcaptures = client.var(self, 'flagcaptured', 0).value
                if team.max_flag < flagcaptures:
                    team.max_flag = flagcaptures
                    team.max_flag_client = client
                if team.min_time == -1 or team.min_time > time_capture:
                    team.min_time = time_capture
                    team.min_time_client = client
                curr_best = client.var(self, 'flagbesttime', -1)
                if curr_best.value == -1 or curr_best.value > time_capture:
                    # new personal record
                    curr_best.value = time_capture
                    self.show_message_to_client(client,
                                                time_capture,
                                                best_time=True)
                else:
                    self.show_message_to_client(client, time_capture)
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
        caps = client.var(self, 'flagcaptured', 0).value
        cap_time = self.show_time(time_capture)
        plural = 's' if caps > 1 else ''
        self.console.write(
            f'{client.name}^3 captured ^5{caps}^3 flag{plural} in '
            f'^5{cap_time}^3'
        )
        if best_time and self._show_personal_best:
            client.message(
                f'^3{client.name}: New personal record for flag capture ! '
                f'(^5{cap_time}^3)'
            )

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
        flags = client.var(self, 'flagtaken', 0).value
        returns = client.var(self, 'flagreturned', 0).value
        caps = client.var(self, 'flagcaptured', 0).value
        defends = (
                client.var(self, 'flagreturned', 0).value +
                client.var(self, 'flagcarrierkill', 0).value
        )
        best_time = self.show_time(client.var(self, 'flagbesttime', -1).value)
        return (
            f'^7{client.name} took ^5{flags} ^7flags, returned ^5{returns}^7, '
            f'captured ^5{caps}^7, def ^5{defends}^7, '
            f'best capture time ^5{best_time} ^7'
        )

    def game_reinit(self, event) -> None:
        self.red_team = TeamData(b3.TEAM_RED)
        self.blue_team = TeamData(b3.TEAM_BLUE)
        if self._reset_flagstats_stats:
            for c in self.console.clients.getList():
                self.init_flagstats_stats(c)

    def init_flagstats_stats(self, client) -> None:
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
    def show_time(sec) -> str:
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
            msg_blue = self.team_awards_message(self.blue_team)
            msg_red = self.team_awards_message(self.red_team)
            if not msg_red and not msg_blue:
                message_func(
                    'There is no flag stats recorded yet, '
                    'please wait for a capture to happen.'
                )
            else:
                if msg_blue:
                    message_func(f'^4Blue Awards: ^3{msg_blue}')
                if msg_red:
                    message_func(f'^4Red Awards: ^3{msg_red}')
        else:
            if msg := self.merged_awards_message():
                message_func(f'^3CTF Awards: {msg}')
            else:
                if client:
                    message_func(
                        'There is no flag stats recorded yet, '
                        'please wait for a capture to happen.'
                    )

    def merged_awards_message(self) -> str:
        if self.blue_team.max_flag > self.red_team.max_flag:
            plural = 's' if self.blue_team.max_flag > 1 else ''
            msg = (
                f'Most Flags: {self.blue_team.max_flag_client.name} [^4Blue^3] '
                f'(^5{self.blue_team.max_flag}^3 flag{plural}) - '
            )
        elif self.blue_team.max_flag < self.red_team.max_flag:
            plural = 's' if self.red_team.max_flag > 1 else ''
            msg = (
                f'Most Flags: {self.red_team.max_flag_client.name} [^1Red^3] '
                f'(^5{self.red_team.max_flag}^3 flag{plural} - '
            )
        elif (
                self.blue_team.max_flag == self.red_team.max_flag
                and self.blue_team.max_flag_client is not None
        ):
            msg = (
                f'Most Flags: {self.blue_team.max_flag_client.name} [^4Blue^3] '
                f'and {self.red_team.max_flag_client.name} [^1Red^3] '
                f'(^5{self.red_team.max_flag}^3 flags) - '
            )
        else:  # both are None
            msg = ''

        best_client, best_score = self.best_defensive_scorer()
        if best_score > 0:
            if best_client.team == b3.TEAM_BLUE:
                team_name = '^4Blue'
            elif best_client.team == b3.TEAM_RED:
                team_name = '^1Red'
            else:
                team_name = '^1Free'
            msg += (
                f'Best Defender: {best_client.name} [{team_name}^3] '
                f'(def ^5{best_score}^3) - '
            )

        # FASTEST CAPTURE
        # If blue team's fastest cap time is smaller than red team's, we take
        # blue's score.
        # Another case: blue team captured, red did not, so red time is -1 by
        # default, but in this case blue team's fastest cap time is taken.
        b_time = self.blue_team.min_time
        r_time = self.red_team.min_time
        if b_time != -1 and (r_time == -1 or r_time > b_time):
            msg += (
                f'Fastest Cap: {self.blue_team.min_time_client.name} '
                f'[^4Blue^3] (^5{self.show_time(b_time)}^3)'
            )
        elif r_time != -1 and (b_time == -1 or b_time > r_time):
            msg += (
                f'Fastest Cap: {self.red_team.min_time_client.name} [^1Red^3] '
                f'(^5{self.show_time(r_time)}^3)'
            )
        elif b_time != -1 and r_time == b_time:
            msg += (
                f'Fastest Cap: {self.blue_team.min_time_client.name} '
                f'[^4Blue^3] and {self.red_team.min_time_client.name} '
                f'[^1Red^3] (^5{self.show_time(b_time)}^3)'
            )

        return msg

    def team_awards_message(self, team: TeamData) -> str:
        if team.max_flag_client is not None:
            plural = 's' if team.max_flag > 1 else ''
            msg = (
                f'Most Flags: {team.max_flag_client.name} '
                f'(^5{team.max_flag}^3 flag{plural}) - '
            )
        else:
            msg = ''

        best_client, best_score = self.best_defensive_scorer(team)
        if best_score > 0:
            msg += (
                f'Best Defender: {best_client.name} '
                f'[^4{team.name}^3] (def ^5{best_score}^3) - '
            )

        if team.min_time_client is not None:
            msg += (
                f'Fastest Cap: {team.min_time_client.name} '
                f'(^5{self.show_time(team.min_time)}^3)'
            )

        return msg

    def best_defensive_scorer(
            self,
            team: TeamData = None,
    ) -> tuple[Optional[Client], int]:
        clients = [
            (c, self.defensive_score(c))
            for c in self.console.clients.getList()
            if team is None or team.team == c.team
        ]
        return functools.reduce(
            lambda a, b: b if b[1] > a[1] else a,
            clients,
            (None, -1),
        )

    def defensive_score(self, client: Client) -> int:
        if not client:
            return -1
        return (
                client.var(self, 'flagcarrierkill', 0).value +
                client.var(self, 'flagreturned', 0).value
        )
