import operator
import threading

import b3.functions
import b3.plugin
import b3.plugins.hof

__author__ = 'SvaRoX'
__version__ = '0.3'


class KniferPlugin(b3.plugin.Plugin):

    def __init__(self, console, config=None):
        super().__init__(console, config)
        self._admin_plugin = None
        self._active = True
        self._stfu = False  # if True, no bigtexts
        self._total_kills = 0
        self._top_n = 3
        self._msg_levels = set()
        self._killers = {}
        self._challenges = {}
        self._max_challenges = 5
        self._challenge_duration = 300
        self._hof_plugin_name = 'knifer'
        self._weapons = (
            console.UT_MOD_KNIFE,
            console.UT_MOD_KNIFE_THROWN,
        )

    def onLoadConfig(self):
        self._admin_plugin = self.console.getPlugin('admin')
        if not self._admin_plugin:
            self.error('Could not find admin plugin')
            return False

        self._top_n = self.getSetting(
            'settings',
            'top_n',
            b3.INTEGER,
            self._top_n,
        )

        self._active = self.getSetting(
            'settings',
            'enabled',
            b3.BOOLEAN,
            self._active,
        )

        self._challenge_duration = self.getSetting(
            'settings',
            'challengeduration',
            b3.INTEGER,
            self._challenge_duration,
        )

        for m in self.config.options('messages'):
            sp = m.split('_', maxsplit=1)
            if len(sp) == 2:
                try:
                    self._msg_levels.add(int(sp[1]))
                except Exception:
                    pass

        self.register_commands_from_config()

    def onStartup(self):
        self.registerEvent('EVT_GAME_ROUND_START', self.on_round_start)
        self.registerEvent('EVT_CLIENT_KILL', self.on_client_kill)
        self.registerEvent('EVT_GAME_EXIT', self.on_round_end)

    def on_round_start(self, event):
        self.cancel_challenges()
        for c in self.console.clients.getList():
            c.setvar(self, 'knifeKills', 0)

    def on_client_kill(self, event):
        if event.data[1] in self._weapons:
            self.handle_kill(event.client, event.target, event.data)

    def handle_kill(self, client, target, data=None):
        self._total_kills += 1
        if self._total_kills == 1:
            self.console.write(
                f'bigtext "^3{client.exactName} ^7: first knife kill"'
            )

        if client.cid not in self._killers:
            num_cuts = 1
            self._killers[client.cid] = client
        else:
            num_cuts = client.var(self, 'knifeKills', 0).value + 1

        client.setvar(self, 'knifeKills', num_cuts)

        if not self._stfu and num_cuts in self._msg_levels:
            msg = self.getMessage(f'knkills_{num_cuts}',
                                  {'name': client.exactName, 'score': num_cuts})
            self.console.write(f'bigtext "{msg}"')

        if self._challenges and target is not None:
            challenge_thread = self._challenges.pop(target.cid, None)
            if challenge_thread:
                self.cancel_challenge_thread(challenge_thread)
                self.console.write(
                    f'bigtext "^7Good job ^3{client.exactName}^7, '
                    f'you sliced ^3{target.exactName} ^7!"'
                )

    def on_round_end(self, event):
        self.display_scores()
        b3.functions.start_daemon_thread(
            target=self.update_hall_of_fame,
            args=(self._killers, self.console.game.mapName),
            name='knifer-hof',
        )
        self.reset_scores()
        self.cancel_challenges()

    def cmd_knenable(self, data, client, cmd=None):
        """\
        Enable the plugin
        """
        cmd.sayLoudOrPM(client, '^7Plugin : enabled')
        self._active = True

    def cmd_kndisable(self, data, client, cmd=None):
        """\
        Disable plugin commands, but still counts knife kills
        """
        cmd.sayLoudOrPM(client, '^7Plugin : disabled')
        self._active = False

    def cmd_knstfu(self, data, client, cmd=None):
        """\
        Enable/disable silent mode (no more bigtexts)
        """
        self._stfu = False if self._stfu else True
        msg = 'on' if self._stfu else 'off'
        cmd.sayLoudOrPM(client, f'^7Knife plugin : silent mode {msg}')

    def cmd_knstats(self, data, client, cmd=None):
        """\
        <player> Display knife kills stats for a given client (or yourself)
        """
        if not self._active:
            cmd.sayLoudOrPM(client, '^7Knife stats are disabled')
            return
        msg = None
        if not data:
            if client.cid in self._killers:
                kills = client.var(self, 'knifeKills', 0).value
                msg = f'{client.exactName} : ^2{kills} ^7knife kills'
            else:
                msg = '^7No knife kill yet... try again'
        else:
            if m := self._admin_plugin.parseUserCmd(data):
                if sclient := self._admin_plugin.findClientPrompt(m[0], client):
                    kills = sclient.var(self, 'knifeKills', 0).value
                    msg = f'{sclient.exactName} : ^2{kills} ^7knife kills'
                else:
                    msg = 'No player found'
        if msg:
            cmd.sayLoudOrPM(client, msg)

    def cmd_kntopstats(self, data, client, cmd=None):
        """\
        List the top slicers for the current map
        """
        if not self._active:
            client.message('^7Knife stats are disabled')
            return
        if not self._killers:
            client.message('^7No top knife stats for the moment')
        else:
            self.display_scores()

    def cmd_knchallenge(self, data, client, cmd=None):
        """\
        <player> Challenge someone. The first player to slice them wins the challenge.
        """
        if not self._active or self._stfu:
            cmd.sayLoudOrPM(client, '^7Knife stats are disabled')
            return

        if not (m := self._admin_plugin.parseUserCmd(data)):
            client.message('^7Invalid data, try !help knchallenge')
            return

        if not (sclient := self._admin_plugin.findClientPrompt(m[0], client)):
            return

        if self._challenges.get(sclient.cid):
            client.message(
                f'There is already a challenge underway for {sclient.exactName}'
            )
            return

        if len(self._challenges) >= self._max_challenges:
            client.message(
                'There are already several challenges underway, '
                'try again later'
            )
            return

        self.console.write(
            f'bigtext "^7New challenge : try to slice ^3{sclient.exactName}"'
        )
        challenge_thread = threading.Timer(
            self._challenge_duration,
            self.challenge_end,
            args=(sclient.cid, sclient.exactName),
        )
        challenge_thread.start()
        self._challenges[sclient.cid] = challenge_thread

    def cmd_knrecord(self, data, client, cmd=None):
        """\
        Displays the best knife user for the current map
        """
        try:
            record = b3.plugins.hof.record_holder(
                self.console,
                self._hof_plugin_name,
            )
        except LookupError:
            message = '^7No record found on this map'
        else:
            message = (
                f'^7Knife kills record on this map: '
                f'^1{record.client.exactName} ^2{record.score} ^7kills'
            )

        client.message(message)

    def display_scores(self):
        if top_kills := self._top_killers(self._killers,'knifeKills', limit=self._top_n):
            results = [
                f'^1#{i}. ^4{score[1].name} ^1(^3{score[0]}^1)^7'
                for i, score in enumerate(top_kills)
            ]
            self.console.say(
                f'^1Top {len(top_kills)} knife killers '
                f'(total {self._total_kills})  : {" ,".join(results)}'
            )

    def reset_scores(self):
        self._total_kills = 0
        self._killers = {}

    def cancel_challenges(self):
        while True:
            try:
                _, challenge_thread = self._challenges.popitem()
                self.cancel_challenge_thread(challenge_thread)
            except KeyError:
                break

    def cancel_challenge_thread(self, challenge_thread):
        try:
            challenge_thread.cancel()
        except Exception:
            pass

    def challenge_end(self, target_id=None, target_name=None):
        self.console.write(
            f'bigtext "^3{target_name} ^7has won the knife challenge!"'
        )
        try:
            del self._challenges[target_id]
        except KeyError:
            pass

    def update_hall_of_fame(self, killers, map_name):
        if top_kills := self._top_killers(killers, 'knifeKills', limit=1):
            best_score, best_player = top_kills[0]
        else:
            return

        record = b3.plugins.hof.update_hall_of_fame(
            self.console,
            self._hof_plugin_name,
            map_name,
            best_player,
            best_score,
        )

        if record.is_new:
            message = (
                f'^2{record.score} ^7knife kills: congratulations '
                f'^3{record.client.exactName}^7, new record on this map!!'
            )
        else:
            message = (
                f'^7Knife kills record on this map: '
                f'^1{record.client.exactName} ^2{record.score} ^7kills'
            )

        self.console.say(message)

    def _top_killers(self, killers, cvar_name, limit=5):
        scores = [
            (c.var(self, cvar_name, 0).value, c)
            for c in killers.values()
        ]
        scores.sort(key=operator.itemgetter(0), reverse=True)
        return [x for x in scores[:limit] if x[0] > 0]
