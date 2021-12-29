import b3
import b3.events
import b3.plugin
import re

from b3.functions import clamp

__author__ = 'ThorN, Courgette'
__version__ = '1.4.4'


class SpamcontrolPlugin(b3.plugin.Plugin):

    def __init__(self, console, config=None):
        super().__init__(console, config)
        self._adminPlugin = console.getPlugin('admin')
        self._maxSpamins = 10
        self._modLevel = 20
        self._falloffRate = 6.5

    def onLoadConfig(self):
        """
        Load plugin configuration
        """
        self._maxSpamins = self.getSetting('settings', 'max_spamins', b3.INTEGER, self._maxSpamins,
                                           lambda x: clamp(x, minv=0))
        self._modLevel = self.getSetting('settings', 'mod_level', b3.LEVEL, self._modLevel)
        self._falloffRate = self.getSetting('settings', 'falloff_rate', b3.FLOAT, self._falloffRate)

    def onStartup(self):
        """
        Initialize the plugin.
        """
        # register the events needed
        self.registerEvent('EVT_CLIENT_SAY', self.onChat)
        self.registerEvent('EVT_CLIENT_TEAM_SAY', self.onChat)
        self.registerEvent('EVT_CLIENT_PRIVATE_SAY', self.onChat)
        self.registerEvent('EVT_CLIENT_RADIO', self.onRadio)

        self.register_commands_from_config()

    def getTime(self):
        """
        Just to ease automated tests.
        """
        return self.console.time()

    def add_spam_points(self, client, points, text):
        """
        Add spam points to the given client.
        """
        now = self.getTime()
        if client.var(self, 'ignore_till', now).value > now:
            # ignore the user
            raise b3.events.VetoEvent

        last_message_time = client.var(self, 'last_message_time', now).value
        gap = now - last_message_time

        if gap < 2:
            points += 1

        spamins = client.var(self, 'spamins', 0).value + points

        # apply natural points decrease due to time
        spamins -= int(gap / self._falloffRate)

        if spamins < 1:
            spamins = 0

        # set new values
        client.setvar(self, 'spamins', spamins)
        client.setvar(self, 'last_message_time', now)
        client.setvar(self, 'last_message', text)

        # should we warn ?
        if spamins >= self._maxSpamins:
            client.setvar(self, 'ignore_till', now + 2)
            self._adminPlugin.warnClient(client, 'spam')
            spamins = int(spamins / 1.5)
            client.setvar(self, 'spamins', spamins)
            raise b3.events.VetoEvent

    def onChat(self, event):
        """
        Handle EVT_CLIENT_SAY and EVT_CLIENT_TEAM_SAY and EVT_CLIENT_PRIVATE_SAY
        """
        if not event.client or event.client.maxLevel >= self._modLevel:
            return

        points = 0
        client = event.client
        text = event.data
        last_message = client.var(self, 'last_message').value
        color = re.match(r'\^[0-9]', event.data)
        if color and text == last_message:
            points += 5
        elif text == last_message:
            points += 3
        elif color:
            points += 2
        elif text.startswith('QUICKMESSAGE_'):
            points += 2
        else:
            points += 1

        if text[:1] == '!':
            points += 1

        self.add_spam_points(client, points, text)

    def onRadio(self, event):
        new_event = b3.events.Event(
            type=event.type,
            client=event.client,
            target=event.target,
            data=repr(event.data)
        )
        self.onChat(new_event)

    def cmd_spamins(self, data, client, cmd=None):
        """
        [<name>] - display a spamins level
        """
        if data:
            sclient = self._adminPlugin.findClientPrompt(data, client)
            if not sclient:
                return
        else:
            sclient = client

        if sclient.maxLevel >= self._modLevel:
            cmd.sayLoudOrPM(client, '%s ^7is too cool to spam' % sclient.exactName)
        else:
            now = self.getTime()
            last_message_time = sclient.var(self, 'last_message_time', now).value
            gap = now - last_message_time

            msmin = smin = sclient.var(self, 'spamins', 0).value
            smin -= int(gap / self._falloffRate)

            if smin < 1:
                smin = 0

            cmd.sayLoudOrPM(client, '%s ^7currently has %s spamins, peak was %s' % (sclient.exactName, smin, msmin))
