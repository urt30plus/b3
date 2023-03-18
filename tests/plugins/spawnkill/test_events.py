from textwrap import dedent

from tests.plugins.spawnkill import SpawnkillTestCase


class Test_events(SpawnkillTestCase):
    def test_client_spawntime_mark(self):
        # GIVEN
        self.init()
        self.mike.connects("1")
        self.bill.connects("2")
        # WHEN
        self.console.parseLine("""ClientSpawn: 1""")
        self.console.parseLine("""ClientSpawn: 2""")
        # THEN
        self.assertEqual(True, self.mike.isvar(self.p, "spawntime"))
        self.assertEqual(True, self.bill.isvar(self.p, "spawntime"))

    def test_client_spawn_hit_admin_level_bypass(self):
        # GIVEN
        self.init(
            dedent(
                r"""
            [hit]
            maxlevel: admin
            delay: 10
            penalty: warn
            duration: 3m
            reason: do not shoot to spawning players!
        """
            )
        )
        self.mark.connects("1")
        self.bill.connects("2")
        self.mark.setvar(self.p, "spawntime", self.console.time() - 5)
        self.bill.setvar(self.p, "spawntime", self.console.time() - 5)
        # WHEN
        self.mark.damages(self.bill)
        # THEN
        self.assertEqual(0, self.console.storage.numPenalties(self.mark, "Warning"))

    def test_client_spawn_hit_no_spawntime_marked(self):
        # GIVEN
        self.init(
            dedent(
                r"""
            [hit]
            maxlevel: admin
            delay: 10
            penalty: warn
            duration: 3m
            reason: do not shoot to spawning players!
        """
            )
        )
        self.mike.connects("1")
        self.bill.connects("2")
        # WHEN
        self.mike.damages(self.bill)
        # THEN
        self.assertEqual(0, self.console.storage.numPenalties(self.mike, "Warning"))

    def test_client_spawn_hit_warn(self):
        # GIVEN
        self.init(
            dedent(
                r"""
            [hit]
            maxlevel: admin
            delay: 10
            penalty: warn
            duration: 3m
            reason: do not shoot to spawning players!
        """
            )
        )
        self.mike.connects("1")
        self.bill.connects("2")
        self.mike.setvar(self.p, "spawntime", self.console.time() - 5)
        self.bill.setvar(self.p, "spawntime", self.console.time() - 5)
        # WHEN
        self.mike.clearMessageHistory()
        self.mike.damages(self.bill)
        # THEN
        self.assertEqual(1, self.console.storage.numPenalties(self.mike, "Warning"))
        self.assertListEqual(
            ["WARNING [1]: Mike,  do not shoot to spawning players!"],
            self.mike.message_history,
        )

    def test_client_spawn_hit_kick(self):
        # GIVEN
        self.init(
            dedent(
                r"""
            [hit]
            maxlevel: admin
            delay: 10
            penalty: kick
            duration: 3m
            reason: do not shoot to spawning players!
        """
            )
        )
        self.mike.connects("1")
        self.bill.connects("2")
        self.mike.setvar(self.p, "spawntime", self.console.time() - 5)
        self.bill.setvar(self.p, "spawntime", self.console.time() - 5)
        # WHEN
        self.mike.clearMessageHistory()
        self.mike.damages(self.bill)
        # THEN
        self.assertEqual(1, self.console.storage.numPenalties(self.mike, "Kick"))

    def test_client_spawn_hit_tempban(self):
        # GIVEN
        self.init(
            dedent(
                r"""
            [hit]
            maxlevel: admin
            delay: 10
            penalty: tempban
            duration: 3m
            reason: do not shoot to spawning players!
        """
            )
        )
        self.mike.connects("1")
        self.bill.connects("2")
        self.mike.setvar(self.p, "spawntime", self.console.time() - 5)
        self.bill.setvar(self.p, "spawntime", self.console.time() - 5)
        # WHEN
        self.mike.clearMessageHistory()
        self.mike.damages(self.bill)
        # THEN
        self.assertEqual(1, self.console.storage.numPenalties(self.mike, "TempBan"))

    def test_client_spawn_hit_slap(self):
        # TODO: implement test case
        pass

    def test_client_spawn_hit_nuke(self):
        # TODO: implement test case
        pass

    def test_client_spawn_hit_kill(self):
        # TODO: implement test case
        pass

    def test_client_spawn_kill_admin_level_bypass(self):
        # GIVEN
        self.init(
            dedent(
                r"""
            [hit]
            maxlevel: admin
            delay: 10
            penalty: warn
            duration: 3m
            reason: do not shoot to spawning players!
        """
            )
        )
        self.mark.connects("1")
        self.bill.connects("2")
        self.mark.setvar(self.p, "spawntime", self.console.time() - 5)
        self.bill.setvar(self.p, "spawntime", self.console.time() - 5)
        # WHEN
        self.mark.kills(self.bill)
        # THEN
        self.assertEqual(0, self.console.storage.numPenalties(self.mark, "Warning"))

    def test_client_spawn_kill_no_spawntime_marked(self):
        # GIVEN
        self.init(
            dedent(
                r"""
            [hit]
            maxlevel: admin
            delay: 10
            penalty: warn
            duration: 3m
            reason: do not shoot to spawning players!
        """
            )
        )
        self.mike.connects("1")
        self.bill.connects("2")
        # WHEN
        self.mike.kills(self.bill)
        # THEN
        self.assertEqual(0, self.console.storage.numPenalties(self.mike, "Warning"))

    def test_client_spawn_kill_warn(self):
        # GIVEN
        self.init(
            dedent(
                r"""
            [kill]
            maxlevel: admin
            delay: 10
            penalty: warn
            duration: 5m
            reason: spawnkilling is not allowed on this server!
        """
            )
        )
        self.mike.connects("1")
        self.bill.connects("2")
        self.mike.setvar(self.p, "spawntime", self.console.time() - 5)
        self.bill.setvar(self.p, "spawntime", self.console.time() - 5)
        # WHEN
        self.mike.clearMessageHistory()
        self.mike.kills(self.bill)
        # THEN
        self.assertEqual(1, self.console.storage.numPenalties(self.mike, "Warning"))
        self.assertListEqual(
            ["WARNING [1]: Mike,  spawnkilling is not allowed on this server!"],
            self.mike.message_history,
        )

    def test_client_spawn_kill_kick(self):
        # GIVEN
        self.init(
            dedent(
                r"""
            [kill]
            maxlevel: admin
            delay: 10
            penalty: kick
            duration: 5m
            reason: spawnkilling is not allowed on this server!
        """
            )
        )
        self.mike.connects("1")
        self.bill.connects("2")
        self.mike.setvar(self.p, "spawntime", self.console.time() - 5)
        self.bill.setvar(self.p, "spawntime", self.console.time() - 5)
        # WHEN
        self.mike.clearMessageHistory()
        self.mike.kills(self.bill)
        # THEN
        self.assertEqual(1, self.console.storage.numPenalties(self.mike, "Kick"))

    def test_client_spawn_kill_tempban(self):
        # GIVEN
        self.init(
            dedent(
                r"""
            [kill]
            maxlevel: admin
            delay: 10
            penalty: tempban
            duration: 5m
            reason: spawnkilling is not allowed on this server!
        """
            )
        )
        self.mike.connects("1")
        self.bill.connects("2")
        self.mike.setvar(self.p, "spawntime", self.console.time() - 5)
        self.bill.setvar(self.p, "spawntime", self.console.time() - 5)
        # WHEN
        self.mike.clearMessageHistory()
        self.mike.kills(self.bill)
        # THEN
        self.assertEqual(1, self.console.storage.numPenalties(self.mike, "TempBan"))

    def test_client_spawn_kill_slap(self):
        # TODO: implement test case
        pass

    def test_client_spawn_kill_nuke(self):
        # TODO: implement test case
        pass

    def test_client_spawn_kill_kill(self):
        # TODO: implement test case
        pass
