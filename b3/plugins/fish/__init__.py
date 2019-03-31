# ################################################################### #
#                                                                     #
#  This program is free software; you can redistribute it and/or      #
#  modify it under the terms of the GNU General Public License        #
#  as published by the Free Software Foundation; either version 2     #
#  of the License, or (at your option) any later version.             #
#                                                                     #
#  This program is distributed in the hope that it will be useful,    #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of     #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the       #
#  GNU General Public License for more details.                       #
#                                                                     #
#  You should have received a copy of the GNU General Public License  #
#  along with this program; if not, write to the Free Software        #
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA      #
#  02110-1301, USA.                                                   #
#                                                                     #
# ################################################################### #

__author__ = '|30+|moneyshot'
__version__ = '1.0.0'

import b3.plugin


class FishPlugin(b3.plugin.Plugin):
    _adminPlugin = None
    _target_name = None
    _is_warmup = False

    def onLoadConfig(self):
        self.register_commands_from_config()

    def onStartup(self):
        self._adminPlugin = self.console.getPlugin('admin')
        self.registerEvent('EVT_GAME_WARMUP', self.on_round_warmup)
        self.registerEvent('EVT_GAME_ROUND_START', self.on_round_start)
        self.registerEvent('EVT_CLIENT_SPAWN', self.on_client_spawn)

    def on_round_warmup(self, event):
        self._is_warmup = self._target_name is not None

    def on_round_start(self, event):
        self._is_warmup = False

    def on_client_spawn(self, event):
        if self._target_name and self._is_warmup and event.client.name == self._target_name:
            self.console.write(f'smite {event.client.cid}')
            event.client.message(self.getMessage('fish_nap', {'name': event.client.exactName}))
            self._is_warmup = False

    def cmd_fish(self, data, client, cmd=None):
        """
        <blank> - display current player being fished
        off - disable fishing
        on <player> - fish for this player
        """
        input = self._adminPlugin.parseUserCmd(data)
        if input is None:
            cmd.sayLoudOrPM(client, f'fishing for {self._target_name}')
            return
        if input[0] == 'off':
            if self._target_name is not None:
                client.message(f'no more fishing for {self._target_name}')
                self._target_name = None
            return
        if input[0] != 'on' or len(input) != 2:
            client.message('invalid command, type !help fish')
            return
        sclient = self._adminPlugin.findClientPrompt(input[1], client)
        if not sclient:
            return
        self._target_name = sclient.name
        client.message(f'now fishing for {self._target_name}')
        sclient.message(f'Watch out, {client.exactName} is fishing for you')
