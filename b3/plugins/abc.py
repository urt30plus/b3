import abc
import contextlib
import operator
import threading

import b3
import b3.functions
import b3.plugin
import b3.plugins.hof


class WeaponKillPlugin(abc.ABC, b3.plugin.Plugin):
    def __init__(self, console, config=None):
        super().__init__(console, config)
        self._active = True
        self._stfu = False  # if True, no bigtexts
        self._total_kills = 0
        self._top_n = 3
        self._msg_levels = set()
        self._killers = {}
        self._challenges = {}
        self._max_challenges = 5
        self._challenge_duration = 120

    @property
    @abc.abstractmethod
    def cmd_msg_prefix(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def weapon_name(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def weapon_action(self) -> str:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def weapons_handled(self) -> tuple[int, ...]:
        raise NotImplementedError

    def handle_kill(self, client, target, data=None):
        self._total_kills += 1
        if self._total_kills == 1:
            self.console.write(
                f'bigtext "^3{client.exactName} ^7: first {self.weapon_name} kill"'
            )

        if client.cid not in self._killers:
            num_cuts = 1
            self._killers[client.cid] = client
        else:
            num_cuts = client.var(self, "kills", 0).value + 1

        client.setvar(self, "kills", num_cuts)

        if not self._stfu and num_cuts in self._msg_levels:
            msg = self.getMessage(
                f"{self.cmd_msg_prefix}kills_{num_cuts}",
                {"name": client.exactName, "score": num_cuts},
            )
            self.console.write(f'bigtext "{msg}"')

        if self._challenges and target is not None:
            challenge_thread = self._challenges.pop(target.cid, None)
            if challenge_thread:
                self.cancel_challenge_thread(challenge_thread)
                self.console.write(
                    f'bigtext "^7Good job ^3{client.exactName}^7, '
                    f'you {self.weapon_action}d ^3{target.exactName} ^7!"'
                )

    def onLoadConfig(self):
        self._top_n = self.getSetting(
            "settings",
            "top_n",
            b3.INTEGER,
            self._top_n,
        )

        self._active = self.getSetting(
            "settings",
            "enabled",
            b3.BOOLEAN,
            self._active,
        )

        self._challenge_duration = self.getSetting(
            "settings",
            "challengeduration",
            b3.INTEGER,
            self._challenge_duration,
        )

        for m in self.config.options("messages"):
            sp = m.split("_", maxsplit=1)
            if len(sp) == 2:
                with contextlib.suppress(Exception):
                    self._msg_levels.add(int(sp[1]))

        self.create_missing_command_methods()
        self.register_commands_from_config()

    def create_missing_command_methods(self):
        wanted_methods = {
            f"cmd_{self.cmd_msg_prefix}{x[4:]}": getattr(self, x)
            for x in dir(WeaponKillPlugin)
            if x.startswith("cmd_")
        }
        for name, method in wanted_methods.items():
            if not hasattr(self, name):
                setattr(self, name, method)

    def onStartup(self):
        self.registerEvent("EVT_GAME_ROUND_START", self.on_round_start)
        self.registerEvent("EVT_CLIENT_KILL", self.on_client_kill)
        self.registerEvent("EVT_GAME_EXIT", self.on_round_end)

    def on_round_start(self, event):
        self.cancel_challenges()
        for c in self.console.clients.getList():
            c.setvar(self, "kills", 0)

    def on_client_kill(self, event):
        if event.data[1] in self.weapons_handled:
            self.handle_kill(event.client, event.target, event.data)

    def on_round_end(self, event):
        self.display_scores()
        b3.functions.start_daemon_thread(
            target=self.update_hall_of_fame,
            args=(self._killers, self.console.game.mapName),
            name=self.plugin_name,
        )
        self.reset_scores()
        self.cancel_challenges()

    def cmd_enable(self, data, client, cmd=None):
        """\
        Enable the plugin
        """
        cmd.sayLoudOrPM(client, f"^7{self.plugin_name.title()} Plugin : enabled")
        self._active = True

    def cmd_disable(self, data, client, cmd=None):
        """\
        Disable plugin commands, but still counts kills
        """
        cmd.sayLoudOrPM(client, f"^7{self.plugin_name.title()} Plugin : disabled")
        self._active = False

    def cmd_stfu(self, data, client, cmd=None):
        """\
        Enable/disable silent mode (no more bigtexts)
        """
        self._stfu = not self._stfu
        msg = "on" if self._stfu else "off"
        cmd.sayLoudOrPM(
            client, f"^7{self.weapon_name.title()} plugin : silent mode {msg}"
        )

    def cmd_stats(self, data, client, cmd=None):
        """\
        <player> Display kills stats for a given client (or yourself)
        """
        if not self._active:
            cmd.sayLoudOrPM(client, f"^7{self.weapon_name.title()} stats are disabled")
            return
        msg = None
        if not data:
            if client.cid in self._killers:
                kills = client.var(self, "kills", 0).value
                msg = f"{client.exactName} : ^2{kills} ^7{self.weapon_name} kills"
            else:
                msg = f"^7No {self.weapon_name} kill yet... try again"
        else:
            if m := self.parseUserCmd(data):
                if sclient := self.findClientPrompt(m[0], client):
                    kills = sclient.var(self, "kills", 0).value
                    msg = f"{sclient.exactName} : ^2{kills} ^7{self.weapon_name} kills"
                else:
                    msg = "No player found"
        if msg:
            cmd.sayLoudOrPM(client, msg)

    def cmd_topstats(self, data, client, cmd=None):
        """\
        List the top killers for the current map
        """
        if not self._active:
            client.message(f"^7{self.weapon_name.title()} stats are disabled")
            return
        if not self._killers:
            client.message(f"^7No top {self.weapon_name} stats for the moment")
        else:
            self.display_scores()

    def cmd_challenge(self, data, client, cmd=None):
        """\
        <player> Challenge someone. The first player to kill wins the challenge.
        """
        if not self._active or self._stfu:
            cmd.sayLoudOrPM(
                client, f"^7{self.weapon_name.title()} challenges are disabled"
            )
            return

        if not (m := self.parseUserCmd(data)):
            client.message(f"^7Invalid data, try !help {self.cmd_msg_prefix}challenge")
            return

        if not (sclient := self.findClientPrompt(m[0], client)):
            return

        if self._challenges.get(sclient.cid):
            client.message(
                f"There is already a challenge underway for {sclient.exactName}"
            )
            return

        if len(self._challenges) >= self._max_challenges:
            client.message(
                "There are already several challenges underway, try again later"
            )
            return

        self.console.write(
            f'bigtext "^7New challenge : try to {self.weapon_action} '
            f'^3{sclient.exactName}"'
        )
        challenge_thread = threading.Timer(
            self._challenge_duration,
            self.challenge_end,
            args=(sclient.cid, sclient.exactName),
        )
        challenge_thread.start()
        self._challenges[sclient.cid] = challenge_thread

    def cmd_record(self, data, client, cmd=None):
        """\
        Displays the best user for the current map
        """
        try:
            record = b3.plugins.hof.record_holder(
                self.console,
                self.plugin_name,
            )
        except LookupError:
            message = "^7No record found on this map"
        else:
            message = (
                f"^7{self.weapon_name.title()} kills record on this map: "
                f"^1{record.client.exactName} ^2{record.score} ^7kills"
            )

        client.message(message)

    def display_scores(self):
        if top_kills := self._top_killers(self._killers, "kills", limit=self._top_n):
            results = [
                f"^1#{i}. ^4{score[1].name} ^1(^3{score[0]}^1)^7"
                for i, score in enumerate(top_kills)
            ]
            self.console.say(
                f"^1Top {len(top_kills)} {self.weapon_name} killers "
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
        with contextlib.suppress(Exception):
            challenge_thread.cancel()

    def challenge_end(self, target_id=None, target_name=None):
        self.console.write(
            f'bigtext "^3{target_name} ^7has won the {self.weapon_name} challenge!"'
        )
        with contextlib.suppress(KeyError):
            del self._challenges[target_id]

    def update_hall_of_fame(self, killers, map_name):
        if top_kills := self._top_killers(killers, "kills", limit=1):
            best_score, best_player = top_kills[0]
        else:
            return

        record = b3.plugins.hof.update_hall_of_fame(
            self.console,
            self.plugin_name,
            map_name,
            best_player,
            best_score,
        )

        if record.is_new:
            message = (
                f"^2{record.score} ^{self.weapon_name} kills: congratulations "
                f"^3{record.client.exactName}^7, new record on this map!!"
            )
        else:
            message = (
                f"^7{self.weapon_name.title()} kills record on this map: "
                f"^1{record.client.exactName} ^2{record.score} ^7kills"
            )

        self.console.say(message)

    def _top_killers(self, killers, cvar_name, limit=5):
        scores = [(c.var(self, cvar_name, 0).value, c) for c in killers.values()]
        scores.sort(key=operator.itemgetter(0), reverse=True)
        return [x for x in scores[:limit] if x[0] > 0]
