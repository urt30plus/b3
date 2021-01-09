from unittest.mock import Mock, sentinel

from b3.plugins.tk import TkInfo
from tests.plugins.tk import Tk_functional_test


class Test_TkInfo(Tk_functional_test):

    def setUp(self):
        super().setUp()
        self.my_cid = 1
        self.mock_plugin = self.p
        self.info = TkInfo(self.mock_plugin, self.my_cid)

    def test_construct(self):
        self.assertIsNone(self.info.last_attacker)
        self.assertEqual({}, self.info.attackers)
        self.assertEqual({}, self.info.attacked)
        self.assertEqual(0, self.info.points)

    def test_damage(self):
        self.assertNotIn(2, self.info._attacked)
        self.info.damage(cid=2, points=5)
        self.assertTrue(self.info._attacked[2])

    def test_damaged(self):
        cidA = 3
        self.assertNotIn(cidA, self.info._attackers)
        self.info.damaged(cidA, points=15)
        self.assertEqual(15, self.info._attackers[cidA])

        self.info.damaged(cidA, points=5)
        self.assertEqual(20, self.info._attackers[cidA])

        cidB = 2
        self.info.damaged(cidB, points=7)
        self.assertEqual(20, self.info._attackers[cidA])
        self.assertEqual(7, self.info._attackers[cidB])

    def test_grudge(self):
        cid = 4
        self.assertNotIn(cid, self.info._grudged)
        self.assertFalse(self.info.is_grudged(cid))
        self.info.grudge(cid=cid)
        self.assertIn(cid, self.info._grudged)
        self.assertTrue(self.info.is_grudged(cid))

    def test_attacker_points(self):
        cidA = 2
        s = sentinel
        self.info._attackers[cidA] = s
        self.assertEqual(s, self.info.attacker_points(cidA))

        cidB = 3
        self.assertEqual(0, self.info.attacker_points(cidB))

    def test_points(self):
        self.assertEqual(0, self.info.points)

        cid2 = 2
        cid3 = 3
        infos = {
            cid2: TkInfo(self.mock_plugin, cid2),
            cid3: TkInfo(self.mock_plugin, cid3)
        }
        self.mock_plugin.console.clients.getByCID = Mock(side_effect=lambda cid: cid)
        self.mock_plugin.client_tkinfo = Mock(side_effect=lambda cid: infos[cid])

        points_2 = 45
        self.info.damage(cid2, points_2)
        infos[cid2].damaged(self.my_cid, points_2)
        self.assertEqual(points_2, self.info.points)

        points_3 = 21
        self.info.damage(cid3, points_3)
        infos[cid3].damaged(self.my_cid, points_3)
        self.assertEqual(points_2 + points_3, self.info.points)

    def test_last_attacker(self):
        self.assertIsNone(self.info.last_attacker)
        cid2 = 2
        self.info.damaged(cid2, 32)
        self.assertEqual(cid2, self.info.last_attacker)

    def test_forgive(self):
        cid2 = 2
        cid3 = 3
        self.info.damaged(cid2, 75)
        self.info.damaged(cid3, 47)
        self.assertEqual(75, self.info.attacker_points(cid2))
        self.assertEqual(47, self.info.attacker_points(cid3))
        self.info.forgive(cid2)
        self.assertEqual(0, self.info.attacker_points(cid2))
        self.assertEqual(47, self.info.attacker_points(cid3))

    def test_forgive_last_attacker(self):
        cid2 = 2
        cid3 = 3
        self.info.damaged(cid2, 75)
        self.info.damaged(cid3, 47)
        self.assertEqual(75, self.info.attacker_points(cid2))
        self.assertEqual(47, self.info.attacker_points(cid3))
        self.assertEqual(cid3, self.info.last_attacker)
        self.info.forgive(cid3)
        self.assertEqual(75, self.info.attacker_points(cid2))
        self.assertEqual(0, self.info.attacker_points(cid3))
        self.assertNotEqual(cid3, self.info.last_attacker)

    def test_forgiven(self):
        self.mock_plugin.console = Mock()
        cid2 = 2
        self.info._attacked[cid2] = True
        self.info._warnings[cid2] = mock_warn = Mock()

        self.info.forgiven(cid2)

        self.assertNotIn(cid2, self.info._attacked)
        self.assertEqual(1, mock_warn.inactive)
        mock_warn.save.assert_called_once_with(self.mock_plugin.console)
