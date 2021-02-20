import b3.plugin
import operator
import threading

from b3.functions import start_daemon_thread

__author__ = 'SvaRoX'
__version__ = '0.3'


class KniferPlugin(b3.plugin.Plugin):
    _adminPlugin = None
    _xlrstatsPlugin = None
    _minLevel = 100
    _knifeId = 12  # see config file
    _knEnabled = 0
    _stfu = 0  # if 1, no bigtexts
    _nbKK = 0  # Total number of knife kills
    _nbTop = 5
    _msgLevels = set()
    _cutKillers = {}
    _challenges = {}
    _max_challenges = 5
    _challengeDuration = 300
    _hof_plugin_name = 'knifer'

    def onLoadConfig(self):
        self._adminPlugin = self.console.getPlugin('admin')
        if not self._adminPlugin:
            self.error('Could not find admin plugin')
            return False
        self._xlrstatsPlugin = self.console.getPlugin('xlrstats')
        if not self._xlrstatsPlugin:
            self.debug('Could not find xlrstats plugin')

        try:
            self._minLevel = self.config.getint('settings', 'minlevel')
        except:
            pass
        self.debug('Minimum Level to use commands = %d' % self._minLevel)

        try:
            self._nbTop = self.config.getint('settings', 'nbtop')
        except:
            pass
        self.debug('Number of top slicers displayed = %d' % self._nbTop)

        try:
            if self.config.getint('settings', 'enabled') == 1:
                self._knEnabled = 1
        except:
            pass

        try:
            self._knifeId = self.config.getint('settings', 'knifeid')
        except:
            pass
        self.debug('Knife ID = %d' % self._knifeId)

        try:
            self._challengeDuration = self.config.getint('settings', 'challengeduration')
        except:
            pass
        self.debug('Challenge duration = %d' % self._challengeDuration)

        for m in self.config.options('messages'):
            sp = m.split('_')
            nb = 0
            if len(sp) == 2:
                try:
                    nb = int(sp[1])
                    self._msgLevels.add(nb)
                    self.debug('Message displayed at %d knife kills' % nb)
                except:
                    pass

        self._adminPlugin.registerCommand(self, 'knenable', self._minLevel, self.cmd_knenable)
        self._adminPlugin.registerCommand(self, 'kndisable', self._minLevel, self.cmd_kndisable)
        self._adminPlugin.registerCommand(self, 'knstfu', self._minLevel, self.cmd_stfu)
        self._adminPlugin.registerCommand(self, 'knstats', 0, self.cmd_displaySelfScores, 'kns')
        self._adminPlugin.registerCommand(self, 'kntopstats', 0, self.cmd_displayScores, 'knts')
        self._adminPlugin.registerCommand(self, 'knallstats', 0, self.cmd_allstats, 'knas')
        self._adminPlugin.registerCommand(self, 'knchallenge', 0, self.cmd_challenge, 'knch')
        self._adminPlugin.registerCommand(self, 'kntestscore', 0, self.cmd_testscore, 'kntest')
        self._adminPlugin.registerCommand(self, 'knrecord', 0, self.cmd_record, 'knrec')

        self.query = self.console.storage.query

    def onStartup(self):
        self.registerEvent('EVT_GAME_ROUND_START', self.on_round_start)
        self.registerEvent('EVT_GAME_EXIT', self.on_round_end)
        # '-> See poweradmin 604
        self.registerEvent('EVT_CLIENT_KILL', self.on_client_kill)

    def on_round_start(self, event):
        self._cancel_challenges()
        for c in self.console.clients.getList():
            prev_kills = c.var(self, 'knifeKills', 0).value
            if prev_kills > 0:
                self.debug("Resetting [knifeKills] var [%d] for client %s" % (prev_kills, c.name))
                c.setvar(self, 'knifeKills', 0)

    def on_round_end(self, event):
        self.displayScores(0)
        start_daemon_thread(target=self.updateHallOfFame, args=(self._cutKillers, self.console.game.mapName), name='knifer-hof')
        self.resetScores()
        self._cancel_challenges()

    def _cancel_challenges(self):
        while True:
            try:
                _, challenge_thread = self._challenges.popitem()
                self._cancel_challenge_thread(challenge_thread)
            except KeyError:
                break

    def _cancel_challenge_thread(self, challenge_thread):
        try:
            challenge_thread.cancel()
        except Exception:
            pass

    def on_client_kill(self, event):
        self.someoneKilled(event.client, event.target, event.data)

    def resetScores(self):
        self._nbKK = 0
        self._cutKillers = {}

    def cmd_stfu(self, data, client, cmd=None):
        """\
        Enable/disable silent mode (no more bigtexts)
        """
        msg = ['off', 'on']
        self._stfu = (self._stfu + 1) % 2
        cmd.sayLoudOrPM(client, '^7Knife plugin : silent mode %s' % msg[self._stfu])

    def cmd_knenable(self, data, client, cmd=None):
        """\
        Enable the plugin
        """
        cmd.sayLoudOrPM(client, '^7Knife plugin : enabled')
        self._knEnabled = 1

    def cmd_kndisable(self, data, client, cmd=None):
        """\
        Disable plugin commands, but still counts knife kills
        """
        cmd.sayLoudOrPM(client, '^7Knife plugin : disabled')
        self._knEnabled = 0

    def cmd_displaySelfScores(self, data, client, cmd=None):
        """\
        <player> Display knife kills stats for a given client (or yourself)
        """
        if not self._knEnabled:
            cmd.sayLoudOrPM(client, '^7Knife stats are disabled')
            return
        msg = ''
        if not data:
            if client.cid in self._cutKillers:
                msg = '%s : ^2%d ^7knife kills' % (client.exactName, client.var(self, 'knifeKills', 0).value)
            else:
                msg = '^7No knife kill yet... try again'
        else:
            m = self._adminPlugin.parseUserCmd(data)
            if m:
                sclient = self._adminPlugin.findClientPrompt(m[0], client)
                if not sclient:
                    msg = 'No player found'
                # elif len(sclient) > 1:
                # msg = 'Too many players found, please try an other request'
                else:
                    msg = '%s : ^2%d ^7knife kills' % (sclient.exactName, sclient.var(self, 'knifeKills', 0).value)
        # if unnecessary ?
        if msg:
            cmd.sayLoudOrPM(client, msg)

    def cmd_displayScores(self, data, client, cmd=None):
        """\
        List the top slicers for the current map
        """
        if not self._knEnabled:
            client.message('^7Knife stats are disabled')
            return
        if not self._cutKillers:
            client.message('^7No top knife stats for the moment')
        else:
            self.displayScores(1)

    def cmd_challenge(self, data, client, cmd=None):
        """\
        <player> Challenge someone. The first player to slice them wins the challenge.
        """
        if (not self._knEnabled) or (self._stfu == 1):
            cmd.sayLoudOrPM(client, '^7Knife stats are disabled')
            return

        m = self._adminPlugin.parseUserCmd(data)
        if not m:
            client.message('^7Invalid data, try !help knchallenge')
            return

        sclient = self._adminPlugin.findClientPrompt(m[0], client)
        if not sclient:
            return

        existing_challenge = self._challenges.get(sclient.cid)
        if existing_challenge:
            client.message(f'There is already a challenge underway for {sclient.exactName}')
            return

        if len(self._challenges) >= self._max_challenges:
            client.message(f'There are already several challenges underway, try again later')
            return

        self.console.write('bigtext "^7New challenge : try to slice ^3%s"' % sclient.exactName)
        challenge_thread = threading.Timer(self._challengeDuration, self.challengeEnd, args=(sclient.cid, sclient.exactName))
        challenge_thread.start()
        self._challenges[sclient.cid] = challenge_thread
        self.debug('Starting challenge thread : %d seconds' % self._challengeDuration)

    def cmd_allstats(self, data, client, cmd=None):
        """\
        [<player>] Displays the total knife kills for you/someone from xlrstats
        """
        if self._xlrstatsPlugin is None:
            client.message('Command unavailable, please try later"')
            return

        # cid = client.id
        fclient = client
        if data:
            m = self._adminPlugin.parseUserCmd(data)
            if m:
                sclient = self._adminPlugin.findClientPrompt(m[0], client)
                if not sclient:
                    # msg = 'No player found'
                    return
                else:
                    fclient = sclient

        self.allStats(client, fclient)

    def cmd_testscore(self, data, client, cmd=None):
        """\
        <player> Displays the XLR skills points gained when killing a player
        """
        if self._xlrstatsPlugin is None:
            client.message('Command unavailable, please try later"')
            return

        if not data:
            client.message('Wrong parameter, try !help kntestscore')
        else:
            m = self._adminPlugin.parseUserCmd(data)
            if m:
                sclient = self._adminPlugin.findClientPrompt(m[0], client)
                if not sclient:
                    pass
                    # cmd.sayLoudOrPM(client, 'No player found')
                else:
                    # if client.cid == sclient.cid:
                    # client.message('You cannot slice yourself...')
                    # return
                    self.testScore(client, sclient)

    def cmd_record(self, data, client, cmd=None):
        """\
        Displays the best knife user for the current map
        """
        message = '^7No record found on this map'
        (currentRecordHolder, currentRecordValue) = self.getRecord()
        if (currentRecordHolder != '') and (currentRecordValue != ''):
            message = '^7Knife kills record on this map: ^1%s ^2%s ^7kills' % (currentRecordHolder, currentRecordValue)
            # message = '^7Knife kills record on this map: ^1%s %s' % (currentRecordHolder, currentRecordValue)
        client.message(message)

    def displayScores(self, fromCmd):
        # From stats plugin
        listKills = []
        ck = self._cutKillers
        for cid, c in ck.items():
            listKills.append((c, ck[cid].var(self, 'knifeKills', 0).value))

        if listKills:
            tmplist = [(x[1], x) for x in listKills]
            tmplist.sort(key=operator.itemgetter(0))
            listKills = [x for (key, x) in tmplist]
            listKills.reverse()

            limit = self._nbTop
            if len(listKills) < limit:
                limit = len(listKills)

            i = 0
            results = []
            for c, kills in listKills:
                i = i + 1
                results.append('^1#%d. ^4%s ^1(^3%d^1)^7' % (i, c.name, c.var(self, 'knifeKills', 0).value))
                if i >= limit:
                    break

            self.console.say(
                '^1Top %d knife killers (total %d)  : %s' % (limit, self._nbKK, ' ,'.join(results)))

    def someoneKilled(self, client, target, data=None):
        if data[1] == self.console.UT_MOD_KNIFE:
            self._nbKK += 1
            if self._nbKK == 1:
                self.console.write('bigtext "^3%s ^7: first knife kill"' % client.exactName)
            numCuts = 1
            if client.cid not in self._cutKillers:
                client.setvar(self, 'knifeKills', 1)
                self._cutKillers[client.cid] = client
            else:
                numCuts = self._cutKillers[client.cid].var(self, 'knifeKills', 0).value + 1
                self._cutKillers[client.cid].setvar(self, 'knifeKills', numCuts)
            self.debug('Client %s, %d knife kills' % (client.name, client.var(self, 'knifeKills', 0).value))
            # if not numCuts % 3:
            # self.console.write('bigtext "%s : %d knife kills !"' % (client.name, client.var(self, 'knifeKills', 0).value))
            if (not self._stfu) and (numCuts in self._msgLevels):
                msg = self.getMessage('knkills_%d' % numCuts, {'name': client.exactName, 'score': numCuts})
                self.console.write('bigtext "%s"' % msg)

            if self._challenges and target is not None:
                self.debug('challenges and target exists')
                challenge_thread = self._challenges.pop(target.cid, None)
                if challenge_thread:
                    self._cancel_challenge_thread(challenge_thread)
                    self.console.write(
                        'bigtext "^7Good job ^3%s^7, you sliced ^3%s ^7!"' % (client.exactName, target.exactName))

    def allStats(self, client, fclient):
        knifeXlrId = self._xlrstatsPlugin.get_WeaponStats(self._knifeId).id
        # self.debug('XLR knife id = %d' % knifeXlrId)
        player = self._xlrstatsPlugin.get_PlayerStats(fclient)
        xlrResult = self._xlrstatsPlugin.get_WeaponUsage(knifeXlrId, player.id)
        # self.info('Nb of kills = %d' % xlrResult.kills)
        client.message('^7Total knife kills (xlrstats): ^2%d' % xlrResult.kills)

    def challengeEnd(self, target_id=None, target_name=None):
        self.debug('Challenge has ended')
        self.console.write('bigtext "^3%s ^7has won the knife challenge!"' % target_name)
        try:
            del self._challenges[target_id]
        except KeyError:
            pass

    def testScore(self, client, sclient):
        # for cmd in self._xlrstatsPlugin.config.options('commands'):
        # self.debug(cmd)
        killerstats = self._xlrstatsPlugin.get_PlayerStats(client)
        victimstats = self._xlrstatsPlugin.get_PlayerStats(sclient)
        killer_prob = self._xlrstatsPlugin.win_prob(killerstats.skill, victimstats.skill)
        victim_prob = self._xlrstatsPlugin.win_prob(victimstats.skill, killerstats.skill)
        self.debug('Killer skill = %s, victim skill = %s' % (killerstats.skill, victimstats.skill))
        try:
            weapon_factor = self.config.getfloat('settings', 'knifefactor')
        except:
            weapon_factor = 1.0
        kill_bonus = self._xlrstatsPlugin.kill_bonus
        if killerstats.kills > self._xlrstatsPlugin.Kswitch_kills:
            KfactorKiller = self._xlrstatsPlugin.Kfactor_low
        else:
            KfactorKiller = self._xlrstatsPlugin.Kfactor_high
        if victimstats.kills > self._xlrstatsPlugin.Kswitch_kills:
            KfactorVictim = self._xlrstatsPlugin.Kfactor_low
        else:
            KfactorVictim = self._xlrstatsPlugin.Kfactor_high
        # skillGained = kill_bonus * Kfactor * weapon_factor * (1-killer_prob)
        skillGained = kill_bonus * KfactorKiller * (1 - killer_prob)
        skillLost = KfactorVictim * (0 - victim_prob)
        self.debug('kill bonus=%s, kfactorKiller=%s, kfactorVictim=%s, weapfact =%s, killer_prb=%s' % (
            kill_bonus, KfactorKiller, KfactorVictim, weapon_factor, killer_prob))
        # client.message('%s*%s=^1%s ^7skill points gained for slicing ^3%s^7, opponent will loose %s*%s=^1%s' % (str(weapon_factor), str(round(skillGained, 2)), str(round(weapon_factor*skillGained, 2)), sclient.exactName, str(weapon_factor), str(round(-1*skillLost, 2)), str(round(-1*weapon_factor*skillLost, 2))))
        # client.message('%s*%s=^1%s ^7skill points gained for slicing ^3%s^7, opponent will loose %s*%s=^1%s' % (str(weapon_factor), str(skillGained), str(weapon_factor*skillGained), sclient.exactName, str(weapon_factor), str(-1*skillLost), str(-1*weapon_factor*skillLost)))
        client.message(
            '%s*%1.02f=^1%1.02f ^7skill points gained for slicing ^3%s^7, opponent will loose %s*%1.02f=^1%1.02f' % (
                str(weapon_factor), skillGained, weapon_factor * skillGained, sclient.exactName, str(weapon_factor),
                -1 * skillLost, -1 * weapon_factor * skillLost))

    def updateHallOfFame(self, cutKillers, mapName):
        if len(cutKillers) == 0:
            return

        newRecord = 0

        # Find the best knife player
        listKills = []
        ck = cutKillers
        for cid, c in ck.items():
            listKills.append((c, ck[cid].var(self, 'knifeKills', 0).value))

        if listKills:
            tmplist = [(x[1], x) for x in listKills]
            tmplist.sort(key=operator.itemgetter(0))
            listKills = [x for (key, x) in tmplist]
            listKills.reverse()

        bestPlayer, topKills = listKills[0]
        if topKills == 0:
            return

        # Retrieve data for current map (if exists)
        currentMap = mapName
        currentRecordHolder, currentRecordValue = self.getRecord()
        if currentRecordValue == '-1':
            self.error('SQL error, cannot get record')
            return

        # Retrieve HOF for the current map
        if (currentRecordHolder != '') and (currentRecordValue != '0'):
            if topKills > int(currentRecordValue):
                # New record
                newRecord = 1
                currentRecordHolder = bestPlayer.exactName
                currentRecordValue = topKills
                q = """UPDATE plugin_hof SET player_id=%s, score=%s WHERE plugin_name='%s' and map_name='%s'""" % (
                    bestPlayer.id, topKills, self._hof_plugin_name, currentMap
                )
                try:
                    cursor = self.query(q)
                except:
                    self.error('Can\'t execute query : %s' % q)
        else:
            # New record
            newRecord = 1
            currentRecordHolder = bestPlayer.exactName
            currentRecordValue = topKills
            q = """INSERT INTO plugin_hof (plugin_name, map_name, player_id, score) VALUES('%s', '%s', %s, %s)""" % (
                self._hof_plugin_name, currentMap, bestPlayer.id, topKills
            )
            try:
                cursor = self.query(q)
            except:
                self.error('Can\'t execute query : %s' % q)
        if newRecord:
            message = '^2%s ^7knife kills: congratulations ^3%s^7, new record on this map!!' % (
                currentRecordValue, currentRecordHolder)
        else:
            message = '^7Knife kills record on this map: ^1%s ^2%s ^7kills' % (currentRecordHolder, currentRecordValue)
        self.console.say(message)

    def getRecord(self):
        RecordHolder = ''
        RecordValue = '-1'
        q = f"SELECT * FROM plugin_hof WHERE plugin_name='{self._hof_plugin_name}' and map_name='{self.console.game.mapName}'"
        self.debug('getRecord : %s', q)
        try:
            cursor = self.query(q)
        except:
            self.error('Can\'t execute query : %s' % q)
            return RecordHolder, RecordValue

        r = cursor.getOneRow()
        if r:
            # clients:899 -> m = re.match(r'^@([0-9]+)$', id) -> add @
            id = '@' + str(r['player_id'])
            clientList = self.console.clients.getByDB(id)
            if clientList:
                RecordHolder = clientList[0].exactName
                self.debug('record holder found: %s' % clientList[0].exactName)
            RecordValue = r['score']
        else:
            RecordValue = 0

        return RecordHolder, str(RecordValue)
