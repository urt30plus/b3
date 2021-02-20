import itertools
import os
import time

import b3
import b3.cron
import b3.plugin

__author__ = 'ThorN'
__version__ = '1.6.1'



class AdvPlugin(b3.plugin.Plugin):

    def __init__(self, console, config=None):
        super().__init__(console, config)
        self._admin_plugin = self.console.getPlugin('admin')
        self._xlrstats_plugin = self.console.getPlugin('xlrstats')
        self._crontab = None
        self._file_name = None
        self._rate = '2'
        self._ad_list = None
        self._msg_cycle = None

    def onLoadConfig(self):
        self._rate = self.getSetting("settings", "rate", default=self._rate)

        if self.config.has_option('settings', 'ads'):
            self._file_name = self.getSetting("settings", "ads", b3.PATH)
            self.load_from_file(self._file_name)
        else:
            self._file_name = None
            self.load_from_config()

        if self._crontab:
            self.console.cron - self._crontab

        m, _ = self._get_rate_minsec(self._rate)
        self._crontab = b3.cron.PluginCronTab(self, self.adv, minute=m)
        self.console.cron + self._crontab

    def onStartup(self):
        if not self._xlrstats_plugin:
            self.debug('XLRstats not installed: @topstats not available!')
        self.register_commands_from_config()

    def _update_ad_list(self, ad_list=None):
        if ad_list is None:
            ad_list = []
        self._ad_list = ad_list
        self._msg_cycle = itertools.cycle(ad_list)

    @property
    def ad_list(self):
        if not self._ad_list:
            return []
        return self._ad_list[:]

    def save(self):
        if self._file_name:
            with open(self._file_name, 'w') as f:
                for msg in self._ad_list:
                    if msg:
                        f.write(msg + "\n")
        else:
            raise Exception('save to XML config not supported')

    def load_from_file(self, filename):
        if not os.path.isfile(filename):
            self.error('advertisement file %s does not exist', filename)
            return

        with open(filename, 'r') as f:
            self.load(f.readlines())

    def load_from_config(self):
        self.load([e.text for e in self.config.get('ads/ad')])

    def load(self, items=None):
        if not items:
            self._update_ad_list()
            return

        ad_list = []
        for w in items:
            w = w.strip()
            if len(w) > 1:
                if w[:6] == '/spam#':
                    w = self._admin_plugin.getSpam(w[6:])
                ad_list.append(w)
        self._update_ad_list(ad_list)

    def adv(self, first_try=True):
        """
        Display an advertisement message.
        :param first_try: Whether or not it's the first time we try to display this ad
        """
        if self.console.clients:
            if ad := next(self._msg_cycle):
                self.print_ad(ad, first_try)

    def print_ad(self, ad, first_try=True):
        if ad == "@nextmap":
            if nextmap := self.console.getNextMap():
                ad = "^2Next map: ^3" + nextmap
            else:
                self.debug('could not get nextmap')
                ad = None
        elif ad == "@time":
            ad = "^2Time: ^3" + self.console.formatTime(time.time())
        elif ad == "@topstats":
            if self._xlrstats_plugin:
                self._xlrstats_plugin.cmd_xlrtopstats(data='3', client=None, cmd=None, ext=True)
                if first_try:
                    # try another ad
                    self.adv(first_try=False)
                    return
                else:
                    ad = None
            else:
                self.error('XLRstats not installed! Cannot use @topstats in adv plugin!')
                ad = '@topstats not available: XLRstats is not installed!'
        elif ad == "@admins":
            try:
                command = self._admin_plugin._commands['admins']
                command.executeLoud(data=None, client=None)
                ad = None
            except Exception as err:
                self.error("could not send adv message @admins", exc_info=err)
                if first_try:
                    # try another ad
                    self.adv(first_try=False)
                    return
                else:
                    ad = None
        elif ad == "@regulars":
            try:
                command = self._admin_plugin._commands['regulars']
                command.executeLoud(data=None, client=None)
                ad = None
            except Exception as err:
                self.error("could not send adv message @regulars", exc_info=err)
                if first_try:
                    # try another ad
                    self.adv(first_try=False)
                    return
                else:
                    ad = None

        if ad:
            self.console.say(ad)

    def _get_rate_minsec(self, rate):
        """
        Allow to define the rate in second by adding 's' at the end
        :param rate: The rate string representation
        """
        seconds = 0
        minutes = '*'
        if rate[-1] == 's':
            # rate is in seconds
            s = rate[:-1]
            if int(s) > 59:
                s = 59
            seconds = f'*/{s}'
        else:
            minutes = f'*/{rate}'
        self.debug('%s -> (%s,%s)', rate, minutes, seconds)
        return minutes, seconds

    def cmd_advadd(self, data, client=None, cmd=None):
        """
        <add> - add a new advertisement message
        """
        if not data:
            client.message('Missing data, try !help advadd')
        else:
            new_ad_list = self.ad_list
            new_ad_list.append(data)
            self._update_ad_list(new_ad_list)
            client.message(f'^3Adv: ^7"{data}^7" added')
            if self._file_name:
                self.save()

    def cmd_advsave(self, data, client=None, cmd=None):
        """
        - save the current advertisement list
        """
        try:
            self.save()
            client.message(f'^3Adv: ^7saved {len(self._ad_list)} messages')
        except Exception as e:
            client.message(f'^3Adv: ^7error saving: {e}')

    def cmd_advload(self, data, client=None, cmd=None):
        """
        Reload adv plugin configuration.
        """
        self.onLoadConfig()
        client.message(f'^3Adv: ^7loaded {len(self._ad_list)} messages')

    def cmd_advrate(self, data, client=None, cmd=None):
        """
        [<rate>] - get/set the advertisement rotation rate
        """
        if not data:
            if self._rate[-1] == 's':
                client.message(f'Current rate is every minute')
            else:
                client.message(f'Current rate is every {self._rate} minutes')
        else:
            self._rate = data
            m, s = self._get_rate_minsec(self._rate)
            self._crontab.minute = m
            if self._rate[-1] == 's':
                self._crontab.minute = '*'
                client.message(f'^3Adv: ^7rate set to every minute')
            else:
                client.message(f'^3Adv: ^7rate set to {self._rate} minutes')

    def cmd_advrem(self, data, client=None, cmd=None):
        """
        <index> - removes an advertisement message
        """
        if not data:
            client.message('Missing data, try !help advrem')
            return

        try:
            item_index = int(data) - 1
        except ValueError:
            client.message("Invalid data, use the !advlist command to list valid items numbers")
        else:
            new_ad_list = self.ad_list
            if not 0 <= item_index < len(new_ad_list):
                client.message("Invalid data, use the !advlist command to list valid items numbers")
            else:
                item = new_ad_list.pop(item_index)
                self._update_ad_list(new_ad_list)
                if self._file_name:
                    self.save()
                client.message(f'^3Adv: ^7removed item: {item}')

    def cmd_advlist(self, data, client=None, cmd=None):
        """
        List advertisement messages
        """
        if self._ad_list:
            for i, msg in enumerate(self._ad_list, start=1):
                client.message(f'^3Adv: ^7[^2{i}^7] {msg}')
        else:
            client.message('^3Adv: ^7no ads loaded')
