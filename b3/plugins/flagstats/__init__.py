import functools
import time
from typing import Optional

import b3
import b3.config
import b3.events
import b3.functions
import b3.plugin
import b3.plugins.hof
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
        self.registerEvent('EVT_GAME_EXIT', self.on_game_exit)

        self.register_commands_from_config()

    def isEnabled(self):
        return self.console.game.game_type == 'ctf' and super().isEnabled()

    def on_round_start(self, event):
        self.game_reinit(event)

    def on_game_exit(self, event):
        b3.functions.start_daemon_thread(
            target=self.update_hall_of_fame,
            args=(self.blue_team, self.red_team, self.console.game.mapName),
            name='flagstats-hof',
        )
        if self._show_awards:
            self.flag_awards_show()

    def update_hall_of_fame(
            self,
            blue_team: TeamData,
            red_team: TeamData,
            map_name: str
    ) -> None:
        self.update_hall_of_fame_caps(blue_team, red_team, map_name)
        self.update_hall_of_fame_time(blue_team, red_team, map_name)

    def update_hall_of_fame_caps(
            self,
            blue_team: TeamData,
            red_team: TeamData,
            map_name: str
    ) -> None:
        best_team_caps, _ = self.best_team_flag_caps(blue_team, red_team)
        if best_team_caps:
            record = b3.plugins.hof.update_hall_of_fame(
                self.console,
                'flagstats_caps',
                map_name,
                best_team_caps.max_flag_client,
                best_team_caps.max_flag,
            )
            if record.is_new:
                message = (
                    f'^2{record.score} ^7flag caps: congratulations '
                    f'^3{record.client.exactName}^7, new record on this map!!'
                )
            else:
                message = (
                    f'^7Flag record on this map: ^1{record.client.exactName} '
                    f'^2{record.score} ^caps'
                )
            self.console.say(message)

    def update_hall_of_fame_time(
            self,
            blue_team: TeamData,
            red_team: TeamData,
            map_name: str
    ) -> None:
        best_team_time, _ = self.best_team_flag_time(blue_team, red_team)
        if best_team_time:
            # Store as a negative number since the update function only
            # updates records where the new score is greater than the stored
            # score. And since score is stored as an INT we convert from
            # a FLOAT (fractional seconds to milliseconds).
            score = int(best_team_time.min_time * -1000)
            record = b3.plugins.hof.update_hall_of_fame(
                self.console,
                'flagstats_time',
                map_name,
                best_team_time.min_time_client,
                score,
            )
            # Convert back into fractional seconds, see comment above
            score = self.show_time(abs(record.score / 1000))
            if record.is_new:
                message = (
                    f'^2{score} ^7flag cap time: congratulations '
                    f'^3{record.client.exactName}^7, new record on this map!!'
                )
            else:
                message = (
                    f'^7Flag record on this map: ^1{record.client.exactName} '
                    f'^2{score} ^cap time'
                )
            self.console.say(message)

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
                    # new personal record, but only show as best time if it
                    # is not the first recorded best time
                    show_best_time = curr_best.value != -1
                    curr_best.value = time_capture
                    self.show_message_to_client(client,
                                                time_capture,
                                                best_time=show_best_time)
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
        cap_time = self.show_time(time_capture)
        self.console.write(
            f'{client.name}^3 captured the flag in ^5{cap_time}^3'
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
            if args := self.parseUserCmd(data):
                if not (sclient := self.findClientPrompt(args[0], client)):
                    return
            else:
                client.message('^7Invalid data, try !help flag')
                return

        msg = self.format_client_stats(sclient)
        client.message(msg)

    def cmd_flagrecord(self, data, client, cmd=None):
        """\
        Displays the best flag caps/time for the current map
        """
        try:
            caps_record = b3.plugins.hof.record_holder(self.console,
                                                       'flagstats_caps')
            time_record = b3.plugins.hof.record_holder(self.console,
                                                       'flagstats_time')
        except LookupError:
            messages = ['^7No record found on this map']
        else:
            # see comment in self.update_hall_of_fame_time
            record_time = self.show_time(abs(time_record.score / 1000))
            messages = [
                f'^7Flag record most caps: '
                f'^1{caps_record.client.exactName} ^2{caps_record.score}',
                f'^7Flag record fastest cap: '
                f'^1{time_record.client.exactName} ^2{record_time}',
            ]
        for message in messages:
            client.message(message)

    def format_client_stats(self, client: Client) -> str:
        flags = client.var(self, 'flagtaken', 0).value
        returns = client.var(self, 'flagreturned', 0).value
        caps = client.var(self, 'flagcaptured', 0).value
        defends = (
                client.var(self, 'flagreturned', 0).value +
                client.var(self, 'flagcarrierkill', 0).value
        )
        msg = (
            f'^7{client.name} took ^5{flags} ^7flags, returned ^5{returns}^7, '
            f'captured ^5{caps}^7, def ^5{defends}^7'
        )
        if caps > 0:
            if best_time := client.var(self, 'flagbesttime', -1).value > 0:
                best_time = self.show_time(best_time)
                msg += f', best capture time ^5{best_time} ^7'
        return msg

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
        if sec < 60:
            result = '%0.2f s' % sec
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

    @staticmethod
    def best_team_flag_caps(
            team1: TeamData,
            team2: TeamData,
    ) -> tuple[Optional[TeamData], ...]:
        if team1.max_flag > team2.max_flag:
            return team1, None
        elif team2.max_flag > team1.max_flag:
            return team2, None
        elif team1.max_flag == team2.max_flag and team1.max_flag > 0:
            return team1, team2
        else:
            return None, None

    @staticmethod
    def best_team_flag_time(
            team1: TeamData,
            team2: TeamData,
    ) -> tuple[Optional[TeamData], ...]:
        t1_time = team1.min_time
        t2_time = team2.min_time
        if t1_time != -1 and (t2_time == -1 or t2_time > t1_time):
            return team1, None
        elif t2_time != -1 and (t1_time == -1 or t1_time > t2_time):
            return team2, None
        elif t1_time != -1 and t1_time == t2_time:
            return team1, team2
        else:
            return None, None

    def merged_awards_message(self) -> str:
        team1, team2 = self.best_team_flag_caps(self.blue_team, self.red_team)
        if team1 and team2:
            msg = (
                f'Most Flags: {team1.max_flag_client.name} [^4{team1.name}^3] '
                f'and {team2.max_flag_client.name} [^1{team2.name}^3] '
                f'(^5{team1.max_flag}^3 flags) - '
            )
        elif team1:
            plural = 's' if team1.max_flag > 1 else ''
            color = '^4' if team1.team == b3.TEAM_BLUE else '^1'
            msg = (
                f'Most Flags: {team1.max_flag_client.name} '
                f'[{color}{team1.name}^3] '
                f'(^5{team1.max_flag}^3 flag{plural}) - '
            )
        else:
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

        team1, team2 = self.best_team_flag_time(self.blue_team, self.red_team)
        if team1 and team2:
            msg += (
                f'Fastest Cap: {team1.min_time_client.name} '
                f'[^4Blue^3] and {team2.min_time_client.name} '
                f'[^1Red^3] (^5{self.show_time(team1.min_time)}^3)'
            )
        elif team1:
            msg += (
                f'Fastest Cap: {team1.min_time_client.name} '
                f'[^4Blue^3] (^5{self.show_time(team1.min_time)}^3)'
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
