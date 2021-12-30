import b3
from b3.plugin import Plugin

__author__ = "|30+|moneyshot"
__version__ = "1.1.0"


class FishPlugin(Plugin):

    _fish_commands = ("smite", "nuke", "slap")
    _team_map = {"blue": b3.TEAM_BLUE, "red": b3.TEAM_RED}

    def __init__(self, console, config=None):
        super().__init__(console, config)
        self._fish_cmd = self._fish_commands[0]
        self._target_name = None
        self._target_team = None
        self._is_warmup = False
        self._target_team_fished = []

    def onLoadConfig(self):
        self.register_commands_from_config()

    def onStartup(self):
        self.registerEvent("EVT_GAME_WARMUP", self.on_round_warmup)
        self.registerEvent("EVT_GAME_ROUND_START", self.on_round_start)
        self.registerEvent("EVT_CLIENT_SPAWN", self.on_client_spawn)

    def on_round_warmup(self, event):
        self._is_warmup = any((self._target_name, self._target_team))
        self.debug("on_round_warmup: %s", self._is_warmup)

    def on_round_start(self, event):
        self.debug("on_round_start: is_warmup=%s", self._is_warmup)
        if self._is_warmup:
            self._is_warmup = False
            self._target_name = None
            self._target_team = None
            self._fish_cmd = self._fish_commands[0]
        self._target_team_fished.clear()

    def on_client_spawn(self, event):
        if not self._is_warmup:
            return

        if self._target_name and event.client.name == self._target_name:
            self.console.write(f"{self._fish_cmd} {event.client.cid}")
            self._target_name = None
            event.client.message(
                self.getMessage("fish_nap", {"name": event.client.exactName})
            )

        if self._target_team and event.client.team == self._target_team and \
                event.client.cid not in self._target_team_fished:
            self.console.write(f"{self._fish_cmd} {event.client.cid}")
            self._target_team_fished.append(event.client.cid)
            event.client.message(
                self.getMessage("fish_nap", {"name": event.client.exactName})
            )

    def cmd_fish(self, data, client, cmd=None):
        """
        <blank> - display current player being fished
        off - disable fishing
        <command: smite (default), nuke, slap> <player> - fish for this player
        """
        if not (input := self.parseUserCmd(data)):
            cmd.sayLoudOrPM(client, f"fishing for {self._target_name} with {self._fish_cmd}")
            return
        if input[0] == "off":
            if self._target_name is not None:
                client.message(f"no more fishing for {self._target_name} with {self._fish_cmd}")
                self._target_name = None
            return
        fish_command = input[0]
        if fish_command == "on":
            fish_command = self._fish_commands[0]
        if fish_command not in self._fish_commands or len(input) != 2:
            client.message("invalid command, type !help fish")
            return
        if sclient := self.findClientPrompt(input[1], client):
            self._fish_cmd = fish_command
            self._target_name = sclient.name
            client.message(f"now fishing for {self._target_name} with {self._fish_cmd}")
            sclient.message(f"Watch out, {client.exactName} is fishing for you")

    def cmd_fishteam(self, data, client, cmd=None):
        """
        <blank> - display current team being fished
        off - disable fishing
        <command: smite (default), nuke, slap> <team: blue|red> - fish for this team
        """
        if not (input := self.parseUserCmd(data)):
            if self._target_team:
                cmd.sayLoudOrPM(client, f"fishing for {self.__team_name()} team with {self._fish_cmd}")
            else:
                cmd.sayLoudOrPM(client, f"no team is being fished")
            return
        if input[0] == "off":
            if self._target_team is not None:
                client.message(f"no more fishing for {self.__team_name()} team with {self._fish_cmd}")
                self._target_team = None
            else:
                client.message(f"ignored, no team was being fished")
            return
        fish_command = input[0]
        if fish_command == "on":
            fish_command = self._fish_commands[0]
        if fish_command not in self._fish_commands or len(input) != 2:
            client.message("invalid command, type !help fishteam")
            return
        self._target_team = self._team_map.get(input[1])
        if not self._target_team:
            client.message(f"Unknown team [{input[1]}], valid values are 'blue' or 'red'")
            return
        self._fish_cmd = fish_command
        client.message(f"now fishing for {input[1]} team with {self._fish_cmd}")

    def __team_name(self):
        if not (team_key := self._target_team):
            return None
        for k, v in self._team_map.items():
            if v == team_key:
                return k
