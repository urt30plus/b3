# -*- coding: utf-8 -*-

# ################################################################### #
#                                                                     #
#  BigBrotherBot(B3) (www.bigbrotherbot.net)                          #
#  Copyright (C) 2005 Michael "ThorN" Thornton                        #
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

__author__ = 'xlr8or, Courgette, Fenix'
__version__ = '4.34'

import re
import time

import b3
import b3.clients
import b3.events
import b3.parser
from b3.clients import Client
from b3.functions import getStuffSoundingLike
from b3.functions import prefixText
from b3.functions import start_daemon_thread
from b3.functions import time2minutes
from b3.parsers.q3a.abstractParser import AbstractParser


class Iourt43Client(Client):

    def auth_by_guid(self):
        """
        Authorize this client using his GUID.
        """
        self.console.debug("Auth by guid: %r", self.guid)
        try:
            return self.console.storage.getClient(self)
        except KeyError as msg:
            self.console.debug('User not found %s: %s', self.guid, msg)
            return False

    def auth_by_pbid(self):
        """
        Authorize this client using his PBID.
        """
        self.console.debug("Auth by FSA: %r", self.pbid)
        clients_matching_pbid = self.console.storage.getClientsMatching(dict(pbid=self.pbid))
        if len(clients_matching_pbid) > 1:
            self.console.warning("Found %s client having FSA '%s'", len(clients_matching_pbid), self.pbid)
            return self.auth_by_pbid_and_guid()
        elif len(clients_matching_pbid) == 1:
            self.id = clients_matching_pbid[0].id
            # we may have a second client entry in database with current guid.
            # we want to update our current client guid only if it is not the case.
            try:
                client_by_guid = self.console.storage.getClient(Iourt43Client(guid=self.guid))
            except KeyError:
                pass
            else:
                if client_by_guid.id != self.id:
                    # so storage.getClient is able to overwrite the value which will make
                    # it remain unchanged in database when .save() will be called later on
                    self._guid = None
            return self.console.storage.getClient(self)
        else:
            self.console.debug('Frozen Sand account [%s] unknown in database', self.pbid)
            return False

    def auth_by_pbid_and_guid(self):
        """
        Authorize this client using both his PBID and GUID.
        """
        self.console.debug("Auth by both guid and FSA: %r, %r", self.guid, self.pbid)
        clients_matching_pbid = self.console.storage.getClientsMatching({'pbid': self.pbid, 'guid': self.guid})
        if len(clients_matching_pbid):
            self.id = clients_matching_pbid[0].id
            return self.console.storage.getClient(self)
        else:
            self.console.debug("Frozen Sand account [%s] with guid '%s' unknown in database", self.pbid, self.guid)
            return False

    def auth(self):
        """
        The b3.clients.Client.auth method needs to be changed to fit the UrT4.2 authentication scheme.
        In UrT4.2 :
           * all connected players have a cl_guid
           * some have a Frozen Sand account (FSA)
        The FSA is a worldwide identifier while the cl_guid only identify a player on a given game server.
        See http://forum.bigbrotherbot.net/urban-terror-4-2/urt-4-2-discussion/
        """
        if not self.authed and self.guid and not self.authorizing:

            self.authorizing = True

            name = self.name
            pbid = self.pbid
            guid = self.guid
            ip = self.ip

            if not pbid and self.cid:
                fsa_info = self.console.queryClientFrozenSandAccount(self.cid)
                self.pbid = pbid = fsa_info.get('login', None)

            self.console.verbose("Auth with %r", {'name': name, 'ip': ip, 'pbid': pbid, 'guid': guid})

            # FSA will be found in pbid
            if not self.pbid:
                # auth with cl_guid only
                try:
                    in_storage = self.auth_by_guid()
                    # fix up corrupted data due to bug #162
                    if in_storage and in_storage.pbid == 'None':
                        in_storage.pbid = None
                except Exception as e:
                    self.console.error("Auth by guid failed", exc_info=e)
                    self.authorizing = False
                    return False
            else:
                # auth with FSA
                try:
                    in_storage = self.auth_by_pbid()
                except Exception as e:
                    self.console.error("Auth by FSA failed", exc_info=e)
                    self.authorizing = False
                    return False

                if not in_storage:
                    # fallback on auth with cl_guid only
                    try:
                        in_storage = self.auth_by_guid()
                    except Exception as e:
                        self.console.error("Auth by guid failed (when no known FSA)", exc_info=e)
                        self.authorizing = False
                        return False

            if in_storage:
                self.lastVisit = self.timeEdit
                self.console.bot("Client found in the storage @%s: welcome back %s [FSA: '%s']", self.id, self.name,
                                 self.pbid)
            else:
                self.console.bot("Client not found in the storage %s [FSA: '%s'], create new", str(self.guid),
                                 self.pbid)

            self.connections = int(self.connections) + 1
            self.name = name
            self.ip = ip
            if pbid:
                self.pbid = pbid
            self.save()
            self.authed = True

            self.console.debug("Client authorized: %s [@%s] [GUID: '%s'] [FSA: '%s']", self.name, self.id, self.guid,
                               self.pbid)

            # check for bans
            if self.numBans > 0:
                ban = self.lastBan
                if ban:
                    self.reBan(ban)
                    self.authorizing = False
                    return False

            self.refreshLevel()
            self.console.queueEvent(self.console.getEvent('EVT_CLIENT_AUTH', data=self, client=self))
            self.authorizing = False
            return self.authed
        else:
            return False

    def __str__(self):
        return "Client43<@%s:%s|%s:\"%s\":%s>" % (self.id, self.guid, self.pbid, self.name, self.cid)


class Iourt43Parser(AbstractParser):
    """This parser is meant to serve as the new base parser for
    all UrT version from 4.3 on.
    """
    gameName = 'iourt43'

    """
    Translate the gametype to a readable format (also for teamkill plugin!)
    """
    game_types = {
        "0": "ffa",
        "1": "lms",
        "2": "dm",
        "3": "tdm",
        "4": "ts",
        "5": "ftl",
        "6": "cah",
        "7": "ctf",
        "8": "bm",
        "9": "jump",
        "10": "freeze",
        "11": "gungame",
    }

    _logSync = 2

    _permban_with_frozensand = False
    _tempban_with_frozensand = False
    _allow_userinfo_overflow = False

    IpsOnly = False
    IpCombi = False

    _maplist = None
    _empty_name_default = 'EmptyNameDefault'

    _commands = {
        'broadcast': '%(message)s',
        'message': 'tell %(cid)s %(message)s',
        'deadsay': 'tell %(cid)s %(message)s',
        'say': 'say %(message)s',
        'saybig': 'bigtext "%(message)s"',
        'set': 'set %(name)s "%(value)s"',
        'kick': 'kick %(cid)s "%(reason)s"',
        'ban': 'addip %(cid)s',
        'tempban': 'kick %(cid)s "%(reason)s"',
        'banByIp': 'addip %(ip)s',
        'unbanByIp': 'removeip %(ip)s',
        'auth-permban': 'auth-ban %(cid)s 0 0 0',
        'auth-tempban': 'auth-ban %(cid)s %(days)s %(hours)s %(minutes)s',
        'slap': 'slap %(cid)s',
        'nuke': 'nuke %(cid)s',
        'mute': 'mute %(cid)s %(seconds)s',
        'kill': 'smite %(cid)s',
    }

    _eventMap = {
        # 'warmup' : b3.events.EVT_GAME_WARMUP,
        # 'shutdowngame' : b3.events.EVT_GAME_ROUND_END
    }

    # remove the time off of the line
    _lineClear = re.compile(r'^(?:[0-9:]+\s?)?')
    _line_length = 90

    _lineFormats = (
        # Radio: 0 - 7 - 2 - "New Alley" - "I'm going for the flag"
        re.compile(r'^(?P<action>Radio): '
                   r'(?P<data>(?P<cid>[0-9]+) - '
                   r'(?P<msg_group>[0-9]+) - '
                   r'(?P<msg_id>[0-9]+) - '
                   r'"(?P<location>.*)" - '
                   r'"(?P<text>.*)")$', re.IGNORECASE),

        # Callvote: 1 - "map dressingroom"
        re.compile(r'^(?P<action>Callvote): (?P<data>(?P<cid>[0-9]+) - "(?P<vote_string>.*)")$', re.IGNORECASE),

        # Vote: 0 - 2
        re.compile(r'^(?P<action>Vote): (?P<data>(?P<cid>[0-9]+) - (?P<value>.*))$', re.IGNORECASE),

        # VotePassed: 1 - 0 - "reload"
        re.compile(r'^(?P<action>VotePassed): (?P<data>(?P<yes>[0-9]+) - (?P<no>[0-9]+) - "(?P<what>.*)")$', re.I),

        # VoteFailed: 1 - 1 - "restart"
        re.compile(r'^(?P<action>VoteFailed): (?P<data>(?P<yes>[0-9]+) - (?P<no>[0-9]+) - "(?P<what>.*)")$', re.I),

        # FlagCaptureTime: 0: 1234567890
        # FlagCaptureTime: 1: 1125480101
        re.compile(r'^(?P<action>FlagCaptureTime):\s(?P<cid>[0-9]+):\s(?P<captime>[0-9]+)$', re.IGNORECASE),

        # 13:34 ClientJumpRunStarted: 0 - way: 1
        # 13:34 ClientJumpRunStarted: 0 - way: 1 - attempt: 1 of 5
        re.compile(r'^(?P<action>ClientJumpRunStarted):\s'
                   r'(?P<cid>\d+)\s-\s'
                   r'(?P<data>way:\s'
                   r'(?P<way_id>\d+)'
                   r'(?:\s-\sattempt:\s'
                   r'(?P<attempt_num>\d+)\sof\s'
                   r'(?P<attempt_max>\d+))?)$', re.IGNORECASE),

        # 13:34 ClientJumpRunStopped: 0 - way: 1 - time: 12345
        # 13:34 ClientJumpRunStopped: 0 - way: 1 - time: 12345 - attempt: 1 of 5
        re.compile(r'^(?P<action>ClientJumpRunStopped):\s'
                   r'(?P<cid>\d+)\s-\s'
                   r'(?P<data>way:\s'
                   r'(?P<way_id>\d+)'
                   r'\s-\stime:\s'
                   r'(?P<way_time>\d+)'
                   r'(?:\s-\sattempt:\s'
                   r'(?P<attempt_num>\d+)\sof\s'
                   r'(?P<attempt_max>\d+'
                   r'))?)$', re.IGNORECASE),

        # 13:34 ClientJumpRunCanceled: 0 - way: 1
        # 13:34 ClientJumpRunCanceled: 0 - way: 1 - attempt: 1 of 5
        re.compile(r'^(?P<action>ClientJumpRunCanceled):\s'
                   r'(?P<cid>\d+)\s-\s'
                   r'(?P<data>way:\s'
                   r'(?P<way_id>\d+)'
                   r'(?:\s-\sattempt:\s'
                   r'(?P<attempt_num>\d+)\sof\s'
                   r'(?P<attempt_max>\d+))?)$', re.IGNORECASE),

        # 13:34 ClientSavePosition: 0 - 335.384887 - 67.469154 - -23.875000
        # 13:34 ClientLoadPosition: 0 - 335.384887 - 67.469154 - -23.875000
        re.compile(r'^(?P<action>Client(Save|Load)Position):\s'
                   r'(?P<cid>\d+)\s-\s'
                   r'(?P<data>'
                   r'(?P<x>-?\d+(?:\.\d+)?)\s-\s'
                   r'(?P<y>-?\d+(?:\.\d+)?)\s-\s'
                   r'(?P<z>-?\d+(?:\.\d+)?))$', re.IGNORECASE),

        # 13:34 ClientGoto: 0 - 1 - 335.384887 - 67.469154 - -23.875000
        re.compile(r'^(?P<action>ClientGoto):\s'
                   r'(?P<cid>\d+)\s-\s'
                   r'(?P<tcid>\d+)\s-\s'
                   r'(?P<data>'
                   r'(?P<x>-?\d+(?:\.\d+)?)\s-\s'
                   r'(?P<y>-?\d+(?:\.\d+)?)\s-\s'
                   r'(?P<z>-?\d+(?:\.\d+)?))$', re.IGNORECASE),

        # ClientSpawn: 0
        # ClientMelted: 1
        re.compile(r'^(?P<action>Client(Melted|Spawn)):\s(?P<cid>[0-9]+)$', re.IGNORECASE),

        # Generated with ioUrbanTerror v4.1:
        # Hit: 12 7 1 19: BSTHanzo[FR] hit ercan in the Helmet
        # Hit: 13 10 0 8: Grover hit jacobdk92 in the Head
        re.compile(r'^(?P<action>Hit):\s'
                   r'(?P<data>'
                   r'(?P<cid>[0-9]+)\s'
                   r'(?P<acid>[0-9]+)\s'
                   r'(?P<hitloc>[0-9]+)\s'
                   r'(?P<aweap>[0-9]+):\s+'
                   r'(?P<text>.*))$', re.IGNORECASE),

        # Assist: 0 14 15: -[TPF]-PtitBigorneau assisted Bot1 to kill Bot2
        re.compile(r'^(?P<action>Assist):\s(?P<acid>[0-9]+)\s(?P<kcid>[0-9]+)\s(?P<dcid>[0-9]+):\s+(?P<text>.*)$',
                   re.IGNORECASE),

        # 6:37 Kill: 0 1 16: XLR8or killed =lvl1=Cheetah by UT_MOD_SPAS
        # 2:56 Kill: 14 4 21: Qst killed Leftovercrack by UT_MOD_PSG1
        # 6:37 Freeze: 0 1 16: Fenix froze Biddle by UT_MOD_SPAS
        re.compile(r'^(?P<action>[a-z]+):\s'
                   r'(?P<data>'
                   r'(?P<acid>[0-9]+)\s'
                   r'(?P<cid>[0-9]+)\s'
                   r'(?P<aweap>[0-9]+):\s+'
                   r'(?P<text>.*))$', re.IGNORECASE),

        # ThawOutStarted: 0 1: Fenix started thawing out Biddle
        # ThawOutFinished: 0 1: Fenix thawed out Biddle
        re.compile(r'^(?P<action>ThawOut(Started|Finished)):\s'
                   r'(?P<data>'
                   r'(?P<cid>[0-9]+)\s'
                   r'(?P<tcid>[0-9]+):\s+'
                   r'(?P<text>.*))$', re.IGNORECASE),

        # Processing chats and tell events...
        # 5:39 saytell: 15 16 repelSteeltje: nno
        # 5:39 saytell: 15 15 repelSteeltje: nno
        re.compile(r'^(?P<action>[a-z]+):\s'
                   r'(?P<data>'
                   r'(?P<cid>[0-9]+)\s'
                   r'(?P<acid>[0-9]+)\s'
                   r'(?P<name>.+?):\s+'
                   r'(?P<text>.*))$', re.IGNORECASE),

        # SGT: fix issue with onSay when something like this come and the match could'nt find the name group
        # say: 7 -crespino-:
        # say: 6 ^5Marcel ^2[^6CZARMY^2]: !help
        re.compile(r'^(?P<action>[a-z]+):\s'
                   r'(?P<data>'
                   r'(?P<cid>[0-9]+)\s'
                   r'(?P<name>[^ ]+):\s*'
                   r'(?P<text>.*))$', re.IGNORECASE),

        # 15:42 Flag Return: RED
        # 15:42 Flag Return: BLUE
        re.compile(r'^(?P<action>Flag Return):\s(?P<data>(?P<color>.+))$', re.IGNORECASE),

        # Bombmode actions:
        # 3:06 Bombholder is 2
        re.compile(r'^(?P<action>Bombholder)(?P<data>\sis\s(?P<cid>[0-9]))$', re.IGNORECASE),

        # was planted, was defused, was tossed, has been collected (doh, how gramatically correct!)
        # 2:13 Bomb was tossed by 2
        # 2:32 Bomb was planted by 2
        # 3:01 Bomb was defused by 3!
        # 2:17 Bomb has been collected by 2
        re.compile(r'^(?P<action>Bomb)\s'
                   r'(?P<data>(was|has been)\s'
                   r'(?P<subaction>[a-z]+)\sby\s'
                   r'(?P<cid>[0-9]+).*)$', re.IGNORECASE),

        # 17:24 Pop!
        re.compile(r'^(?P<action>Pop)!$', re.IGNORECASE),

        # Falling thru? Item stuff and so forth
        re.compile(r'^(?P<action>[a-z]+):\s(?P<data>.*)$', re.IGNORECASE),

        # Shutdowngame and Warmup... the one word lines
        re.compile(r'^(?P<action>[a-z]+):$', re.IGNORECASE)
    )

    # map: ut4_casa
    # num score ping name            lastmsg address               qport rate
    # --- ----- ---- --------------- ------- --------------------- ----- -----
    #   2     0   19 ^1XLR^78^8^9or        0 145.99.135.227:27960  41893  8000  # player with a live ping
    #   4     0 CNCT Dz!k^7              450 83.175.191.27:64459   50308 20000  # connecting player
    #   9     0 ZMBI ^7                 1900 81.178.80.68:27960    10801  8000  # zombies (need to be disconnected!)
    _regPlayer = re.compile(r'^(?P<slot>[0-9]+)\s+'
                            r'(?P<score>[0-9-]+)\s+'
                            r'(?P<ping>[0-9]+|CNCT|ZMBI)\s+'
                            r'(?P<name>.*?)\s+'
                            r'(?P<last>[0-9]+)\s+'
                            r'(?P<ip>[0-9.]+):(?P<port>[0-9-]+)\s+'
                            r'(?P<qport>[0-9]+)\s+'
                            r'(?P<rate>[0-9]+)$', re.IGNORECASE)

    _reColor = re.compile(r'(\^\d)')

    # Map: ut4_algiers
    # Players: 8
    # Scores: R:97 B:98
    # 0:  FREE k:0 d:0 ping:0
    # 4: yene RED k:16 d:8 ping:50 92.104.110.192:63496
    _reTeamScores = re.compile(r'^Scores:\s+'
                               r'R:(?P<RedScore>.+)\s+'
                               r'B:(?P<BlueScore>.+)$', re.IGNORECASE)

    _rePlayerScore = re.compile(r'^(?P<slot>[0-9]+):(?P<name>.*)\s+'
                                r'TEAM:(?P<team>RED|BLUE|SPECTATOR|FREE)\s+'
                                r'KILLS:(?P<kill>[0-9]+)\s+'
                                r'DEATHS:(?P<death>[0-9]+)\s+'
                                r'ASSISTS:(?P<assist>[0-9]+)\s+'
                                r'PING:(?P<ping>[0-9]+|CNCT|ZMBI)\s+'
                                r'AUTH:(?P<auth>.*)\s+IP:(?P<ip>.*)$', re.IGNORECASE)

    # /rcon auth-whois replies patterns
    # 'auth: id: 0 - name: ^7Courgette - login: courgette - notoriety: serious - level: -1  \n'
    _re_authwhois = re.compile(r'^auth: id: (?P<cid>\d+) - '
                               r'name: \^7(?P<name>.+?) - '
                               r'login: (?P<login>.*?) - '
                               r'notoriety: (?P<notoriety>.+?) - '
                               r'level: (?P<level>-?\d+?)(?:\s+- (?P<extra>.*))?\s*$', re.MULTILINE)

    ## kill modes
    MOD_WATER = '1'
    MOD_LAVA = '3'
    MOD_TELEFRAG = '5'
    MOD_FALLING = '6'
    MOD_SUICIDE = '7'
    MOD_TRIGGER_HURT = '9'
    MOD_CHANGE_TEAM = '10'
    UT_MOD_KNIFE = '12'
    UT_MOD_KNIFE_THROWN = '13'
    UT_MOD_BERETTA = '14'
    UT_MOD_DEAGLE = '15'
    UT_MOD_SPAS = '16'
    UT_MOD_UMP45 = '17'
    UT_MOD_MP5K = '18'
    UT_MOD_LR300 = '19'
    UT_MOD_G36 = '20'
    UT_MOD_PSG1 = '21'
    UT_MOD_HK69 = '22'
    UT_MOD_BLED = '23'
    UT_MOD_KICKED = '24'
    UT_MOD_HEGRENADE = '25'
    UT_MOD_SR8 = '28'
    UT_MOD_AK103 = '30'
    UT_MOD_SPLODED = '31'
    UT_MOD_SLAPPED = '32'
    UT_MOD_SMITED = '33'
    UT_MOD_BOMBED = '34'
    UT_MOD_NUKED = '35'
    UT_MOD_NEGEV = '36'
    UT_MOD_HK69_HIT = '37'
    UT_MOD_M4 = '38'
    UT_MOD_GLOCK = '39'
    UT_MOD_COLT1911 = '40'
    UT_MOD_MAC11 = '41'
    UT_MOD_FRF1 = '42'
    UT_MOD_BENELLI = '43'
    UT_MOD_P90 = '44'
    UT_MOD_MAGNUM = '45'
    UT_MOD_TOD50 = '46'
    UT_MOD_FLAG = '47'
    UT_MOD_GOOMBA = '48'

    # HIT LOCATIONS
    HL_HEAD = '1'
    HL_HELMET = '2'
    HL_TORSO = '3'
    HL_VEST = '4'
    HL_ARM_L = '5'
    HL_ARM_R = '6'
    HL_GROIN = '7'
    HL_BUTT = '8'
    HL_LEG_UPPER_L = '9'
    HL_LEG_UPPER_R = '10'
    HL_LEG_LOWER_L = '11'
    HL_LEG_LOWER_R = '12'
    HL_FOOT_L = '13'
    HL_FOOT_R = '14'

    # WORLD CID (used for Mr. Sentry detection)
    WORLD = '1022'

    ## weapons id on Hit: lines are different than the one
    ## on the Kill: lines. Here the translation table
    hitweapon2killweapon = {
        1: UT_MOD_KNIFE,
        2: UT_MOD_BERETTA,
        3: UT_MOD_DEAGLE,
        4: UT_MOD_SPAS,
        5: UT_MOD_MP5K,
        6: UT_MOD_UMP45,
        8: UT_MOD_LR300,
        9: UT_MOD_G36,
        10: UT_MOD_PSG1,
        14: UT_MOD_SR8,
        15: UT_MOD_AK103,
        17: UT_MOD_NEGEV,
        19: UT_MOD_M4,
        20: UT_MOD_GLOCK,
        21: UT_MOD_COLT1911,
        22: UT_MOD_MAC11,
        23: UT_MOD_FRF1,
        24: UT_MOD_BENELLI,
        25: UT_MOD_P90,
        26: UT_MOD_MAGNUM,
        29: UT_MOD_KICKED,
        30: UT_MOD_KNIFE_THROWN,
    }

    ## damage table
    ## Fenix: Hit locations start with index 1 (HL_HEAD).
    ##        Since lists are 0 indexed we'll need to adjust the hit location
    ##        code to match the index number. Instead of adding random values
    ##        in the damage table, the adjustment will be made in _getDamagePoints.
    damage = {
        MOD_TELEFRAG: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        UT_MOD_KNIFE: [100, 60, 44, 35, 20, 20, 40, 37, 20, 20, 18, 18, 15, 15],
        UT_MOD_KNIFE_THROWN: [100, 60, 44, 35, 20, 20, 40, 37, 20, 20, 18, 18, 15, 15],
        UT_MOD_BERETTA: [100, 40, 33, 22, 13, 13, 22, 22, 15, 15, 13, 13, 11, 11],
        UT_MOD_DEAGLE: [100, 66, 57, 38, 22, 22, 42, 38, 28, 28, 22, 22, 18, 18],
        UT_MOD_SPAS: [100, 80, 80, 40, 32, 32, 59, 59, 40, 40, 40, 40, 40, 40],
        UT_MOD_UMP45: [100, 51, 44, 29, 17, 17, 31, 28, 20, 20, 17, 17, 14, 14],
        UT_MOD_MP5K: [50, 34, 30, 22, 13, 13, 22, 20, 15, 15, 13, 13, 11, 11],
        UT_MOD_LR300: [100, 51, 44, 29, 17, 17, 31, 28, 20, 20, 17, 17, 14, 14],
        UT_MOD_G36: [100, 51, 44, 29, 17, 17, 29, 28, 20, 20, 17, 17, 14, 14],
        UT_MOD_PSG1: [100, 100, 97, 70, 36, 36, 75, 70, 41, 41, 36, 36, 29, 29],
        UT_MOD_HK69: [50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50],
        UT_MOD_BLED: [15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15, 15],
        UT_MOD_KICKED: [30, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20],
        UT_MOD_HEGRENADE: [50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50, 50],
        UT_MOD_SR8: [100, 100, 100, 100, 50, 50, 100, 100, 60, 60, 50, 50, 40, 40],
        UT_MOD_AK103: [100, 58, 51, 34, 19, 19, 39, 35, 22, 22, 19, 19, 15, 15],
        UT_MOD_NEGEV: [50, 34, 30, 22, 11, 11, 23, 21, 13, 13, 11, 11, 9, 9],
        UT_MOD_HK69_HIT: [20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20, 20],
        UT_MOD_M4: [100, 51, 44, 29, 17, 17, 31, 28, 20, 20, 17, 17, 14, 14],
        UT_MOD_GLOCK: [100, 45, 29, 35, 15, 15, 29, 27, 20, 20, 15, 15, 11, 11],
        UT_MOD_COLT1911: [100, 60, 40, 30, 15, 15, 32, 29, 22, 22, 15, 15, 11, 11],
        UT_MOD_MAC11: [50, 29, 20, 16, 13, 13, 16, 15, 15, 15, 13, 13, 11, 11],
        UT_MOD_GOOMBA: [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100],
        UT_MOD_TOD50: [100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100, 100],
        UT_MOD_FRF1: [100, 100, 96, 76, 40, 40, 76, 74, 50, 50, 40, 40, 30, 30],
        UT_MOD_BENELLI: [100, 100, 90, 67, 32, 32, 60, 50, 35, 35, 30, 30, 20, 20],
        UT_MOD_P90: [50, 40, 33, 27, 16, 16, 27, 25, 17, 17, 15, 15, 12, 12],
        UT_MOD_MAGNUM: [100, 82, 66, 50, 33, 33, 57, 52, 40, 33, 25, 25],
    }

    # {"A": "0", "B": "1", "C": "2"...., "Y": "24", "Z": "25"}
    letters2slots = {chr(i): str(i - ord("A"))
                     for i in range(ord("A"), ord("Z") + 1)}

    def __new__(cls, *args, **kwargs):
        Iourt43Parser.patch_Clients()
        return AbstractParser.__new__(cls)

    def startup(self):
        try:
            cvar = self.getCvar('gamename')
            gamename = cvar.getString() if cvar else None
            if not self.is_valid_game(gamename):
                self.critical(
                    "The %s B3 parser cannot be used with a game server other than [%s]" % (self.gameName, gamename))
        except Exception as e:
            self.warning("Could not query server for gamename.", exc_info=e)

        if not self.config.has_option('server', 'game_log'):
            self.critical("Your main config file is missing the 'game_log' setting in section 'server'")

        self.__setup_events()
        self.__setup_world_client()
        self.__setup_maps()
        self.__setup_log_sync()
        self.__setup_gamepaths()
        self.load_conf_frozensand_ban_settings()
        self.load_conf_userinfo_overflow()

    def is_valid_game(self, gamename):
        return gamename == 'q3urt43'

    def pluginsStarted(self):
        self.__setup_connected_players()

    def load_conf_frozensand_ban_settings(self):
        """
        Load ban settings according to auth system cvars.
        """
        try:
            frozensand_auth_available = self.is_frozensand_auth_available()
        except Exception as e:
            self.warning("Could not query server for cvar auth", exc_info=e)
            frozensand_auth_available = False
        self.info("Frozen Sand auth system enabled : %s" % ('yes' if frozensand_auth_available else 'no'))

        try:
            cvar = self.getCvar('auth_owners')
            if cvar:
                frozensand_auth_owners = cvar.getString()
            else:
                frozensand_auth_owners = None
        except Exception as e:
            self.warning("Could not query server for cvar auth_owners", exc_info=e)
            frozensand_auth_owners = ""

        yn = ('yes - %s' % frozensand_auth_available) if frozensand_auth_owners else 'no'
        self.info("Frozen Sand auth_owners set : %s" % yn)

        if frozensand_auth_available and frozensand_auth_owners:
            self.load_conf_permban_with_frozensand()
            self.load_conf_tempban_with_frozensand()
            if self._permban_with_frozensand or self._tempban_with_frozensand:
                self.info("NOTE: when banning with the Frozen Sand auth system, B3 cannot remove "
                          "the bans on the urbanterror.info website. To unban a player you will "
                          "have to first unban him on B3 and then also unban him on the official Frozen Sand "
                          "website : http://www.urbanterror.info/groups/list/all/?search=%s" % frozensand_auth_owners)
        else:
            self.info("Ignoring settings about banning with Frozen Sand auth system as the "
                      "auth system is not enabled or auth_owners not set")

    def load_conf_permban_with_frozensand(self):
        """
        Load permban configuration from b3.xml.
        """
        self._permban_with_frozensand = False
        if self.config.has_option('server', 'permban_with_frozensand'):
            try:
                self._permban_with_frozensand = self.config.getboolean('server', 'permban_with_frozensand')
            except ValueError as err:
                self.warning(err)

        self.info("Send permbans to Frozen Sand : %s" % ('yes' if self._permban_with_frozensand else 'no'))

    def load_conf_tempban_with_frozensand(self):
        """
        Load tempban configuration from b3.xml.
        """
        self._tempban_with_frozensand = False
        if self.config.has_option('server', 'tempban_with_frozensand'):
            try:
                self._tempban_with_frozensand = self.config.getboolean('server', 'tempban_with_frozensand')
            except ValueError as err:
                self.warning(err)

        self.info("Send temporary bans to Frozen Sand : %s" % ('yes' if self._tempban_with_frozensand else 'no'))

    def load_conf_userinfo_overflow(self):
        """
        Load userinfo overflow configuration settings.
        """
        self._allow_userinfo_overflow = False
        if self.config.has_option('server', 'allow_userinfo_overflow'):
            try:
                self._allow_userinfo_overflow = self.config.getboolean('server', 'allow_userinfo_overflow')
            except ValueError as err:
                self.warning(err)

        self.info("Allow userinfo string overflow : %s" % ('yes' if self._allow_userinfo_overflow else 'no'))

        if self._allow_userinfo_overflow:
            self.info("NOTE: due to a bug in UrT 4.2 gamecode it is possible to exploit the maximum client name length "
                      "and generate a userinfo string longer than the imposed limits: clients connecting with nicknames "
                      "longer than 32 characters will be automatically kicked by B3 in order to prevent any sort of error")
        else:
            self.info("NOTE: due to a bug in UrT 4.2 gamecode it is possible to exploit the maximum client name length "
                      "and generate a userinfo string longer than the imposed limits: B3 will truncate nicknames of clients "
                      "which are longer than 32 characters")

    def unpause(self):
        """
        Unpause B3 log parsing.
        """
        self.pluginsStarted()  # so we get teams refreshed
        self.clients.sync()
        b3.parser.Parser.unpause(self)

    def getLineParts(self, line):
        """
        Parse a log line returning extracted tokens.
        :param line: The line to be parsed
        """
        line = re.sub(self._lineClear, '', line, 1)
        m = None
        for f in self._lineFormats:
            m = re.match(f, line)
            if m:
                break

        if m is not None:
            client = None
            target = None
            try:
                data = m.group('data').strip()
            except:
                data = None
            return m, m.group('action').lower(), data, client, target
        elif '------' not in line:
            self.verbose('Line did not match format: %s' % line)

    def parseUserInfo(self, info):
        """
        Parse an infostring.
        :param info: The infostring to be parsed.
        """
        # 2 \ip\145.99.135.227:27960\challenge\-232198920\qport\2781\protocol\68\battleye\1\name\[SNT]^1XLR^78or...
        # 7 n\[SNT]^1XLR^78or\t\3\r\2\tl\0\f0\\f1\\f2\\a0\0\a1\0\a2\0
        player_id, info = info.split(' ', 1)

        if info[:1] != '\\':
            info = '\\' + info

        self.verbose2('Parsing userinfo: %s', info)
        options = re.findall(r'\\([^\\]+)\\([^\\]+)', info)

        data = dict()
        for o in options:
            data[o[0]] = o[1]

        data['cid'] = player_id
        return data

    def OnClientconnect(self, action, data, match=None):
        self.debug('Client connected: ready to parse userinfo line')
        # client = self.clients.getByCID(data)
        # return b3.events.Event(b3.events.EVT_CLIENT_JOIN, None, client)

    def OnClientbegin(self, action, data, match=None):
        # we get user info in two parts:
        # 19:42.36 ClientBegin: 4
        client = self.getByCidOrJoinPlayer(data)
        if client:
            return b3.events.Event(self.getEventID('EVT_CLIENT_JOIN'), data=data, client=client)

    def OnClientuserinfo(self, action, data, match=None):
        # 2 \ip\145.99.135.227:27960\challenge\-232198920\qport\2781\protocol\68\battleye\1\name\[SNT]^1XLR^78or..
        # 0 \gear\GMIORAA\team\blue\skill\5.000000\characterfile\bots/ut_chicken_c.c\color\4\sex\male\race\2\snaps\20\..
        bclient = self.parseUserInfo(data)
        bot = False
        if not 'cl_guid' in bclient and 'skill' in bclient:
            # must be a bot connecting
            self.bot('Bot connecting!')
            bclient['ip'] = '0.0.0.0'
            bclient['cl_guid'] = 'BOT' + str(bclient['cid'])
            bot = True

        if 'name' in bclient:
            # remove spaces from name
            bclient['name'] = bclient['name'].replace(' ', '')

        # split port from ip field
        if 'ip' in bclient:
            ip_port_data = bclient['ip'].split(':', 1)
            bclient['ip'] = ip_port_data[0]
            if len(ip_port_data) > 1:
                bclient['port'] = ip_port_data[1]

        if 'team' in bclient:
            bclient['team'] = self.getTeam(bclient['team'])

        self.verbose('Parsed user info: %s' % bclient)

        if bclient:

            client = self.clients.getByCID(bclient['cid'])

            if client:
                # update existing client
                for k, v in bclient.items():
                    if hasattr(client, 'gear') and k == 'gear' and client.gear != v:
                        self.queueEvent(b3.events.Event(self.getEventID('EVT_CLIENT_GEAR_CHANGE'), v, client))
                    if not k.startswith('_') and k not in (
                            'login', 'password', 'groupBits', 'maskLevel', 'autoLogin', 'greeting'):
                        setattr(client, k, v)
            else:
                # make a new client
                if 'cl_guid' in bclient:
                    guid = bclient['cl_guid']
                else:
                    guid = 'unknown'

                if 'authl' in bclient:
                    # authl contains FSA since UrT 4.2.022
                    fsa = bclient['authl']
                else:
                    # query FrozenSand Account
                    auth_info = self.queryClientFrozenSandAccount(bclient['cid'])
                    fsa = auth_info.get('login', None)

                # v1.0.17 - mindriot - 02-Nov-2008
                if 'name' not in bclient:
                    bclient['name'] = self._empty_name_default

                # v 1.10.5 => https://github.com/BigBrotherBot/big-brother-bot/issues/346
                if len(bclient['name']) > 32:
                    self.debug("UrT4.2 bug spotted! %s [GUID: '%s'] [FSA: '%s'] has a too long "
                               "nickname (%s characters)", bclient['name'], guid, fsa, len(bclient['name']))
                    if self._allow_userinfo_overflow:
                        x = bclient['name'][0:32]
                        self.debug('Truncating %s (%s) nickname => %s (%s)', bclient['name'], len(bclient['name']), x,
                                   len(x))
                        bclient['name'] = x
                    else:
                        self.debug("Connection denied to  %s [GUID: '%s'] [FSA: '%s']", bclient['name'], guid, fsa)
                        self.write(
                            self.getCommand('kick', cid=bclient['cid'], reason='userinfo string overflow protection'))
                        return

                if 'ip' not in bclient:
                    if guid == 'unknown':
                        # happens when a client is (temp)banned and got kicked so client was destroyed,
                        # but infoline was still waiting to be parsed.
                        self.debug('Client disconnected: ignoring...')
                        return None
                    else:
                        try:
                            # see issue xlr8or/big-brother-bot#87 - ip can be missing
                            self.debug("Missing ip: trying to get ip with 'status'")
                            plist = self.getPlayerList()
                            client_data = plist[bclient['cid']]
                            bclient['ip'] = client_data['ip']
                        except Exception as err:
                            bclient['ip'] = ''
                            self.warning("Failed to get client %s ip address" % bclient['cid'], err)

                nguid = ''
                # override the guid... use ip's only if self.console.IpsOnly is set True.
                if self.IpsOnly:
                    nguid = bclient['ip']
                # replace last part of the guid with two segments of the ip
                elif self.IpCombi:
                    i = bclient['ip'].split('.')
                    d = len(i[0]) + len(i[1])
                    nguid = guid[:-d] + i[0] + i[1]
                # Quake clients don't have a cl_guid, we'll use ip instead
                elif guid == 'unknown':
                    nguid = bclient['ip']

                if nguid != '':
                    guid = nguid

                self.clients.newClient(bclient['cid'], name=bclient['name'], ip=bclient['ip'], bot=bot, guid=guid,
                                       pbid=fsa)

        return None

    def OnClientuserinfochanged(self, action, data, match=None):
        # 7 n\[SNT]^1XLR^78or\t\3\r\2\tl\0\f0\\f1\\f2\\a0\0\a1\0\a2\0
        parseddata = self.parseUserInfo(data)
        self.verbose('Parsed userinfo: %s' % parseddata)
        if parseddata:
            client = self.clients.getByCID(parseddata['cid'])
            if client:
                # update existing client
                if 'n' in parseddata:
                    setattr(client, 'name', parseddata['n'])

                if 't' in parseddata:
                    team = self.getTeam(parseddata['t'])
                    setattr(client, 'team', team)

                    if 'r' in parseddata:
                        if team == b3.TEAM_BLUE:
                            setattr(client, 'raceblue', parseddata['r'])
                        elif team == b3.TEAM_RED:
                            setattr(client, 'racered', parseddata['r'])
                        elif team == b3.TEAM_FREE:
                            setattr(client, 'racefree', parseddata['r'])

                    if parseddata.get('f0') is not None \
                            and parseddata.get('f1') is not None \
                            and parseddata.get('f2') is not None:

                        data = "%s,%s,%s" % (parseddata['f0'], parseddata['f1'], parseddata['f2'])
                        if team == b3.TEAM_BLUE:
                            setattr(client, 'funblue', data)
                        elif team == b3.TEAM_RED:
                            setattr(client, 'funred', data)

                if 'a0' in parseddata and 'a1' in parseddata and 'a2' in parseddata:
                    setattr(client, 'cg_rgb', "%s %s %s" % (parseddata['a0'], parseddata['a1'], parseddata['a2']))

    def OnRadio(self, action, data, match=None):
        cid = match.group('cid')
        msg_group = match.group('msg_group')
        msg_id = match.group('msg_id')
        location = match.group('location')
        text = match.group('text')
        client = self.getByCidOrJoinPlayer(cid)
        if not client:
            self.debug('No client found')
            return None
        return self.getEvent('EVT_CLIENT_RADIO', client=client, data={'msg_group': msg_group, 'msg_id': msg_id,
                                                                      'location': location, 'text': text})

    def OnHit(self, action, data, match=None):
        # Hit: 13 10 0 8: Grover hit jacobdk92 in the Head
        # Hit: cid acid hitloc aweap: text
        victim = self.clients.getByCID(match.group('cid'))
        if not victim:
            self.debug('No victim')
            # self.on_clientuserinfo(action, data, match)
            return None

        attacker = self.clients.getByCID(match.group('acid'))
        if not attacker:
            self.debug('No attacker')
            return None

        event = self.getEventID('EVT_CLIENT_DAMAGE')
        if attacker.cid == victim.cid:
            event = self.getEventID('EVT_CLIENT_DAMAGE_SELF')
        elif attacker.team != b3.TEAM_UNKNOWN and attacker.team == victim.team:
            event = self.getEventID('EVT_CLIENT_DAMAGE_TEAM')

        hitloc = match.group('hitloc')
        weapon = self._convertHitWeaponToKillWeapon(match.group('aweap'))
        points = self._getDamagePoints(weapon, hitloc)
        event_data = (points, weapon, hitloc)
        victim.data['lastDamageTaken'] = event_data
        # victim.state = b3.STATE_ALIVE
        # need to pass some amount of damage for the teamkill plugin - 15 seems okay
        return self.getEvent(event, event_data, attacker, victim)

    def OnCallvote(self, action, data, match=None):
        cid = match.group('cid')
        vote_string = match.group('vote_string')
        client = self.getByCidOrJoinPlayer(cid)
        if not client:
            self.debug('No client found')
            return None
        return self.getEvent('EVT_CLIENT_CALLVOTE', client=client, data=vote_string)

    def OnVote(self, action, data, match=None):
        cid = match.group('cid')
        value = match.group('value')
        client = self.getByCidOrJoinPlayer(cid)
        if not client:
            self.debug('No client found')
            return None
        return self.getEvent('EVT_CLIENT_VOTE', client=client, data=value)

    def OnVotepassed(self, action, data, match=None):
        yes_count = int(match.group('yes'))
        no_count = int(match.group('no'))
        vote_what = match.group('what')
        return self.getEvent('EVT_VOTE_PASSED', data={'yes': yes_count, 'no': no_count, 'what': vote_what})

    def OnVotefailed(self, action, data, match=None):
        yes_count = int(match.group('yes'))
        no_count = int(match.group('no'))
        vote_what = match.group('what')
        return self.getEvent('EVT_VOTE_FAILED', data={'yes': yes_count, 'no': no_count, 'what': vote_what})

    def OnFlagcapturetime(self, action, data, match=None):
        # FlagCaptureTime: 0: 1234567890
        # FlagCaptureTime: 1: 1125480101
        cid = match.group('cid')
        captime = int(match.group('captime'))
        client = self.getByCidOrJoinPlayer(cid)
        if not client:
            self.debug('No client found')
            return None
        return self.getEvent('EVT_FLAG_CAPTURE_TIME', client=client, data=captime)

    def OnClientjumprunstarted(self, action, data, match=None):
        cid = match.group('cid')
        way_id = match.group('way_id')
        attempt_num = match.group('attempt_num')
        attempt_max = match.group('attempt_max')
        client = self.getByCidOrJoinPlayer(cid)
        if not client:
            self.debug('No client found')
            return None
        return self.getEvent('EVT_CLIENT_JUMP_RUN_START', client=client, data={'way_id': way_id,
                                                                               'attempt_num': attempt_num,
                                                                               'attempt_max': attempt_max})

    def OnClientjumprunstopped(self, action, data, match=None):
        cid = match.group('cid')
        way_id = match.group('way_id')
        way_time = match.group('way_time')
        attempt_num = match.group('attempt_num')
        attempt_max = match.group('attempt_max')
        client = self.getByCidOrJoinPlayer(cid)
        if not client:
            self.debug('No client found')
            return None
        return self.getEvent('EVT_CLIENT_JUMP_RUN_STOP', client=client, data={'way_id': way_id,
                                                                              'way_time': way_time,
                                                                              'attempt_num': attempt_num,
                                                                              'attempt_max': attempt_max})

    def OnClientjumpruncanceled(self, action, data, match=None):
        cid = match.group('cid')
        way_id = match.group('way_id')
        attempt_num = match.group('attempt_num')
        attempt_max = match.group('attempt_max')
        client = self.getByCidOrJoinPlayer(cid)
        if not client:
            self.debug('No client found')
            return None
        return self.getEvent('EVT_CLIENT_JUMP_RUN_CANCEL', client=client, data={'way_id': way_id,
                                                                                'attempt_num': attempt_num,
                                                                                'attempt_max': attempt_max})

    def OnClientsaveposition(self, action, data, match=None):
        cid = match.group('cid')
        position = float(match.group('x')), float(match.group('y')), float(match.group('z'))
        client = self.getByCidOrJoinPlayer(cid)
        if not client:
            self.debug('No client found')
            return None
        return self.getEvent('EVT_CLIENT_POS_SAVE', client=client, data={'position': position})

    def OnClientloadposition(self, action, data, match=None):
        cid = match.group('cid')
        position = float(match.group('x')), float(match.group('y')), float(match.group('z'))
        client = self.getByCidOrJoinPlayer(cid)
        if not client:
            self.debug('No client found')
            return None
        return self.getEvent('EVT_CLIENT_POS_LOAD', client=client, data={'position': position})

    def OnClientgoto(self, action, data, match=None):
        cid = match.group('cid')
        tcid = match.group('tcid')
        position = float(match.group('x')), float(match.group('y')), float(match.group('z'))
        client = self.getByCidOrJoinPlayer(cid)
        if not client:
            self.debug('No client found')
            return None

        target = self.getByCidOrJoinPlayer(tcid)
        if not target:
            self.debug('No target client found')
            return None

        return self.getEvent('EVT_CLIENT_GOTO', client=client, target=target, data={'position': position})

    def OnClientspawn(self, action, data, match=None):
        # ClientSpawn: 0
        cid = match.group('cid')
        client = self.getByCidOrJoinPlayer(cid)
        if not client:
            self.debug('No client found')
            return None

        client.state = b3.STATE_ALIVE
        return self.getEvent('EVT_CLIENT_SPAWN', client=client)

    def OnClientmelted(self, action, data, match=None):
        # ClientMelted: 0
        cid = match.group('cid')
        client = self.getByCidOrJoinPlayer(cid)
        if not client:
            self.debug('No client found')
            return None

        client.state = b3.STATE_ALIVE
        return self.getEvent('EVT_CLIENT_MELTED', client=client)

    def OnSurvivorwinner(self, action, data, match=None):
        # SurvivorWinner: Blue
        # SurvivorWinner: Red
        # SurvivorWinner: 0
        # queue round and in any case (backwards compatibility for plugins)
        self.queueEvent(self.getEvent('EVT_GAME_ROUND_END'))
        if data in ('Blue', 'Red'):
            return self.getEvent('EVT_SURVIVOR_WIN', data=data)
        else:
            client = self.getByCidOrJoinPlayer(data)
            if not client:
                self.debug('No client found')
                return None
            return self.getEvent('EVT_CLIENT_SURVIVOR_WINNER', client=client)

    def OnFreeze(self, action, data, match=None):
        # 6:37 Freeze: 0 1 16: Fenix froze Biddle by UT_MOD_SPAS
        victim = self.getByCidOrJoinPlayer(match.group('cid'))
        if not victim:
            self.debug('No victim')
            return None

        attacker = self.getByCidOrJoinPlayer(match.group('acid'))
        if not attacker:
            self.debug('No attacker')
            return None

        weapon = match.group('aweap')
        if not weapon:
            self.debug('No weapon')
            return None

        victim.state = b3.STATE_DEAD
        return self.getEvent('EVT_CLIENT_FREEZE', data=weapon, client=attacker, target=victim)

    def OnThawoutstarted(self, action, data, match=None):
        # ThawOutStarted: 0 1: Fenix started thawing out Biddle
        client = self.getByCidOrJoinPlayer(match.group('cid'))
        if not client:
            self.debug('No client')
            return None

        target = self.getByCidOrJoinPlayer(match.group('tcid'))
        if not target:
            self.debug('No target')
            return None

        return self.getEvent('EVT_CLIENT_THAWOUT_STARTED', client=client, target=target)

    def OnThawoutfinished(self, action, data, match=None):
        # ThawOutFinished: 0 1: Fenix thawed out Biddle
        client = self.getByCidOrJoinPlayer(match.group('cid'))
        if not client:
            self.debug('No client')
            return None

        target = self.getByCidOrJoinPlayer(match.group('tcid'))
        if not target:
            self.debug('No target')
            return None

        target.state = b3.STATE_ALIVE
        return self.getEvent('EVT_CLIENT_THAWOUT_FINISHED', client=client, target=target)

    def authorizeClients(self):
        """
        For all connected players, fill the client object with properties allowing to find
        the user in the database (usualy guid, ip) and call the
        Client.auth() method.
        """
        pass

    def OnKill(self, action, data, match=None):
        """
        1:      MOD_WATER === exclusive attackers : , 1022(<world>), 0(<non-client>)
        3:      MOD_LAVA === exclusive attackers : , 1022(<world>), 0(<non-client>)
        5:      MOD_TELEFRAG --- normal kill line
        6:      MOD_FALLING === exclusive attackers : , 1022(<world>), 0(<non-client>)
        7:      MOD_SUICIDE ===> attacker is always the victim
        9:      MOD_TRIGGER_HURT === exclusive attackers : , 1022(<world>)
        10:     MOD_CHANGE_TEAM ===> attacker is always the victim
        12:     UT_MOD_KNIFE --- normal kill line
        13:     UT_MOD_KNIFE_THROWN --- normal kill line
        14:     UT_MOD_BERETTA --- normal kill line
        15:     UT_MOD_DEAGLE --- normal kill line
        16:     UT_MOD_SPAS --- normal kill line
        17:     UT_MOD_UMP45 --- normal kill line
        18:     UT_MOD_MP5K --- normal kill line
        19:     UT_MOD_LR300 --- normal kill line
        20:     UT_MOD_G36 --- normal kill line
        21:     UT_MOD_PSG1 --- normal kill line
        22:     UT_MOD_HK69 --- normal kill line
        23:     UT_MOD_BLED --- normal kill line
        24:     UT_MOD_KICKED --- normal kill line
        25:     UT_MOD_HEGRENADE --- normal kill line
        28:     UT_MOD_SR8 --- normal kill line
        30:     UT_MOD_AK103 --- normal kill line
        31:     UT_MOD_SPLODED ===> attacker is always the victim
        32:     UT_MOD_SLAPPED ===> attacker is always the victim
        33:     UT_MOD_BOMBED --- normal kill line
        34:     UT_MOD_NUKED --- normal kill line
        35:     UT_MOD_NEGEV --- normal kill line
        37:     UT_MOD_HK69_HIT --- normal kill line
        38:     UT_MOD_M4 --- normal kill line
        39:     UT_MOD_FLAG === exclusive attackers : , 0(<non-client>)
        40:     UT_MOD_GOOMBA --- normal kill line
        """
        self.debug('OnKill: %s (%s)' % (match.group('aweap'), match.group('text')))
        victim = self.getByCidOrJoinPlayer(match.group('cid'))
        if not victim:
            self.debug('No victim')
            # self.OnClientuserinfo(action, data, match)
            return None

        weapon = match.group('aweap')
        if not weapon:
            self.debug('No weapon')
            return None

        ## Fix attacker
        if match.group('aweap') in (self.UT_MOD_SLAPPED, self.UT_MOD_NUKED, self.MOD_TELEFRAG):
            self.debug('OnKill: slap/nuke => attacker should be None')
            attacker = self.clients.getByCID('-1')  # make the attacker 'World'
        elif match.group('aweap') in (self.MOD_WATER, self.MOD_LAVA, self.MOD_FALLING,
                                      self.MOD_TRIGGER_HURT, self.UT_MOD_BOMBED, self.UT_MOD_FLAG):
            # those kills should be considered suicides
            self.debug('OnKill: water/lava/falling/trigger_hurt/bombed/flag should be suicides')
            attacker = victim
        else:
            attacker = self.getByCidOrJoinPlayer(match.group('acid'))
        ## End fix attacker

        if not attacker:
            # handle the case where Mr.Sentry killed a player
            if match.group('aweap') == self.UT_MOD_BERETTA and match.group('acid') == self.WORLD:
                return self.getEvent('EVT_SENTRY_KILL', target=victim)
            else:
                self.debug('No attacker')
                return None

        damagetype = match.group('text').split()[-1:][0]
        if not damagetype:
            self.debug('No damage type, weapon: %s' % weapon)
            return None

        event = self.getEventID('EVT_CLIENT_KILL')

        # fix event for team change and suicides and tk
        if attacker.cid == victim.cid:
            if weapon == self.MOD_CHANGE_TEAM:
                # do not pass a teamchange event here
                # that event is passed shortly after the kill
                self.verbose('Team change event caught: exiting...')
                return None
            else:
                event = self.getEventID('EVT_CLIENT_SUICIDE')
        elif attacker.team != b3.TEAM_UNKNOWN and attacker.team == victim.team:
            event = self.getEventID('EVT_CLIENT_KILL_TEAM')

        # if not logging damage we need a general hitloc (for xlrstats)
        if 'lastDamageTaken' in victim.data:
            last_damage_data = victim.data['lastDamageTaken']
            del victim.data['lastDamageTaken']
        else:
            last_damage_data = (100, weapon, 'body')

        victim.state = b3.STATE_DEAD
        # self.verbose('OnKill Victim: %s, Attacker: %s, Weapon: %s, Hitloc: %s, dType: %s' %
        #              (victim.name, attacker.name, weapon, victim.hitloc, dType))
        # need to pass some amount of damage for the teamkill plugin - 100 is a kill
        return self.getEvent(event, (last_damage_data[0], weapon, last_damage_data[2], damagetype), attacker, victim)

    def OnAssist(self, action, data, match=None):
        # Assist: 0 14 15: -[TPF]-PtitBigorneau assisted Bot1 to kill Bot2
        cid = match.group('acid')
        vid = match.group('dcid')
        aid = match.group('kcid')

        client = self.getByCidOrJoinPlayer(cid)
        if not client:
            self.debug('No client')
            return None

        victim = self.getByCidOrJoinPlayer(vid)
        if not victim:
            self.debug('No victim')
            return None

        attacker = self.getByCidOrJoinPlayer(aid)
        if not attacker:
            self.debug('No attacker')
            return None

        return self.getEvent('EVT_ASSIST', client=client, target=victim, data=attacker)

    def OnClientdisconnect(self, action, data, match=None):
        client = self.clients.getByCID(data)
        if client:
            client.disconnect()
        return None

    def OnFlag(self, action, data, match=None):
        # Flag: 1 2: team_CTF_blueflag
        # Flag: <_cid> <_subtype:0/1/2>: <text>
        cid = match.group('cid')
        subtype = int(match.group('name'))
        data = match.group('text')

        if subtype == 0:
            actiontype = 'flag_dropped'
        elif subtype == 1:
            actiontype = 'flag_returned'
        elif subtype == 2:
            actiontype = 'flag_captured'
        else:
            return None
        return self.OnAction(cid, actiontype, data)

    def OnFlagReturn(self, action, data, match=None):
        # Flag Return: RED
        # Flag Return: BLUE
        # Flag Return: <color>
        color = match.group('color')
        return self.getEvent('EVT_GAME_FLAG_RETURNED', data=color)

    def OnPop(self, action, data, match=None):
        return self.getEvent('EVT_BOMB_EXPLODED')

    def OnBomb(self, action, data, match=None):
        cid = match.group('cid')
        subaction = match.group('subaction')
        if subaction == 'planted':
            actiontype = 'bomb_planted'
        elif subaction == 'defused':
            actiontype = 'bomb_defused'
        elif subaction == 'tossed':
            actiontype = 'bomb_tossed'
        elif subaction == 'collected':
            actiontype = 'bomb_collected'
        else:
            return None
        return self.OnAction(cid, actiontype, data)

    def OnBombholder(self, action, data, match=None):
        cid = match.group('cid')
        actiontype = 'bomb_holder_spawn'
        return self.OnAction(cid, actiontype, data)

    def OnAction(self, cid, actiontype, data, match=None):
        client = self.clients.getByCID(cid)
        if not client:
            self.debug('No client found')
            return None
        self.verbose('onAction: %s: %s %s' % (client.name, actiontype, data))
        return self.getEvent('EVT_CLIENT_ACTION', data=actiontype, client=client)

    def OnItem(self, action, data, match=None):
        # Item: 3 ut_item_helmet
        # Item: 0 team_CTF_redflag
        cid, item = data.split(' ', 1)
        client = self.getByCidOrJoinPlayer(cid)
        if client:
            # correct flag/bomb-pickups
            if 'flag' in item or 'bomb' in item:
                self.verbose('Item pickup corrected to action: %s' % item)
                return self.OnAction(cid, item, data)
            # self.verbose('on_item: %s picked up %s' % (client.name, item) )
            return self.getEvent('EVT_CLIENT_ITEM_PICKUP', data=item, client=client)
        return None

    def OnSay(self, action, data, match=None):
        # 3:53 say: 8 denzel: lol
        if match is None:
            return

        name = self.stripColors(match.group('name'))
        client = self.getByCidOrJoinPlayer(match.group('cid'))

        if not client or client.name != name:
            self.debug('Urban Terror bug spotted: trying to get client by name')
            client = self.clients.getByName(name)

        if not client:
            self.verbose('No client found')
            return None

        self.verbose('Client found: %s on slot %s' % (client.name, client.cid))

        data = match.group('text')

        # removal of weird characters
        if data and ord(data[:1]) == 21:
            data = data[1:]

        return self.getEvent('EVT_CLIENT_SAY', data=data, client=client)

    def OnSayteam(self, action, data, match=None):
        # 2:28 sayteam: 12 New_UrT_Player_v4.1: wokele
        if match is None:
            return

        name = self.stripColors(match.group('name'))
        client = self.getByCidOrJoinPlayer(match.group('cid'))

        if not client or client.name != name:
            self.debug('Urban Terror bug spotted: trying to get client by name')
            client = self.clients.getByName(name)

        if not client:
            self.verbose('no client found!')
            return None

        self.verbose('Client found: %s on slot %s' % (client.name, client.cid))

        data = match.group('text')
        if data and ord(data[:1]) == 21:
            data = data[1:]

        return self.getEvent('EVT_CLIENT_TEAM_SAY', data=data, client=client, target=client.team)

    def OnSaytell(self, action, data, match=None):
        # 5:39 saytell: 15 16 repelSteeltje: nno
        # 5:39 saytell: 15 15 repelSteeltje: nno
        if match is None:
            return

        name = self.stripColors(match.group('name'))
        client = self.getByCidOrJoinPlayer(match.group('cid'))
        target = self.clients.getByCID(match.group('acid'))

        if not client or client.name != name:
            self.debug('Urban Terror bug spotted: trying to get client by name')
            client = self.clients.getByName(name)

        if not client:
            self.verbose('No client found')
            return None

        self.verbose('client found: %s on slot %s' % (client.name, client.cid))

        data = match.group('text')
        if data and ord(data[:1]) == 21:
            data = data[1:]

        return self.getEvent('EVT_CLIENT_PRIVATE_SAY', data=data, client=client, target=target)

    def OnTell(self, action, data, match=None):
        # 5:27 tell: woekele to XLR8or: test
        # We'll use saytell instead
        #
        # client = self.clients.get_by_exact_name(match.group('name'))
        # target = self.clients.get_by_exact_name(match.group('aname'))
        #
        # if not client:
        #    self.verbose('no client found!')
        #    return None
        #
        # data = match.group('text')
        # if data and ord(data[:1]) == 21:
        #    data = data[1:]
        #
        # client.name = match.group('name')
        # return self.get_Event('EVT_CLIENT_PRIVATE_SAY', data=data, client=client, target=target)
        return None

    # endmap/shutdown
    def OnShutdowngame(self, action, data=None, match=None):
        self.game.mapEnd()
        # self.clients.sync()
        # self.debug('Synchronizing client info')
        self._maplist = None  # when UrT server reloads, newly uploaded maps get available: force refresh
        return self.getEvent('EVT_GAME_EXIT', data=data)

    # Startgame
    def OnInitgame(self, action, data, match=None):
        options = re.findall(r'\\([^\\]+)\\([^\\]+)', data)
        # capturelimit / fraglimit / timelimit
        for o in options:
            if o[0] == 'mapname':
                self.game.mapName = o[1]
            elif o[0] == 'g_gametype':
                self.game.gameType = self.defineGameType(o[1])
            elif o[0] == 'fs_game':
                self.game.modName = o[1]
            elif o[0] == 'capturelimit':
                self.game.captureLimit = o[1]
            elif o[0] == 'fraglimit':
                self.game.fragLimit = o[1]
            elif o[0] == 'timelimit':
                self.game.timeLimit = o[1]
            else:
                setattr(self.game, o[0], o[1])

        self.verbose('...self.console.game.gameType: %s' % self.game.gameType)
        self.game.startMap()
        self.game.rounds = 0
        start_daemon_thread(self.clients.sync)
        return self.getEvent('EVT_GAME_ROUND_START', data=self.game)

    def OnWarmup(self, action, data=None, match=None):
        self.game.rounds = 0
        return self.getEvent('EVT_GAME_WARMUP', data=data)

    def OnInitround(self, action, data, match=None):
        options = re.findall(r'\\([^\\]+)\\([^\\]+)', data)
        # capturelimit / fraglimit / timelimit
        for o in options:
            if o[0] == 'mapname':
                self.game.mapName = o[1]
            elif o[0] == 'g_gametype':
                self.game.gameType = self.defineGameType(o[1])
            elif o[0] == 'fs_game':
                self.game.modName = o[1]
            elif o[0] == 'capturelimit':
                self.game.captureLimit = o[1]
            elif o[0] == 'fraglimit':
                self.game.fragLimit = o[1]
            elif o[0] == 'timelimit':
                self.game.timeLimit = o[1]
            else:
                setattr(self.game, o[0], o[1])

        self.verbose('...self.console.game.gameType: %s' % self.game.gameType)
        self.game.startMap()
        self.game.rounds = 0
        start_daemon_thread(self.clients.sync)
        return self.getEvent('EVT_GAME_ROUND_START', data=self.game)

    def broadcast(self, text):
        """
        A Say variant in UrT which will print text upper left, server message area.
        :param text: The message to be sent.
        """
        lines = []
        message = prefixText([self.msgPrefix], text)
        message = message.strip()
        for line in self.getWrap(message):
            lines.append(self.getCommand('broadcast', message=line))
        self.writelines(lines)

    def saybig(self, text, *args):
        """
        Print a message in the center screen.
        :param text: The message to be sent.
        """
        lines = []
        message = prefixText([self.msgPrefix], text)
        message = message.strip()
        for line in self.getWrap(message):
            lines.append(self.getCommand('saybig', message=line))
        self.writelines(lines)

    def ban(self, client, reason='', admin=None, silent=False, *kwargs):
        """
        Ban a given client.
        :param client: The client to ban
        :param reason: The reason for this ban
        :param admin: The admin who performed the ban
        :param silent: Whether or not to announce this ban
        """
        self.debug('BAN : client: %s, reason: %s', client, reason)
        if isinstance(client, Client) and not client.guid:
            # client has no guid, kick instead
            return self.kick(client, reason, admin, silent)
        elif isinstance(client, str) and re.match('^[0-9]+$', client):
            self.write(self.getCommand('ban', cid=client, reason=reason))
            return
        elif not client.id:
            # no client id, database must be down, do tempban
            self.error('Q3AParser.ban(): no client id, database must be down, doing tempban')
            return self.tempban(client, reason, 1440, admin, silent)

        if admin:
            variables = self.getMessageVariables(client=client, reason=reason, admin=admin)
            fullreason = self.getMessage('banned_by', variables)
        else:
            variables = self.getMessageVariables(client=client, reason=reason)
            fullreason = self.getMessage('banned', variables)

        if client.cid is None:
            # ban by ip, this happens when we !permban @xx a player that is not connected
            self.debug('EFFECTIVE BAN : %s', self.getCommand('banByIp', ip=client.ip, reason=reason))
            self.write(self.getCommand('banByIp', ip=client.ip, reason=reason))
        else:
            # ban by cid
            self.debug('EFFECTIVE BAN : %s', self.getCommand('ban', cid=client.cid, reason=reason))

            if self._permban_with_frozensand:
                cmd = self.getCommand('auth-permban', cid=client.cid)
                self.info('Sending ban to Frozen Sand : %s' % cmd)
                rv = self.write(cmd)
                if rv:
                    if rv == "Auth services disabled" or rv.startswith("auth: not banlist available."):
                        self.warning(rv)
                    elif rv.startswith("auth: sending ban"):
                        self.info(rv)
                        time.sleep(.250)
                    else:
                        self.warning(rv)
                        time.sleep(.250)

            if client.connected:
                cmd = self.getCommand('ban', cid=client.cid, reason=reason)
                self.info('Sending ban to server : %s' % cmd)
                rv = self.write(cmd)
                if rv:
                    self.info(rv)

        if not silent and fullreason != '':
            self.say(fullreason)

        if admin:
            admin.message('^7Banned^7: ^1%s^7 (^2@%s^7)' % (client.exactName, client.id))
            admin.message('^7His last ip (^1%s^7) has been added to banlist' % client.ip)

        self.queueEvent(self.getEvent('EVT_CLIENT_BAN', data={'reason': reason, 'admin': admin}, client=client))
        client.disconnect()

    def tempban(self, client, reason='', duration=2, admin=None, silent=False, *kwargs):
        """
        Tempban a client.
        :param client: The client to tempban
        :param reason: The reason for this tempban
        :param duration: The duration of the tempban
        :param admin: The admin who performed the tempban
        :param silent: Whether or not to announce this tempban
        """
        duration = time2minutes(duration)
        if isinstance(client, Client) and not client.guid:
            # client has no guid, kick instead
            return self.kick(client, reason, admin, silent)
        elif isinstance(client, str) and re.match('^[0-9]+$', client):
            self.write(self.getCommand('tempban', cid=client, reason=reason))
            return
        elif admin:
            banduration = b3.functions.minutesStr(duration)
            variables = self.getMessageVariables(client=client, reason=reason, admin=admin, banduration=banduration)
            fullreason = self.getMessage('temp_banned_by', variables)
        else:
            banduration = b3.functions.minutesStr(duration)
            variables = self.getMessageVariables(client=client, reason=reason, banduration=banduration)
            fullreason = self.getMessage('temp_banned', variables)

        if self._tempban_with_frozensand:
            minutes = duration
            days = hours = 0
            while minutes >= 60:
                hours += 1
                minutes -= 60
            while hours >= 24:
                days += 1
                hours -= 24

            cmd = self.getCommand('auth-tempban', cid=client.cid, days=days, hours=hours, minutes=int(minutes))
            self.info('Sending ban to Frozen Sand : %s' % cmd)
            rv = self.write(cmd)
            if rv:
                if rv == "Auth services disabled" or rv.startswith("auth: not banlist available."):
                    self.warning(rv)
                elif rv.startswith("auth: sending ban"):
                    self.info(rv)
                    time.sleep(.250)
                else:
                    self.warning(rv)
                    time.sleep(.250)

        if client.connected:
            cmd = self.getCommand('tempban', cid=client.cid, reason=reason)
            self.info('Sending ban to server : %s' % cmd)
            rv = self.write(cmd)
            if rv:
                self.info(rv)

        if not silent and fullreason != '':
            self.say(fullreason)

        self.queueEvent(self.getEvent('EVT_CLIENT_BAN_TEMP', data={'reason': reason,
                                                                   'duration': duration,
                                                                   'admin': admin}, client=client))
        client.disconnect()

    def queryClientFrozenSandAccount(self, cid):
        """
        : auth-whois 0
        auth: id: 0 - name: ^7laCourge - login:  - notoriety: 0 - level: 0  - ^7no account

        : auth-whois 0
        auth: id: 0 - name: ^7laCourge - login: courgette - notoriety: serious - level: -1

        : auth-whois 3
        Client 3 is not active.
        """
        data = self.write('auth-whois %s' % cid)
        if not data:
            return dict()

        if data == "Client %s is not active." % cid:
            return dict()

        m = self._re_authwhois.match(data)
        if m:
            return m.groupdict()
        else:
            return {}

    def queryAllFrozenSandAccount(self, max_retries=None):
        """
        Query the accounts of all the online clients.
        """
        data = self.write('auth-whois all', maxRetries=max_retries)
        if not data:
            return {}
        players = {}
        for m in re.finditer(self._re_authwhois, data):
            players[m.group('cid')] = m.groupdict()
        return players

    def is_frozensand_auth_available(self):
        """
        Check whether the auth system is available.
        """
        cvar = self.getCvar('auth')
        if cvar:
            auth = cvar.getInt()
            return auth != 0
        else:
            return False

    def defineGameType(self, gametype_int):
        gametype = str(gametype_int)
        return self.game_types.get(gametype, gametype)

    @staticmethod
    def patch_Clients():

        def newClient(self, cid, **kwargs):
            """
            Patch the newClient method in the Clients class to handle UrT 4.2 specific client instances.
            """
            client = Iourt43Client(console=self.console, cid=cid, timeAdd=self.console.time(), **kwargs)
            self[client.cid] = client
            self.resetIndex()

            self.console.debug('Urt4 Client Connected: [%s] %s - %s (%s)', self[client.cid].cid, self[client.cid].name,
                               self[client.cid].guid, self[client.cid].data)

            self.console.queueEvent(self.console.getEvent('EVT_CLIENT_CONNECT', data=client, client=client))

            if client.guid:
                client.auth()
            elif not client.authed:
                self.authorizeClients()
            return client

        def newGetByMagic(self, handle):
            """
            Patch the getByMagic method in the Clients class so it's possible to lookup players using the auth login.
            """
            handle = handle.strip()
            if re.match(r'^[0-9]+$', handle):
                client = self.getByCID(handle)
                if client:
                    return [client]
                return []
            elif re.match(r'^@([0-9]+)$', handle):
                return self.getByDB(handle)
            elif handle[:1] == '\\':
                c = self.getByName(handle[1:])
                if c and not c.hide:
                    return [c]
                return []
            else:
                clients = []
                needle = re.sub(r'\s', '', handle.lower())
                for cid, c in self.items():
                    cleanname = re.sub(r'\s', '', c.name.lower())
                    if not c.hide and (needle in cleanname or needle in c.pbid) and not c in clients:
                        clients.append(c)
                return clients

        b3.clients.Clients.newClient = newClient
        b3.clients.Clients.getByMagic = newGetByMagic

    def unban(self, client, reason='', admin=None, silent=False, *kwargs):
        """
        Unban a client.
        :param client: The client to unban
        :param reason: The reason for the unban
        :param admin: The admin who unbanned this client
        :param silent: Whether or not to announce this unban
        """
        self.debug('EFFECTIVE UNBAN : %s', self.getCommand('unbanByIp', ip=client.ip, reason=reason))
        cmd = self.getCommand('unbanByIp', ip=client.ip, reason=reason)
        # UrT adds multiple instances to banlist.txt
        # Make sure we remove up to 5 duplicates in a separate thread
        self.writelines([cmd, cmd, cmd, cmd, cmd])
        if admin:
            admin.message('^7Unbanned^7: ^1%s^7 (^2@%s^7)' % (client.exactName, client.id))
            admin.message('^7His last ip (^1%s^7) has been removed from banlist' % client.ip)
            admin.message('^7Trying to remove duplicates...')

        self.queueEvent(self.getEvent('EVT_CLIENT_UNBAN', data=admin, client=client))

    def getPlayerPings(self, filter_client_ids=None):
        """
        Returns a dict having players' id for keys and players' ping for values.
        :param filter_client_ids: If filter_client_id is an iterable, only return values for the given client ids.
        """
        data = self.write('status')
        if not data:
            return dict()

        players = dict()
        for line in data.split('\n'):
            m = re.match(self._regPlayer, line.strip())
            if m:
                if m.group('ping') == 'ZMBI':
                    # ignore them, let them not bother us with errors
                    pass
                else:
                    try:
                        players[str(m.group('slot'))] = int(m.group('ping'))
                    except ValueError:
                        players[str(m.group('slot'))] = 999

        return players

    def sync(self):
        """
        For all connected players returned by self.get_player_list(), get the matching Client
        object from self.clients (with self.clients.getByCID(cid) or similar methods) and
        look for inconsistencies. If required call the client.disconnect() method to remove
        a client from self.clients.
        """
        self.debug('synchronizing client info')
        plist = self.getPlayerList(maxRetries=4)
        mlist = dict()

        for cid, c in plist.items():
            client = self.getByCidOrJoinPlayer(cid)
            if client:
                # Disconnect the zombies first
                if c['ping'] == 'ZMBI':
                    self.debug('slot is in state zombie: %s - ignoring', c['ip'])
                    # client.disconnect()
                elif client.guid and 'guid' in c:
                    if client.guid == c['guid']:
                        # player matches
                        self.debug('in-sync %s == %s', client.guid, c['guid'])
                        mlist[str(cid)] = client
                    else:
                        self.debug('no-sync %s <> %s', client.guid, c['guid'])
                        client.disconnect()
                elif client.ip and 'ip' in c:
                    if client.ip == c['ip']:
                        # player matches
                        self.debug('in-sync %s == %s', client.ip, c['ip'])
                        mlist[str(cid)] = client
                    else:
                        self.debug('no-sync %s <> %s', client.ip, c['ip'])
                        client.disconnect()
                else:
                    self.debug('no-sync: no guid or ip found')

        return mlist

    def rotateMap(self):
        """
        Load the next map/level.
        """
        self.say('^7Changing to next map')
        time.sleep(1)
        self.write('cyclemap')

    def changeMap(self, map_name):
        """
        Load a given map/level.
        """
        rv = self.getMapsSoundingLike(map_name)
        if isinstance(rv, str):
            self.say('^7Changing map to %s' % rv)
            time.sleep(1)
            self.write('map %s' % rv)
        else:
            return rv

    def getMaps(self):
        """
        Return the available maps/levels name.
        """
        if self._maplist is not None:
            return self._maplist

        data = self.write('fdir *.bsp', socketTimeout=1.5)
        if not data:
            return []

        mapregex = re.compile(r'^maps/(?P<map>.+)\.bsp$', re.I)
        maps = []
        for line in data.split('\n'):
            m = re.match(mapregex, line.strip())
            if m:
                if m.group('map'):
                    maps.append(m.group('map'))

        self._maplist = maps
        self.info(f"getMaps() cached {len(maps)} maps")
        return maps

    def inflictCustomPenalty(self, penalty_type, client, reason=None, duration=None, admin=None, data=None):
        """
        Urban Terror specific punishments.
        """
        if penalty_type == 'slap' and client:
            cmd = self.getCommand('slap', cid=client.cid)
            self.write(cmd)
            if reason:
                client.message("%s" % reason)
            return True

        elif penalty_type == 'nuke' and client:
            cmd = self.getCommand('nuke', cid=client.cid)
            self.write(cmd)
            if reason:
                client.message("%s" % reason)
            return True

        elif penalty_type == 'mute' and client:
            if duration is None:
                seconds = 60
            else:
                seconds = round(float(time2minutes(duration) * 60), 0)

            # make sure to unmute first
            cmd = self.getCommand('mute', cid=client.cid, seconds=0)
            self.write(cmd)
            # then mute
            cmd = self.getCommand('mute', cid=client.cid, seconds=seconds)
            self.write(cmd)
            if reason:
                client.message("%s" % reason)
            return True

        elif penalty_type == 'kill' and client:
            cmd = self.getCommand('kill', cid=client.cid)
            self.write(cmd)
            if reason:
                client.message("%s" % reason)
            return True

    def getTeam(self, team):
        """
        Return a B3 team given the team value.
        :param team: The team value
        """
        if str(team).lower() == 'red':
            team = 1
        elif str(team).lower() == 'blue':
            team = 2
        elif str(team).lower() == 'spectator':
            team = 3
        elif str(team).lower() == 'free':
            team = -1  # will fall back to b3.TEAM_UNKNOWN

        team = int(team)
        if team == 1:
            result = b3.TEAM_RED
        elif team == 2:
            result = b3.TEAM_BLUE
        elif team == 3:
            result = b3.TEAM_SPEC
        else:
            result = b3.TEAM_UNKNOWN

        return result

    def getNextMap(self):
        """
        Return the next map/level name to be played.
        """
        cvars = self.cvarList('g_next')
        # let's first check if a vote passed for the next map
        nmap = cvars.get('g_nextmap')
        self.debug('g_nextmap: %s' % nmap)
        if nmap != "":
            return nmap

        nmap = cvars.get('g_nextcyclemap')
        self.debug('g_nextcyclemap: %s' % nmap)
        if nmap != "":
            return nmap

        return None

    def getMapsSoundingLike(self, mapname):
        """
        Return a valid mapname.
        If no exact match is found, then return close candidates as a list.
        """
        wanted_map = mapname.lower()
        supported_maps = self.getMaps()
        if wanted_map in supported_maps:
            return wanted_map

        cleaned_supported_maps = {}
        for map_name in supported_maps:
            cleaned_supported_maps[re.sub("^ut4?_", '', map_name, count=1)] = map_name

        if wanted_map in cleaned_supported_maps:
            return cleaned_supported_maps[wanted_map]

        cleaned_wanted_map = re.sub("^ut4?_", '', wanted_map, count=1)

        matches = [cleaned_supported_maps[match] for match in getStuffSoundingLike(cleaned_wanted_map,
                                                                                   list(cleaned_supported_maps.keys()))]
        if len(matches) == 1:
            # one match, get the map id
            return matches[0]
        else:
            # multiple matches, provide suggestions
            return matches

    def getTeamScores(self):
        """
        Return current team scores in a tuple.
        """
        data = self.write('players')
        if not data:
            return None

        line = data.split('\n')[3]
        m = re.match(self._reTeamScores, line.strip())
        if m:
            return [int(m.group('RedScore')), int(m.group('BlueScore'))]
        return None

    def getScores(self):
        """
        NOTE: this won't work properly if the server has private slots.
        See http://forums.urbanterror.net/index.php/topic,9356.0.html
        """
        data = self.write('players')
        if not data:
            return None

        scores = {'red': None, 'blue': None, 'players': {}}
        line = data.split('\n')[3]
        m = re.match(self._reTeamScores, line.strip())
        if m:
            scores['red'] = int(m.group('RedScore'))
            scores['blue'] = int(m.group('BlueScore'))

        for line in data.split('\n')[3:]:
            m = re.match(self._rePlayerScore, line.strip())
            if m:
                scores['players'][int(m.group('slot'))] = {'kills': int(m.group('kill')),
                                                           'deaths': int(m.group('death'))}

        return scores

    def queryClientUserInfoByCid(self, cid):
        """
        : dumpuser 5
        Player 5 is not on the server

        : dumpuser 3
        userinfo
        --------
        ip                  62.235.246.103:27960
        name                Shinki
        racered             2
        raceblue            2
        rate                8000
        ut_timenudge        0
        cg_rgb              255 0 255
        cg_predictitems     0
        cg_physics          1
        gear                GLJAXUA
        cl_anonymous        0
        sex                 male
        handicap            100
        color2              5
        color1              4
        team_headmodel      *james
        team_model          james
        headmodel           sarge
        model               sarge
        snaps               20
        teamtask            0
        cl_guid             8982B13A8DCEE4C77A32E6AC4DD7EEDF
        weapmodes           00000110220000020002
        """
        data = self.write('dumpuser %s' % cid)
        if not data:
            return None

        if data.split('\n')[0] != "userinfo":
            self.debug("dumpuser %s returned : %s" % (cid, data))
            self.debug('Client %s probably disconnected, but its character is still hanging in game...' % cid)
            return None

        datatransformed = "%s " % cid
        for line in data.split('\n'):
            if line.strip() == "userinfo" or line.strip() == "--------":
                continue

            var = line[:20].strip()
            val = line[20:].strip()
            datatransformed += "\\%s\\%s" % (var, val)

        return datatransformed

    def getByCidOrJoinPlayer(self, cid):
        """
        Return the client matchign the given string.
        Will create a new client if needed
        """
        client = self.clients.getByCID(cid)
        if client:
            return client
        else:
            userinfostring = self.queryClientUserInfoByCid(cid)
            if userinfostring:
                self.OnClientuserinfo(None, userinfostring)
            return self.clients.getByCID(cid)

    def getPlayerTeams(self):
        """
        Return a dict having cid as keys and a B3 team as value for
        as many slots as we can get a team for.

        /rcon players
        Map: ut4_heroic_beta1
        Players: 16
        Scores: R:51 B:92
        0:  FREE k:0 d:0 ping:0
        0:  FREE k:0 d:0 ping:0
        2: Anibal BLUE k:24 d:11 ping:69 90.47.240.44:27960
        3: kasper01 RED k:6 d:28 ping:56 93.22.173.133:27960
        4: notorcan RED k:16 d:10 ping:51 86.206.51.250:27960
        5: laCourge SPECTATOR k:0 d:0 ping:48 81.56.143.41:27960
        6: fundy_kill BLUE k:6 d:9 ping:50 92.129.99.62:27960
        7: brillko BLUE k:25 d:11 ping:56 85.224.201.172:27960
        8: -Tuxmania- BLUE k:16 d:7 ping:48 81.231.39.32:27960
        9: j.i.goe RED k:1 d:4 ping:51 86.218.69.81:27960
        10: EasyRider RED k:10 d:12 ping:53 85.176.137.142:27960
        11: Ferd75 BLUE k:4 d:8 ping:48 90.3.171.84:27960
        12: frag4#Gost0r RED k:11 d:16 ping:74 79.229.27.54:27960
        13: {'OuT'}ToinetoX RED k:6 d:13 ping:67 81.48.189.135:27960
        14: GibsonSG BLUE k:-1 d:2 ping:37 84.60.3.67:27960
        15: Kjeldor BLUE k:16 d:9 ping:80 85.246.3.196:50851

        NOTE: this won't work fully if the server has private slots.
        see http://forums.urbanterror.net/index.php/topic,9356.0.html
        """
        player_teams = {}
        players_data = self.write('players')
        for line in players_data.split('\n')[3:]:
            self.debug(line.strip())
            m = re.match(self._rePlayerScore, line.strip())
            if m and line.strip() != '0:  FREE k:0 d:0 ping:0':
                cid = m.group('slot')
                team = self.getTeam(m.group('team'))
                player_teams[cid] = team

        cvars = self.cvarList("*teamlist")
        g_blueteamlist = cvars.get('g_blueteamlist')
        if g_blueteamlist:
            for letter in g_blueteamlist:
                player_teams[self.letters2slots[letter]] = b3.TEAM_BLUE

        g_redteamlist = cvars.get('g_redteamlist')
        if g_redteamlist:
            for letter in g_redteamlist:
                player_teams[self.letters2slots[letter]] = b3.TEAM_RED
        return player_teams

    def _getDamagePoints(self, weapon, hitloc):
        """
        Provide the estimated number of damage points inflicted by
        a hit of a given weapon to a given body location.
        """
        try:
            points = self.damage[weapon][int(hitloc) - 1]
            self.debug("_getDamagePoints(%s, %s) -> %d" % (weapon, hitloc, points))
            return points
        except (KeyError, IndexError) as err:
            self.warning("_getDamagePoints(%s, %s) cannot find value : %s" % (weapon, hitloc, err))
            return 15

    def _convertHitWeaponToKillWeapon(self, hitweapon_id):
        """
        on Hit: lines identifiers for weapons are different than
        the one on Kill: lines
        """
        try:
            return self.hitweapon2killweapon[int(hitweapon_id)]
        except KeyError as err:
            self.warning("Unknown weapon ID on Hit line: %s", err)
            return None

    def cvarList(self, cvar_filter=None):
        """
        Return a dict having cvar id as keys and strings values.
        If cvar_filter is provided, it will be passed to the rcon cvarlist command as a parameter.

        /rcon cvarlist
            cvarlist
            S R     g_modversion "4.2.009"
            S R     auth_status "public"
            S R     auth "1"
            S       g_enablePrecip "0"
            S R     g_survivor "0"
            S     C g_antilagvis "0"

            6 total cvars
            6 cvar indexes
        """
        cvars = dict()
        cmd = 'cvarlist' if cvar_filter is None else ('cvarlist %s' % cvar_filter)
        raw_data = self.write(cmd)
        if raw_data:
            re_line = re.compile(r"""^.{7} (?P<cvar>\s*\w+)\s+"(?P<value>.*)"$""", re.MULTILINE)
            for m in re_line.finditer(raw_data):
                cvars[m.group('cvar').lower()] = m.group('value')
        return cvars

    def __setup_gamepaths(self):
        cvarlist = self.cvarList("fs_")

        self.game.fs_game = cvarlist.get('fs_game')
        if not self.game.fs_game:
            self.warning("Could not query server for fs_game")
        else:
            self.debug("fs_game: %s" % self.game.fs_game)

        self.game.fs_basepath = cvarlist.get('fs_basepath')
        if not self.game.fs_basepath:
            self.warning("Could not query server for fs_basepath")
        else:
            self.game.fs_basepath = self.game.fs_basepath.rstrip('/')
            self.debug('fs_basepath: %s' % self.game.fs_basepath)

        self.game.fs_homepath = cvarlist.get('fs_homepath')
        if not self.game.fs_homepath:
            self.warning("Could not query server for fs_homepath")
        else:
            self.game.fs_homepath = self.game.fs_homepath.rstrip('/')
            self.debug('fs_homepath: %s' % self.game.fs_homepath)

    def __setup_events(self):
        # add event mappings
        self._eventMap['warmup'] = self.getEventID('EVT_GAME_WARMUP')
        self._eventMap['shutdowngame'] = self.getEventID('EVT_GAME_ROUND_END')
        self._eventMap['hotpotato'] = self.getEventID('EVT_GAME_FLAG_HOTPOTATO')

    def __setup_world_client(self):
        self.clients.newClient('-1', guid='WORLD', name='World', hide=True, pbid='WORLD')

    def __setup_maps(self):
        mapname = self.getMap()
        if mapname:
            self.game.mapName = mapname
            self.info('map is: %s' % self.game.mapName)
        self.getMaps()

    def __setup_log_sync(self):
        self.debug('Forcing server cvar g_logsync to %s' % self._logSync)
        self.setCvar('g_logsync', self._logSync)

    def __setup_connected_players(self):
        player_list = self.getPlayerList()
        for cid in player_list.keys():
            userinfostring = self.queryClientUserInfoByCid(cid)
            if userinfostring:
                self.OnClientuserinfo(None, userinfostring)
        self.__reconcile_connected_player_teams(player_list)

    def __reconcile_connected_player_teams(self, player_list):
        player_teams = dict()
        tries = 0
        while tries < 3:
            try:
                tries += 1
                player_teams = self.getPlayerTeams()
                break
            except Exception as err:
                if tries < 3:
                    self.warning(err)
                else:
                    self.error("Cannot fix players teams: %s" % err)
                    return

        for cid in player_list.keys():
            client = self.clients.getByCID(cid)
            if client and client.cid in player_teams:
                newteam = player_teams[client.cid]
                if newteam != client.team:
                    self.debug('Fixing client team for %s : %s is now %s' % (client.name, client.team, newteam))
                    setattr(client, 'team', newteam)
