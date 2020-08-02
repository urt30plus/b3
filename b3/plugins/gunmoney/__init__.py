__version__ = '4.0'
__author__ = 'LouK,|30+|money'

import calendar
import re
import time
import threading

import b3
import b3.cron
import b3.events
import b3.functions
import b3.plugin


def cdate():
    time_epoch = time.time()
    time_struct = time.gmtime(time_epoch)
    date = time.strftime('%Y-%m-%d %H:%M:%S', time_struct)
    mysql_time_struct = time.strptime(date, '%Y-%m-%d %H:%M:%S')
    cdate = calendar.timegm(mysql_time_struct)
    return cdate


class SpreeStats:
    kills = 0
    deaths = 0

    god = 0
    inv = False

    spec = True
    suicide = True
    connecting = False
    _tp_counter = 1
    _kill_counter = 1
    _dis_counter = 1


class GunmoneyPlugin(b3.plugin.Plugin):
    requiresConfigFile = False
    _cronTab = None
    time_swap = 5
    _clientvar_name = 'spree_info'
    _swap_num = True
    _nim = True
    _swap_status = True

    def onStartup(self):
        # get the admin plugin so we can register commands
        self.registerEvent(b3.events.EVT_CLIENT_SUICIDE)
        self.registerEvent(b3.events.EVT_CLIENT_TEAM_CHANGE)
        self.registerEvent(b3.events.EVT_CLIENT_DISCONNECT)
        self.registerEvent(b3.events.EVT_CLIENT_CONNECT)
        self.registerEvent(b3.events.EVT_GAME_ROUND_START)
        self.registerEvent(b3.events.EVT_CLIENT_KILL)
        self.registerEvent(b3.events.EVT_CLIENT_AUTH)
        self.registerEvent(b3.events.EVT_GAME_EXIT)
        self._adminPlugin = self.console.getPlugin('admin')
        self.query = self.console.storage.query

        if not self._adminPlugin:
            # something is wrong, can't start without admin plugin
            self.error('No se pudo encontrar el plugin de administracion')
            return

        # Register commands
        self._adminPlugin.registerCommand(self, 'buy', 0, self.cmd_getweapon, 'b')
        self._adminPlugin.registerCommand(self, 'buylist', 0, self.cmd_buy, 'bl')
        self._adminPlugin.registerCommand(self, 'price', 0, self.cmd_price, 'cost')
        self._adminPlugin.registerCommand(self, 'money', 0, self.cmd_money, 'mo')
        self._adminPlugin.registerCommand(self, 'moneytopstats', 0, self.cmd_moneytopstats, 'motopstats')
        self._adminPlugin.registerCommand(self, 'teleport', 0, self.cmd_teleport, 'tp')
        self._adminPlugin.registerCommand(self, 'kill', 0, self.cmd_kill, 'kl')
        self._adminPlugin.registerCommand(self, 'givemoney', 100, self.cmd_update, 'gm')
        self._adminPlugin.registerCommand(self, 'pay', 0, self.cmd_pay, 'give')
        self._adminPlugin.registerCommand(self, 'disarm', 0, self.cmd_disarm, 'dis')
        self._adminPlugin.registerCommand(self, 'spree', 0, self.cmd_spree)
        self._adminPlugin.registerCommand(self, 'spec', 20, self.cmd_spec)

    def onEvent(self, event):
        if event.type == b3.events.EVT_GAME_ROUND_START:
            self.autoMessage(event)

        elif (event.type == b3.events.EVT_CLIENT_AUTH):
            sclient = event.client
            if (sclient.maxLevel < 100):
                q = ('SELECT * FROM `plugin_gunmoney` WHERE `client_id` = "%s"' % (sclient.id))
                self.debug(q)
                cursor = self.console.storage.query(q)
                if (cursor.rowcount == 0):
                    q = ('INSERT INTO `plugin_gunmoney`(`client_id`, `balance`) VALUES (%s, 10000)' % (sclient.id))
                    self.console.storage.query(q)

        elif (event.type == b3.events.EVT_CLIENT_DISCONNECT):
            sclient = event.client
            q = ('DELETE FROM automoney WHERE client_id = "%s"' % (sclient.id))
            self.console.storage.query(q)

        elif (event.type == b3.events.EVT_GAME_EXIT):
            if self._swap_status:
                if self._swap_num:
                    if self._nim:
                        self._nim = False
                        TimeS1 = GunmoneyPlugin.time_swap * 1
                        swaptimer = threading.Timer(TimeS1, self.Fin_S2)
                        swaptimer.start()
                    else:
                        self._swap_num = False
                        self._nim = True
                else:
                    self._swap_num = True
                    TimeS1 = GunmoneyPlugin.time_swap * 1
                    swaptimer = threading.Timer(TimeS1, self.Fin_S1)
                    swaptimer.start()

        elif (event.type == b3.events.EVT_CLIENT_TEAM_CHANGE):
            sclient = event.client
            if (sclient.team == b3.TEAM_SPEC):
                if (sclient.maxLevel < 10):
                    Stats = self.get_spree_stats(sclient)
                    self.console.write("forceteam %s" % (sclient.cid))
                    if Stats.spec:
                        if Stats.connecting == False:
                            warnings = sclient.numWarnings
                            sclient.warn(duration='10m',
                                         warning='^1WARNING^7 [^3%s^7]: Do not join spec team ^3Newb' % (warnings + 1))
                            self.console.say('Do not join spec team Newbie %s' % (sclient.exactName))
                            if warnings >= 2:
                                sclient.tempban(duration='5m', reason='Too many warnings: Do not join spec team')
                        else:
                            Stats.connecting = False
                    else:
                        Stats.spec = True

        elif (event.type == b3.events.EVT_CLIENT_SUICIDE):
            sclient = event.client
            Stats = self.get_spree_stats(sclient)
            sdata = event.data
            if sdata[1] != self.console.MOD_LAVA:
                if Stats.suicide:
                    warnings = sclient.numWarnings
                    sclient.warn(duration='10m',
                                 warning='^1WARNING^7 [^3%s^7]: Do not kill yourself idiot' % (warnings + 1))
                    self.console.say('%s, try to kill yourself again ^1n00b' % (sclient.exactName))
                    if warnings >= 2:
                        sclient.tempban(duration='5m', reason='Too many warnings: Do not kill yourself idiot')
                else:
                    Stats.suicide = True

        elif event.type == b3.events.EVT_CLIENT_KILL:
            self.knifeKill(event.client, event.target, event.data)
            self.spreeKill(event.client, event.target)

        elif (event.type == b3.events.EVT_CLIENT_CONNECT):
            sclient = event.client
            Status = self.get_spree_stats(sclient)
            Status.connecting = True
            Status.spec = False

    def Fin_S1(self):
        self.console.write("restart")
        self.console.write("swapteams")

    def Fin_S2(self):
        self.console.write("swapteams")

    def update(self):
        for c in self.console.clients.getList():
            if (c.team != b3.TEAM_SPEC) or (c.maxLevel < 100):
                q = ('SELECT * FROM automoney WHERE client_id ="%s"' % (c.id))
                cursor = self.console.storage.query(q)
                r = cursor.getRow()
                veces = r['veces']
                fin = r['datefin']
                datenow = cdate()
                self.debug('%s - %s' % (fin, datenow))
                if int(fin) < int(datenow):
                    fin = 3600 + cdate()
                    # fin = 60 + cdate()
                    q = ('UPDATE `automoney` SET `datefin` =%s, veces=veces+1 WHERE client_id = "%s"' % (fin, c.id))
                    self.console.storage.query(q)
                    veces2 = 5000 * veces
                    q = ('UPDATE `plugin_gunmoney` SET `balance` = balance+%s WHERE client_id = "%s"' % (veces2, c.id))
                    self.console.storage.query(q)
                    if (veces == 1):
                        self.console.say('%s ^7For having played ^21 hour ^7you won ^2%s' % (c.exactName, veces2))
                    else:
                        self.console.say(
                            '%s ^7For having played ^2%s hours ^7you won ^2%s' % (c.exactName, veces, veces2))

    def knifeKill(self, client, target, data=None):
        if (client.maxLevel < 100):
            if (client.team == b3.TEAM_RED and client.id != target.id):
                if (data[
                    1] == self.console.UT_MOD_KNIFE or self.console.UT_MOD_KNIFE_THROWN or self.console.UT_MOD_HEGRENADE or self.console.UT_MOD_BLED or self.console.UT_MOD_KICKED):
                    q = ('UPDATE `plugin_gunmoney` SET `balance` = balance+300 WHERE client_id = "%s"' % (client.id))
                    self.console.storage.query(q)
                    client.message('^7For kill %s you won ^2300 ^7Coins' % (target.exactName))

            if (client.team == b3.TEAM_BLUE and client.id != target.id):
                if (data[
                    1] == self.console.UT_MOD_BERETTA or self.console.UT_MOD_DEAGLE or self.console.UT_MOD_MP5K or self.console.UT_MOD_SPAS
                        or self.console.UT_MOD_UMP45 or self.console.UT_MOD_LR300 or self.console.UT_MOD_G36 or self.console.UT_MOD_PSG1 or self.console.UT_MOD_HK69 or self.console.UT_MOD_BLED
                        or self.console.UT_MOD_KICKED or self.console.UT_MOD_SR8 or self.console.UT_MOD_AK103 or self.console.UT_MOD_NEGEV or self.console.UT_MOD_HK69_HIT or self.console.UT_MOD_M4 or self.console.UT_MOD_GOOMBA):
                    q = ('UPDATE `plugin_gunmoney` SET `balance` = balance+600 WHERE client_id = "%s"' % (client.id))
                    self.console.storage.query(q)
                    client.message('^7For kill %s you won ^2600 ^7Coins' % (target.exactName))

            if (data[1] == self.console.UT_MOD_KICKED):
                self.console.write("gh %s +25" % (client.cid))
                self.console.say("%s ^7made a ^6Boot ^7kill! ^1= ^2+25 ^7hps" % client.exactName)

    def spreeKill(self, client=None, victim=None):
        if client and client.id != victim.id:
            spreeStats = self.get_spree_stats(client)
            spreeStats.kills += 1
            if client.team == b3.TEAM_RED:
                if spreeStats.kills == 5:
                    q = ('UPDATE `plugin_gunmoney` SET `balance` = balance+500 WHERE client_id = "%s"' % (client.id))
                    self.debug(q)
                    cursor = self.console.storage.query(q)
                    cursor.close()
                    self.console.say('%s made ^55 ^7kills in a row and won ^2500 ^7Coins!' % client.exactName)
                if spreeStats.kills == 10:
                    q = ('UPDATE `plugin_gunmoney` SET `balance` = balance+1000 WHERE client_id = "%s"' % (client.id))
                    self.debug(q)
                    cursor = self.console.storage.query(q)
                    cursor.close()
                    self.console.say('%s made ^510 ^7kills in a row and won ^21000 ^7Coins!' % client.exactName)
                if spreeStats.kills == 15:
                    q = ('UPDATE `plugin_gunmoney` SET `balance` = balance+1500 WHERE client_id = "%s"' % (client.id))
                    self.debug(q)
                    cursor = self.console.storage.query(q)
                    cursor.close()
                    self.console.say('%s made ^55 ^7kills in a row and won ^21500 ^7Coins!' % client.exactName)
                if spreeStats.kills == 20:
                    q = ('UPDATE `plugin_gunmoney` SET `balance` = balance+2500 WHERE client_id = "%s"' % (client.id))
                    self.debug(q)
                    cursor = self.console.storage.query(q)
                    cursor.close()
                    self.console.say('%s made ^55 ^7kills in a row, you won ^22500 ^7Coins!' % client.exactName)

            elif client.team == b3.TEAM_BLUE:
                if spreeStats.kills == 5:
                    q = ('UPDATE `plugin_gunmoney` SET `balance` = balance+1000 WHERE client_id = "%s"' % (client.id))
                    self.debug(q)
                    cursor = self.console.storage.query(q)
                    cursor.close()
                    self.console.say('%s made ^55 ^7kills in a row and won ^21000 ^7Coins!' % client.exactName)
                if spreeStats.kills == 10:
                    q = ('UPDATE `plugin_gunmoney` SET `balance` = balance+2000 WHERE client_id = "%s"' % (client.id))
                    self.debug(q)
                    cursor = self.console.storage.query(q)
                    cursor.close()
                    self.console.say('%s made ^510 ^7kills in a row and won ^22000 ^7Coins!' % client.exactName)
                if spreeStats.kills == 15:
                    q = ('UPDATE `plugin_gunmoney` SET `balance` = balance+3000 WHERE client_id = "%s"' % (client.id))
                    self.debug(q)
                    cursor = self.console.storage.query(q)
                    cursor.close()
                    self.console.say('%s made ^55 ^7kills in a row and won ^23000 ^7Coins!' % client.exactName)
                if spreeStats.kills == 20:
                    q = ('UPDATE `plugin_gunmoney` SET `balance` = balance+5000 WHERE client_id = "%s"' % (client.id))
                    self.debug(q)
                    cursor = self.console.storage.query(q)
                    cursor.close()
                    self.console.say('%s made ^55 ^7kills in a row, you won ^25000 ^7Coins!' % client.exactName)
            spreeStats.deaths = 0

        if victim and client.id != victim.id:
            spreeStats = self.get_spree_stats(victim)
            spreeStats.deaths += 1
            spreeStats.kills = 0

    def init_spree_stats(self, client):
        client.setvar(self, self._clientvar_name, SpreeStats())

    def get_spree_stats(self, client):
        if not client.isvar(self, self._clientvar_name):
            client.setvar(self, self._clientvar_name, SpreeStats())

        return client.var(self, self._clientvar_name).value

    def cmd_spree(self, data, client, cmd=None):
        spreeStats = self.get_spree_stats(client)

        if spreeStats.kills > 0:
            cmd.sayLoudOrPM(client, '^7You have ^2%s^7 kills in a row' % spreeStats.kills)
        elif spreeStats.deaths > 0:
            cmd.sayLoudOrPM(client, '^7You have ^1%s^7 deaths in a row' % spreeStats.deaths)
        else:
            cmd.sayLoudOrPM(client, '^7You\'re not having a spree right now')

        if client.team == b3.TEAM_BLUE:
            cmd.sayLoudOrPM(client, '^55 ^7Kills ^1-> ^21000 ^7Coins')
            cmd.sayLoudOrPM(client, '^510 ^7Kills ^1-> ^22000 ^7Coins')
            cmd.sayLoudOrPM(client, '^515 ^7Kills ^1-> ^23000 ^7Coins')
            cmd.sayLoudOrPM(client, '^520 ^7Kills ^1-> ^25000 ^7Coins')
        elif client.team == b3.TEAM_RED:
            cmd.sayLoudOrPM(client, '^55 ^7Kills ^1-> ^2500 ^7Coins')
            cmd.sayLoudOrPM(client, '^510 ^7Kills ^1-> ^21000 ^7Coins')
            cmd.sayLoudOrPM(client, '^515 ^7Kills ^1-> ^21500 ^7Coins')
            cmd.sayLoudOrPM(client, '^520 ^7Kills ^1-> ^22500 ^7Coins')

    def cmd_teleport(self, data, client, cmd=None):
        if (client.maxLevel >= 100):
            input = self._adminPlugin.parseUserCmd(data)
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if not data:
                client.message('^7Type !teleport <player>')
                return False
            self.console.write("teleport %s %s" % (client.cid, sclient.cid))
        else:
            q = ('SELECT * FROM `plugin_gunmoney` WHERE `client_id` = "%s"' % (client.id))
            self.debug(q)
            cursor = self.console.storage.query(q)
            r = cursor.getRow()
            balance = r['balance']
            cursor.close()
            input = self._adminPlugin.parseUserCmd(data)
            if not data:
                client.message('Correct usage is ^2!teleport ^4<player>')
                return False
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if not sclient: return False
            status = self.get_spree_stats(client)
            price = teleport.price * status._tp_counter
            if (balance > price):
                if client.team == sclient.team:
                    q = ('UPDATE `plugin_gunmoney` SET `balance` = balance-%s WHERE client_id = "%s"' % (price, client.id))
                    self.console.storage.query(q)
                    self.console.write("teleport %s %s" % (client.cid, sclient.cid))
                    client.message('^7You teleported to %s^7. ^1-%s ^7Coins' % (sclient.exactName, price))
                    status._tp_counter += 1
                    return True
                elif (balance > (price * 5)):
                    price *= 5
                    q = ('UPDATE `plugin_gunmoney` SET `balance` = balance-%s WHERE client_id = "%s"' % (price, client.id))
                    self.console.storage.query(q)
                    self.console.write("teleport %s %s" % (client.cid, sclient.cid))
                    client.message('^7You teleported to %s^7. ^1-%s ^7Coins' % (sclient.exactName, price))
                    status._tp_counter += 1
                    return True
                else:
                    self.noCoins(client, balance)
            else:
                self.noCoins(client, balance)

    def cmd_kill(self, data, client, cmd=None):
        if (client.maxLevel >= 100):
            input = self._adminPlugin.parseUserCmd(data)
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            Stats = self.get_spree_stats(sclient)
            Stats.suicide = False
            self.console.write("kill %s" % (sclient.cid))
        else:
            q = ('SELECT * FROM `plugin_gunmoney` WHERE `client_id` = "%s"' % (client.id))
            cursor = self.console.storage.query(q)
            r = cursor.getRow()
            balance = r['balance']
            cursor.close()
            input = self._adminPlugin.parseUserCmd(data)
            if not data:
                client.message('Correct usage is ^2!kill ^4<player>')
                return False
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if not sclient: return False
            status = self.get_spree_stats(client)
            price = kill.price * status._kill_counter
            if (balance > price):
                status.suicide = False
                q = ('UPDATE `plugin_gunmoney` SET `balance` = balance-%s WHERE client_id = "%s"' % (price, client.id))
                self.console.storage.query(q)
                self.console.write("kill %s" % (sclient.cid))
                client.message('You killed %s! ^1-%s ^7Coins' % (sclient.exactName, price))
                status._kill_counter += 1
                return True
            else:
                self.noCoins(client, balance)

    def cmd_disarm(self, data, client, cmd=None):
        if (client.maxLevel >= 100):
            input = self._adminPlugin.parseUserCmd(data)
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            self.console.write("gw %s -@" % (sclient.cid))
        else:
            q = ('SELECT * FROM `plugin_gunmoney` WHERE `client_id` = "%s"' % (client.id))
            cursor = self.console.storage.query(q)
            r = cursor.getRow()
            balance = r['balance']
            cursor.close()
            input = self._adminPlugin.parseUserCmd(data)
            if not data:
                client.message('Correct usage is ^2!disarm ^4<player>')
                return False
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if not sclient: return False
            status = self.get_spree_stats(client)
            price = disarm.price * status._dis_counter
            if (balance > price):
                if client.team != sclient.team:
                    if (client.team == b3.TEAM_RED):
                        q = ('UPDATE `plugin_gunmoney` SET `balance` = balance-%s WHERE client_id = "%s"' % (price, client.id))
                        self.console.storage.query(q)
                        self.console.write("gw %s -@" % (sclient.cid))
                        client.message('You disarmed %s! ^1-%s ^7Coins' % (sclient.exactName, price))
                        status._dis_counter += 1
                        return True
                    else:
                        client.message('^2!disarm ^7can only be used by the red team')
                        return True
                else:
                    client.message('^7You Can only disarm Enemies.')
                    return True
            else:
                self.noCoins(client, balance)

    def cmd_update(self, data, client, cmd=None):
        input = self._adminPlugin.parseUserCmd(data)
        input = data.split(' ', 1)
        cname = input[0]
        dato = input[1]
        sclient = self._adminPlugin.findClientPrompt(cname, client)
        if not sclient: return False
        if not dato: return False
        q = ('UPDATE `plugin_gunmoney` SET `balance` = balance%s WHERE client_id = "%s"' % (dato, sclient.id))
        self.debug(q)
        cursor = self.console.storage.query(q)
        cursor.close()
        client.message('^2Done.')

    def cmd_spec(self, data, client, cmd=None):
        input = self._adminPlugin.parseUserCmd(data)
        cname = input[0]
        sclient = self._adminPlugin.findClientPrompt(cname, client)
        Stats = self.get_spree_stats(sclient)
        if not sclient:
            client.message('^7Force spec Who?')
            return False
        Stats.spec = False
        self.console.write("forceteam %s s" % (sclient.cid))
        client.message('^7%s forced to spectator.' % sclient.exactName)

    def cmd_pay(self, data, client, cmd=None):
        if data is None or data == "":
            client.message('^7Pay Who?')
            return False
        if '.' in data or ',' in data:
            self.console.say('That number is not allowed')
            return False
        cursor = self.console.storage.query('SELECT * FROM `plugin_gunmoney` WHERE `client_id` = "%s"' % (client.id))
        r = cursor.getRow()
        balance = r['balance']
        if client.connections < 10:
            client.message('You need at least ^610 ^7connections to the server to use this command')
            return True
        regex = re.compile(r"""^(?P<string>\w+) (?P<number>\d+)$""");
        match = regex.match(data)

        cname = match.group('string')
        dato = int(match.group('number'))
        sclient = self._adminPlugin.findClientPrompt(cname, client)
        if dato > balance:
            self.noCoins(client, balance)
            return False
        else:
            self.console.storage.query(
                'UPDATE `plugin_gunmoney` SET `balance` = balance+%s WHERE client_id = "%s"' % (dato, sclient.id))
            self.console.storage.query(
                'UPDATE `plugin_gunmoney` SET `balance` = balance-%s WHERE client_id = "%s"' % (dato, client.id))
            cursor.close()
            client.message("You paid ^2%s ^7Coins to %s" % (dato, sclient.exactName))

            sclient.message("^7%s paid you ^2%s ^7Coins" % (client.exactName, dato))
            return False

    def cmd_money(self, data, client, cmd=None):
        if data is None or data == '':
            if (client.maxLevel >= 100):
                client.message('^7You have: ^2Infinite')
                return True
            else:
                q = ('SELECT * FROM `plugin_gunmoney` WHERE `client_id` = "%s"' % (client.id))
                cursor = self.console.storage.query(q)
                r = cursor.getRow()
                balance = r['balance']
                client.message("You have: ^2%s ^7Coins" % (balance))
                cursor.close()
                return True
        else:
            input = self._adminPlugin.parseUserCmd(data)
            sclient = self._adminPlugin.findClientPrompt(input[0], client)
            if not sclient: return False
            if (sclient.maxLevel >= 100):
                client.message('%s has: ^2Infinite' % (sclient.exactName))
                return True
            else:
                q = ('SELECT * FROM `plugin_gunmoney` WHERE `client_id` = "%s"' % (sclient.id))
                cursor = self.console.storage.query(q)
                r = cursor.getRow()
                balance = r['balance']
                client.message("%s has: ^2%s ^7Coins" % (sclient.exactName, balance))
                cursor.close()
                return True

    def cmd_price(self, data, client, cmd=None):
        if not data:
            client.message('Correct usage is ^2!price ^4<weapon>')
            return False
        else:
            input = self._adminPlugin.parseUserCmd(data)
            weapon = input[0]
            status = self.get_spree_stats(client)
            if (weapon == "sr8") or (weapon == "SR8"):
                name = sr8.name
                value = sr8.value
                self.price(client, name, value)
            elif (weapon == "disarm") or (weapon == "dis"):
                value = disarm.price * status._dis_counter
                name = disarm.name
                self.price(client, name, value)
            elif (weapon == "teleport") or (weapon == "tp"):
                value = teleport.price * status._tp_counter
                name = teleport.name
                self.price(client, name, value)
            elif (weapon == "kill") or (weapon == "kl"):
                value = kill.price * status._kill_counter
                name = kill.name
                self.price(client, name, value)
            elif (weapon == "god") or (weapon == "godmode"):
                name = god.name
                value = ("%s(per round)" % god.value)
                self.price(client, name, value)
            elif (weapon == "inv") or (weapon == "invisible"):
                name = invisible.name
                value = ("%s(per minute)" % invisible.value)
                self.price(client, name, value)
            elif (weapon == "spas") or (weapon == "SPAS") or (weapon == "FRANCHI") or (weapon == "franchi"):
                name = spas.name
                value = spas.value
                self.price(client, name, value)
            elif (weapon == "mp5") or (weapon == "MP5") or (weapon == "MP5K") or (weapon == "mp5k"):
                name = mp5.name
                value = mp5.value
                self.price(client, name, value)
            elif (weapon == "ump") or (weapon == "UMP") or (weapon == "UMP45") or (weapon == "ump45"):
                name = ump.name
                value = ump.value
                self.price(client, name, value)
            elif (weapon == "HK69") or (weapon == "hk69") or (weapon == "hk") or (weapon == "HK"):
                name = hk.name
                value = hk.value
                self.price(client, name, value)
            elif (weapon == "lr300") or (weapon == "LR300") or (weapon == "LR") or (weapon == "lr"):
                name = lr.name
                value = lr.value
                self.price(client, name, value)
            elif (weapon == "PSG") or (weapon == "psg") or (weapon == "PSG1") or (weapon == "psg1"):
                name = psg.name
                value = psg.value
                self.price(client, name, value)
            elif (weapon == "lr300") or (weapon == "LR300") or (weapon == "LR") or (weapon == "lr"):
                name = lr.name
                value = lr.value
                self.price(client, name, value)
            elif (weapon == "g36") or (weapon == "G36"):
                name = g36.name
                value = g36.value
                self.price(client, name, value)
            elif (weapon == "ak") or (weapon == "AK") or (weapon == "AK103") or (weapon == "ak103"):
                name = ak.name
                value = ak.value
                self.price(client, name, value)
            elif (weapon == "NEGEV") or (weapon == "negev") or (weapon == "NE") or (weapon == "ne"):
                name = negev.name
                value = negev.value
                self.price(client, name, value)
            elif (weapon == "M4") or (weapon == "m4") or (weapon == "m4a") or (weapon == "M4A"):
                name = m4.name
                value = m4.value
                self.price(client, name, value)
            elif (weapon == "grenade") or (weapon == "GRENADE") or (weapon == "HE") or (weapon == "he"):
                name = he.name
                value = he.value
                self.price(client, name, value)
            elif (weapon == "SMOKE") or (weapon == "smoke") or (weapon == "SM") or (weapon == "sm"):
                name = smoke.name
                value = smoke.value
                self.price(client, name, value)
            elif (weapon == "KNIFE") or (weapon == "knife") or (weapon == "KN") or (weapon == "kn"):
                name = knife.name
                value = knife.value
                self.price(client, name, value)
            elif (weapon == "kevlar") or (weapon == "KEVLAR") or (weapon == "KEV") or (weapon == "kev"):
                name = kevlar.name
                value = kevlar.value
                self.price(client, name, value)
            elif (weapon == "helmet") or (weapon == "HELMET") or (weapon == "HEL") or (weapon == "hel"):
                name = helmet.name
                value = helmet.value
                self.price(client, name, value)
            elif (weapon == "medkit") or (weapon == "MEDKIT") or (weapon == "MEDIC") or (weapon == "medic") or (
                    weapon == "MED") or (weapon == "med"):
                name = medkit.name
                value = medkit.value
                self.price(client, name, value)
            elif (weapon == "TAC") or (weapon == "tac") or (weapon == "nvg") or (weapon == "NVG") or (
                    weapon == "goggles") or (weapon == "TacGoggles") or (weapon == "tacgoggles"):
                name = tac.name
                value = tac.value
                self.price(client, name, value)
            elif (weapon == "HEALTH") or (weapon == "health") or (weapon == "heal") or (weapon == "HEAL") or (
                    weapon == "H") or (weapon == "h"):
                name = health.name
                value = health.value
                self.price(client, name, value)
            else:
                client.message("Couldn't find: ^2%s" % input[0])
                return True

    def price(self, client, name, value):
        client.message("^2%s ^7Price: ^2%s" % (name, value))
        return True

    def cmd_moneytopstats(self, data, client, cmd=None, ext=False):
        """\
        [<#>] - list the top # players of the last 14 days.
        """
        b3.functions.start_daemon_thread(self.doTopList, (data, client, cmd, ext))
        return

    def doTopList(self, data, client, cmd=None, ext=False):
        limit = 3
        if data:
            if re.match('^[0-9]+$', data, re.I):
                limit = int(data)
                if limit > 10:
                    limit = 10

        #TODO: ensure this works with sqlite (UNIX_TIMESTAMP)
        q = (
            'SELECT c.id, c.name, m.client_id, m.balance FROM plugin_gunmoney m, clients c '
            'WHERE c.id = m.client_id AND c.id NOT IN ( SELECT distinct(c.id) FROM penalties p, clients c '
            'WHERE (p.type = "Ban" OR p.type = "TempBan") AND inactive = 0 AND p.client_id = c.id  AND '
            f'( p.time_expire = -1 OR p.time_expire > UNIX_TIMESTAMP(NOW()) ) ) ORDER BY m.balance DESC LIMIT 0, {limit}'
        )
        cursor = self.console.storage.query(q)
        if cursor and (cursor.rowcount > 0):
            message = '^2Money ^7Top ^5%s ^7Players:' % limit
            if ext:
                self.console.say(message)
            else:
                cmd.sayLoudOrPM(client, message)
            c = 1
            while not cursor.EOF:
                r = cursor.getRow()
                name = r['name']
                balance = r['balance']
                message = '^3# %s: ^7%s : ^2%s ^7Coins' % (c, name, balance)
                if ext:
                    self.console.say(message)
                else:
                    cmd.sayLoudOrPM(client, message)
                cursor.moveNext()
                c += 1
                time.sleep(1)

        return

    def cmd_buy(self, data, client, cmd=None):
        if client.team == b3.TEAM_BLUE:
            self.console.write('tell %s ^7Key:^2SR8^7 / Weapon:^2Remington SR8^7 / Price: ^2600' % (client.cid))
            self.console.write('tell %s ^7Key:^2SPAS^7 / Weapon:^2Franchi SPAS12^7 / Price: ^2300' % (client.cid))
            self.console.write('tell %s ^7Key:^2MP5^7 / Weapon:^2HK MP5K^7 / Price: ^2500' % (client.cid))
            self.console.write('tell %s ^7Key:^2UMP^7 / Weapon:^2UMP45^7 / Price: ^2550' % (client.cid))
            self.console.write('tell %s ^7Key:^2LR^7 / Weapon:^2ZM LR300^7 / Price: ^2650' % (client.cid))
            self.console.write('tell %s ^7Key:^2PSG^7 / Weapon:^2HK PSG1^7 / Price: ^21000' % (client.cid))
            self.console.write('tell %s ^7Key:^2HK^7 / Weapon:^2HK69 40mm^7 / Price: ^22000' % (client.cid))
            self.console.write('tell %s ^7Key:^2G36^7 / Weapon:^2HK G36^7 / Price: ^21000' % (client.cid))
            self.console.write('tell %s ^7Key:^2AK^7 / Weapon:^2AK103 7.62mm^7 / Price: ^2700' % (client.cid))
            self.console.write('tell %s ^7Key:^2NE^7 / Weapon:^2IMI Negev^7 / Price: ^2750' % (client.cid))
            self.console.write('tell %s ^7Key:^2M4^7 / Weapon:^2Colt M4A1^7 / Price: ^2650' % (client.cid))
            self.console.write('tell %s ^7Key:^2INV^7 / ^2Invisible^7 / Price: ^2150000' % (client.cid))
            self.console.write('tell %s ^7Key:^2GOD^7 / ^2Godmode^7 / Price: ^230000' % (client.cid))
            self.console.write('tell %s ^7Key:^2KL^7 / ^2Kill^7 / Price: ^210000' % (client.cid))
            self.console.write('tell %s ^7Key:^2TP^7 / ^2Teleport^7 / Team: ^21000 ^7Enemy: ^25000' % (client.cid))
            return True
        if client.team == b3.TEAM_RED:
            self.console.write('tell %s ^7Key:^2HE^7 / Weapon:^2HE Grenade^7 / Price:^2 350' % (client.cid))
            self.console.write('tell %s ^7Key:^2SM^7 / Weapon:^2SMOKE Grenade^7 / Price:^2 250' % (client.cid))
            self.console.write('tell %s ^7Key:^2KN^7 / Weapon:^2Knife^7 / Price:^2 300' % (client.cid))
            self.console.write('tell %s ^7Key:^2KEV^7 / Weapon:^2Kevlar Vest^7 / Price:^2 1200' % (client.cid))
            self.console.write('tell %s ^7Key:^2HEL^7 / Weapon:^2Helmet^7 / Price:^2 800' % (client.cid))
            self.console.write('tell %s ^7Key:^2MED^7 / Weapon:^2Medkit^7 / Price:^2 500' % (client.cid))
            self.console.write('tell %s ^7Key:^2NVG^7 / Weapon:^2TacGoggles^7 / Price:^2 200' % (client.cid))
            self.console.write('tell %s ^7Key:^2HEAL^7 / Weapon:^2Health^7 / Price:^2 2000' % (client.cid))
            self.console.write('tell %s ^7Key:^2KL^7 / ^2Kill^7 / Price: ^210000' % (client.cid))
            self.console.write('tell %s ^7Key:^2DIS^7 / ^2Disarm^7 / Price: ^23000' % (client.cid))
            self.console.write('tell %s ^7Key:^2TP^7 / ^2Teleport^7 / Team: ^21000 ^7Enemy: ^25000' % (client.cid))
            return True

    def putOnOff(self, client, status, key, value, weapon, name):
        q = ('SELECT * FROM `plugin_gunmoney` WHERE `client_id` = "%s"' % (client.id))
        self.debug(q)
        cursor = self.console.storage.query(q)
        r = cursor.getRow()
        blue = r['blue']
        red = r['red']
        if (status == "on") or (status == "ON"):
            if client.team == b3.TEAM_BLUE:
                if ("%s" % key) not in blue:
                    lol = blue.replace(blue, blue + ("%s" % key))
                    q = ('UPDATE `plugin_gunmoney` SET `blue`="%s",`price_blue`=price_blue+%s WHERE client_id = "%s"' % (
                    lol, value, client.id))
                    self.console.storage.query(q)
                    self.autoBuying(client, weapon)
                else:
                    self.autoBuyingAlready(client, weapon)
            elif client.team == b3.TEAM_RED:
                if ("%s" % key) not in red:
                    lol = red.replace(red, red + ("%s" % key))
                    q = ('UPDATE `plugin_gunmoney` SET `red`="%s",`price_red`=price_red+%s WHERE client_id = "%s"' % (
                    lol, value, client.id))
                    self.console.storage.query(q)
                    self.autoBuying(client, weapon)
                else:
                    self.autoBuyingAlready(client, weapon)
        elif (status == "off") or (status == "OFF"):
            if client.team == b3.TEAM_BLUE:
                if ("%s" % key) in blue:
                    lol = blue.replace(("%s" % key), "")
                    q = ('UPDATE `plugin_gunmoney` SET `blue`="%s",`price_blue`=price_blue-%s WHERE client_id = "%s"' % (
                    lol, value, client.id))
                    self.console.storage.query(q)
                    self.autoBuyingStop(client, weapon)
                else:
                    self.autoBuyingNot(client)
            elif client.team == b3.TEAM_RED:
                if ("%s" % key) in red:
                    lol = red.replace(("%s" % key), "")
                    q = ('UPDATE `plugin_gunmoney` SET `red`="%s",`price_red`=price_red-%s WHERE client_id = "%s"' % (
                    lol, value, client.id))
                    self.console.storage.query(q)
                    self.autoBuyingStop(client, weapon)
                else:
                    self.autoBuyingNot(client)

    def buyItem(self, client, key, value, name):
        q = ('SELECT * FROM `plugin_gunmoney` WHERE `client_id` = "%s"' % (client.id))
        self.debug(q)
        cursor = self.console.storage.query(q)
        r = cursor.getRow()
        balance = r['balance']
        if (client.maxLevel >= 100):
            self.console.write("gi %s %s" % (client.cid, key))
            return True
        else:
            if (value > balance):
                self.noCoins(client, balance)
            else:
                q = ('UPDATE `plugin_gunmoney` SET `balance` = balance-%s WHERE client_id = "%s"' % (value, client.id))
                self.console.storage.query(q)
                self.console.write("gi %s %s" % (client.cid, key))
                new_balance = (balance - value)
                self.clientBought(client, name, new_balance)

    def buyWeapon(self, client, key, value, name):
        q = ('SELECT * FROM `plugin_gunmoney` WHERE `client_id` = "%s"' % (client.id))
        self.debug(q)
        cursor = self.console.storage.query(q)
        r = cursor.getRow()
        balance = r['balance']
        if (client.maxLevel >= 100):
            self.console.write("gw %s %s" % (client.cid, key))
            return True
        else:
            if (value > balance):
                self.noCoins(client, balance)
            else:
                q = ('UPDATE `plugin_gunmoney` SET `balance` = balance-%s WHERE client_id = "%s"' % (value, client.id))
                self.console.storage.query(q)
                self.console.write("gw %s %s" % (client.cid, key))
                new_balance = (balance - value)
                self.clientBought(client, name, new_balance)

    def buyVeces(self, client, key, value, name, veces):
        q = ('SELECT * FROM `plugin_gunmoney` WHERE `client_id` = "%s"' % (client.id))
        self.debug(q)
        cursor = self.console.storage.query(q)
        r = cursor.getRow()
        balance = r['balance']
        valueTotal = (value * veces)

        if (valueTotal > balance):
            self.noCoins(client, balance)
        else:
            q = ('UPDATE `plugin_gunmoney` SET `balance` = balance-%s WHERE client_id = "%s"' % (valueTotal, client.id))
            self.console.storage.query(q)
            new_balance = (balance - valueTotal)
            self.console.write("gw %s %s +%s" % (client.cid, key, veces))
            client.message("You have Bought ^5%s ^2%s ^7You have:^2%s ^7Coins" % (veces, name, new_balance))

    def stopInv(self, client):
        Status = self.get_spree_stats(client)
        Status.inv = False
        client.message('Your ^4Invisible ^7time finishes in ^53')
        time.sleep(2)
        client.message('Your ^4Invisible ^7time finishes in ^52')
        time.sleep(2)
        client.message('Your ^4Invisible ^7time finishes in ^51')
        time.sleep(2)

        self.console.write('forcecvar %s cg_rgb "1"' % (client.cid))
        self.console.write('forcecvar %s cg_rgb "0"' % (client.cid))
        self.console.write('bigtext "%s ^7is now ^2Visible ^7again!"' % (client.exactName))

    def cmd_getweapon(self, data, client=None, cmd=None):
        """\
        ^6Type ^2!buy help / !buy ayuda
        """
        q = ('SELECT * FROM `plugin_gunmoney` WHERE `client_id` = "%s"' % (client.id))
        self.debug(q)
        cursor = self.console.storage.query(q)
        r = cursor.getRow()
        balance = r['balance']
        input = self._adminPlugin.parseUserCmd(data)
        if not data:
            client.message('Type ^2!buy help ^7to see how to use this command')
            return False
        weapon = input[0]
        status = input[1]
        veces = input[1]
        if (weapon == "help"):
            self.console.write('tell %s ^7Type ^2!money ^7to see your money' % (client.cid))
            self.console.write('tell %s ^7Type ^2!bl ^7to see the weapons and items prices' % (client.cid))
            self.console.write('tell %s ^7Type ^2!b ^4<weapon or item> ^7to buy whatever you want' % (client.cid))
            self.console.write(
                'tell %s ^7Type ^2!price <weapon, item or command> ^7to see a concrete price' % (client.cid))
            self.console.write(
                'tell %s ^7Type ^2!pay ^4<player> <amount> ^7to give money to a player' % (client.cid))
            self.console.write('tell %s ^7Type ^2!disarm ^4<player> ^7to disarm a human enemy' % (client.cid))
            self.console.write('tell %s ^7Type ^2!moneytopstats ^7to see money top players' % (client.cid))
            self.console.write('tell %s ^7Type ^2!tp ^4<player> ^7to teleport to a player' % (client.cid))
            self.console.write('tell %s ^7Type ^2!kill ^4<player> ^7to kill a enemy' % (client.cid))
            self.console.write('tell %s ^7Type ^2!b god ^7to buy godmode(for one round)' % (client.cid))
            self.console.write('tell %s ^7Type ^2!b inv ^7to buy invisible(until teams swap)' % (client.cid))
            return False
        if client.team == b3.TEAM_BLUE:
            if (weapon == "god") or (weapon == "godmode"):
                name = god.name
                value = god.value
                if (client.maxLevel >= 100):
                    self.console.write("exec god%s.cfg" % (client.cid))
                    self.console.write('bigtext "%s ^7Is ^6GoD"' % (client.exactName))
                    return True
                else:
                    if veces:
                        regex = re.compile(r"""^(?P<string>\w+) (?P<number>\d+)$""")
                        match = regex.match(data)
                        weapon = match.group('string')
                        veces = int(match.group('number'))
                        if veces <= 0:
                            client.message('You cant buy ^5%s ^7rounds!' % (veces))
                            return False
                        value = (value * veces)
                    else:
                        veces = 0
                    q = ('SELECT * FROM `plugin_gunmoney` WHERE `client_id` = "%s"' % (client.id))
                    cursor = self.console.storage.query(q)
                    r = cursor.getRow()
                    balance = r['balance']
                    if (balance > value):
                        q = ('UPDATE `plugin_gunmoney` SET `balance` = balance-%s WHERE client_id = "%s"' % (value, client.id))
                        self.console.storage.query(q)
                        self.console.write("exec god%s.cfg" % (client.cid))
                        self.console.write(
                            'bigtext "%s ^7bought ^6GoDMoDe ^7for ^5%s ^7Rounds!"' % (client.exactName, veces))
                        Status = self.get_spree_stats(client)
                        Status.god += veces
                        new_balance = (balance - value)
                        client.message('You Have Bought ^6%s ^7for ^5%s ^7Rounds You have: ^2%s ^7Coins' % (
                        name, veces, new_balance))
                    else:
                        self.noCoins(client, balance)

            elif (weapon == "inv") or (weapon == "invisible"):
                name = invisible.name
                value = invisible.value
                if (client.maxLevel >= 100):
                    self.console.write("inv %s" % (client.cid))
                    self.console.write('bigtext "%s ^7Is ^4Invisible"' % (client.exactName))
                    return True
                else:
                    if veces:
                        regex = re.compile(r"""^(?P<string>\w+) (?P<number>\d+)$""")
                        match = regex.match(data)
                        weapon = match.group('string')
                        veces = int(match.group('number'))
                        if veces <= 0:
                            client.message('You cant buy ^5%s ^7minutes!' % (veces))
                            return False
                        value = (value * veces)
                    else:
                        veces = 1
                    q = ('SELECT * FROM `plugin_gunmoney` WHERE `client_id` = "%s"' % (client.id))
                    cursor = self.console.storage.query(q)
                    r = cursor.getRow()
                    balance = r['balance']
                    if (balance > value):
                        q = ('UPDATE `plugin_gunmoney` SET `balance` = balance-%s WHERE client_id = "%s"' % (value, client.id))
                        self.console.storage.query(q)
                        self.console.write("inv %s" % (client.cid))
                        self.console.write(
                            'bigtext "%s ^7bought ^4Invisible ^7for ^5%s ^7minutes!"' % (client.exactName, veces))
                        Status = self.get_spree_stats(client)
                        Status.inv = True
                        t = threading.Timer((veces * 60), self.stopInv, args=[client])
                        t.start()
                        new_balance = (balance - value)
                        client.message(
                            'You Have Bought ^6%s ^7for ^5%s^7min You have: ^2%s ^7Coins' % (name, veces, new_balance))
                    else:
                        self.noCoins(client, balance)

            elif (weapon == "sr8") or (weapon == "SR8"):
                name = sr8.name
                key = sr8.key
                value = sr8.value

                if status:
                    self.putOnOff(client, status, key, value, weapon, name)
                    return False
                else:
                    self.buyWeapon(client, key, value, name)

            elif (weapon == "spas") or (weapon == "SPAS") or (weapon == "FRANCHI") or (weapon == "franchi"):
                name = spas.name
                key = spas.key
                value = spas.value

                if status:
                    self.putOnOff(client, status, key, value, weapon, name)
                    return False
                else:
                    self.buyWeapon(client, key, value, name)

            elif (weapon == "mp5") or (weapon == "MP5") or (weapon == "MP5K") or (weapon == "mp5k"):
                name = mp5.name
                key = mp5.key
                value = mp5.value

                if status:
                    self.putOnOff(client, status, key, value, weapon, name)
                    return False
                else:
                    self.buyWeapon(client, key, value, name)

            elif (weapon == "ump") or (weapon == "UMP") or (weapon == "UMP45") or (weapon == "ump45"):
                name = ump.name
                key = ump.key
                value = ump.value

                if status:
                    self.putOnOff(client, status, key, value, weapon, name)
                    return False
                else:
                    self.buyWeapon(client, key, value, name)

            elif (weapon == "HK69") or (weapon == "hk69") or (weapon == "hk") or (weapon == "HK"):
                name = hk.name
                key = hk.key
                value = hk.value

                if status:
                    self.putOnOff(client, status, key, value, weapon, name)
                    return False
                else:
                    self.buyWeapon(client, key, value, name)

            elif (weapon == "lr300") or (weapon == "LR300") or (weapon == "LR") or (weapon == "lr"):
                name = lr.name
                key = lr.key
                value = lr.value

                if status:
                    self.putOnOff(client, status, key, value, weapon, name)
                    return False
                else:
                    self.buyWeapon(client, key, value, name)

            elif (weapon == "PSG") or (weapon == "psg") or (weapon == "PSG1") or (weapon == "psg1"):
                name = psg.name
                key = psg.key
                value = psg.value

                if status:
                    self.putOnOff(client, status, key, value, weapon, name)
                    return False
                else:
                    self.buyWeapon(client, key, value, name)

            elif (weapon == "g36") or (weapon == "G36"):
                name = g36.name
                key = g36.key
                value = g36.value

                if status:
                    self.putOnOff(client, status, key, value, weapon, name)
                    return False
                else:
                    self.buyWeapon(client, key, value, name)

            elif (weapon == "ak") or (weapon == "AK") or (weapon == "AK103") or (weapon == "ak103"):
                name = ak.name
                key = ak.key
                value = ak.value

                if status:
                    self.putOnOff(client, status, key, value, weapon, name)
                    return False
                else:
                    self.buyWeapon(client, key, value, name)

            elif (weapon == "NEGEV") or (weapon == "negev") or (weapon == "NE") or (weapon == "ne"):
                name = negev.name
                key = negev.key
                value = negev.value

                if status:
                    self.putOnOff(client, status, key, value, weapon, name)
                    return False
                else:
                    self.buyWeapon(client, key, value, name)

            elif (weapon == "M4") or (weapon == "m4") or (weapon == "m4a") or (weapon == "M4A"):
                name = m4.name
                key = m4.key
                value = m4.value

                if status:
                    self.putOnOff(client, status, key, value, weapon, name)
                    return False
                else:
                    self.buyWeapon(client, key, value, name)
            else:
                client.message("^7Couldn't find: ^1%s^7" % input[0])
            return False

        if client.team == b3.TEAM_RED:
            weapon = input[0]
            status = input[1]
            veces = input[1]
            ############################## HE Grenade ##############################
            if (weapon == "grenade") or (weapon == "GRENADE") or (weapon == "HE") or (weapon == "he"):
                name = he.name
                key = he.key
                value = he.value

                if client.maxLevel >= 100:
                    if veces:
                        self.console.write("gw %s %s +%s" % (client.cid, key, veces))
                    else:
                        self.console.write("gw %s %s +1" % (client.cid, key))
                else:
                    if veces:
                        regex = re.compile(r"""^(?P<string>\w+) (?P<number>\d+)$""")
                        match = regex.match(data)
                        weapon = match.group('string')
                        veces = int(match.group('number'))
                        self.buyVeces(client, key, value, name, veces)
                    else:
                        self.buyWeapon(client, key, value, name)

            elif (weapon == "SMOKE") or (weapon == "smoke") or (weapon == "SM") or (weapon == "sm"):
                name = smoke.name
                key = smoke.key
                value = smoke.value

                if client.maxLevel >= 100:
                    if veces:
                        self.console.write("gw %s %s +%s" % (client.cid, key, veces))
                    else:
                        self.console.write("gw %s %s +1" % (client.cid, key))
                else:
                    if veces:
                        regex = re.compile(r"""^(?P<string>\w+) (?P<number>\d+)$""")
                        match = regex.match(data)
                        weapon = match.group('string')
                        veces = int(match.group('number'))
                        self.buyVeces(client, key, value, name, veces)
                    else:
                        self.buyWeapon(client, key, value, name)

            elif (weapon == "KNIFE") or (weapon == "knife") or (weapon == "kn") or (weapon == "KN"):
                name = knife.name
                key = knife.key
                value = knife.value

                if client.maxLevel >= 100:
                    if veces:
                        self.console.write("gw %s %s +%s" % (client.cid, key, veces))
                    else:
                        self.console.write("gw %s %s +1" % (client.cid, key))
                else:
                    if veces:
                        regex = re.compile(r"""^(?P<string>\w+) (?P<number>\d+)$""")
                        match = regex.match(data)
                        weapon = match.group('string')
                        veces = int(match.group('number'))
                        self.buyVeces(client, key, value, name, veces)
                    else:
                        self.buyWeapon(client, key, value, name)

            elif (weapon == "FLASH") or (weapon == "flash") or (weapon == "fla") or (weapon == "FLA"):
                name = flash.name
                key = flash.key
                value = flash.value
                if (client.maxLevel >= 100):
                    if (veces):
                        self.console.write("gw %s L %s" % (client.cid, veces))
                        return True
                    else:
                        self.console.write("gw %s L" % client.cid)
                        return True
                else:
                    client.message('^2Flash nade ^7is not allowed..')

            elif (weapon == "kevlar") or (weapon == "KEVLAR") or (weapon == "KEV") or (weapon == "kev"):
                name = kevlar.name
                key = kevlar.key
                value = kevlar.value

                if status:
                    self.putOnOff(client, status, key, value, weapon, name)
                    return False
                else:
                    self.buyItem(client, key, value, name)

            elif (weapon == "helmet") or (weapon == "HELMET") or (weapon == "HEL") or (weapon == "hel"):
                name = helmet.name
                key = helmet.key
                value = helmet.value

                if status:
                    self.putOnOff(client, status, key, value, weapon, name)
                    return False
                else:
                    self.buyItem(client, key, value, name)

            elif (weapon == "medkit") or (weapon == "MEDKIT") or (weapon == "MEDIC") or (weapon == "medic") or (
                    weapon == "MED") or (weapon == "med"):
                name = medkit.name
                key = medkit.key
                value = medkit.value

                if status:
                    self.putOnOff(client, status, key, value, weapon, name)
                    return False
                else:
                    self.buyItem(client, key, value, name)

            elif (weapon == "TAC") or (weapon == "tac") or (weapon == "nvg") or (weapon == "NVG") or (
                    weapon == "goggles") or (weapon == "TacGoggles") or (weapon == "tacgoggles"):
                name = tac.name
                key = tac.key
                value = tac.value

                if status:
                    self.putOnOff(client, status, key, value, weapon, name)
                    return False
                else:
                    self.buyItem(client, key, value, name)

            elif (weapon == "HEALTH") or (weapon == "health") or (weapon == "heal") or (weapon == "HEAL") or (
                    weapon == "H") or (weapon == "h"):
                value = health.value
                name = health.name
                if input[1]:
                    sclient = self._adminPlugin.findClientPrompt(input[1], client)
                    if sclient:
                        if (client.maxLevel >= 100):
                            self.console.write("gh %s +100" % sclient.cid)
                            return True
                        else:
                            if (value > balance):
                                self.noCoins(client, balance)
                            else:
                                q = ('UPDATE `plugin_gunmoney` SET `balance` = balance-%s WHERE client_id = "%s"' % (
                                value, client.id))
                                self.console.storage.query(q)
                                self.console.write("gh %s +100" % sclient.cid)
                                new_balance = balance - value
                                client.message('^7You have Bought ^2%s^7 to %s. You have:^2%s ^7coins' % (
                                name, sclient.exactName, new_balance))
                                return True
                else:
                    if (client.maxLevel >= 100):
                        self.console.write("gh %s +100" % client.cid)
                        return True
                    else:
                        if (value > balance):
                            self.noCoins(client, balance)
                        else:
                            q = ('UPDATE `plugin_gunmoney` SET `balance` = balance-%s WHERE client_id = "%s"' % (value, client.id))
                            self.console.storage.query(q)
                            self.console.write("gh %s +100" % client.cid)
                            new_balance = balance - value
                            self.clientBought(client, name, new_balance)
            else:
                client.message("Couldn't find: ^1%s" % input[0])
                return False

    def autoMessage(self, event):
        for c in self.console.clients.getList():
            if (c.team == b3.TEAM_BLUE):
                q = ('SELECT * FROM `plugin_gunmoney` WHERE `client_id` = "%s"' % (c.id))
                cursor = self.console.storage.query(q)
                r = cursor.getRow()
                blue = r['blue']
                balance = r['balance']
                price_blue = r['price_blue']
                if (c.maxLevel >= 100):
                    self.console.write("gw %s %s" % (c.cid, blue))
                else:
                    if blue:
                        weapon = []
                        if 'N' in blue:
                            weapon.insert(1, sr8.name)
                        if 'D' in blue:
                            weapon.insert(1, spas.name)
                        if 'E' in blue:
                            weapon.insert(1, mp5.name)
                        if 'F' in blue:
                            weapon.insert(1, ump.name)
                        if 'G' in blue:
                            weapon.insert(1, hk.name)
                        if 'H' in blue:
                            weapon.insert(1, lr.name)
                        if 'I' in blue:
                            weapon.insert(1, g36.name)
                        if 'J' in blue:
                            weapon.insert(1, psg.name)
                        if 'O' in blue:
                            weapon.insert(1, ak.name)
                        if 'Q' in blue:
                            weapon.insert(1, negev.name)
                        if 'S' in blue:
                            weapon.insert(1, m4.name)
                        if (balance > price_blue):
                            q = ('UPDATE `plugin_gunmoney` SET `balance` = balance-%s WHERE client_id = "%s"' % (price_blue, c.id))
                            self.console.storage.query(q)
                            self.console.write("gw %s %s" % (c.cid, blue))
                            c.message('You are autobuying: ^2%s' % ('^7, ^2'.join(weapon)))
                        else:
                            self.noCoins(c, balance)

                Status = self.get_spree_stats(c)
                if Status.god > 0:
                    self.console.write("exec god%s.cfg" % (c.cid))
                    Status.god -= 1
                    c.message('^5%s ^7Rounds left to lose your ^6GoD ^7status!' % Status.god)
                if Status.inv == True:
                    self.console.write("inv %s" % (c.cid))

            if (c.team == b3.TEAM_RED):
                q = ('SELECT * FROM `plugin_gunmoney` WHERE `client_id` = "%s"' % (c.id))
                cursor = self.console.storage.query(q)
                r = cursor.getRow()
                red = r['red']
                balance = r['balance']
                price_red = r['price_red']
                if (c.maxLevel >= 100):
                    self.console.write("gi %s %s" % (c.cid, red))
                else:
                    if red:
                        weapon = []
                        if 'K' in red:
                            weapon.insert(1, he.name)
                        if 'L' in red:
                            weapon.insert(1, flash.name)
                        if 'M' in red:
                            weapon.insert(1, smoke.name)
                        if 'A' in red:
                            weapon.insert(1, kevlar.name)
                        if 'B' in red:
                            weapon.insert(1, tac.name)
                        if 'C' in red:
                            weapon.insert(1, medkit.name)
                        if 'F' in red:
                            weapon.insert(1, helmet.name)
                        if (balance > price_red):
                            q = ('UPDATE `plugin_gunmoney` SET `balance` = balance-%s WHERE client_id = "%s"' % (price_red, c.id))
                            self.console.storage.query(q)
                            self.console.write("gi %s %s" % (c.cid, red))
                            c.message('You are autobuying: ^2%s' % ('^7, ^2'.join(weapon)))
                        else:
                            self.noCoins(c, balance)

    def clientBought(self, client, name, new_balance):
        client.message('You Have Bought ^2%s ^7You have: ^2%s ^7Coins' % (name, new_balance))

    def noCoins(self, client, balance):
        client.message("You ^1don't have ^7enough coins. You have: ^2%s ^7Coins" % balance)

    def autoBuying(self, client, weapon):
        client.message('You ^2started^7 to autobuy ^2%s' % weapon)

    def autoBuyingStop(self, client, weapon):
        client.message('You ^1stopped ^7to autobuy ^2%s' % weapon)

    def autoBuyingAlready(self, client, weapon):
        client.message('You ^2are already^7 autobuying ^2%s' % weapon)

    def autoBuyingNot(self, client):
        client.message("You ^1have not^7 activated Autobuy")


class god():
    name = 'GoD'
    value = 15000


class invisible():
    name = 'Invisible'
    value = 10000


class teleport():
    name = 'Teleport'
    price = 1000


class kill():
    name = 'Kill'
    price = 10000


class disarm():
    name = 'Disarm'
    price = 4000


class sr8():
    name = 'Remington SR8'
    key = 'N'
    value = 600


class spas():
    name = 'Franchi SPAS12'
    key = 'D'
    value = 450


class mp5():
    name = 'HK MP5K'
    key = 'E'
    value = 300


class ump():
    name = 'HK UMP45'
    key = 'F'
    value = 350


class hk():
    name = 'HK69 40mm'
    key = 'G'
    value = 2000


class lr():
    name = 'ZM LR300'
    key = 'H'
    value = 650


class psg():
    name = 'HK PSG1'
    key = 'J'
    value = 1000


class g36():
    name = 'HK G36'
    key = 'I'
    value = 1000


class ak():
    name = 'AK103 7.62mm'
    key = 'O'
    value = 700


class negev():
    name = 'IMI Negev'
    key = 'Q'
    value = 800


class m4():
    name = 'Colt M4A1'
    key = 'S'
    value = 650


class he():
    name = 'HE Grenade'
    key = 'K'
    value = 300


class smoke():
    name = 'Smoke Grenade'
    key = 'M'
    value = 200


class flash():
    name = 'Flash Grenade'
    key = 'L'
    value = 1000


class knife():
    name = 'Knife'
    key = 'A'
    value = 150


class kevlar():
    name = 'Kevlar Vest'
    key = 'A'
    value = 1000


class helmet():
    name = 'Helmet'
    key = 'F'
    value = 800


class medkit():
    name = 'Medkit'
    key = 'C'
    value = 500


class tac():
    name = 'TacGoggles'
    key = 'B'
    value = 2000


class health():
    name = 'Health'
    value = 2000
