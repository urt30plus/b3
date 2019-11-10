import unittest

from b3.functions import splitDSN
from b3.storage.sqlite import SqliteStorage
from tests import B3TestCase
from tests.core.storage.common import StorageAPITest

SQLITE_DB = ":memory:"


# SQLITE_DB = "c:/Users/Thomas/b3.db"

class Test_sqlite(B3TestCase, StorageAPITest):

    def setUp(self):
        """this method is called before each test"""
        B3TestCase.setUp(self)
        self.storage = self.console.storage = SqliteStorage('sqlite://' + SQLITE_DB, splitDSN('sqlite://' + SQLITE_DB),
                                                            self.console)
        self.storage.connect()
        # self.storage.queryFromFile("@b3/sql/sqlite/b3.sql")

    def tearDown(self):
        """this method is called after each test"""
        B3TestCase.tearDown(self)
        self.storage.shutdown()

    def test_getTables(self):
        self.assertSetEqual(set(
            ['sqlite_sequence',
             'aliases',
             'ipaliases',
             'clients',
             'groups',
             'penalties',
             'data',
             'plugin_hof',
             ]), set(self.storage.getTables()))


if __name__ == '__main__':
    unittest.main()
