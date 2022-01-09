import b3
import b3.events
import b3.plugin

__author__ = 'Walker, ThorN'
__version__ = '1.2.3'


class SpreeStats:

    def __init__(self) -> None:
        self.kills = 0
        self.deaths = 0
        self.end_losing_spree_message = None
        self.end_killing_spree_message = None

    def register_kill(self) -> int:
        self.deaths = 0
        self.kills += 1
        return self.kills

    def register_death(self) -> int:
        self.kills = 0
        self.deaths += 1
        return self.deaths


class SpreePlugin(b3.plugin.Plugin):

    VAR_NAME = 'spree_info'

    def __init__(self, console, config=None) -> None:
        super().__init__(console, config)
        self._killing_messages = {}
        self._losing_messages = {}
        self._reset_spree_stats = False

    def onLoadConfig(self) -> None:
        self._reset_spree_stats = self.getSetting(
            'settings',
            'reset_spree',
            b3.BOOL,
            self._reset_spree_stats,
        )
        self.load_messages(self._killing_messages, 'killing_spree_messages')
        self.load_messages(self._losing_messages, 'losing_spree_messages')

    def load_messages(self, mapping: dict, msg_type: str) -> None:
        for count, message in self.config.items(msg_type):
            start_msg, msg_sep, stop_msg = message.partition('#')
            if msg_sep:
                mapping[int(count)] = (start_msg.strip(), stop_msg.strip())
            else:
                self.warning("ignoring %s %r due to missing '#'",
                             msg_type, message)

    def onStartup(self) -> None:
        self.register_commands_from_config()
        self.registerEvent('EVT_CLIENT_KILL', self.on_client_kill)
        if self._reset_spree_stats:
            self.registerEvent('EVT_GAME_EXIT', self.on_game_exit)

    def on_client_kill(self, event):
        killer = event.client
        victim = event.target

        if killer:
            spree_stats = self.get_spree_stats(killer)
            kills = spree_stats.register_kill()
            if spree_stats.end_losing_spree_message:
                self.show_message(
                    killer,
                    victim,
                    spree_stats.end_losing_spree_message,
                )
                spree_stats.end_losing_spree_message = None

            if message := self.get_spree_message(kills, 0):
                # Save the message to use when the spree ends
                spree_stats.end_killing_spree_message = message[1]
                self.show_message(killer, victim, message[0])

        if victim:
            spree_stats = self.get_spree_stats(victim)
            kills = spree_stats.kills
            deaths = spree_stats.register_death()
            if spree_stats.end_killing_spree_message:
                self.show_message(
                    killer,
                    victim,
                    spree_stats.end_killing_spree_message,
                    kills,
                )
                spree_stats.end_killing_spree_message = None

            if message := self.get_spree_message(0, deaths):
                # Save the message to use when the spree ends
                spree_stats.end_losing_spree_message = message[1]
                self.show_message(victim, killer, message[0])

    def on_game_exit(self, event):
        for c in self.console.clients.getList():
            self.init_spree_stats(c)

    def init_spree_stats(self, client):
        client.setvar(self, self.VAR_NAME, SpreeStats())

    def get_spree_stats(self, client) -> SpreeStats:
        if spree_stats := client.var(self, self.VAR_NAME).value:
            return spree_stats
        return client.setvar(self, self.VAR_NAME, SpreeStats()).value

    def get_spree_message(self, kills: int, deaths: int) -> str:
        """
        Get the appropriate spree message.
        Return a list in the format (start spree message, end spree message)
        """
        if kills != 0:
            message = self._killing_messages.get(kills)
        elif deaths != 0:
            message = self._losing_messages.get(deaths)
        else:
            message = None
        return message

    def show_message(
            self,
            client,
            victim=None,
            message: str = None,
            spree_kills: int = 0,
    ) -> None:
        """
        Replace variables and display the message
        """
        if message and not client.hide:
            message = message.replace('%player%', client.name)
            if victim:
                message = message.replace('%victim%', victim.name)
                if spree_kills:
                    message = message.replace('%spree%', str(spree_kills))
            self.console.say(message)

    def cmd_spree(self, data, client, cmd=None):
        """
        <player> - show a players' winning/losing spree
        """
        if not data:
            sclient = client
            targm = '^7You have'
            targmns = '^7You are'
        else:
            if sclient := self.findClientPrompt(data, client):
                targm = f'{sclient.name} has'
                targmns = f'{sclient.name} is'
            else:
                return

        spree_stats = self.get_spree_stats(sclient)
        if spree_stats.kills > 0:
            cmd.sayLoudOrPM(client,
                            f'{targm} ^2{spree_stats.kills}^7 kills in a row')
        elif spree_stats.deaths > 0:
            cmd.sayLoudOrPM(client,
                            f'{targm} ^1{spree_stats.deaths}^7 deaths in a row')
        else:
            cmd.sayLoudOrPM(client, f'{targmns} not having a spree right now')
