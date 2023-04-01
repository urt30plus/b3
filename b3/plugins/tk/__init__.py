import contextlib
import re
import threading
import time

import b3
import b3.cron
import b3.events
import b3.plugin
from b3.config import NoOptionError

__version__ = "1.5"
__author__ = "ThorN, mindriot, Courgette, xlr8or, SGT, 82ndab-Bravo17, ozon, Fenix"


class TkInfo:
    def __init__(self, plugin, cid):
        self._attackers = {}
        self._attacked = {}
        self._warnings = {}
        self._last_attacker = None
        self._grudged = []
        self.plugin = plugin
        self.cid = cid
        self.lastwarntime = 0

    @property
    def attackers(self):
        return self._attackers

    @property
    def attacked(self):
        return self._attacked

    def forgive(self, cid):
        if (points := self._attackers.pop(cid, -1)) == -1:
            return 0

        if self._last_attacker == cid:
            self._last_attacker = None

        if cid in self._grudged:
            self._grudged = [g for g in self._grudged if g != cid]

        return points

    def warn(self, cid, warning):
        self._warnings[cid] = warning

    def forgiven(self, cid):
        with contextlib.suppress(KeyError):
            del self._attacked[cid]

        if w := self._warnings.pop(cid, None):
            w.inactive = 1
            w.save(self.plugin.console)
            del w

    def damage(self, cid, points):
        self._attacked[cid] = True

    def damaged(self, cid, points):
        try:
            self._attackers[cid] += points
        except KeyError:
            self._attackers[cid] = points
        self._last_attacker = cid

    @property
    def last_attacker(self):
        return self._last_attacker

    def grudge(self, cid):
        if cid not in self._grudged:
            self._grudged.append(cid)

    def is_grudged(self, cid):
        return cid in self._grudged

    def attacker_points(self, cid):
        return self._attackers.get(cid, 0)

    @property
    def points(self):
        points = 0
        if self._attacked:
            for cid, _bol in self._attacked.items():
                try:
                    client = self.plugin.console.clients.getByCID(cid)
                    points += self.plugin.client_tkinfo(client).attacker_points(
                        self.cid
                    )
                except Exception as exc:
                    self.plugin.console.warning(
                        "failed to get points for %s: %r", cid, exc
                    )
        return points


class TkPlugin(b3.plugin.Plugin):
    loadAfterPlugins = ["spawnkill"]

    def __init__(self, console, config=None):
        """
        Object constructor.
        :param console: The console instance
        :param config: The plugin configuration
        """
        super().__init__(console, config)

        # game types that have no team based game play and for which there should be no tk detected
        self._ffa = ["dm", "ffa", "syc-ffa", "lms", "gungame"]

        self._default_messages = {
            "ban": "^7team damage over limit",
            "forgive": "^7$vname^7 has forgiven $aname [^3$points^7]",
            "grudged": "^7$vname^7 has a ^1grudge ^7against $aname [^3$points^7]",
            "forgive_many": "^7$vname^7 has forgiven $attackers",
            "forgive_warning": "^1ALERT^7: $name^7 auto-kick if not forgiven. Type ^3!forgive $cid ^7to forgive. [^3damage: $points^7]",
            "no_forgive": "^7no one to forgive",
            "players": "^7Forgive who? %s",
            "forgive_info": "^7$name^7 has ^3$points^7 TK points",
            "forgive_clear": "^7$name^7 cleared of ^3$points^7 TK points",
            "tk_warning_reason": "^3Do not attack teammates, ^1Attacked: ^7$vname ^7[^3$points^7]",
            "tk_request_action": "^7type ^3!fp ^7 to forgive ^3%s",
        }

        # settings
        self._max_points = 400
        self._levels = {
            0: (2.0, 1.0, 2),
            1: (2.0, 1.0, 2),
            2: (1.0, 0.5, 1),
            20: (1.0, 0.5, 0),
            40: (0.75, 0.5, 0),
        }

        self._max_level = 40
        self._round_grace = 7
        self._issue_warning = "sfire"
        self._grudge_enable = True
        self._grudge_level = 0
        self._private_messages = True
        self._damage_threshold = 100
        self._warn_level = 2
        self._tk_points_halflife = 0
        self._crontab_tkhalflife = None
        self._tk_warn_duration = "1h"

    def onLoadConfig(self):
        """
        Load plugin configuration.
        """
        self._issue_warning = self.getSetting(
            "settings", "issue_warning", b3.STR, self._issue_warning
        )
        self._round_grace = self.getSetting(
            "settings", "round_grace", b3.INT, self._round_grace
        )
        self._max_points = self.getSetting(
            "settings", "max_points", b3.INT, self._max_points
        )
        self._private_messages = self.getSetting(
            "settings", "private_messages", b3.BOOL, self._private_messages
        )
        self._damage_threshold = self.getSetting(
            "settings", "damage_threshold", b3.INT, self._damage_threshold
        )
        self._tk_warn_duration = self.getSetting(
            "settings", "warn_duration", b3.STR, self._tk_warn_duration
        )
        self._warn_level = self.getSetting(
            "settings", "warn_level", b3.INT, self._warn_level
        )
        self._tk_points_halflife = self.getSetting(
            "settings", "halflife", b3.INT, self._tk_points_halflife
        )
        self._grudge_enable = self.getSetting(
            "settings", "grudge_enable", b3.BOOL, self._grudge_enable
        )
        self._grudge_level = self.getSetting(
            "settings", "grudge_level", b3.INT, self._grudge_level
        )

        try:
            self._levels = self.load_config_for_levels()
            self.debug("loaded levels: %s" % ",".join(map(str, self._levels.keys())))
        except NoOptionError:
            self.warning(
                "could not find levels in config file, "
                "using default: %s" % ",".join(map(str, self._levels.keys()))
            )
        except ValueError as e:
            self.error("could not load levels from config value: %s" % e)
            self.debug(
                "using default levels: %s" % ",".join(map(str, self._levels.keys()))
            )

        self._max_level = max(self._levels.keys())
        self.debug("teamkill max level is %s", self._max_level)

    def load_config_for_levels(self):
        """
        Load teamkill configuration values for levels
        """
        levels_data = {}
        is_valid = True

        levels = []
        raw_levels = self.config.get("settings", "levels").split(",")

        def level_section_name(level):
            """
            find config level section based on level as a group keyword or level.

            :return None if section not found, or the section name
            """
            if f"level_{level}" in self.config.sections():
                return f"level_{level}"
            elif f"level_{self.console.getGroupLevel(level)}" in self.config.sections():
                return f"level_{self.console.getGroupLevel(level)}"

        for lev in raw_levels:
            # check the level number is valid
            try:
                level_number = int(self.console.getGroupLevel(lev))
                levels.append(level_number)
            except KeyError:
                self.error("%r is not a valid level" % lev)
                is_valid = False
                continue

            # check if we have a config section named after this level
            section_name = level_section_name(lev)
            if section_name is None:
                self.error(
                    "section %r is missing from the config file" % ("level_%s" % lev)
                )
                is_valid = False
                continue

            # init to remove warnings
            kill_multiplier = 0
            damage_multiplier = 0
            ban_length = 0

            try:
                kill_multiplier = self.config.getfloat(section_name, "kill_multiplier")
            except NoOptionError:
                self.error(
                    "option kill_multiplier is missing in section %s" % section_name
                )
                is_valid = False
            except ValueError as err:
                self.error("value for kill_multiplier is invalid. %s" % err)
                is_valid = False

            try:
                damage_multiplier = self.config.getfloat(
                    section_name, "damage_multiplier"
                )
            except NoOptionError:
                self.error(
                    "option damage_multiplier is missing in section %s" % section_name
                )
                is_valid = False
            except ValueError as err:
                self.error("value for damage_multiplier is invalid. %s" % err)
                is_valid = False

            try:
                ban_length = self.config.getint(section_name, "ban_length")
            except NoOptionError:
                self.error("option ban_length is missing in section %s" % section_name)
                is_valid = False
            except ValueError as err:
                self.error("value for ban_length is invalid. %s" % err)
                is_valid = False

            if is_valid:
                levels_data[level_number] = (
                    kill_multiplier,
                    damage_multiplier,
                    ban_length,
                )

        if not is_valid:
            raise ValueError

        return levels_data

    def onStartup(self):
        """
        Plugin startup
        """
        # register events needed
        self.registerEvent("EVT_CLIENT_DAMAGE_TEAM")
        self.registerEvent("EVT_CLIENT_KILL_TEAM")
        self.registerEvent("EVT_CLIENT_DISCONNECT")
        self.registerEvent("EVT_GAME_EXIT")
        self.registerEvent("EVT_GAME_ROUND_END")
        self.registerEvent("EVT_GAME_ROUND_START")

        self.admin_plugin.registerCommand(self, "forgive", 0, self.cmd_forgive, "f")
        self.admin_plugin.registerCommand(
            self, "forgivelist", 0, self.cmd_forgivelist, "fl"
        )
        self.admin_plugin.registerCommand(
            self, "forgiveall", 0, self.cmd_forgiveall, "fa"
        )
        self.admin_plugin.registerCommand(
            self, "forgiveinfo", 20, self.cmd_forgiveinfo, "fi"
        )
        self.admin_plugin.registerCommand(
            self, "forgiveclear", 60, self.cmd_forgiveclear, "fc"
        )
        self.admin_plugin.registerCommand(
            self, "forgiveprev", 0, self.cmd_forgivelast, "fp"
        )

        if self._grudge_enable:
            self.admin_plugin.registerCommand(
                self, "grudge", self._grudge_level, self.cmd_grudge, "grudge"
            )

        if self._tk_points_halflife > 0:
            minute, sec = self.crontab_time()
            self._crontab_tkhalflife = b3.cron.OneTimeCronTab(
                self.halveTKPoints, minute=minute
            )
            self.console.cron + self._crontab_tkhalflife
            self.debug("TK Crontab started")

    def onEvent(self, event):
        """
        Handle intercepted events
        """
        if self.console.game.gameType in self._ffa:
            # game type is deathmatch, ignore
            return
        elif event.type == self.console.getEventID("EVT_CLIENT_DAMAGE_TEAM"):
            if event.client.maxLevel <= self._max_level:
                self.clientDamage(event.client, event.target, int(event.data[0]))

        elif event.type == self.console.getEventID("EVT_CLIENT_KILL_TEAM"):
            if event.client.maxLevel <= self._max_level:
                self.clientDamage(event.client, event.target, int(event.data[0]), True)

        elif event.type == self.console.getEventID("EVT_CLIENT_DISCONNECT"):
            self.forgive_all(event.data)
            return

        elif event.type == self.console.getEventID("EVT_GAME_EXIT"):
            if self._crontab_tkhalflife:
                # remove existing crontab
                self.console.cron - self._crontab_tkhalflife
            self.halveTKPoints("map end: cutting all teamkill points in half")
            return

        elif event.type == self.console.getEventID("EVT_GAME_ROUND_START"):
            if self._tk_points_halflife > 0:
                if self._crontab_tkhalflife:
                    # remove existing crontab
                    self.console.cron - self._crontab_tkhalflife
                (m, s) = self.crontab_time()
                self._crontab_tkhalflife = b3.cron.OneTimeCronTab(
                    self.halveTKPoints, minute=m
                )
                self.console.cron + self._crontab_tkhalflife
                self.debug("TK crontab started")

            return
        else:
            return

        tkinfo = self.client_tkinfo(event.client)
        points = tkinfo.points
        if points >= self._max_points:
            if points >= self._max_points + (self._max_points / 2):
                self.forgive_all(event.client.cid)
                event.client.tempban(
                    self.getMessage("ban"), "tk", self.getMultipliers(event.client)[2]
                )
            elif event.client.var(self, "checkBan").value:
                pass
            else:
                msg = ""
                if len(tkinfo.attacked) > 0:
                    myvictims = []
                    for cid, _bol in tkinfo.attacked.items():
                        victim = self.console.clients.getByCID(cid)
                        if not victim:
                            continue

                        v = self.client_tkinfo(victim)
                        myvictims.append(
                            "%s ^7(^1%s^7)"
                            % (victim.name, v.attacker_points(event.client.cid))
                        )

                    if myvictims:
                        msg += ", ^1Attacked^7: %s" % ", ".join(myvictims)

                self.console.say(
                    self.getMessage(
                        "forgive_warning",
                        {
                            "name": event.client.exactName,
                            "points": points,
                            "cid": event.client.cid,
                        },
                    )
                    + msg
                )
                event.client.setvar(self, "checkBan", True)
                t = threading.Timer(30, self.checkTKBan, (event.client,))
                t.start()

    def checkTKBan(self, client):
        """
        Check if we have to tempban a client for teamkilling.
        :param client: The client on who perform the check
        """
        client.setvar(self, "checkBan", False)
        tkinfo = self.client_tkinfo(client)
        if tkinfo.points >= self._max_points:
            self.forgive_all(client.cid)
            mult = len(tkinfo.attacked)
            if mult < 1:
                mult = 1

            duration = self.getMultipliers(client)[2] * mult
            for cid, _a in list(tkinfo.attacked.items()):
                self.forgive(cid, client, True)

            client.tempban(self.getMessage("ban"), "tk", duration)

    def halveTKPoints(self, msg=None):
        """
        Halve all the teamkill points
        """
        if msg is None:
            msg = "halving all TK Points"
        self.debug(msg)
        for _cid, c in self.console.clients.items():
            tkinfo = self.client_tkinfo(c)
            for acid, points in list(tkinfo.attackers.items()):
                points = int(round(points / 2))
                if points == 0:
                    self.forgive(acid, c, True)
                else:
                    tkinfo.attackers[acid] = points

        if self._tk_points_halflife > 0:
            if self._crontab_tkhalflife:
                # remove existing crontab
                self.console.cron - self._crontab_tkhalflife
            m, s = self.crontab_time()
            self._crontab_tkhalflife = b3.cron.OneTimeCronTab(
                self.halveTKPoints, minute=m
            )
            self.console.cron + self._crontab_tkhalflife
            self.debug("TK crontab re-started")

    def crontab_time(self):
        s = self._tk_points_halflife
        m = int(time.strftime("%M"))
        s += int(time.strftime("%S"))
        while s > 59:
            m += 1
            s -= 60
        if m > 59:
            m -= 60
        return m, s

    def getMultipliers(self, client):
        level = ()
        for lev, mult in self._levels.items():
            if lev <= client.maxLevel:
                level = mult

        if not level:
            return 0, 0, 0

        # self.debug('getMultipliers = %s', level)
        # self.debug('round time %s' % self.console.game.roundTime())
        if self._round_grace and self.console.game.roundTime() < self._round_grace:
            # triple tk damage for first 15 seconds of round
            level = (level[0] * 1.5, level[1] * 3, level[2])

        return level

    def clientDamage(self, attacker, victim, points, killed=False):
        points = int(min(100, points))

        a = self.client_tkinfo(attacker)
        v = self.client_tkinfo(victim)

        # 10/20/2008 - 1.1.6b0 - mindriot
        # * in clientDamage, kill and damage mutlipliers were reversed - changed if killed: to [0] and else: to [1]
        if killed:
            points = int(round(points * self.getMultipliers(attacker)[0]))
        else:
            points = int(round(points * self.getMultipliers(attacker)[1]))

        a.damage(v.cid, points)
        v.damaged(a.cid, points)

        self.debug(
            "attacker: %s, TK points: %s, attacker.maxLevel: %s, last warn time: %s, console time: %s"
            % (
                attacker.exactName,
                points,
                attacker.maxLevel,
                a.lastwarntime,
                self.console.time(),
            )
        )

        if (
            self._round_grace
            and self._issue_warning
            and self.console.game.roundTime() < self._round_grace
            and a.lastwarntime + 60 < self.console.time()
        ):
            a.lastwarntime = self.console.time()
            self.admin_plugin.warnClient(attacker, self._issue_warning, None, False)
        elif (
            points > self._damage_threshold
            and attacker.maxLevel < self._warn_level
            and a.lastwarntime + 180 < self.console.time()
        ):
            a.lastwarntime = self.console.time()
            msg = self.getMessage(
                "tk_warning_reason", {"vname": victim.exactName, "points": points}
            )
            warning = self.admin_plugin.warnClient(
                attacker, msg, None, False, newDuration=self._tk_warn_duration
            )
            a.warn(v.cid, warning)
            victim.message(self.getMessage("tk_request_action", attacker.exactName))

    def client_tkinfo(self, client):
        """
        Return client teamkill info.
        """
        if not client.isvar(self, "tkinfo"):
            client.setvar(self, "tkinfo", TkInfo(self, client.cid))
        if not client.isvar(self, "checkBan"):
            client.setvar(self, "checkBan", False)
        return client.var(self, "tkinfo").value

    def forgive(self, acid, victim, silent=False):
        """
        Forgive a client.
        :param acid: The attacket slot number
        :param victim: The victim client object instance
        :param silent: Whether or not to announce the forgive
        """
        v = self.client_tkinfo(victim)
        points = v.forgive(acid)
        if attacker := self.console.clients.getByCID(acid):
            a = self.client_tkinfo(attacker)
            a.forgiven(victim.cid)

            if not silent:
                if self._private_messages:
                    variables = {
                        "vname": victim.exactName,
                        "aname": attacker.name,
                        "points": points,
                    }
                    victim.message(self.getMessage("forgive", variables))
                    variables = {
                        "vname": victim.exactName,
                        "aname": attacker.name,
                        "points": points,
                    }
                    attacker.message(self.getMessage("forgive", variables))
                else:
                    variables = {
                        "vname": victim.exactName,
                        "aname": attacker.name,
                        "points": points,
                    }
                    self.console.say(self.getMessage("forgive", variables))
        elif not silent:
            if self._private_messages:
                variables = {"vname": victim.exactName, "aname": acid, "points": points}
                victim.message(self.getMessage("forgive", variables))
            else:
                variables = {"vname": victim.exactName, "aname": acid, "points": points}
                self.console.say(self.getMessage("forgive", variables))

        return points

    def grudge(self, acid, victim, silent=False):
        """
        Grudge a client.
        :param acid: The slot number of the client to grudge
        :param victim: The victim client object instance
        :param silent: Whether or not to announce this grudge
        """
        if attacker := self.console.clients.getByCID(acid):
            v = self.client_tkinfo(victim)
            points = v.attacker_points(attacker.cid)
            v.grudge(attacker.cid)

            if not silent:
                if self._private_messages:
                    variables = {
                        "vname": victim.exactName,
                        "aname": attacker.name,
                        "points": points,
                    }
                    victim.message(self.getMessage("grudged", variables))
                    variables = {
                        "vname": victim.exactName,
                        "aname": attacker.name,
                        "points": points,
                    }
                    attacker.message(self.getMessage("grudged", variables))
                else:
                    variables = {
                        "vname": victim.exactName,
                        "aname": attacker.name,
                        "points": points,
                    }
                    self.console.say(self.getMessage("grudged", variables))
            return points
        return False

    def forgive_all(self, acid):
        """
        Forgive all the clients
        """
        if not (attacker := self.console.clients.getByCID(acid)):
            return

        a = self.client_tkinfo(attacker)
        a._attacked = {}

        # forgive all his points
        points = 0
        for _cid, c in list(self.console.clients.items()):
            v = self.client_tkinfo(c)
            points += v.forgive(acid)
            a.forgiven(v.cid)

        return points

    def cmd_grudge(self, data, client, cmd=None):
        """
        <name> - grudge a player for team damaging, a grudge player will not be auto-forgiven
        """
        v = self.client_tkinfo(client)
        if not v.attackers:
            client.message(self.getMessage("no_forgive"))
            return

        if not data:
            if len(v.attackers) == 1:
                for cid, _points in list(v.attackers.items()):
                    self.grudge(cid, client)
            else:
                self.cmd_forgivelist(data, client)
        elif data == "last":
            self.grudge(v.last_attacker, client)
        elif re.match(r"^[0-9]+$", data):
            self.grudge(data, client)
        else:
            data = data.lower()
            for cid, _points in list(v.attackers.items()):
                c = self.console.clients.getByCID(cid)
                if c and c.name.lower().find(data) != -1:
                    self.grudge(c.cid, client)

    def cmd_forgive(self, data, client, cmd=None):
        """
        <name> - forgive a player for team damaging
        """
        v = self.client_tkinfo(client)
        if not v.attackers:
            client.message(self.getMessage("no_forgive"))
            return

        if not data:
            if len(v.attackers) == 1:
                for cid, _points in list(v.attackers.items()):
                    self.forgive(cid, client)
            else:
                self.cmd_forgivelist(data, client)
        elif data == "last":
            self.forgive(v.last_attacker, client)
        elif re.match(r"^[0-9]+$", data):
            self.forgive(data, client)
        else:
            data = data.lower()
            for cid, _points in list(v.attackers.items()):
                c = self.console.clients.getByCID(cid)
                if c and c.name.lower().find(data) != -1:
                    self.forgive(c.cid, client)

    def cmd_forgivelast(self, data, client, cmd=None):
        """
        - forgive the last person to tk you
        """
        v = self.client_tkinfo(client)
        if len(v.attackers) == 1:
            for cid, _attacker in list(v.attackers.items()):
                if v.is_grudged(cid):
                    client.message(self.getMessage("no_forgive"))
                else:
                    self.forgive(cid, client)
        elif v.last_attacker and not v.is_grudged(v.last_attacker):
            self.forgive(v.last_attacker, client)
        else:
            client.message(self.getMessage("no_forgive"))

    def cmd_forgiveall(self, data, client, cmd=None):
        """
        - forgive all attackers' tk points
        """
        v = self.client_tkinfo(client)
        if len(v.attackers) > 0:
            forgave = []
            for cid, points in list(v.attackers.items()):
                if v.is_grudged(cid):
                    continue

                attacker = self.console.clients.getByCID(cid)
                points = self.forgive(cid, client, True)
                if attacker and points:
                    forgave.append(f"{attacker.name}^7 [^3{points}^7]")
                    if self._private_messages:
                        attacker.message(
                            self.getMessage(
                                "forgive_many",
                                {
                                    "vname": client.exactName,
                                    "attackers": attacker.exactName,
                                },
                            )
                        )

            if forgave:
                if self._private_messages:
                    variables = {
                        "vname": client.exactName,
                        "attackers": ", ".join(forgave),
                    }
                    client.message(self.getMessage("forgive_many", variables))
                else:
                    variables = {
                        "vname": client.exactName,
                        "attackers": ", ".join(forgave),
                    }
                    self.console.say(self.getMessage("forgive_many", variables))
            else:
                client.message(self.getMessage("no_forgive"))
        else:
            client.message(self.getMessage("no_forgive"))

    def cmd_forgivelist(self, data, client, cmd=None):
        """
        - list all the players who have shot you
        """
        # do some stuff here to list forgivable players
        v = self.client_tkinfo(client)
        if len(v.attackers) > 0:
            myattackers = []
            # Make a copy of items to avoid `dictionary changed size during
            # iteration` error since `v.forgive` can mutate the same dict
            for cid, points in list(v.attackers.items()):
                attacker = self.console.clients.getByCID(cid)
                if not attacker:
                    v.forgive(cid)
                    continue

                if v.is_grudged(cid):
                    myattackers.append(
                        "^7[^2%s^7] ^1%s ^7(^1%s^7)"
                        % (attacker.cid, attacker.name, points)
                    )
                else:
                    myattackers.append(
                        "^7[^2%s^7] %s ^7[^3%s^7]"
                        % (attacker.cid, attacker.name, points)
                    )

            if myattackers:
                client.message(self.getMessage("players", ", ".join(myattackers)))
            else:
                client.message(self.getMessage("no_forgive"))
        else:
            client.message(self.getMessage("no_forgive"))

    def cmd_forgiveinfo(self, data, client, cmd=None):
        """
        <name> - display a user's tk points
        """
        if not re.match("^([a-z0-9]+)$", data):
            client.message("^7Invalid parameters")
            return

        if sclient := self.findClientPrompt(data, client):
            tkinfo = self.client_tkinfo(sclient)
            msg = ""
            if len(tkinfo.attacked) > 0:
                myvictims = []
                for cid, _bol in tkinfo.attacked.items():
                    if not (victim := self.console.clients.getByCID(cid)):
                        continue

                    v = self.client_tkinfo(victim)
                    myvictims.append(
                        f"{victim.name} ^7(^1{v.attacker_points(sclient.cid)}^7)"
                    )

                if myvictims:
                    msg += ", ^1Attacked^7: %s" % ", ".join(myvictims)

            if len(tkinfo.attackers) > 0:
                myattackers = []
                for cid, points in tkinfo.attackers.items():
                    if not (attacker := self.console.clients.getByCID(cid)):
                        continue

                    if tkinfo.is_grudged(attacker.cid):
                        myattackers.append(f"^1{attacker.name} ^7[^3{points}^7]")
                    else:
                        myattackers.append(f"{attacker.name} ^7[^3{points}^7]")

                if myattackers:
                    msg += ", ^3Attacked By^7: %s" % ", ".join(myattackers)

            cmd.sayLoudOrPM(
                client,
                self.getMessage(
                    "forgive_info", {"name": sclient.exactName, "points": tkinfo.points}
                )
                + msg,
            )

    def cmd_forgiveclear(self, data, client, cmd=None):
        """
        <name> - clear a user's tk points
        """
        if not re.match("^([a-z0-9]+)$", data):
            client.message("^7Invalid parameters")
            return False

        if sclient := self.findClientPrompt(data, client):
            points = self.forgive_all(sclient.cid)
            if self._private_messages:
                client.message(
                    self.getMessage(
                        "forgive_clear", {"name": sclient.exactName, "points": points}
                    )
                )
                sclient.message(
                    self.getMessage(
                        "forgive_clear", {"name": sclient.exactName, "points": points}
                    )
                )
            else:
                self.console.say(
                    self.getMessage(
                        "forgive_clear", {"name": sclient.exactName, "points": points}
                    )
                )

            return True
