import re
import threading
import time

import b3.plugin
from b3.config import NoOptionError

__version__ = '1.4'
__author__ = 'ThorN, xlr8or, Courgette'

F_FIRST = 4
F_NEWB = 1
F_USER = 16
F_ANNOUNCE_FIRST = 8
F_ANNOUNCE_USER = 2
F_CUSTOM_GREETING = 32


class WelcomePlugin(b3.plugin.Plugin):

    def __init__(self, console, config=None):
        super().__init__(console, config)
        self._adminPlugin = None
        self._newbConnections = 15
        self._welcomeFlags = F_FIRST | F_NEWB | F_USER | F_ANNOUNCE_FIRST | F_ANNOUNCE_USER | F_CUSTOM_GREETING
        self._welcomeDelay = 30
        self._min_gap = 3600
        self._default_messages = {
            'first': '^7Welcome $name^7, this must be your first visit, you are player ^3#$id. Type !help for help',
            'newb': '^7[^2Authed^7] Welcome back $name ^7[^3@$id^7], last visit ^3$lastVisit. '
                    'Type !register in chat to register. Type !help for help',
            'user': '^7[^2Authed^7] Welcome back $name ^7[^3@$id^7], last visit ^3$lastVisit^7, '
                    'you\'re a ^2$group^7, played $connections times',
            'announce_first': '^7Everyone welcome $name^7, player number ^3#$id^7, to the server',
            'announce_user': '^7Everyone welcome back $name^7, player number ^3#$id^7, to the server, '
                             'played $connections times',
            'greeting': '^7$name^7 joined: $greeting',
            'greeting_empty': '^7You have no greeting set',
            'greeting_yours': '^7Your greeting is %s',
            'greeting_bad': '^7Greeting is not formatted properly: %s',
            'greeting_changed': '^7Greeting changed to: %s',
            'greeting_cleared': '^7Greeting cleared',
        }

    def onStartup(self):
        self._adminPlugin = self.console.getPlugin('admin')
        self.register_commands_from_config()
        self.registerEvent('EVT_CLIENT_AUTH', self.onAuth)

    def onLoadConfig(self):
        self._load_config_flags()

        self._newbConnections = self.getSetting(
            'settings',
            'newb_connections',
            b3.INTEGER,
            15,
        )

        self._welcomeDelay = self.getSetting(
            'settings',
            'delay',
            b3.INTEGER,
            30,
            lambda x: x if 15 <= x <= 90 else 30,
        )

        self._min_gap = self.getSetting(
            'settings',
            'min_gap',
            b3.INTEGER,
            3600,
            lambda x: x if x >= 0 else 0,
        )

    def _load_config_flags(self):
        flag_options = [
            ('welcome_first', F_FIRST),
            ('welcome_newb', F_NEWB),
            ('welcome_user', F_USER),
            ('announce_first', F_ANNOUNCE_FIRST),
            ('announce_user', F_ANNOUNCE_USER),
            ('show_user_greeting', F_CUSTOM_GREETING),
        ]

        config_options = list(zip(*flag_options))[0]

        def set_flag(flag):
            self._welcomeFlags |= flag

        def unset_flag(flag):
            self._welcomeFlags &= ~flag

        if not any([self.config.has_option('settings', o) for o in config_options]):
            if self.config.has_option('settings', 'flags'):
                # old style config
                try:
                    self._welcomeFlags = self.config.getint('settings', 'flags')
                except (NoOptionError, ValueError) as e:
                    self.error('could not load settings/flags config value: %s', e)
            else:
                self.warning(
                    "could not find any of '%s' in config: "
                    "all welcome messages will be shown",
                    "', '".join(config_options)
                )
        else:
            for opt, F in flag_options:
                if self.config.has_option('settings', opt):
                    try:
                        _ = self.config.getboolean('settings', opt)
                        set_flag(F) if _ else unset_flag(F)
                    except (NoOptionError, ValueError) as e:
                        self.error('could not load settings/%s config value: %s', opt, e)
                else:
                    set_flag(F)
                    self.warning('could not find settings/%s config value', opt)

    def onAuth(self, event):
        if self._welcomeFlags <= 0 or \
                not event.client or \
                event.client.id is None or \
                event.client.cid is None or \
                not event.client.connected or \
                event.client.pbid == 'WORLD':
            return
        if self.console.upTime() < 300:
            return
        t = threading.Timer(self._welcomeDelay, self.welcome, (event.client,))
        t.start()

    def welcome(self, client):
        if client.lastVisit:
            _timeDiff = time.time() - client.lastVisit
        else:
            _timeDiff = 1000000  # big enough so it will welcome new players

        # don't need to welcome people who got kicked or where already 
        # welcomed in before _min_gap s ago
        if client.connected and _timeDiff > self._min_gap:
            info = self.get_client_info(client)
            if client.connections >= 2:
                if client.maskedLevel > 0:
                    if self._welcomeFlags & F_USER:
                        client.message(self.getMessage('user', info))
                elif self._welcomeFlags & F_NEWB:
                    client.message(self.getMessage('newb', info))

                if self._welcomeFlags & F_ANNOUNCE_USER and client.connections < self._newbConnections:
                    self.console.say(self.getMessage('announce_user', info))
            else:
                if self._welcomeFlags & F_FIRST:
                    client.message(self.getMessage('first', info))
                if self._welcomeFlags & F_ANNOUNCE_FIRST:
                    self.console.say(self.getMessage('announce_first', info))

            if self._welcomeFlags & F_CUSTOM_GREETING and client.greeting:
                _info = {'greeting': client.greeting % info}
                _info.update(info)
                self.console.say(self.getMessage('greeting', _info))

    def get_client_info(self, client):
        info = {
            'name': client.exactName,
            'id': str(client.id),
            'connections': str(client.connections)
        }

        if client.maskedGroup:
            info['group'] = client.maskedGroup.name
            info['level'] = str(client.maskedGroup.level)
        else:
            info['group'] = 'None'
            info['level'] = '0'

        if client.connections >= 2 and client.lastVisit:
            info['lastVisit'] = self.console.formatTime(client.lastVisit)
        else:
            info['lastVisit'] = 'Unknown'

        return info

    def cmd_greeting(self, data, client, cmd=None):
        """
        [<greeting>] - set or list your greeting (use 'none' to remove)
        """
        if data.lower() == 'none':
            client.greeting = ''
            client.save()
            client.message(self.getMessage('greeting_cleared'))
        elif data:
            prepared_data = re.sub(r'\$(name|maxLevel|group|connections)', r'%(\1)s', data)
            if len(prepared_data) > 255:
                client.message('^7Your greeting is too long')
            else:
                try:
                    client.message('Greeting Test: %s' % (str(prepared_data) % {
                        'name': client.exactName,
                        'maxLevel': client.maxLevel,
                        'group': getattr(client.maxGroup, 'name', None),
                        'connections': client.connections
                    }))
                except ValueError as msg:
                    client.message(self.getMessage('greeting_bad', msg))
                    return False
                else:
                    client.greeting = prepared_data
                    client.save()
                    client.message(self.getMessage('greeting_changed', data))
                    return True
        else:
            if client.greeting:
                client.message(self.getMessage('greeting_yours', client.greeting))
            else:
                client.message(self.getMessage('greeting_empty'))
