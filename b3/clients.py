import re
import threading
import time

import b3
import b3.functions


class Cvar:
    def __init__(self, name, **kwargs):
        """
        Object constructor.
        :param name: The CVAR name.
        :param kwargs: A dict containing optional value and default.
        """
        self.name = name
        self.value = kwargs.get("value")
        self.default = kwargs.get("default")

    def __getitem__(self, key):
        """
        Used to get CVAR attributes using dict keys:
            - name = cvar['name']
            - value = cvar['value']
            - default = cvar['default']
            - value = cvar[0]
            - default = cvar[1]
        """
        if isinstance(key, int):
            if key == 0:
                return self.value
            elif key == 1:
                return self.default
            else:
                raise KeyError(f"no key {key}")
        else:
            return self.__dict__[key]

    def __repr__(self):
        """
        String object representation.
        :return A string representing this CVAR.
        """
        return '<%s name: "%s", value: "%s", default: "%s">' % (
            self.__class__.__name__,
            self.name,
            self.value,
            self.default,
        )

    def getString(self):
        """
        Return the CVAR value as a string.
        :return basestring
        """
        return str(self.value)

    def getInt(self):
        """
        Return the CVAR value as an integer.
        :return int
        """
        return int(self.value)

    def getFloat(self):
        """
        Return the CVAR value as a floating point number.
        :return float
        """
        return float(self.value)

    def getBoolean(self):
        """
        Return the CVAR value as a boolean value.
        :return boolean
        """
        if self.value in ("yes", "1", "on", "true"):
            return True
        elif self.value in ("no", "0", "off", "false"):
            return False
        else:
            raise ValueError(f"{self.value} is not a boolean value")

    def save(self, console):
        """
        Set the CVAR current value.
        :param console: The console to be used to send the cvar set command.
        """
        console.setCvar(self.name, self.value)


class ClientVar:
    def __init__(self, value):
        """
        Object constructor.
        :param value: The variable value.
        """
        self.value = value

    def toInt(self):
        """
        Return the current variable as an integer.
        """
        if self.value is None:
            return 0
        return int(self.value)

    def toString(self):
        """
        Return the current variable as a string.
        """
        if self.value is None:
            return ""
        return str(self.value)

    def items(self):
        """
        Return the elements contained in the variable.
        """
        if self.value is None:
            return ()
        return list(self.value.items())

    def length(self):
        """
        Return the length of the variable.
        """
        if self.value is None:
            return 0
        return len(self.value)


class Client:
    # PVT
    _autoLogin = 1
    _data = None
    _exactName = ""
    _greeting = ""
    _groupBits = 0
    _groups = None
    _guid = ""
    _id = 0
    _ip = ""
    _lastVisit = None
    _login = ""
    _maskGroup = None
    _maskLevel = 0
    _maxGroup = None
    _maxLevel = None
    _name = ""
    _password = ""
    _pluginData = None
    _pbid = ""
    _team = b3.TEAM_UNKNOWN
    _tempLevel = None
    _timeAdd = 0
    _timeEdit = 0

    # PUB
    authed = False
    authorizing = False
    bot = False
    cid = None
    connected = True
    console = None
    hide = False
    state = None

    def __init__(self, **kwargs):
        """
        Object constructor.
        :param kwargs: A dict containing client object attributes.
        """
        self._pluginData = {}
        self.state = b3.STATE_UNKNOWN
        self._data = {}

        # make sure to set console before anything else
        if "console" in kwargs:
            self.console = kwargs["console"]

        for k, v in kwargs.items():
            setattr(self, k, v)

    def isvar(self, plugin, key):
        """
        Check whether the given plugin stored a variable under the given key.
        :param plugin: The plugin that stored the value.
        :param key: The key associated to the value.
        :return True if there is a value, False otherwise
        """
        try:
            return key in self._pluginData[id(plugin)]
        except KeyError:
            return False

    def setvar(self, plugin, key, value=None):
        """
        Store a new variable in this client object indexing it under plugin/key combination.
        :param plugin: The plugin that is saving the value.
        :param key: The key to associate to this variable.
        :param value: The value of this variable.
        :return The stored variable.
        """
        plugin_id = id(plugin)
        try:
            plugin_data = self._pluginData[plugin_id]
        except KeyError:
            client_var = ClientVar(value)
            self._pluginData[plugin_id] = {key: client_var}
        else:
            try:
                client_var = plugin_data[key]
                client_var.value = value
            except KeyError:
                client_var = ClientVar(value)
                plugin_data[key] = client_var
        return client_var

    def var(self, plugin, key, default=None):
        """
        Return a variable previously stored by a plugin.
        :param plugin: The plugin that stored the variable.
        :param key: The key of the variable.
        :param default: A default value to be returned if the variable is not stored.
        :return The variable saved under the plugin/key combination or default if it doesn't exists.
        """
        try:
            return self._pluginData[id(plugin)][key]
        except KeyError:
            return self.setvar(plugin, key, default)

    def varlist(self, plugin, key, default=None):
        if not default:
            default = []
        return self.var(plugin, key, default)

    def vardict(self, plugin, key, default=None):
        if not default:
            default = {}
        return self.var(plugin, key, default)

    def delvar(self, plugin, key):
        """
        Delelte a variable stored by a plugin.
        :param plugin: The plugin that stored the variable.
        :param key: The key of the variable.
        """
        try:
            del self._pluginData[id(plugin)][key]
        except Exception:
            pass

    def getAliases(self):
        return self.console.storage.getClientAliases(self)

    aliases = property(getAliases)

    def getBans(self):
        return self.console.storage.getClientPenalties(self, type=("Ban", "TempBan"))

    bans = property(getBans)

    def _set_data(self, data):
        for k, v in data.items():
            self._data[k] = v

    def _get_data(self):
        return self._data

    data = property(_get_data, _set_data)

    def _get_firstWarn(self):
        if not self.id:
            return None
        return self.console.storage.getClientFirstPenalty(self, "Warning")

    firstWarning = property(_get_firstWarn)

    def getGroups(self):
        if not self._groups:
            self._groups = []
            groups = self.console.storage.getGroups()
            guest_group = None
            for g in groups:
                if g.id == 0:
                    guest_group = g
                if g.id & self._groupBits:
                    self._groups.append(g)
            if not len(self._groups) and guest_group:
                self._groups.append(guest_group)
        return self._groups

    groups = property(getGroups)

    def getIpAddresses(self):
        return self.console.storage.getClientIpAddresses(self)

    ip_addresses = property(getIpAddresses)

    def _get_last_visit(self):
        return self._lastVisit

    def _set_last_visit(self, lastVisit):
        self._lastVisit = lastVisit

    lastVisit = property(_get_last_visit, _set_last_visit)

    def _get_lastBan(self):
        if not self.id:
            return None
        return self.console.storage.getClientLastPenalty(self, ("Ban", "TempBan"))

    lastBan = property(_get_lastBan)

    def _get_lastWarn(self):
        if not self.id:
            return None
        return self.console.storage.getClientLastPenalty(self, "Warning")

    lastWarning = property(_get_lastWarn)

    def _get_maxLevel(self):
        if self._maxLevel is None:
            if self.groups:
                m = -1
                for g in self.groups:
                    if g.level > m:
                        m = g.level
                        self._maxGroup = g

                self._maxLevel = m
            elif self._tempLevel:
                self._maxGroup = Group(id=-1, name="Unspecified", level=self._tempLevel)
                return self._tempLevel
            else:
                return 0

        return self._maxLevel

    maxLevel = property(_get_maxLevel)

    def _get_maxGroup(self):
        self._get_maxLevel()
        return self._maxGroup

    maxGroup = property(_get_maxGroup)

    def _get_numBans(self):
        if not self.id:
            return 0
        return self.console.storage.numPenalties(self, ("Ban", "TempBan"))

    numBans = property(_get_numBans)

    def _get_numWarns(self):
        if not self.id:
            return 0
        return self.console.storage.numPenalties(self, "Warning")

    numWarnings = property(_get_numWarns)

    def _set_team(self, team):
        if self._team != team:
            previous_team = self.team
            self._team = team
            if self.console:
                self.console.queueEvent(
                    self.console.getEvent("EVT_CLIENT_TEAM_CHANGE", self.team, self)
                )
                self.console.queueEvent(
                    self.console.getEvent(
                        "EVT_CLIENT_TEAM_CHANGE2",
                        {"previous": previous_team, "new": self.team},
                        self,
                    )
                )

    def _get_team(self):
        return self._team

    team = property(_get_team, _set_team)

    def getWarnings(self):
        return self.console.storage.getClientPenalties(self, type="Warning")

    warnings = property(getWarnings)

    def getattr(self, name, default=None):
        return getattr(self, name, default)

    def _set_auto_login(self, autoLogin):
        self._autoLogin = autoLogin

    def _get_auto_login(self):
        return self._autoLogin

    autoLogin = property(_get_auto_login, _set_auto_login)

    _connections = 0

    def _set_connections(self, v):
        self._connections = int(v)

    def _get_connections(self):
        return self._connections

    connections = property(_get_connections, _set_connections)

    def _set_greeting(self, greeting):
        self._greeting = greeting

    def _get_greeting(self):
        return self._greeting

    greeting = property(_get_greeting, _set_greeting)

    def _set_groupBits(self, bits):
        self._groupBits = int(bits)
        self.refreshLevel()

    def _get_groupBits(self):
        return self._groupBits

    groupBits = property(_get_groupBits, _set_groupBits)

    def addGroup(self, group):
        self.groupBits = self.groupBits | group.id

    def setGroup(self, group):
        self.groupBits = group.id

    def remGroup(self, group):
        self.groupBits = self.groupBits ^ group.id

    def inGroup(self, group):
        return self.groupBits & group.id

    def _set_guid(self, guid):
        if guid and len(guid) > 2:
            if self._guid and self._guid != guid:
                self.console.warning(
                    "Client has guid but its not the same %s <> %s", self._guid, guid
                )
                self.authed = False
            elif not self._guid:
                self._guid = guid
        else:
            self.authed = False
            self._guid = ""

    def _get_guid(self):
        return self._guid

    guid = property(_get_guid, _set_guid)

    def _set_id(self, v):
        if not v:
            self._id = 0
        else:
            self._id = int(v)

    def _get_id(self):
        return self._id

    id = property(_get_id, _set_id)

    def _set_ip(self, ip):
        if ":" in ip:
            ip = ip[0 : ip.find(":")]
        if self._ip != ip:
            self.makeIpAlias(self._ip)
        self._ip = ip

    def _get_ip(self):
        return self._ip

    ip = property(_get_ip, _set_ip)

    def _set_login(self, login):
        self._login = login

    def _get_login(self):
        return self._login

    login = property(_get_login, _set_login)

    def _set_maskGroup(self, g):
        self.maskLevel = g.level
        self._maskGroup = None

    def _get_maskGroup(self):
        if not self.maskLevel:
            return None
        elif not self._maskGroup:
            try:
                group = self.console.storage.getGroup(Group(level=self.maskLevel))
            except Exception as err:
                self.console.error(
                    "Could not find group with level %r" % self.maskLevel, exc_info=err
                )
                self.maskLevel = 0
                return None
            else:
                self._maskGroup = group
        return self._maskGroup

    maskGroup = property(_get_maskGroup, _set_maskGroup)

    def _get_maskedGroup(self):
        group = self.maskGroup
        return group if group else self.maxGroup

    maskedGroup = property(_get_maskedGroup)

    def _set_maskLevel(self, v):
        self._maskLevel = int(v)
        self._maskGroup = None

    def _get_maskLevel(self):
        return self._maskLevel

    maskLevel = property(_get_maskLevel, _set_maskLevel)

    def _get_maskedLevel(self):
        if group := self.maskedGroup:
            return group.level
        else:
            return 0

    maskedLevel = property(_get_maskedLevel)

    def _set_name(self, name):
        if self.console:
            newName = self.console.stripColors(name)
        else:
            newName = name.strip()

        if self._name == newName:
            return
        if self.cid == "-1" or self.cid == "Server":  # bfbc2 addition
            return

        self.makeAlias(self._name)
        self._name = newName
        self._exactName = name + "^7"

        if self.console and self.authed:
            self.console.queueEvent(
                self.console.getEvent("EVT_CLIENT_NAME_CHANGE", self.name, self)
            )

    def _get_name(self):
        return self._name

    def _get_exactName(self):
        return self._exactName

    name = property(_get_name, _set_name)  # cleaned
    exactName = property(_get_exactName, _set_name)  # with color codes

    def _set_password(self, password):
        self._password = password

    def _get_password(self):
        return self._password

    password = property(_get_password, _set_password)

    def _set_pbid(self, pbid):
        self._pbid = pbid

    def _get_pbid(self):
        return self._pbid

    pbid = property(_get_pbid, _set_pbid)

    def _set_timeAdd(self, timeAdd):
        self._timeAdd = int(timeAdd)

    def _get_timeAdd(self):
        return self._timeAdd

    timeAdd = property(_get_timeAdd, _set_timeAdd)

    def _set_timeEdit(self, timeEdit):
        self._timeEdit = int(timeEdit)

    def _get_timeEdit(self):
        return self._timeEdit

    timeEdit = property(_get_timeEdit, _set_timeEdit)

    def refreshLevel(self):
        """
        Refresh the client level.
        """
        self._maxLevel = None
        self._groups = None

    def disconnect(self):
        """
        Disconnect the client.
        """
        self.console.clients.disconnect(self)

    def kick(self, reason="", keyword=None, admin=None, silent=False, data="", *kwargs):
        """
        Kick the client.
        :param reason: The reason for this kick
        :param keyword: The keyword specified before the reason
        :param admin: The admin who performed the kick
        :param silent: Whether or not to announce this kick
        :param data: Extra data to add to the penalty
        """
        self.console.kick(self, reason, admin, silent)

        if self.id:
            kick = ClientKick()

            if admin:
                kick.adminId = admin.id
            else:
                kick.adminId = 0

            kick.clientId = self.id
            kick.data = data
            kick.keyword = keyword
            kick.reason = reason
            kick.timeExpire = -1
            kick.save(self.console)

    def ban(self, reason="", keyword=None, admin=None, silent=False, data="", *kwargs):
        """
        Permban the client.
        :param reason: The reason for this ban
        :param keyword: The keyword specified before the reason
        :param admin: The admin who performed the ban
        :param silent: Whether or not to announce this ban
        :param data: Extra data to add to the penalty
        """
        self.console.ban(self, reason, admin, silent)

        if self.id:
            ban = ClientBan()

            if admin:
                ban.adminId = admin.id
            else:
                ban.adminId = 0

            ban.clientId = self.id
            ban.data = data
            ban.keyword = keyword
            ban.reason = reason
            ban.timeExpire = -1
            ban.save(self.console)

    def reBan(self, ban):
        """
        Re-apply a ban penalty on this client.
        """
        if ban.timeExpire == -1:
            self.console.ban(self, ban.reason, None, True)
        elif ban.timeExpire > self.console.time():
            self.console.tempban(
                self,
                ban.reason,
                int((ban.timeExpire - self.console.time()) / 60),
                None,
                True,
            )

    def unban(self, reason="", admin=None, silent=False, *kwargs):
        """
        Unban the client.
        :param reason: The reason for the unban
        :param admin: The admin who unbanned this client
        :param silent: Whether or not to announce this unban
        """
        self.console.unban(self, reason, admin, silent)
        for ban in self.bans:
            ban.inactive = 1
            ban.save(self.console)

    def tempban(
        self,
        reason="",
        keyword=None,
        duration=2,
        admin=None,
        silent=False,
        data="",
        *kwargs,
    ):
        """
        Tempban this client.
        :param reason: The reason for this tempban
        :param keyword: The keyword specified before the reason
        :param duration: The duration of the tempban
        :param admin: The admin who performed the tempban
        :param silent: Whether or not to announce this tempban
        :param data: Extra data to add to the penalty
        """
        duration = b3.functions.time2minutes(duration)
        self.console.tempban(self, reason, duration, admin, silent)

        if self.id:
            ban = ClientTempBan()

            if admin:
                ban.adminId = admin.id
            else:
                ban.adminId = 0

            ban.clientId = self.id
            ban.data = data
            ban.duration = duration
            ban.keyword = keyword
            ban.reason = reason
            ban.timeExpire = self.console.time() + (duration * 60)
            ban.save(self.console)

    def message(self, msg, *args):
        """
        Send a private message to this client
        :param msg: the message to send
        :param args: substitution arguments (if any).
        """
        self.console.message(self, msg, *args)

    def warn(self, duration, warning, keyword=None, admin=None, data=""):
        """
        Warn this client.
        :param duration: The duration of this warning
        :param warning: The reason for this warning
        :param keyword: The keyword specified before the reason
        :param admin: The admin who performed the ban
        :param data: Extra data to add to the penalty
        """
        if self.id:
            duration = b3.functions.time2minutes(duration)
            warn = ClientWarning()

            if admin:
                warn.adminId = admin.id
            else:
                warn.adminId = 0

            warn.clientId = self.id
            warn.data = data
            warn.duration = duration
            warn.keyword = keyword
            warn.reason = warning
            warn.timeExpire = self.console.time() + (duration * 60)
            warn.save(self.console)

            if self.console:
                self.console.queueEvent(
                    self.console.getEvent(
                        "EVT_CLIENT_WARN",
                        data={
                            "reason": warn.reason,
                            "duration": warn.duration,
                            "data": warn.data,
                            "admin": admin,
                            "timeExpire": warn.timeExpire,
                        },
                        client=self,
                    )
                )

            return warn

    def notice(self, notice, spare, admin=None):
        """
        Add a notice to this client.
        :param notice: The notice text
        :param spare: Wtf is this one?!?!?
        :param admin: The admin who added the notice
        """
        if self.id:
            notice_object = ClientNotice()

            if admin:
                notice_object.adminId = admin.id
            else:
                notice_object.adminId = 0

            notice_object.clientId = self.id
            notice_object.reason = notice
            notice_object.timeAdd = self.console.time()
            notice_object.save(self.console)

            if self.console:
                self.console.queueEvent(
                    self.console.getEvent(
                        "EVT_CLIENT_NOTICE",
                        data={
                            "notice": notice,
                            "admin": admin,
                            "timeAdd": notice_object.timeAdd,
                        },
                        client=self,
                    )
                )

            return notice_object

    def makeAlias(self, name):
        """
        Create a new alias for this client.
        :param name: The alias string
        """
        if not self.id or not name:
            return

        try:
            alias = self.console.storage.getClientAlias(
                Alias(clientId=self.id, alias=name)
            )
        except KeyError:
            alias = None

        if alias:
            if alias.numUsed > 0:
                alias.numUsed += 1
            else:
                alias.numUsed = 1
        else:
            alias = Alias(clientId=self.id, alias=name)

        alias.save(self.console)
        self.console.bot(
            "Created new alias for client @%s: %s", str(self.id), alias.alias
        )

    def makeIpAlias(self, ip):
        """
        Create a new ip alias for this client.
        :param ip: The ip string
        """
        if not self.id or not ip:
            return

        try:
            alias = self.console.storage.getClientIpAddress(
                IpAlias(clientId=self.id, ip=ip)
            )
        except KeyError:
            alias = None

        if alias:
            if alias.numUsed > 0:
                alias.numUsed += 1
            else:
                alias.numUsed = 1
        else:
            alias = IpAlias(clientId=self.id, ip=ip)

        alias.save(self.console)
        self.console.bot(
            "Created new IP alias for client @%s: %s", str(self.id), alias.ip
        )

    def save(self, console=None):
        """
        Save the current client in the storage.
        """
        self.timeEdit = time.time()
        if self.guid is None or str(self.guid) == "0":
            # can't save a client without a guid
            return False
        else:
            # fix missing pbid. Workaround a bug in the database layer that would insert the string "None"
            # in db if pbid is None :/ The empty string being the default value for that db column!!
            if self.pbid is None:
                self.pbid = ""
            if console:
                self.console.queueEvent(
                    self.console.getEvent("EVT_CLIENT_UPDATE", data=self, client=self)
                )
            return self.console.storage.setClient(self)

    def auth(self):
        """
        Authorize this client.
        """
        if not self.authed and self.guid and not self.authorizing:
            self.authorizing = True

            name = self.name
            pbid = self.pbid
            ip = self.ip

            if not pbid and self.cid:
                fsa_info = self.console.queryClientFrozenSandAccount(self.cid)
                self.pbid = pbid = fsa_info.get("login", None)

            # FSA will be found in pbid
            if not self.pbid:
                # auth with cl_guid only
                try:
                    in_storage = self.auth_by_guid()
                    # fix up corrupted data due to bug #162
                    if in_storage and in_storage.pbid == "None":
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
                        self.console.error(
                            "Auth by guid failed (when no known FSA)", exc_info=e
                        )
                        self.authorizing = False
                        return False

            if in_storage:
                self.lastVisit = self.timeEdit
                self.console.bot(
                    "Client found in the storage @%s: welcome back %s [FSA: '%s']",
                    self.id,
                    self.name,
                    self.pbid,
                )
            else:
                self.console.bot(
                    "Client not found in the storage %s [FSA: '%s'], create new",
                    str(self.guid),
                    self.pbid,
                )

            self.connections = int(self.connections) + 1
            self.name = name
            self.ip = ip
            if pbid:
                self.pbid = pbid
            self.save()
            self.authed = True

            # check for bans
            if self.numBans > 0:
                ban = self.lastBan
                if ban:
                    self.reBan(ban)
                    self.authorizing = False
                    return False

            self.refreshLevel()
            self.console.queueEvent(
                self.console.getEvent("EVT_CLIENT_AUTH", data=self, client=self)
            )
            self.authorizing = False
            return self.authed
        else:
            return False

    def auth_by_guid(self):
        """
        Authorize this client using his GUID.
        """
        try:
            return self.console.storage.getClient(self)
        except KeyError as msg:
            self.console.warning("auth_by_guid: user not found %s: %s", self.guid, msg)
            return False

    def auth_by_pbid(self):
        """
        Authorize this client using his PBID.
        """
        clients_matching_pbid = self.console.storage.getClientsMatching(
            {"pbid": self.pbid}
        )
        if len(clients_matching_pbid) > 1:
            self.console.warning(
                "Found %s client having FSA '%s'", len(clients_matching_pbid), self.pbid
            )
            return self.auth_by_pbid_and_guid()
        elif len(clients_matching_pbid) == 1:
            self.id = clients_matching_pbid[0].id
            # we may have a second client entry in database with current guid.
            # we want to update our current client guid only if it is not the case.
            try:
                client_by_guid = self.console.storage.getClient(Client(guid=self.guid))
            except KeyError:
                pass
            else:
                if client_by_guid.id != self.id:
                    # so storage.getClient is able to overwrite the value which will make
                    # it remain unchanged in database when .save() will be called later on
                    self._guid = None
            return self.console.storage.getClient(self)
        else:
            self.console.warning(
                "Frozen Sand account [%s] unknown in database", self.pbid
            )
            return False

    def auth_by_pbid_and_guid(self):
        """
        Authorize this client using both his PBID and GUID.
        """
        clients_matching_pbid = self.console.storage.getClientsMatching(
            {"pbid": self.pbid, "guid": self.guid}
        )
        if clients_matching_pbid:
            self.id = clients_matching_pbid[0].id
            return self.console.storage.getClient(self)
        else:
            self.console.warning(
                "Frozen Sand account [%s] with guid '%s' unknown in database",
                self.pbid,
                self.guid,
            )
            return False

    def __str__(self):
        return 'Client<@%s:%s|%s:"%s":%s>' % (
            self.id,
            self.guid,
            self.pbid,
            self.name,
            self.cid,
        )


class Struct:
    """
    Base class for Penalty/Alias/IpAlias/Group classes.
    """

    _id = 0

    def __init__(self, **kwargs):
        """
        Object constructor.
        """
        for k, v in kwargs.items():
            setattr(self, k, v)

    def _set_id(self, v):
        if not v:
            self._id = 0
        else:
            self._id = int(v)

    def _get_id(self):
        return self._id

    id = property(_get_id, _set_id)


class Penalty(Struct):
    """
    Represent a penalty.
    """

    data = ""
    inactive = 0
    keyword = ""
    reason = ""
    type = ""

    _adminId = None
    _clientId = None
    _timeAdd = 0
    _timeEdit = 0
    _timeExpire = 0
    _duration = 0

    def _set_admin_id(self, v):
        self._adminId = v

    def _get_admin_id(self):
        return self._adminId

    adminId = property(_get_admin_id, _set_admin_id)

    def _set_client_id(self, v):
        self._clientId = v

    def _get_client_id(self):
        return self._clientId

    clientId = property(_get_client_id, _set_client_id)

    def _set_duration(self, v):
        self._duration = b3.functions.time2minutes(v)

    def _get_duration(self):
        return self._duration

    duration = property(_get_duration, _set_duration)

    def _set_timeAdd(self, v):
        self._timeAdd = int(v)

    def _get_timeAdd(self):
        return self._timeAdd

    timeAdd = property(_get_timeAdd, _set_timeAdd)

    def _set_timeEdit(self, v):
        self._timeEdit = int(v)

    def _get_timeEdit(self):
        return self._timeEdit

    timeEdit = property(_get_timeEdit, _set_timeEdit)

    def _set_timeExpire(self, v):
        self._timeExpire = int(v)

    def _get_timeExpire(self):
        return self._timeExpire

    timeExpire = property(_get_timeExpire, _set_timeExpire)

    def save(self, console):
        """
        Save the penalty in the storage.
        :param console: The console instance
        """
        self.timeEdit = console.time()
        if not self.id:
            self.timeAdd = console.time()
        return console.storage.setClientPenalty(self)


class ClientWarning(Penalty):
    """
    Represent a Warning.
    """

    type = "Warning"

    def _get_reason(self):
        return self.reason

    def _set_reason(self, v):
        self.reason = v

    warning = property(_get_reason, _set_reason)


class ClientNotice(Penalty):
    """
    Represent a Notice.
    """

    type = "Notice"

    def _get_reason(self):
        return self.reason

    def _set_reason(self, v):
        self.reason = v

    notice = property(_get_reason, _set_reason)


class ClientBan(Penalty):
    """
    Represent a Ban.
    """

    type = "Ban"


class ClientTempBan(Penalty):
    """
    Represent a TempBan.
    """

    type = "TempBan"


class ClientKick(Penalty):
    """
    Represent a Kick.
    """

    type = "Kick"


class Alias(Struct):
    """
    Represent an Alias.
    """

    _alias = ""
    _clientId = 0
    _numUsed = 1
    _timeAdd = 0
    _timeEdit = 0

    def _set_alias(self, v):
        self._alias = v

    def _get_alias(self):
        return self._alias

    alias = property(_get_alias, _set_alias)

    def _set_client_id(self, v):
        self._clientId = v

    def _get_client_id(self):
        return self._clientId

    clientId = property(_get_client_id, _set_client_id)

    def _set_num_used(self, v):
        self._numUsed = v

    def _get_num_used(self):
        return self._numUsed

    numUsed = property(_get_num_used, _set_num_used)

    def _set_time_add(self, v):
        self._timeAdd = int(v)

    def _get_time_add(self):
        return self._timeAdd

    timeAdd = property(_get_time_add, _set_time_add)

    def _set_time_edit(self, v):
        self._timeEdit = int(v)

    def _get_time_edit(self):
        return self._timeEdit

    timeEdit = property(_get_time_edit, _set_time_edit)

    def save(self, console):
        """
        Save the alias in the storage.
        :param console: The console instance.
        """
        self.timeEdit = console.time()
        if not self.id:
            self.timeAdd = console.time()
        return console.storage.setClientAlias(self)

    def __str__(self):
        return 'Alias(id=%s, alias="%s", clientId=%s, numUsed=%s)' % (
            self.id,
            self.alias,
            self.clientId,
            self.numUsed,
        )


class IpAlias(Struct):
    """
    Represent an Ip Alias.
    """

    _ip = None
    _clientId = 0
    _numUsed = 1
    _timeAdd = 0
    _timeEdit = 0

    def _set_ip(self, v):
        self._ip = v

    def _get_ip(self):
        return self._ip

    ip = property(_get_ip, _set_ip)

    def _set_client_id(self, v):
        self._clientId = v

    def _get_client_id(self):
        return self._clientId

    clientId = property(_get_client_id, _set_client_id)

    def _set_num_used(self, v):
        self._numUsed = v

    def _get_num_used(self):
        return self._numUsed

    numUsed = property(_get_num_used, _set_num_used)

    def _set_time_add(self, v):
        self._timeAdd = int(v)

    def _get_time_add(self):
        return self._timeAdd

    timeAdd = property(_get_time_add, _set_time_add)

    def _set_time_edit(self, v):
        self._timeEdit = int(v)

    def _get_time_edit(self):
        return self._timeEdit

    timeEdit = property(_get_time_edit, _set_time_edit)

    def save(self, console):
        """
        Save the ip alias in the storage.
        :param console: The console implementation
        """
        now = console.time()
        self.timeEdit = now
        if not self.id:
            self.timeAdd = now
        return console.storage.setClientIpAddress(self)

    def __str__(self):
        return 'IpAlias(id=%s, ip="%s", clientId=%s, numUsed=%s)' % (
            self.id,
            self.ip,
            self.clientId,
            self.numUsed,
        )


class Group(Struct):
    """
    Represent a Group.
    """

    _name = ""
    _keyword = ""
    _level = 0
    _timeAdd = 0
    _timeEdit = 0

    def _set_name(self, v):
        self._name = v

    def _get_name(self):
        return self._name

    name = property(_get_name, _set_name)

    def _set_keyword(self, v):
        self._keyword = v

    def _get_keyword(self):
        return self._keyword

    keyword = property(_get_keyword, _set_keyword)

    def _set_level(self, v):
        self._level = int(v)

    def _get_level(self):
        return self._level

    level = property(_get_level, _set_level)

    def _set_time_add(self, v):
        self._timeAdd = int(v)

    def _get_time_add(self):
        return self._timeAdd

    timeAdd = property(_get_time_add, _set_time_add)

    def _set_time_edit(self, v):
        self._timeEdit = int(v)

    def _get_time_edit(self):
        return self._timeEdit

    timeEdit = property(_get_time_edit, _set_time_edit)

    def save(self, console):
        """
        Save the group in the storage.
        :param console: The console implementation
        """
        now = console.time()
        self.timeEdit = now
        if not self.id:
            self.timeAdd = now
        return console.storage.setGroup(self)

    def __repr__(self):
        return "Group(%r)" % self.__dict__


class Clients(dict):
    _authorizing = False
    _exactNameIndex = None
    _guidIndex = None
    _nameIndex = None

    console = None

    def __init__(self, console):
        """
        Object constructor.
        :param console: The console implementation
        """
        super().__init__()
        self.console = console
        self._exactNameIndex = {}
        self._guidIndex = {}
        self._nameIndex = {}

    def find(self, handle, maxres=None):
        """
        Search a client.
        :param handle: The search input
        :param maxres: A maximum amount of results
        """
        matches = self.getByMagic(handle)
        if len(matches) == 0:
            return None
        elif len(matches) > maxres:
            return matches[0:maxres]
        else:
            return matches

    def getByName(self, name):
        """
        Search a client by matching his name.
        :param name: The name to use for the search
        """
        name = name.lower()
        try:
            return self[self._nameIndex[name]]
        except Exception:
            for cid, c in self.items():
                if c.name and c.name.lower() == name:
                    self._nameIndex[name] = c.cid
                    return c

    def getByExactName(self, name):
        """
        Search a client by matching his exact name.
        :param name: The name to use for the search
        """
        name = name.lower() + "^7"
        try:
            c = self[self._exactNameIndex[name]]
            return c
        except Exception:
            for cid, c in self.items():
                if c.exactName and c.exactName.lower() == name:
                    self._exactNameIndex[name] = c.cid
                    return c

    def getList(self):
        """
        Return the list of line clients.
        """
        return [c for _, c in self.items() if not c.hide]

    def getClientsByLevel(self, min=0, max=100, masked=False):
        """
        Return the list of clients whithin the min/max level range.
        :param min: The minimum level
        :param max: The maximum level
        :param masked: Whether or not to match masked levels
        """
        clist = []
        minlevel, maxlevel = int(min), int(max)
        for cid, c in self.items():
            if c.hide:
                continue
            elif (
                not masked and c.maskGroup and minlevel <= c.maskGroup.level <= maxlevel
            ):
                clist.append(c)
            elif not masked and c.maskGroup:
                continue
            elif minlevel <= c.maxLevel <= maxlevel:
                # self.console.debug('getClientsByLevel hidden = %s', c.hide)
                clist.append(c)
        return clist

    def getClientsByName(self, name):
        """
        Return a list of clients matching the given name.
        :param name: The name to match
        """
        needle = re.sub(r"\s", "", name.lower())
        return [
            c
            for _, c in self.items()
            if not c.hide and needle in re.sub(r"\s", "", c.name.lower())
        ]

    def getClientLikeName(self, name):
        """
        Return the client who has the given name in its name (match substring).
        :param name: The name to match
        """
        name = name.lower()
        for cid, c in self.items():
            if not c.hide and name in c.name.lower():
                return c

    def getClientsByState(self, state):
        """
        Return a list of clients matching the given state.
        :param state: The clients state
        """
        return [c for _, c in self.items() if not c.hide and c.state == state]

    def getByDB(self, client_id):
        """
        Return the client matching the given database id.
        """
        if m := re.match(r"^@([0-9]+)$", client_id):
            try:
                if not (
                    sclient := self.console.storage.getClientsMatching(
                        {"id": m.group(1)}
                    )
                ):
                    return []

                collection = []
                for c in sclient:
                    if connected_client := self.getByGUID(c.guid):
                        c = connected_client
                    else:
                        c.clients = self
                        c.console = self.console
                        c.exactName = c.name
                    collection.append(c)
                    if len(collection) == 5:
                        break

                return collection
            except Exception:
                return []
        else:
            return self.lookupByName(client_id)

    def getByMagic(self, handle):
        """
        Return the client matching the given handle.
        :param handle: The handle to use for the search
        """
        handle = handle.strip()
        if re.match(r"^[0-9]+$", handle):
            client = self.getByCID(handle)
            if client:
                return [client]
            return []
        elif re.match(r"^@([0-9]+)$", handle):
            return self.getByDB(handle)
        elif handle[:1] == "\\":
            c = self.getByName(handle[1:])
            if c and not c.hide:
                return [c]
            return []
        else:
            clients = []
            needle = re.sub(r"\s", "", handle.lower())
            for cid, c in self.items():
                cleanname = re.sub(r"\s", "", c.name.lower())
                if (
                    not c.hide
                    and (needle in cleanname or needle in c.pbid)
                    and c not in clients
                ):
                    clients.append(c)
            return clients

    def getByGUID(self, guid):
        """
        Return the client matching the given GUID.
        :param guid: The GUID to match
        """
        guid = guid.upper()
        try:
            return self[self._guidIndex[guid]]
        except Exception:
            for cid, c in self.items():
                if c.guid and c.guid == guid:
                    self._guidIndex[guid] = c.cid
                    return c
                elif b3.functions.fuzzyGuidMatch(c.guid, guid):
                    # found by fuzzy matching: don't index
                    return c

    def getByCID(self, cid):
        """
        Return the client matching the given slot number.
        :param cid: The client slot number
        """
        try:
            c = self[cid]
        except KeyError:
            return None
        except Exception as e:
            self.console.error("Unexpected error getByCID(%s) - %s", cid, e)
        else:
            if c.cid == cid:
                return c

    def lookupByName(self, name):
        """
        Return a lst of clients matching the given name.
        Will search both on the online clients list and in the storage.
        :param name: The client name
        """
        # first check connected users
        c = self.getClientLikeName(name)
        if c and not c.hide:
            return [c]

        name = b3.functions.escape_string(name)

        if sclient := self.console.storage.getClientsMatching({"%name%": name}):
            clients = []
            for c in sclient:
                c.clients = self
                c.console = self.console
                c.exactName = c.name
                clients.append(c)
                if len(clients) == 5:
                    break
            return clients

        return []

    def lookupSuperAdmins(self):
        """
        Return the list of superadmins.
        Will search in the storage only.
        """
        try:
            group = Group(keyword="superadmin")
            group = self.console.storage.getGroup(group)
        except Exception as e:
            self.console.error("Could not get superadmin group: %s", e)
            return False

        if sclient := self.console.storage.getClientsMatching(
            {"&group_bits": group.id}
        ):
            clients = []
            for c in sclient:
                c.clients = self
                c.console = self.console
                c.exactName = c.name
                clients.append(c)

            return clients

        return []

    def disconnect(self, client):
        """
        Disconnect a client from the game.
        :param client: The client to disconnect.
        """
        client.connected = False
        if client.cid is None:
            return

        cid = client.cid
        if cid in self:
            self[cid] = None
            del self[cid]
            self.console.queueEvent(
                self.console.getEvent("EVT_CLIENT_DISCONNECT", data=cid, client=client)
            )

        self.resetIndex()

    def resetIndex(self):
        """
        Reset the indexes.
        """
        self._nameIndex = {}
        self._guidIndex = {}
        self._exactNameIndex = {}

    def newClient(self, cid, **kwargs):
        """
        Create a new client.
        :param cid: The client slot number
        :param kwargs: The client attributes
        """
        client = Client(
            console=self.console, cid=cid, timeAdd=self.console.time(), **kwargs
        )
        self[client.cid] = client
        self.resetIndex()
        self.console.queueEvent(
            self.console.getEvent("EVT_CLIENT_CONNECT", data=client, client=client)
        )

        if client.guid and not client.bot:
            client.auth()
        elif not client.authed:
            self.authorizeClients()
        return client

    def empty(self):
        """
        Empty the clients list
        """
        self.clear()

    def clear(self):
        """
        Empty the clients list and reset the indexes.
        """
        self.resetIndex()
        for cid, c in list(self.items()):
            if not c.hide:
                del self[cid]

    def sync(self):
        """
        Synchronize the clients list.
        """
        mlist = self.console.sync()
        # remove existing clients
        self.clear()
        # add list of matching clients
        for cid, c in mlist.items():
            self[cid] = c

    def authorizeClients(self):
        """
        Authorize the online clients.
        """
        if not self._authorizing:
            # lookup is delayed to allow time for auth
            # it will also allow us to batch the lookups if several players
            # are joining at once
            self._authorizing = True
            t = threading.Timer(5, self._authorizeClients)
            t.start()

    def _authorizeClients(self):
        """
        Authorize the online clients.
        Must not be called directly: always use authorize_clients().
        """
        self.console.authorizeClients()
        self._authorizing = False
