import os
import unittest
from unittest.mock import Mock

import b3
import b3.functions
from b3.clients import Client
from b3.storage.common import DatabaseStorage
from b3.storage.sqlite import SqliteStorage

# checks whether we can perform tests on SQL script file parsing
B3_SQL_FILE_AVAILABLE = os.path.exists(
    b3.functions.getAbsolutePath("@b3/sql/sqlite/b3.sql")
)
B3_DEFAULT_TABLES = ["aliases", "clients", "data", "groups", "ipaliases", "penalties"]


class Test_DatabaseStorage(unittest.TestCase):
    def test_getClient_connectionfailed(self):
        mock_storage = Mock(spec=SqliteStorage)
        mock_storage.getClient = SqliteStorage.getClient
        mock_storage.db = None
        mock_storage.query = Mock(return_value=None)
        mock_storage.console = Mock()
        mock_storage.console.config = Mock()
        mock_storage.console.config.get = Mock(return_value="123,myname,100")

        mock_storage.console.config.has_option = Mock(return_value=True)
        c1 = Client()
        c2 = mock_storage.getClient(mock_storage, c1)
        self.assertIs(c2, c1)
        self.assertEqual(123, c1.id)
        self.assertEqual("myname", c1.name)
        self.assertEqual(100, c1._tempLevel)

        mock_storage.console.config.has_option = Mock(return_value=False)
        self.assertRaises(KeyError, mock_storage.getClient, mock_storage, Mock(id=666))

    @unittest.skipUnless(
        B3_SQL_FILE_AVAILABLE,
        "B3 SQL script not found @ %s" % b3.functions.getAbsolutePath("@b3/sql/b3.sql"),
    )
    def test_b3_sql_file_parsing(self):
        with open(
            b3.functions.getAbsolutePath("@b3/sql/sqlite/b3.sql"), "r"
        ) as sql_file:
            statements = DatabaseStorage.getQueriesFromFile(sql_file)
            self.assertEqual(15, len(statements))
