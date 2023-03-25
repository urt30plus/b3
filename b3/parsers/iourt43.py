import re
import threading
from collections import Counter

import b3
import b3.clients
import b3.events
import b3.parser
from b3.clients import Client
from b3.functions import getStuffSoundingLike
from b3.functions import prefixText
from b3.functions import start_daemon_thread
from b3.functions import time2minutes

__author__ = "xlr8or, Courgette, Fenix"
__version__ = "4.34"


class Iourt43Parser(b3.parser.Parser):
    """This parser is meant to serve as the new base parser for
    all UrT version from 4.3 on.
    """

    gameName = "iourt43"

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

    _allow_userinfo_overflow = False

    IpsOnly = False
    IpCombi = False

    _maplist = None
    _empty_name_default = "EmptyNameDefault"

    _clientConnectID = None

    _commands = {
        "broadcast": "%(message)s",
        "message": "tell %(cid)s %(message)s",
        "deadsay": "tell %(cid)s %(message)s",
        "say": "say %(message)s",
        "saybig": 'bigtext "%(message)s"',
        "set": 'set %(name)s "%(value)s"',
        "kick": 'kick %(cid)s "%(reason)s"',
        "ban": "addip %(cid)s",
        "tempban": 'kick %(cid)s "%(reason)s"',
        "banByIp": "addip %(ip)s",
        "unbanByIp": "removeip %(ip)s",
        "slap": "slap %(cid)s",
        "nuke": "nuke %(cid)s",
        "mute": "mute %(cid)s %(seconds)s",
        "kill": "smite %(cid)s",
    }

    _eventMap = {
        # 'warmup' : b3.events.EVT_GAME_WARMUP,
        # 'shutdowngame' : b3.events.EVT_GAME_ROUND_END
    }

    _team_map = {
        "red": b3.TEAM_RED,
        "r": b3.TEAM_RED,
        "1": b3.TEAM_RED,
        "blue": b3.TEAM_BLUE,
        "b": b3.TEAM_BLUE,
        "2": b3.TEAM_BLUE,
        "spectator": b3.TEAM_SPEC,
        "spec": b3.TEAM_SPEC,
        "s": b3.TEAM_SPEC,
        "3": b3.TEAM_SPEC,
    }

    _line_length = 90

    _lineFormats = (
        # Hit: 12 7 1 19: BSTHanzo[FR] hit ercan in the Helmet
        # Hit: 13 10 0 8: Grover hit jacobdk92 in the Head
        re.compile(
            r"^(?P<action>Hit):\s"
            r"(?P<data>"
            r"(?P<cid>[0-9]+)\s"
            r"(?P<acid>[0-9]+)\s"
            r"(?P<hitloc>[0-9]+)\s"
            r"(?P<aweap>[0-9]+):\s+"
            r"(?P<text>.*))$"
        ),
        # Item: 4 ut_weapon_glock
        # Item: 0 team_CTF_redflag
        re.compile(r"^(?P<action>Item):\s(?P<data>.*)$"),
        # ClientBegin: 4
        # ClientConnect: 4
        # ClientDisconnect: 4
        # ClientSpawn: 0
        # ClientMelted: 1
        re.compile(
            r"^(?P<action>Client(Begin|Connect|Disconnect|Melted|Spawn)):\s"
            r"(?P<data>"
            r"(?P<cid>[0-9]+))$"
        ),
        # Kill: 0 1 16: XLR8or killed =lvl1=Cheetah by UT_MOD_SPAS
        re.compile(
            r"^(?P<action>Kill):\s"
            r"(?P<data>"
            r"(?P<acid>[0-9]+)\s"
            r"(?P<cid>[0-9]+)\s"
            r"(?P<aweap>[0-9]+):\s+"
            r"(?P<text>.*))$"
        ),
        # ClientUserinfo: 2 \ip\11.181.55.130:27960\snaps\20\name\|30+|money\...
        # ClientUserinfoChanged: 4 n\pibul\t\1\r\1\tl\0\f0\ninja\f1\\f2\\a0\0\a1\0\a2\0
        re.compile(r"^(?P<action>ClientUserinfo(Changed)?):\s" r"(?P<data>.*)$"),
        # Flag: 2 2: team_CTF_blueflag
        re.compile(
            r"^(?P<action>Flag):\s"
            r"(?P<data>"
            r"(?P<cid>[0-9]+)\s"
            r"(?P<name>[^ ]+):\s*"
            r"(?P<text>.*))$"
        ),
        # say: 7 -crespino-:
        # say: 6 ^5Marcel ^2[^6CZARMY^2]: !help
        # sayteam: 9[Rev]BudgetTussle: np
        re.compile(
            r"^(?P<action>(say|sayteam)):\s"
            r"(?P<data>"
            r"(?P<cid>[0-9]+)\s"
            r"(?P<name>[^ ]+):\s*"
            r"(?P<text>.*))$",
            re.IGNORECASE,
        ),
        # Assist: 0 14 15: -[TPF]-PtitBigorneau assisted Bot1 to kill Bot2
        re.compile(
            r"^(?P<action>Assist):\s"
            r"(?P<data>"
            r"(?P<acid>[0-9]+)\s"
            r"(?P<kcid>[0-9]+)\s"
            r"(?P<dcid>[0-9]+):\s+"
            r"(?P<text>.*))$"
        ),
        # Radio: 0 - 7 - 2 - "New Alley" - "I'm going for the flag"
        re.compile(
            r"^(?P<action>Radio): "
            r"(?P<data>"
            r"(?P<cid>[0-9]+) - "
            r"(?P<msg_group>[0-9]+) - "
            r"(?P<msg_id>[0-9]+) - "
            r'"(?P<location>.*)" - '
            r'"(?P<text>.*)")$'
        ),
        # FlagCaptureTime: 0: 1234567890
        # FlagCaptureTime: 1: 1125480101
        re.compile(
            r"^(?P<action>FlagCaptureTime):\s"
            r"(?P<data>"
            r"(?P<cid>[0-9]+):\s"
            r"(?P<captime>[0-9]+))$"
        ),
        # Flag Return: RED
        # Flag Return: BLUE
        re.compile(r"^(?P<action>Flag Return):\s(?P<data>(?P<color>.+))$"),
        # Session data initialised for client on slot 0 at 123456
        re.compile(
            r"^(?P<action>Session data initialised)\s"
            r"(?P<data>for client on slot (?P<slot>\d+)\s"
            r"at (?P<session_id>\d+))"
        ),
        # ShutdownGame:
        # Warmup:
        re.compile(r"^(?P<action>[a-z]+):$", re.IGNORECASE),
        # AccountValidated: 4 - m0neysh0t - -1 - ""
        # InitAuth: \auth\1\auth_status\public\auth_cheaters\1\auth_tags\1\...
        # InitGame: \sv_allowdownload\0\g_matchmode\0\g_gametype\8\...
        # InitRound: \sv_allowdownload\0\g_matchmode\0\g_gametype\7\...
        re.compile(
            r"^(?P<action>(AccountValidated|InitAuth|InitGame|InitRound)):\s"
            r"(?P<data>.*)$"
        ),
        # Bombholder is 2
        re.compile(
            r"^(?P<action>Bombholder)(?P<data>\sis\s(?P<cid>[0-9]+))$", re.IGNORECASE
        ),
        # Bomb was tossed by 2
        # Bomb was planted by 2
        # Bomb was defused by 3!
        # Bomb has been collected by 2
        re.compile(
            r"^(?P<action>Bomb)\s"
            r"(?P<data>(was|has been)\s"
            r"(?P<subaction>[a-z]+)\sby\s"
            r"(?P<cid>[0-9]+).*)$",
            re.IGNORECASE,
        ),
        # Pop!
        re.compile(r"^(?P<action>Pop)!$"),
        # ThawOutStarted: 0 1: Fenix started thawing out Biddle
        # ThawOutFinished: 0 1: Fenix thawed out Biddle
        re.compile(
            r"^(?P<action>ThawOut(Started|Finished)):\s"
            r"(?P<data>"
            r"(?P<cid>[0-9]+)\s"
            r"(?P<tcid>[0-9]+):\s+"
            r"(?P<text>.*))$"
        ),
        # red:12 blue:8
        re.compile(
            r"^(?P<data>((?P<action>red):(?P<score_red>\d+)\s+"
            r"blue:(?P<score_blue>\d+)))$"
        ),
        # Callvote: 1 - "map dressingroom"
        re.compile(
            r'^(?P<action>Callvote): (?P<data>(?P<cid>[0-9]+) - "(?P<vote_string>.*)")$'
        ),
        # Vote: 0 - 2
        re.compile(r"^(?P<action>Vote): (?P<data>(?P<cid>[0-9]+) - (?P<value>.*))$"),
        # VotePassed: 1 - 0 - "reload"
        re.compile(
            r'^(?P<action>VotePassed): (?P<data>(?P<yes>[0-9]+) - (?P<no>[0-9]+) - "(?P<what>.*)")$'
        ),
        # VoteFailed: 1 - 1 - "restart"
        re.compile(
            r'^(?P<action>VoteFailed): (?P<data>(?P<yes>[0-9]+) - (?P<no>[0-9]+) - "(?P<what>.*)")$'
        ),
        # 13:34 ClientJumpRunStarted: 0 - way: 1
        # 13:34 ClientJumpRunStarted: 0 - way: 1 - attempt: 1 of 5
        re.compile(
            r"^(?P<action>ClientJumpRunStarted):\s"
            r"(?P<cid>\d+)\s-\s"
            r"(?P<data>way:\s"
            r"(?P<way_id>\d+)"
            r"(?:\s-\sattempt:\s"
            r"(?P<attempt_num>\d+)\sof\s"
            r"(?P<attempt_max>\d+))?)$"
        ),
        # 13:34 ClientJumpRunStopped: 0 - way: 1 - time: 12345
        # 13:34 ClientJumpRunStopped: 0 - way: 1 - time: 12345 - attempt: 1 of 5
        re.compile(
            r"^(?P<action>ClientJumpRunStopped):\s"
            r"(?P<cid>\d+)\s-\s"
            r"(?P<data>way:\s"
            r"(?P<way_id>\d+)"
            r"\s-\stime:\s"
            r"(?P<way_time>\d+)"
            r"(?:\s-\sattempt:\s"
            r"(?P<attempt_num>\d+)\sof\s"
            r"(?P<attempt_max>\d+"
            r"))?)$"
        ),
        # 13:34 ClientJumpRunCanceled: 0 - way: 1
        # 13:34 ClientJumpRunCanceled: 0 - way: 1 - attempt: 1 of 5
        re.compile(
            r"^(?P<action>ClientJumpRunCanceled):\s"
            r"(?P<cid>\d+)\s-\s"
            r"(?P<data>way:\s"
            r"(?P<way_id>\d+)"
            r"(?:\s-\sattempt:\s"
            r"(?P<attempt_num>\d+)\sof\s"
            r"(?P<attempt_max>\d+))?)$"
        ),
        # 13:34 ClientSavePosition: 0 - 335.384887 - 67.469154 - -23.875000
        # 13:34 ClientLoadPosition: 0 - 335.384887 - 67.469154 - -23.875000
        re.compile(
            r"^(?P<action>Client(Save|Load)Position):\s"
            r"(?P<cid>\d+)\s-\s"
            r"(?P<data>"
            r"(?P<x>-?\d+(?:\.\d+)?)\s-\s"
            r"(?P<y>-?\d+(?:\.\d+)?)\s-\s"
            r"(?P<z>-?\d+(?:\.\d+)?))$"
        ),
        # 13:34 ClientGoto: 0 - 1 - 335.384887 - 67.469154 - -23.875000
        re.compile(
            r"^(?P<action>ClientGoto):\s"
            r"(?P<cid>\d+)\s-\s"
            r"(?P<tcid>\d+)\s-\s"
            r"(?P<data>"
            r"(?P<x>-?\d+(?:\.\d+)?)\s-\s"
            r"(?P<y>-?\d+(?:\.\d+)?)\s-\s"
            r"(?P<z>-?\d+(?:\.\d+)?))$"
        ),
        # 6:37 Kill: 0 1 16: XLR8or killed =lvl1=Cheetah by UT_MOD_SPAS
        # 2:56 Kill: 14 4 21: Qst killed Leftovercrack by UT_MOD_PSG1
        # 6:37 Freeze: 0 1 16: Fenix froze Biddle by UT_MOD_SPAS
        re.compile(
            r"^(?P<action>[a-z]+):\s"
            r"(?P<data>"
            r"(?P<acid>[0-9]+)\s"
            r"(?P<cid>[0-9]+)\s"
            r"(?P<aweap>[0-9]+):\s+"
            r"(?P<text>.*))$",
            re.IGNORECASE,
        ),
        # Processing chats and tell events...
        # 5:39 saytell: 15 16 repelSteeltje: nno
        # 5:39 saytell: 15 15 repelSteeltje: nno
        re.compile(
            r"^(?P<action>[a-z]+):\s"
            r"(?P<data>"
            r"(?P<cid>[0-9]+)\s"
            r"(?P<acid>[0-9]+)\s"
            r"(?P<name>.+?):\s+"
            r"(?P<text>.*))$",
            re.IGNORECASE,
        ),
        # SGT: fix issue with onSay when something like this come and the match could'nt find the name group
        # say: 7 -crespino-:
        # say: 6 ^5Marcel ^2[^6CZARMY^2]: !help
        re.compile(
            r"^(?P<action>[a-z]+):\s"
            r"(?P<data>"
            r"(?P<cid>[0-9]+)\s"
            r"(?P<name>[^ ]+):\s*"
            r"(?P<text>.*))$",
            re.IGNORECASE,
        ),
        # Falling thru? Item stuff and so forth
        re.compile(r"^(?P<action>[a-z]+):\s(?P<data>.*)$", re.IGNORECASE),
    )

    _line_formats_counter = Counter()

    def dump_line_format_counter(self):
        self._line_formats_counter["games"] += 1
        # make sure each line format has an entry
        for i in range(len(self._lineFormats)):
            self._line_formats_counter[i] += 0
        lines = ["Line Format Counts"]
        game_count = 0
        for index, count in self._line_formats_counter.most_common():
            if index == "games":
                game_count = count
                continue
            pattern = self._lineFormats[index].pattern
            lines.append(f"{count:10,}: ({index:2}) {pattern}")
        lines.append(f"Games Played: {game_count}")
        self.info("\n".join(lines))
        if game_count > 50:
            self._line_formats_counter.clear()

    # map: ut4_casa
    # num score ping name            lastmsg address               qport rate
    # --- ----- ---- --------------- ------- --------------------- ----- -----
    #   2     0   19 ^1XLR^78^8^9or        0 145.99.135.227:27960  41893  8000  # player with a live ping
    #   4     0 CNCT Dz!k^7              450 83.175.191.27:64459   50308 20000  # connecting player
    #   9     0 ZMBI ^7                 1900 81.178.80.68:27960    10801  8000  # zombies (need to be disconnected!)
    _regPlayer = re.compile(
        r"^(?P<slot>[0-9]+)\s+"
        r"(?P<score>[0-9-]+)\s+"
        r"(?P<ping>[0-9]+|CNCT|ZMBI)\s+"
        r"(?P<name>.*?)\s+"
        r"(?P<last>[0-9]+)\s+"
        r"(?P<ip>[0-9.]+):(?P<port>[0-9-]+)\s+"
        r"(?P<qport>[0-9]+)\s+"
        r"(?P<rate>[0-9]+)$",
        re.IGNORECASE,
    )

    _reColor = re.compile(r"(\^\d)")

    _rePlayerScore = re.compile(
        r"^(?P<slot>[0-9]+):(?P<name>.*)\s+"
        r"TEAM:(?P<team>RED|BLUE|SPECTATOR|FREE)\s+"
        r"KILLS:(?P<kill>[0-9]+)\s+"
        r"DEATHS:(?P<death>[0-9]+)\s+"
        r"ASSISTS:(?P<assist>[0-9]+)\s+"
        r"PING:(?P<ping>[0-9]+|CNCT|ZMBI)\s+"
        r"AUTH:(?P<auth>.*)\s+IP:(?P<ip>.*)$",
        re.IGNORECASE,
    )

    # /rcon auth-whois replies patterns
    # 'auth: id: 0 - name: ^7Courgette - login: courgette - notoriety: serious - level: -1  \n'
    _re_authwhois = re.compile(
        r"^auth: id: (?P<cid>\d+) - "
        r"name: \^7(?P<name>.+?) - "
        r"login: (?P<login>.*?) - "
        r"notoriety: (?P<notoriety>.+?) - "
        r"level: (?P<level>-?\d+?)(?:\s+- (?P<extra>.*))?\s*$",
        re.MULTILINE,
    )

    _regPlayerShort = re.compile(
        r"\s+(?P<slot>[0-9]+)\s+"
        r"(?P<score>[0-9]+)\s+"
        r"(?P<ping>[0-9]+)\s+"
        r"(?P<name>.*)\^7\s+",
        re.IGNORECASE,
    )

    _reCvarName = re.compile(r"^[a-z0-9_.]+$", re.IGNORECASE)

    _reCvar = (
        # "sv_maxclients" is:"16^7" default:"8^7"
        # latched: "12"
        re.compile(
            r'^"(?P<cvar>[a-z0-9_.]+)"\s+is:\s*'
            r'"(?P<value>.*?)(\^7)?"\s+default:\s*'
            r'"(?P<default>.*?)(\^7)?"$',
            re.IGNORECASE | re.MULTILINE,
        ),
        # "g_maxGameClients" is:"0^7", the default
        # latched: "1"
        re.compile(
            r'^"(?P<cvar>[a-z0-9_.]+)"\s+is:\s*'
            r'"(?P<default>(?P<value>.*?))(\^7)?",\s+the\sdefault$',
            re.IGNORECASE | re.MULTILINE,
        ),
        # "mapname" is:"ut4_abbey^7"
        re.compile(
            r'^"(?P<cvar>[a-z0-9_.]+)"\s+is:\s*"(?P<value>.*?)(\^7)?"$',
            re.IGNORECASE | re.MULTILINE,
        ),
    )

    _reMapNameFromStatus = re.compile(r"^map:\s+(?P<map>.+)$", re.IGNORECASE)

    # kill modes
    MOD_WATER = "1"
    MOD_LAVA = "3"
    MOD_TELEFRAG = "5"
    MOD_FALLING = "6"
    MOD_SUICIDE = "7"
    MOD_TRIGGER_HURT = "9"
    MOD_CHANGE_TEAM = "10"
    UT_MOD_KNIFE = "12"
    UT_MOD_KNIFE_THROWN = "13"
    UT_MOD_BERETTA = "14"
    UT_MOD_DEAGLE = "15"
    UT_MOD_SPAS = "16"
    UT_MOD_UMP45 = "17"
    UT_MOD_MP5K = "18"
    UT_MOD_LR300 = "19"
    UT_MOD_G36 = "20"
    UT_MOD_PSG1 = "21"
    UT_MOD_HK69 = "22"
    UT_MOD_BLED = "23"
    UT_MOD_KICKED = "24"
    UT_MOD_HEGRENADE = "25"
    UT_MOD_SR8 = "28"
    UT_MOD_AK103 = "30"
    UT_MOD_SPLODED = "31"
    UT_MOD_SLAPPED = "32"
    UT_MOD_SMITED = "33"
    UT_MOD_BOMBED = "34"
    UT_MOD_NUKED = "35"
    UT_MOD_NEGEV = "36"
    UT_MOD_HK69_HIT = "37"
    UT_MOD_M4 = "38"
    UT_MOD_GLOCK = "39"
    UT_MOD_COLT1911 = "40"
    UT_MOD_MAC11 = "41"
    UT_MOD_FRF1 = "42"
    UT_MOD_BENELLI = "43"
    UT_MOD_P90 = "44"
    UT_MOD_MAGNUM = "45"
    UT_MOD_TOD50 = "46"
    UT_MOD_FLAG = "47"
    UT_MOD_GOOMBA = "48"

    # HIT LOCATIONS
    HL_HEAD = "1"
    HL_HELMET = "2"
    HL_TORSO = "3"
    HL_VEST = "4"
    HL_ARM_L = "5"
    HL_ARM_R = "6"
    HL_GROIN = "7"
    HL_BUTT = "8"
    HL_LEG_UPPER_L = "9"
    HL_LEG_UPPER_R = "10"
    HL_LEG_LOWER_L = "11"
    HL_LEG_LOWER_R = "12"
    HL_FOOT_L = "13"
    HL_FOOT_R = "14"

    # WORLD CID (used for Mr. Sentry detection)
    WORLD = "1022"

    # weapons id on Hit: lines are different than the one
    # on the Kill: lines. Here the translation table
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
        27: UT_MOD_TOD50,
        29: UT_MOD_KICKED,
        30: UT_MOD_KNIFE_THROWN,
    }

    # damage table
    # Fenix: Hit locations start with index 1 (HL_HEAD).
    #        Since lists are 0 indexed we'll need to adjust the hit location
    #        code to match the index number. Instead of adding random values
    #        in the damage table, the adjustment will be made in _getDamagePoints.
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
        UT_MOD_GOOMBA: [
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
        ],
        UT_MOD_TOD50: [
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
            100,
        ],
        UT_MOD_FRF1: [100, 100, 96, 76, 40, 40, 76, 74, 50, 50, 40, 40, 30, 30],
        UT_MOD_BENELLI: [100, 100, 90, 67, 32, 32, 60, 50, 35, 35, 30, 30, 20, 20],
        UT_MOD_P90: [50, 40, 33, 27, 16, 16, 27, 25, 17, 17, 15, 15, 12, 12],
        UT_MOD_MAGNUM: [100, 82, 66, 50, 33, 33, 57, 52, 40, 33, 25, 25, 20, 20],
    }

    # {"A": "0", "B": "1", "C": "2"...., "Y": "24", "Z": "25"}
    letters2slots = {chr(i): str(i - ord("A")) for i in range(ord("A"), ord("Z") + 1)}

    def startup(self):
        try:
            cvar = self.getCvar("gamename")
            gamename = cvar.getString() if cvar else None
            if not self.is_valid_game(gamename):
                self.critical(
                    "The %s B3 parser cannot be used with a game server other than [%s]"
                    % (self.gameName, gamename)
                )
        except Exception as e:
            self.warning("Could not query server for gamename.", exc_info=e)

        if not self.config.has_option("server", "game_log"):
            self.critical(
                "Your main config file is missing the 'game_log' setting in section 'server'"
            )

        self.__setup_events()
        self.__setup_world_client()
        self.__setup_maps()
        self.__setup_log_sync()
        self.__setup_gamepaths()
        self.load_conf_userinfo_overflow()

    def is_valid_game(self, gamename):
        return gamename == "q3urt43"

    def pluginsStarted(self):
        self.__setup_connected_players()

    def load_conf_userinfo_overflow(self):
        """
        Load userinfo overflow configuration settings.
        """
        self._allow_userinfo_overflow = False
        if self.config.has_option("server", "allow_userinfo_overflow"):
            try:
                self._allow_userinfo_overflow = self.config.getboolean(
                    "server", "allow_userinfo_overflow"
                )
            except ValueError as err:
                self.warning(err)

        self.info(
            "Allow userinfo string overflow : %s"
            % ("yes" if self._allow_userinfo_overflow else "no")
        )

        if self._allow_userinfo_overflow:
            self.info(
                "NOTE: due to a bug in UrT 4.2 gamecode it is possible to exploit the maximum client name length "
                "and generate a userinfo string longer than the imposed limits: clients connecting with nicknames "
                "longer than 32 characters will be automatically kicked by B3 in order to prevent any sort of error"
            )
        else:
            self.info(
                "NOTE: due to a bug in UrT 4.2 gamecode it is possible to exploit the maximum client name length "
                "and generate a userinfo string longer than the imposed limits: B3 will truncate nicknames of clients "
                "which are longer than 32 characters"
            )

    def unpause(self):
        """
        Unpause B3 log parsing.
        """
        self.pluginsStarted()  # so we get teams refreshed
        self.clients.sync()
        super().unpause()

    def getLineParts(self, line):
        """
        Parse a log line returning extracted tokens.
        :param line: The line to be parsed
        """
        line = re.sub(self._lineClear, "", line, 1)
        for index, f in enumerate(self._lineFormats):
            if m := re.match(f, line):
                self._line_formats_counter[index] += 1
                # log lines for the more generalized formats
                if index > 26:
                    self.info("re.match(%s): %s", index, line)
                break
        else:
            if "------" not in line:
                self.warning("Line did not match format: %s", line)
            return None, None, None

        try:
            data = m["data"].strip()
        except:
            data = None

        return m, m["action"].lower(), data

    def parseLine(self, line):
        """
        Parse a log line creating necessary events.
        :param line: The log line to be parsed
        """
        match, action, data = self.getLineParts(line)
        if not match:
            return False

        func_name = f"On{action.title().replace(' ', '')}"

        if func := getattr(self, func_name, None):
            if event := func(action, data, match):
                self.queueEvent(event)
        elif action in self._eventMap:
            self.queueEvent(self.getEvent(self._eventMap[action], data=data))
        else:
            data = str(action) + ": " + str(data)
            self.warning("Unknown Event: %s", data)
            self.queueEvent(self.getEvent("EVT_UNKNOWN", data=data))

        return True

    def OnInitauth(self, action, data, match=None):
        pass

    def OnAccountvalidated(self, action, data, match=None):
        pass

    def OnSessionDataInitialised(self, action, data, match=None):
        pass

    def OnScore(self, action, data, match=None):
        self.info("Score: %s", data)

    def OnRed(self, action, data, match=None):
        self.info("Team Score: %s", data)

    def parseInfoFields(self, info):
        """Parses the back-slash delimited list of fields and returns a dict."""
        # \ip\145.99.135.227:27960\challenge\-232198920\qport\2781\protocol\68\battleye\1\name\[SNT]^1XLR^78or...
        parts = info.lstrip(" \\").split("\\")
        return dict(zip(parts[0::2], parts[1::2]))

    def parseUserInfo(self, info):
        """
        Parse an infostring.
        :param info: The infostring to be parsed.
        """
        # 2 \ip\145.99.135.227:27960\challenge\-232198920\qport\2781\protocol\68\battleye\1\name\[SNT]^1XLR^78or...
        # 7 n\[SNT]^1XLR^78or\t\3\r\2\tl\0\f0\\f1\\f2\\a0\0\a1\0\a2\0
        player_id, info = info.split(" ", 1)
        data = self.parseInfoFields(info)
        data["cid"] = player_id
        return data

    def OnClientconnect(self, action, data, match=None):
        pass

    def OnClientbegin(self, action, data, match=None):
        # we get user info in two parts:
        # 19:42.36 ClientBegin: 4
        if client := self.getByCidOrJoinPlayer(data):
            return self.getEvent("EVT_CLIENT_JOIN", data=data, client=client)

    def OnClientuserinfo(self, action, data, match=None):
        # 2 \ip\145.99.135.227:27960\challenge\-232198920\qport\2781\protocol\68\battleye\1\name\[SNT]^1XLR^78or..
        # 0 \gear\GMIORAA\team\blue\skill\5.000000\characterfile\bots/ut_chicken_c.c\color\4\sex\male\race\2\snaps\20\..
        bclient = self.parseUserInfo(data)

        bot = False
        if "cl_guid" not in bclient and "skill" in bclient:
            # must be a bot connecting
            self.bot("Bot connecting!")
            bclient["ip"] = "0.0.0.0"
            bclient["cl_guid"] = "BOT" + str(bclient["cid"])
            bot = True

        if client_name := bclient.get("name"):
            # remove spaces from name
            bclient["name"] = client_name.replace(" ", "")

        # split port from ip field
        if client_ip := bclient.get("ip"):
            ip, _, port = client_ip.partition(":")
            bclient["ip"] = ip
            if port:
                bclient["port"] = port

        if client_team := bclient.get("team"):
            bclient["team"] = self.getTeam(client_team)

        if client := self.clients.getByCID(bclient["cid"]):
            # update existing client
            excluded_attrs = (
                "login",
                "password",
                "groupBits",
                "maskLevel",
                "autoLogin",
                "greeting",
            )
            for k, v in bclient.items():
                if hasattr(client, "gear") and k == "gear" and client.gear != v:
                    self.queueEvent(self.getEvent("EVT_CLIENT_GEAR_CHANGE", v, client))
                if not k.startswith("_") and k not in excluded_attrs:
                    setattr(client, k, v)
        else:
            # make a new client
            guid = bclient.get("cl_guid", "unknown")

            if client_authl := bclient.get("authl"):
                # authl contains FSA since UrT 4.2.022
                fsa = client_authl
            else:
                # query FrozenSand Account
                auth_info = self.queryClientFrozenSandAccount(bclient["cid"])
                fsa = auth_info.get("login", None)

            # v1.0.17 - mindriot - 02-Nov-2008
            if "name" not in bclient:
                bclient["name"] = self._empty_name_default

            # v 1.10.5 => https://github.com/BigBrotherBot/big-brother-bot/issues/346
            if len(bclient["name"]) > 32:
                self.warning(
                    "UrT4.2 bug spotted! %s [GUID: '%s'] [FSA: '%s'] has a too long "
                    "nickname (%s characters)",
                    bclient["name"],
                    guid,
                    fsa,
                    len(bclient["name"]),
                )
                if self._allow_userinfo_overflow:
                    x = bclient["name"][0:32]
                    self.warning(
                        "Truncating %s (%s) nickname => %s (%s)",
                        bclient["name"],
                        len(bclient["name"]),
                        x,
                        len(x),
                    )
                    bclient["name"] = x
                else:
                    self.warning(
                        "Connection denied to  %s [GUID: '%s'] [FSA: '%s']",
                        bclient["name"],
                        guid,
                        fsa,
                    )
                    self.write(
                        self.getCommand(
                            "kick",
                            cid=bclient["cid"],
                            reason="userinfo string overflow protection",
                        )
                    )
                    return

            if "ip" not in bclient:
                if guid == "unknown":
                    # happens when a client is (temp)banned and got kicked so client was destroyed,
                    # but infoline was still waiting to be parsed.
                    return None
                else:
                    try:
                        # see issue xlr8or/big-brother-bot#87 - ip can be missing
                        plist = self.getPlayerList()
                        client_data = plist[bclient["cid"]]
                        bclient["ip"] = client_data["ip"]
                    except Exception as err:
                        bclient["ip"] = ""
                        self.warning(
                            "Failed to get client %s ip address" % bclient["cid"], err
                        )

            nguid = ""
            # override the guid... use ip's only if self.console.IpsOnly is set True.
            if self.IpsOnly:
                nguid = bclient["ip"]
            # replace last part of the guid with two segments of the ip
            elif self.IpCombi:
                i = bclient["ip"].split(".")
                d = len(i[0]) + len(i[1])
                nguid = guid[:-d] + i[0] + i[1]
            # Quake clients don't have a cl_guid, we'll use ip instead
            elif guid == "unknown":
                nguid = bclient["ip"]

            if nguid != "":
                guid = nguid

            self.clients.newClient(
                bclient["cid"],
                name=bclient["name"],
                ip=bclient["ip"],
                bot=bot,
                guid=guid,
                pbid=fsa,
            )

        return None

    def OnClientuserinfochanged(self, action, data, match=None):
        # 7 n\[SNT]^1XLR^78or\t\3\r\2\tl\0\f0\\f1\\f2\\a0\0\a1\0\a2\0
        parseddata = self.parseUserInfo(data)
        if client := self.clients.getByCID(parseddata["cid"]):
            # update existing client
            if client_name := parseddata.get("n"):
                client.name = client_name

            if client_team := parseddata.get("t"):
                team = self.getTeam(client_team)
                client.team = team

                if client_race := parseddata.get("r"):
                    if team == b3.TEAM_BLUE:
                        client.raceblue = client_race
                    elif team == b3.TEAM_RED:
                        client.racered = client_race
                    elif team == b3.TEAM_FREE:
                        client.racefree = client_race

                fundata = ",".join(
                    filter(
                        None,
                        [
                            parseddata.get("f0"),
                            parseddata.get("f1"),
                            parseddata.get("f2"),
                        ],
                    )
                )
                if fundata:
                    if team == b3.TEAM_BLUE:
                        client.funblue = fundata
                    elif team == b3.TEAM_RED:
                        client.funred = fundata
                    elif team == b3.TEAM_FREE:
                        client.funfree = fundata

            client.cg_rgb = " ".join(
                [
                    parseddata.get("a0", "0"),
                    parseddata.get("a1", "0"),
                    parseddata.get("a2", "0"),
                ]
            )

    def OnRadio(self, action, data, match=None):
        if not (client := self.getByCidOrJoinPlayer(match["cid"])):
            return None
        radio_data = {
            "msg_group": match["msg_group"],
            "msg_id": match["msg_id"],
            "location": match["location"],
            "text": match["text"],
        }
        return self.getEvent("EVT_CLIENT_RADIO", client=client, data=radio_data)

    def OnHit(self, action, data, match=None):
        # Hit: 13 10 0 8: Grover hit jacobdk92 in the Head
        # Hit: cid acid hitloc aweap: text
        if not (victim := self.clients.getByCID(match["cid"])):
            return None

        if not (attacker := self.clients.getByCID(match["acid"])):
            return None

        event = self.getEventID("EVT_CLIENT_DAMAGE")
        if attacker.cid == victim.cid:
            event = self.getEventID("EVT_CLIENT_DAMAGE_SELF")
        elif attacker.team != b3.TEAM_UNKNOWN and attacker.team == victim.team:
            event = self.getEventID("EVT_CLIENT_DAMAGE_TEAM")

        hitloc = match["hitloc"]
        weapon = self._convertHitWeaponToKillWeapon(match["aweap"])
        points = self._getDamagePoints(weapon, hitloc)
        event_data = (points, weapon, hitloc)
        victim.data["lastDamageTaken"] = event_data
        return self.getEvent(event, event_data, attacker, victim)

    def OnCallvote(self, action, data, match=None):
        if not (client := self.getByCidOrJoinPlayer(match["cid"])):
            return None
        return self.getEvent(
            "EVT_CLIENT_CALLVOTE", client=client, data=match["vote_string"]
        )

    def OnVote(self, action, data, match=None):
        if not (client := self.getByCidOrJoinPlayer(match["cid"])):
            return None
        return self.getEvent("EVT_CLIENT_VOTE", client=client, data=match["value"])

    def OnVotepassed(self, action, data, match=None):
        vote_data = {
            "yes": int(match["yes"]),
            "no": int(match["no"]),
            "what": match["what"],
        }
        return self.getEvent("EVT_VOTE_PASSED", data=vote_data)

    def OnVotefailed(self, action, data, match=None):
        vote_data = {
            "yes": int(match["yes"]),
            "no": int(match["no"]),
            "what": match["what"],
        }
        return self.getEvent("EVT_VOTE_FAILED", data=vote_data)

    def OnFlagcapturetime(self, action, data, match=None):
        # FlagCaptureTime: 0: 1234567890
        # FlagCaptureTime: 1: 1125480101
        if not (client := self.getByCidOrJoinPlayer(match["cid"])):
            return None
        return self.getEvent(
            "EVT_FLAG_CAPTURE_TIME", client=client, data=int(match["captime"])
        )

    def OnClientjumprunstarted(self, action, data, match=None):
        if not (client := self.getByCidOrJoinPlayer(match["cid"])):
            return None
        jump_data = {
            "way_id": match["way_id"],
            "attempt_num": match["attempt_num"],
            "attempt_max": match["attempt_max"],
        }
        return self.getEvent("EVT_CLIENT_JUMP_RUN_START", client=client, data=jump_data)

    def OnClientjumprunstopped(self, action, data, match=None):
        if not (client := self.getByCidOrJoinPlayer(match["cid"])):
            return None
        jump_data = {
            "way_id": match["way_id"],
            "way_time": match["way_time"],
            "attempt_num": match["attempt_num"],
            "attempt_max": match["attempt_max"],
        }
        return self.getEvent("EVT_CLIENT_JUMP_RUN_STOP", client=client, data=jump_data)

    def OnClientjumpruncanceled(self, action, data, match=None):
        if not (client := self.getByCidOrJoinPlayer(match["cid"])):
            return None
        jump_data = {
            "way_id": match["way_id"],
            "attempt_num": match["attempt_num"],
            "attempt_max": match["attempt_max"],
        }
        way_id = match["way_id"]
        attempt_num = match["attempt_num"]
        attempt_max = match["attempt_max"]
        return self.getEvent(
            "EVT_CLIENT_JUMP_RUN_CANCEL", client=client, data=jump_data
        )

    def OnClientsaveposition(self, action, data, match=None):
        if not (client := self.getByCidOrJoinPlayer(match["cid"])):
            return None
        position = float(match["x"]), float(match["y"]), float(match["z"])
        return self.getEvent(
            "EVT_CLIENT_POS_SAVE", client=client, data={"position": position}
        )

    def OnClientloadposition(self, action, data, match=None):
        if not (client := self.getByCidOrJoinPlayer(match["cid"])):
            return None
        position = float(match["x"]), float(match["y"]), float(match["z"])
        return self.getEvent(
            "EVT_CLIENT_POS_LOAD", client=client, data={"position": position}
        )

    def OnClientgoto(self, action, data, match=None):
        if not (client := self.getByCidOrJoinPlayer(match["cid"])):
            return None
        tcid = match["tcid"]
        position = float(match["x"]), float(match["y"]), float(match["z"])

        if not (target := self.getByCidOrJoinPlayer(tcid)):
            return None

        return self.getEvent(
            "EVT_CLIENT_GOTO", client=client, target=target, data={"position": position}
        )

    def OnClientspawn(self, action, data, match=None):
        # ClientSpawn: 0
        if not (client := self.getByCidOrJoinPlayer(match["cid"])):
            return None
        client.state = b3.STATE_ALIVE
        return self.getEvent("EVT_CLIENT_SPAWN", client=client)

    def OnClientmelted(self, action, data, match=None):
        # ClientMelted: 0
        if not (client := self.getByCidOrJoinPlayer(match["cid"])):
            return None
        client.state = b3.STATE_ALIVE
        return self.getEvent("EVT_CLIENT_MELTED", client=client)

    def OnSurvivorwinner(self, action, data, match=None):
        # SurvivorWinner: Blue
        # SurvivorWinner: Red
        # SurvivorWinner: 0
        # queue round and in any case (backwards compatibility for plugins)
        self.queueEvent(self.getEvent("EVT_GAME_ROUND_END"))
        if data in ("Blue", "Red"):
            return self.getEvent("EVT_SURVIVOR_WIN", data=data)
        else:
            if not (client := self.getByCidOrJoinPlayer(data)):
                return None
            return self.getEvent("EVT_CLIENT_SURVIVOR_WINNER", client=client)

    def OnFreeze(self, action, data, match=None):
        # 6:37 Freeze: 0 1 16: Fenix froze Biddle by UT_MOD_SPAS
        if not (victim := self.getByCidOrJoinPlayer(match["cid"])):
            return None

        if not (attacker := self.getByCidOrJoinPlayer(match["acid"])):
            return None

        if not (weapon := match["aweap"]):
            return None

        victim.state = b3.STATE_DEAD
        return self.getEvent(
            "EVT_CLIENT_FREEZE", data=weapon, client=attacker, target=victim
        )

    def OnThawoutstarted(self, action, data, match=None):
        # ThawOutStarted: 0 1: Fenix started thawing out Biddle
        if not (client := self.getByCidOrJoinPlayer(match["cid"])):
            return None

        if not (target := self.getByCidOrJoinPlayer(match["tcid"])):
            return None

        return self.getEvent("EVT_CLIENT_THAWOUT_STARTED", client=client, target=target)

    def OnThawoutfinished(self, action, data, match=None):
        # ThawOutFinished: 0 1: Fenix thawed out Biddle
        if not (client := self.getByCidOrJoinPlayer(match["cid"])):
            return None

        if not (target := self.getByCidOrJoinPlayer(match["tcid"])):
            return None

        target.state = b3.STATE_ALIVE
        return self.getEvent(
            "EVT_CLIENT_THAWOUT_FINISHED", client=client, target=target
        )

    def authorizeClients(self):
        """
        For all connected players, fill the client object with properties allowing to find
        the user in the database (usualy guid, ip) and call the
        Client.auth() method.
        """

    def OnKill(self, action, data, match=None):
        if not (victim := self.getByCidOrJoinPlayer(match["cid"])):
            return None

        if not (weapon := match["aweap"]):
            return None

        if weapon in (self.UT_MOD_SLAPPED, self.UT_MOD_NUKED, self.MOD_TELEFRAG):
            attacker = self.clients.getByCID("-1")  # make the attacker 'World'
        elif weapon in (
            self.MOD_WATER,
            self.MOD_LAVA,
            self.MOD_FALLING,
            self.MOD_TRIGGER_HURT,
            self.UT_MOD_BOMBED,
            self.UT_MOD_FLAG,
        ):
            # those kills should be considered suicides
            attacker = victim
        else:
            attacker = self.getByCidOrJoinPlayer(match["acid"])

        if not attacker:
            # handle the case where Mr.Sentry killed a player
            if weapon == self.UT_MOD_BERETTA and match["acid"] == self.WORLD:
                return self.getEvent("EVT_SENTRY_KILL", target=victim)
            else:
                return None

        if not (damagetype := match["text"].split()[-1:][0]):
            return None

        event = self.getEventID("EVT_CLIENT_KILL")

        # fix event for team change and suicides and tk
        if attacker.cid == victim.cid:
            if weapon == self.MOD_CHANGE_TEAM:
                # do not pass a teamchange event here
                # that event is passed shortly after the kill
                return None
            else:
                event = self.getEventID("EVT_CLIENT_SUICIDE")
        elif attacker.team != b3.TEAM_UNKNOWN and attacker.team == victim.team:
            event = self.getEventID("EVT_CLIENT_KILL_TEAM")

        # if not logging damage we need a general hitloc
        last_damage_data = victim.data.pop("lastDamageTaken", (100, weapon, "body"))

        victim.state = b3.STATE_DEAD
        # need to pass some amount of damage for the teamkill plugin - 100 is a kill
        return self.getEvent(
            event,
            (last_damage_data[0], weapon, last_damage_data[2], damagetype),
            attacker,
            victim,
        )

    def OnAssist(self, action, data, match=None):
        # Assist: 0 14 15: -[TPF]-PtitBigorneau assisted Bot1 to kill Bot2
        if not (client := self.getByCidOrJoinPlayer(match["acid"])):
            return None

        if not (victim := self.getByCidOrJoinPlayer(match["dcid"])):
            return None

        if not (attacker := self.getByCidOrJoinPlayer(match["kcid"])):
            return None

        return self.getEvent("EVT_ASSIST", client=client, target=victim, data=attacker)

    def OnClientdisconnect(self, action, data, match=None):
        if client := self.clients.getByCID(data):
            client.disconnect()
        return None

    def OnFlag(self, action, data, match=None):
        # Flag: 1 2: team_CTF_blueflag
        # Flag: <_cid> <_subtype:0/1/2>: <text>
        subtype = int(match["name"])
        if subtype == 0:
            actiontype = "flag_dropped"
        elif subtype == 1:
            actiontype = "flag_returned"
        elif subtype == 2:
            actiontype = "flag_captured"
        else:
            self.error("OnFlag(%s) actiontype unknown", subtype)
            return None
        return self.OnAction(match["cid"], actiontype, match["text"])

    def OnFlagReturn(self, action, data, match=None):
        # Flag Return: RED
        # Flag Return: BLUE
        # Flag Return: <color>
        return self.getEvent("EVT_GAME_FLAG_RETURNED", data=match["color"])

    def OnPop(self, action, data, match=None):
        return self.getEvent("EVT_BOMB_EXPLODED")

    def OnBomb(self, action, data, match=None):
        subaction = match["subaction"]
        if subaction == "planted":
            actiontype = "bomb_planted"
        elif subaction == "defused":
            actiontype = "bomb_defused"
        elif subaction == "tossed":
            actiontype = "bomb_tossed"
        elif subaction == "collected":
            actiontype = "bomb_collected"
        else:
            self.error("OnBomb(%s) actiontype unknown", subaction)
            return None
        return self.OnAction(match["cid"], actiontype, data)

    def OnBombholder(self, action, data, match=None):
        return self.OnAction(match["cid"], "bomb_holder_spawn", data)

    def OnAction(self, cid, actiontype, data, match=None):
        if not (client := self.clients.getByCID(cid)):
            return None
        return self.getEvent("EVT_CLIENT_ACTION", data=actiontype, client=client)

    def OnItem(self, action, data, match=None):
        # Item: 3 ut_item_helmet
        # Item: 0 team_CTF_redflag
        cid, item = data.split(" ", 1)
        if client := self.getByCidOrJoinPlayer(cid):
            # correct flag/bomb-pickups
            if "flag" in item or "bomb" in item:
                return self.OnAction(cid, item, data)
            return self.getEvent("EVT_CLIENT_ITEM_PICKUP", data=item, client=client)
        return None

    def OnSay(self, action, data, match=None):
        # 3:53 say: 8 denzel: lol
        if match is None:
            return

        name = self.stripColors(match["name"])
        client = self.getByCidOrJoinPlayer(match["cid"])

        if not client or client.name != name:
            self.warning(
                "Urban Terror bug spotted: trying to get client by name: %s", name
            )
            client = self.clients.getByName(name)

        if not client:
            return None

        data = match["text"]

        # removal of weird characters
        if data and ord(data[:1]) == 21:
            data = data[1:]

        return self.getEvent("EVT_CLIENT_SAY", data=data, client=client)

    def OnSayteam(self, action, data, match=None):
        # 2:28 sayteam: 12 New_UrT_Player_v4.1: wokele
        if match is None:
            return

        name = self.stripColors(match["name"])
        client = self.getByCidOrJoinPlayer(match["cid"])

        if not client or client.name != name:
            self.warning(
                "Urban Terror bug spotted: trying to get client by name: %s", name
            )
            client = self.clients.getByName(name)

        if not client:
            return None

        data = match["text"]
        if data and ord(data[:1]) == 21:
            data = data[1:]

        return self.getEvent(
            "EVT_CLIENT_TEAM_SAY", data=data, client=client, target=client.team
        )

    def OnSaytell(self, action, data, match=None):
        # 5:39 saytell: 15 16 repelSteeltje: nno
        # 5:39 saytell: 15 15 repelSteeltje: nno
        if match is None:
            return

        name = self.stripColors(match["name"])
        client = self.getByCidOrJoinPlayer(match["cid"])
        target = self.clients.getByCID(match["acid"])

        if not client or client.name != name:
            self.warning(
                "Urban Terror bug spotted: trying to get client by name: %s", name
            )
            client = self.clients.getByName(name)

        if not client:
            return None

        data = match["text"]
        if data and ord(data[:1]) == 21:
            data = data[1:]

        return self.getEvent(
            "EVT_CLIENT_PRIVATE_SAY", data=data, client=client, target=target
        )

    def OnTell(self, action, data, match=None):
        return None

    def OnShutdowngame(self, action, data=None, match=None):
        self.game.mapEnd()
        self.dump_line_format_counter()
        return self.getEvent("EVT_GAME_EXIT", data=data)

    def OnInitgame(self, action, data, match=None, round_start=False):
        game = self.game
        for k, v in self.parseInfoFields(data).items():
            if k == "mapname":
                game.mapName = v
            elif k == "g_gametype":
                game.gameType = self.defineGameType(v)
            elif k == "fs_game":
                game.modName = v
            elif k == "capturelimit":
                game.captureLimit = v
            elif k == "fraglimit":
                game.fragLimit = v
            elif k == "timelimit":
                game.timeLimit = v
            else:
                setattr(game, k, v)

        game.startMap()
        game.rounds = 0
        start_daemon_thread(target=self.clients.sync, name="iourt43-sync")
        if not round_start:
            self.info(
                "Game Start: map [%s], game_type [%s]", game.mapName, game.gameType
            )
        return self.getEvent("EVT_GAME_ROUND_START", data=game)

    def OnWarmup(self, action, data=None, match=None):
        self.game.rounds = 0
        return self.getEvent("EVT_GAME_WARMUP", data=data)

    def OnInitround(self, action, data, match=None):
        return self.OnInitgame(action, data, match, round_start=True)

    def broadcast(self, text):
        """
        A Say variant in UrT which will print text upper left, server message area.
        :param text: The message to be sent.
        """
        self.message(None, text, cmd="broadcast")

    def saybig(self, text, *args):
        """
        Print a message in the center screen.
        :param text: The message to be sent.
        """
        self.message(None, text, *args, cmd="saybig")

    def ban(self, client, reason="", admin=None, silent=False, *kwargs):
        """
        Ban a given client.
        :param client: The client to ban
        :param reason: The reason for this ban
        :param admin: The admin who performed the ban
        :param silent: Whether or not to announce this ban
        """
        self.info("BAN : client: %s, reason: %s", client, reason)
        if isinstance(client, Client) and not client.guid:
            # client has no guid, kick instead
            return self.kick(client, reason, admin, silent)
        elif isinstance(client, str) and re.match("^[0-9]+$", client):
            self.write(self.getCommand("ban", cid=client, reason=reason))
            return
        elif not client.id:
            # no client id, database must be down, do tempban
            self.error(
                "Q3AParser.ban(): no client id, database must be down, doing tempban"
            )
            return self.tempban(client, reason, 1440, admin, silent)

        if admin:
            variables = self.getMessageVariables(
                client=client, reason=reason, admin=admin
            )
            fullreason = self.getMessage("banned_by", variables)
        else:
            variables = self.getMessageVariables(client=client, reason=reason)
            fullreason = self.getMessage("banned", variables)

        if client.cid is None:
            # ban by ip, this happens when we !permban @xx a player that is not connected
            self.info(
                "EFFECTIVE BAN : %s",
                self.getCommand("banByIp", ip=client.ip, reason=reason),
            )
            self.write(self.getCommand("banByIp", ip=client.ip, reason=reason))
        else:
            # ban by cid
            self.info(
                "EFFECTIVE BAN : %s",
                self.getCommand("ban", cid=client.cid, reason=reason),
            )

            if client.connected:
                cmd = self.getCommand("ban", cid=client.cid, reason=reason)
                self.info("Sending ban to server : %s" % cmd)
                rv = self.write(cmd)
                if rv:
                    self.info(rv)

        if not silent and fullreason != "":
            self.say(fullreason)

        if admin:
            admin.message(
                "^7Banned^7: ^1%s^7 (^2@%s^7)" % (client.exactName, client.id)
            )
            admin.message(
                "^7His last ip (^1%s^7) has been added to banlist" % client.ip
            )

        self.queueEvent(
            self.getEvent(
                "EVT_CLIENT_BAN", data={"reason": reason, "admin": admin}, client=client
            )
        )
        client.disconnect()

    def tempban(self, client, reason="", duration=2, admin=None, silent=False, *kwargs):
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
        elif isinstance(client, str) and re.match("^[0-9]+$", client):
            self.write(self.getCommand("tempban", cid=client, reason=reason))
            return
        elif admin:
            banduration = b3.functions.minutesStr(duration)
            variables = self.getMessageVariables(
                client=client, reason=reason, admin=admin, banduration=banduration
            )
            fullreason = self.getMessage("temp_banned_by", variables)
        else:
            banduration = b3.functions.minutesStr(duration)
            variables = self.getMessageVariables(
                client=client, reason=reason, banduration=banduration
            )
            fullreason = self.getMessage("temp_banned", variables)

        if client.connected:
            cmd = self.getCommand("tempban", cid=client.cid, reason=reason)
            self.info("Sending ban to server : %s" % cmd)
            rv = self.write(cmd)
            if rv:
                self.info(rv)

        if not silent and fullreason != "":
            self.say(fullreason)

        self.queueEvent(
            self.getEvent(
                "EVT_CLIENT_BAN_TEMP",
                data={"reason": reason, "duration": duration, "admin": admin},
                client=client,
            )
        )
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
        if not (data := self.write(f"auth-whois {cid}")):
            self.warning("queryClientFrozenSandAccount: auth-whois failed for %s", cid)
            return {}

        if data == f"Client {cid} is not active.":
            self.warning("queryClientFrozenSandAccount: %s is not active", cid)
            return {}

        if m := self._re_authwhois.match(data):
            return m.groupdict()
        else:
            self.warning("queryClientFrozenSandAccount: auth-whois no match: %s", data)
            return {}

    def defineGameType(self, gametype_int):
        gametype = str(gametype_int)
        return self.game_types.get(gametype, gametype)

    def unban(self, client, reason="", admin=None, silent=False, *kwargs):
        """
        Unban a client.
        :param client: The client to unban
        :param reason: The reason for the unban
        :param admin: The admin who unbanned this client
        :param silent: Whether or not to announce this unban
        """
        self.info(
            "EFFECTIVE UNBAN : %s",
            self.getCommand("unbanByIp", ip=client.ip, reason=reason),
        )
        cmd = self.getCommand("unbanByIp", ip=client.ip, reason=reason)
        # UrT adds multiple instances to banlist.txt
        # Make sure we remove up to 5 duplicates in a separate thread
        self.writelines([cmd, cmd, cmd, cmd, cmd])
        if admin:
            admin.message(
                "^7Unbanned^7: ^1%s^7 (^2@%s^7)" % (client.exactName, client.id)
            )
            admin.message(
                "^7His last ip (^1%s^7) has been removed from banlist" % client.ip
            )
            admin.message("^7Trying to remove duplicates...")

        self.queueEvent(self.getEvent("EVT_CLIENT_UNBAN", data=admin, client=client))

    def getPlayerPings(self, filter_client_ids=None):
        """
        Returns a dict having players' id for keys and players' ping for values.
        :param filter_client_ids: If filter_client_id is an iterable, only return values for the given client ids.
        """
        if not (data := self.write("status")):
            self.warning("getPlayerPings: rcon status response empty")
            return {}

        players = {}
        for line in data.splitlines():
            if m := re.match(self._regPlayer, line.strip()):
                if m["ping"] == "ZMBI":
                    # ignore them, let them not bother us with errors
                    pass
                else:
                    try:
                        players[str(m["slot"])] = int(m["ping"])
                    except ValueError:
                        players[str(m["slot"])] = 999

        return players

    def sync(self):
        """
        For all connected players returned by self.get_player_list(), get the matching Client
        object from self.clients (with self.clients.getByCID(cid) or similar methods) and
        look for inconsistencies. If required call the client.disconnect() method to remove
        a client from self.clients.
        """
        plist = self.getPlayerList(maxRetries=4)
        mlist = dict()

        for cid, c in plist.items():
            if client := self.getByCidOrJoinPlayer(cid):
                # Disconnect the zombies first
                if c["ping"] == "ZMBI":
                    pass
                elif client.guid and "guid" in c:
                    if client.guid == c["guid"]:
                        # player matches
                        mlist[str(cid)] = client
                    else:
                        client.disconnect()
                elif client.ip and "ip" in c:
                    if client.ip == c["ip"]:
                        # player matches
                        mlist[str(cid)] = client
                    else:
                        client.disconnect()

        return mlist

    def rotateMap(self):
        """
        Load the next map/level.
        """
        self.say("^7Changing to next map")
        threading.Timer(1.0, self.write, ("cyclemap",)).start()

    def changeMap(self, map_name):
        """
        Load a given map/level.
        """
        rv = self.getMapsSoundingLike(map_name)
        if isinstance(rv, str):
            self.say(f"^7Changing map to {rv}")
            threading.Timer(1.0, self.write, (f"map {rv}",)).start()
        else:
            return rv

    def getMaps(self):
        """
        Return the available maps/levels name.
        """
        if self._maplist is not None:
            return self._maplist

        if not (data := self.write("fdir *.bsp", socketTimeout=1.5)):
            return []

        mapregex = re.compile(r"^maps/(?P<map>.+)\.bsp$", re.I)
        maps = []
        for line in data.splitlines():
            if m := re.match(mapregex, line.strip()):
                maps.append(m["map"])

        self._maplist = maps
        self.info(f"getMaps() cached {len(maps)} maps")
        return maps

    def inflictCustomPenalty(
        self, penalty_type, client, reason=None, duration=None, admin=None, data=None
    ):
        """
        Urban Terror specific punishments.
        """
        if penalty_type == "slap" and client:
            cmd = self.getCommand("slap", cid=client.cid)
            self.write(cmd)
            if reason:
                client.message("%s" % reason)
            return True

        elif penalty_type == "nuke" and client:
            cmd = self.getCommand("nuke", cid=client.cid)
            self.write(cmd)
            if reason:
                client.message("%s" % reason)
            return True

        elif penalty_type == "mute" and client:
            if duration is None:
                seconds = 60
            else:
                seconds = round(float(time2minutes(duration) * 60), 0)

            # make sure to unmute first
            cmd = self.getCommand("mute", cid=client.cid, seconds=0)
            self.write(cmd)
            # then mute
            cmd = self.getCommand("mute", cid=client.cid, seconds=seconds)
            self.write(cmd)
            if reason:
                client.message("%s" % reason)
            return True

        elif penalty_type == "kill" and client:
            cmd = self.getCommand("kill", cid=client.cid)
            self.write(cmd)
            if reason:
                client.message("%s" % reason)
            return True

    def getTeam(self, team):
        """
        Return a B3 team given the team value.
        :param team: The team value
        """
        return self._team_map.get(str(team).lower(), b3.TEAM_UNKNOWN)

    def getNextMap(self):
        """
        Return the next map/level name to be played.
        """
        cvars = self.cvarList("g_next")
        # let's first check if a vote passed for the next map
        nmap = cvars.get("g_nextmap")
        if nmap != "":
            return nmap

        nmap = cvars.get("g_nextcyclemap")
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

        cleaned_supported_maps = {
            re.sub(r"^ut(4|43)?_", "", map_name, count=1): map_name
            for map_name in supported_maps
        }

        cleaned_wanted_map = re.sub(r"^ut(4|43)?_", "", wanted_map, count=1)
        if match := cleaned_supported_maps.get(cleaned_wanted_map):
            return match

        matches = [
            cleaned_supported_maps[match]
            for match in getStuffSoundingLike(
                cleaned_wanted_map, list(cleaned_supported_maps.keys())
            )
        ]
        if len(matches) == 1:
            # one match, get the map id
            return matches[0]
        else:
            # multiple matches, provide suggestions
            return matches

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
        if not (data := self.write("dumpuser %s" % cid)):
            self.warning("queryClientUserInfoByCid: rcon dumpuser %s no response", cid)
            return None

        lines = data.splitlines()

        if lines[0] != "userinfo":
            return None

        datatransformed = f"{cid} "
        for line in lines:
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
        if client := self.clients.getByCID(cid):
            return client
        else:
            if userinfostring := self.queryClientUserInfoByCid(cid):
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
        players_data = self.write("players")
        for line in players_data.splitlines()[3:]:
            m = re.match(self._rePlayerScore, line.strip())
            if m and line.strip() != "0:  FREE k:0 d:0 ping:0":
                cid = m["slot"]
                team = self.getTeam(m["team"])
                player_teams[cid] = team

        cvars = self.cvarList("*teamlist")
        g_blueteamlist = cvars.get("g_blueteamlist")
        if g_blueteamlist:
            for letter in g_blueteamlist:
                player_teams[self.letters2slots[letter]] = b3.TEAM_BLUE

        g_redteamlist = cvars.get("g_redteamlist")
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
            return self.damage[weapon][int(hitloc) - 1]
        except (KeyError, IndexError) as err:
            self.warning(
                "_getDamagePoints(%s, %s) cannot find value : %s"
                % (weapon, hitloc, err)
            )
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
        cmd = "cvarlist" if cvar_filter is None else ("cvarlist %s" % cvar_filter)
        if raw_data := self.write(cmd):
            re_line = re.compile(
                r"""^.{7} (?P<cvar>\s*\w+)\s+"(?P<value>.*)"$""", re.MULTILINE
            )
            for m in re_line.finditer(raw_data):
                cvars[m["cvar"].lower()] = m["value"]
        return cvars

    def __setup_gamepaths(self):
        cvarlist = self.cvarList("fs_")

        self.game.fs_game = cvarlist.get("fs_game")
        if not self.game.fs_game:
            self.warning("Could not query server for fs_game")
        else:
            self.info("fs_game: %s" % self.game.fs_game)

        self.game.fs_basepath = cvarlist.get("fs_basepath")
        if not self.game.fs_basepath:
            self.warning("Could not query server for fs_basepath")
        else:
            self.game.fs_basepath = self.game.fs_basepath.rstrip("/")
            self.info("fs_basepath: %s" % self.game.fs_basepath)

        self.game.fs_homepath = cvarlist.get("fs_homepath")
        if not self.game.fs_homepath:
            self.warning("Could not query server for fs_homepath")
        else:
            self.game.fs_homepath = self.game.fs_homepath.rstrip("/")
            self.info("fs_homepath: %s" % self.game.fs_homepath)

    def __setup_events(self):
        # add event mappings
        self._eventMap["warmup"] = self.getEventID("EVT_GAME_WARMUP")
        self._eventMap["shutdowngame"] = self.getEventID("EVT_GAME_ROUND_END")
        self._eventMap["hotpotato"] = self.getEventID("EVT_GAME_FLAG_HOTPOTATO")

    def __setup_world_client(self):
        self.clients.newClient(
            "-1", guid="WORLD", name="World", hide=True, pbid="WORLD"
        )

    def __setup_maps(self):
        if mapname := self.getMap():
            self.game.mapName = mapname
            self.info("map is: %s" % self.game.mapName)
        self.getMaps()

    def __setup_log_sync(self):
        self.info("Forcing server cvar g_logsync to %s" % self._logSync)
        self.setCvar("g_logsync", self._logSync)

    def __setup_connected_players(self):
        player_list = self.getPlayerList()
        for cid in player_list.keys():
            if userinfostring := self.queryClientUserInfoByCid(cid):
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
                    setattr(client, "team", newteam)

    def getPlayerScores(self):
        """
        Returns a dict having players' id for keys and players' scores for values.
        """
        if not (data := self.write("status")):
            self.warning("getPlayerScores: rcon status no response")
            return {}

        players = {}
        for line in data.splitlines():
            if not (m := re.match(self._regPlayerShort, line)):
                m = re.match(self._regPlayer, line.strip())

            if m:
                players[str(m["slot"])] = int(m["score"])

        return players

    def getPlayerList(self, maxRetries=None):
        """
        Query the game server for connected players.
        Return a dict having players' id for keys and players' data as another dict for values.
        """
        if not (data := self.write("status", maxRetries=maxRetries)):
            self.warning("getPlayerList: rcon status no response")
            return {}

        players = {}
        lastslot = -1
        for line in data.splitlines()[3:]:
            if m := re.match(self._regPlayer, line.strip()):
                d = m.groupdict()
                if int(m["slot"]) > lastslot:
                    lastslot = int(m["slot"])
                    d["pbid"] = None
                    players[str(m["slot"])] = d

        return players

    def getCvar(self, cvar_name):
        """
        Return a CVAR from the server.
        :param cvar_name: The CVAR name.
        """
        if self._reCvarName.match(cvar_name):
            val = self.write(cvar_name)

            for f in self._reCvar:
                if m := re.match(f, val):
                    break
            else:
                return None

            if m["cvar"].lower() == cvar_name.lower():
                try:
                    default_value = m["default"]
                except IndexError:
                    default_value = None
                return b3.clients.Cvar(
                    m["cvar"], value=m["value"], default=default_value
                )

    def setCvar(self, cvar_name, value):
        """
        Set a CVAR on the server.
        :param cvar_name: The CVAR name
        :param value: The CVAR value
        """
        if re.match("^[a-z0-9_.]+$", cvar_name, re.IGNORECASE):
            self.write(self.getCommand("set", name=cvar_name, value=value))
        else:
            self.error("%s is not a valid cvar name", cvar_name)

    def set(self, cvar_name, value):
        """
        Set a CVAR on the server.
        :param cvar_name: The CVAR name
        :param value: The CVAR value
        """
        self.warning("Use of deprecated method: set(): please use: setCvar()")
        self.setCvar(cvar_name, value)

    def getMap(self):
        """
        Return the current map/level name.
        """
        if not (data := self.write("status")):
            self.warning("getMap: rcon status no response")
            return None

        line = data.splitlines()[0]
        if m := re.match(self._reMapNameFromStatus, line.strip()):
            return str(m["map"])

        return None

    def OnExit(self, action, data, match=None):
        self.game.mapEnd()
        return self.getEvent("EVT_GAME_EXIT", None)

    def OnUserinfo(self, action, data, match=None):
        _id = self._clientConnectID
        self._clientConnectID = None

        if not _id:
            self.error("OnUserinfo called without a ClientConnect ID")
            return None

        return self.OnClientuserinfo(action, "%s %s" % (_id, data), match)

    def getClient(self, match=None, attacker=None, victim=None):
        """
        Get a client object using the best available data.
        :param match: The match group extracted from the log line parsing
        :param attacker: The attacker group extracted from the log line parsing
        :param victim: The victim group extracted from the log line parsing
        """
        if attacker:
            return self.clients.getByCID(attacker["acid"])
        elif victim:
            return self.clients.getByCID(victim["cid"])
        elif match:
            return self.clients.getByCID(match["cid"])

    def message(self, client, text, *args, cmd="message"):
        """
        Send a private message to a client.
        :param client: The client to who send the message.
        :param text: The message to be sent.
        """
        kwargs = {}
        if client:
            if client.cid is None:
                return
            kwargs["cid"] = client.cid
            prefixes = [self.msgPrefix, self.pmPrefix]
        else:
            prefixes = [self.msgPrefix]

        message = prefixText(prefixes, text).strip()
        lines = [
            self.getCommand(cmd, message=line, **kwargs)
            for line in self.getWrap(message)
        ]
        self.writelines(lines)

    def say(self, text, *args):
        """
        Broadcast a message to all players.
        :param text: The message to be broadcasted
        """
        self.message(None, text, *args, cmd="say")

    def kick(self, client, reason="", admin=None, silent=False, *kwargs):
        """
        Kick a given client.
        :param client: The client to kick
        :param reason: The reason for this kick
        :param admin: The admin who performed the kick
        :param silent: Whether or not to announce this kick
        """
        if isinstance(client, str) and re.match("^[0-9]+$", client):
            self.write(self.getCommand("kick", cid=client, reason=reason))
            return

        self.write(self.getCommand("kick", cid=client.cid, reason=reason))

        if admin:
            variables = self.getMessageVariables(
                client=client, reason=reason, admin=admin
            )
            fullreason = self.getMessage("kicked_by", variables)
        else:
            variables = self.getMessageVariables(client=client, reason=reason)
            fullreason = self.getMessage("kicked", variables)

        if not silent and fullreason != "":
            self.say(fullreason)

        self.queueEvent(
            self.getEvent("EVT_CLIENT_KICK", {"reason": reason, "admin": admin}, client)
        )
        client.disconnect()
