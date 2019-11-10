import b3
import b3.events
import b3.plugin

__author__ = 'Walker, ThorN'
__version__ = '1.2.3'


class SpreeStats:

    def __init__(self):
        self.kills = 0
        self.deaths = 0
        self.end_loosing_spree_message = None
        self.end_kill_spree_message = None


class SpreePlugin(b3.plugin.Plugin):

    def __init__(self, console, config=None):
        super().__init__(console, config)
        self._admin_plugin = None
        self._killingspree_messages_dict = {}
        self._loosingspree_messages_dict = {}
        self._reset_spree_stats = False
        self._clientvar_name = 'spree_info'

    def onLoadConfig(self):
        self._reset_spree_stats = self.getSetting('settings', 'reset_spree', b3.BOOL, self._reset_spree_stats)
        self.init_spreemessage_list()

    def init_spreemessage_list(self):
        # get the spree messages from the config
        # split the start and end spree messages and save it in the dictionary
        for kills, message in self.config.items('killingspree_messages'):
            if '#' in message:
                start_message, stop_message = message.split('#')
                self._killingspree_messages_dict[int(kills)] = [start_message.strip(), stop_message.strip()]
            else:
                self.warning("ignoring killingspree message %r due to missing '#'", message)
        for deaths, message in self.config.items('loosingspree_messages'):
            if '#' in message:
                start_message, stop_message = message.split('#')
                self._loosingspree_messages_dict[int(deaths)] = [start_message.strip(), stop_message.strip()]
            else:
                self.warning("ignoring killingspree message %r due to missing '#'", message)

    def onStartup(self):
        self._admin_plugin = self.console.getPlugin("admin")
        self.register_commands_from_config()
        self.registerEvent('EVT_CLIENT_KILL', self.on_client_kill)
        self.registerEvent('EVT_GAME_EXIT', self.on_game_exit)

    def on_client_kill(self, event):
        self.handle_kills(event.client, event.target)

    def handle_kills(self, client=None, victim=None):
        """
        A kill was made. Add 1 to the client and set his deaths to 0.
        Add 1 death to the victim and set his kills to 0.
        """
        # client (attacker)
        if client:
            # we grab our SpreeStats object here
            # any changes to its values will be saved "automagically"
            spreeStats = self.get_spree_stats(client)
            spreeStats.kills += 1

            # Check if the client was on a loosing spree. If so then show his end loosing spree msg.
            if spreeStats.end_loosing_spree_message:
                self.show_message(client, victim, spreeStats.end_loosing_spree_message)
                # reset any possible loosing spree to None
                spreeStats.end_loosing_spree_message = None
            # Check if the client is on a killing spree. If so then show it.
            message = self.get_spree_message(spreeStats.kills, 0)
            if message:
                # Save the 'end'spree message in the client. That is used when the spree ends.
                spreeStats.end_kill_spree_message = message[1]

                # Show the 'start'spree message
                self.show_message(client, victim, message[0])

            # deaths spree is over, reset deaths
            spreeStats.deaths = 0

        # victim
        if victim:
            spreeStats = self.get_spree_stats(victim)
            spreeStats.deaths += 1

            # check if the victim had a killing spree and show a end_killing_spree message
            if spreeStats.end_kill_spree_message:
                self.show_message(client, victim, spreeStats.end_kill_spree_message)
                # reset any possible end spree to None
                spreeStats.end_kill_spree_message = None

            # check if the victim is on a 'loosing'spree
            message = self.get_spree_message(0, spreeStats.deaths)
            if message:
                # Save the 'loosing'spree message in the client.
                spreeStats.end_loosing_spree_message = message[1]

                self.show_message(victim, client, message[0])

            # kill spree is over, reset kills
            spreeStats.kills = 0

    def get_spree_stats(self, client):
        # get the clients stats
        # pass the plugin reference first
        # the key second
        # the defualt value first
        if not client.isvar(self, self._clientvar_name):
            # initialize the default spree object
            # we don't just use the client.var(...,default) here so we
            # don't create a new SpreeStats object for no reason every call
            client.setvar(self, self._clientvar_name, SpreeStats())
        return client.var(self, self._clientvar_name).value
    
    def get_spree_message(self, kills, deaths):
        """
        Get the appropriate spree message.
        Return a list in the format (start spree message, end spree message)
        """
        # default is None, there is no message
        message = None
        # killing spree check
        if kills != 0:
            # if there is an entry for this number of kills, grab it, otherwise
            # return None
            message = self._killingspree_messages_dict.get(kills, None)
        # loosing spree check
        elif deaths != 0:
            message = self._loosingspree_messages_dict.get(deaths, None)
        return message

    def show_message(self, client, victim=None, message=None):
        """
        Replace variables and display the message
        """
        if message and not client.hide:
            message = message.replace('%player%', client.name)
            if victim:
                message = message.replace('%victim%', victim.name)
            self.console.say(message)

    def on_game_exit(self, event):
        if self._reset_spree_stats:
            for c in self.console.clients.getList():
                self.init_spree_stats(c)

    def init_spree_stats(self, client):
        # initialize the clients spree stats
        client.setvar(self, self._clientvar_name, SpreeStats())

    def cmd_spree(self, data, client, cmd=None):
        """
        <player> - show a players' winning/loosing spree
        """        
        targm = '^7You have'
        targmns = '^7You are'
        if not data:
            sclient = client
        else:
            sclient = self._admin_plugin.findClientPrompt(data, client)
            if not sclient:
                return
            targm = f'{sclient.name} has'
            targmns = f'{sclient.name} is'

        spreeStats = self.get_spree_stats(sclient)

        if spreeStats.kills > 0:
            cmd.sayLoudOrPM(client, f'{targm} ^2{spreeStats.kills}^7 kills in a row')
        elif spreeStats.deaths > 0:
            cmd.sayLoudOrPM(client, f'{targm} ^1{spreeStats.deaths}^7 deaths in a row')
        else:
            cmd.sayLoudOrPM(client, f'{targmns} not having a spree right now')
