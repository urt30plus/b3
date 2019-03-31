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

import b3
from b3.plugin import Plugin


class FishPlugin(Plugin):

    _team_map = {"blue": b3.TEAM_BLUE, "red": b3.TEAM_RED}

    def __init__(self, console, config=None):
        super().__init__(console, config)
        self._adminPlugin = self.console.getPlugin('admin')
        self._target_name = None
        self._target_team = None
        self._is_warmup = False
        self._target_team_fished = []

    def onLoadConfig(self):
        self.register_commands_from_config()

    def onStartup(self):
        self.registerEvent('EVT_GAME_WARMUP', self.on_round_warmup)
        self.registerEvent('EVT_GAME_ROUND_START', self.on_round_start)
        self.registerEvent('EVT_CLIENT_SPAWN', self.on_client_spawn)

    def on_round_warmup(self, event):
        self._is_warmup = any((self._target_name, self._target_team))
        self.debug("on_round_warmup: %s", self._is_warmup)

    def on_round_start(self, event):
        self.debug("on_round_start: is_warmup=%s", self._is_warmup)
        if self._is_warmup:
            self._is_warmup = False
            self._target_name = None
            self._target_team = None
        self._target_team_fished.clear()

    def on_client_spawn(self, event):
        if not self._is_warmup:
            return

        if self._target_name and event.client.name == self._target_name:
            self.console.write(f'smite {event.client.cid}')
            self._target_name = None
            event.client.message(
                self.getMessage('fish_nap', {'name': event.client.exactName})
            )

        if self._target_team and event.client.team == self._target_team and \
                event.client.cid not in self._target_team_fished:
            self.console.write(f'smite {event.client.cid}')
            self._target_team_fished.append(event.client.cid)
            event.client.message(
                self.getMessage('fish_nap', {'name': event.client.exactName})
            )

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

    def cmd_fishteam(self, data, client, cmd=None):
        """
        <blank> - display current team being fished
        off - disable fishing
        on <blue|red> - fish for this team
        """
        input = self._adminPlugin.parseUserCmd(data)
        if input is None:
            if self._target_team:
                cmd.sayLoudOrPM(client, f'fishing for {self.__team_name()} team')
            else:
                cmd.sayLoudOrPM(client, f'no team is being fished')
            return
        if input[0] == 'off':
            if self._target_team is not None:
                client.message(f'no more fishing for {self.__team_name()} team')
                self._target_team = None
            else:
                client.message(f'ignored, no team was being fished')
            return
        if input[0] != 'on' or len(input) != 2:
            client.message('invalid command, type !help fishteam')
            return
        self._target_team = self._team_map.get(input[1])
        if not self._target_team:
            client.message(f"Unknown team [{input[1]}], valid values are 'blue' or 'red'")
            return
        client.message(f'now fishing for {input[1]} team')

    def __team_name(self):
        team_key = self._target_team
        if not team_key:
            return None
        for k, v in self._team_map.items():
            if v == team_key:
                return k
