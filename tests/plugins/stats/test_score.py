from tests.plugins.stats import StatPluginTestCase


class Test_score(StatPluginTestCase):

    def test_no_points(self):
        # GIVEN
        self.joe.setvar(self.p, 'points', 0)
        self.mike.setvar(self.p, 'points', 0)
        # WHEN
        s = self.p.score(self.joe, self.mike)
        # THEN
        self.assertEqual(12.5, s)

    def test_equal_points(self):
        # GIVEN
        self.joe.setvar(self.p, 'points', 50)
        self.mike.setvar(self.p, 'points', 50)
        # WHEN
        s = self.p.score(self.joe, self.mike)
        # THEN
        self.assertEqual(12.5, s)

    def test_victim_has_more_points(self):
        # GIVEN
        self.joe.setvar(self.p, 'points', 50)
        self.mike.setvar(self.p, 'points', 100)
        # WHEN
        s = self.p.score(self.joe, self.mike)
        # THEN
        self.assertEqual(20.0, s)

    def test_victim_has_less_points(self):
        # GIVEN
        self.joe.setvar(self.p, 'points', 100)
        self.mike.setvar(self.p, 'points', 50)
        # WHEN
        s = self.p.score(self.joe, self.mike)
        # THEN
        self.assertEqual(8.75, s)
