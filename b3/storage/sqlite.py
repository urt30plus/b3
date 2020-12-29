import os

import b3.functions
from b3.storage.common import DatabaseStorage


class SqliteStorage(DatabaseStorage):
    protocol = 'sqlite'

    def __init__(self, dsn, dsnDict, console):
        """
        Object constructor.
        :param dsn: The database connection string.
        :param dsnDict: The database connection string parsed into a dict.
        :param console: The console instance.
        """
        super(SqliteStorage, self).__init__(dsn, dsnDict, console)

    def connect(self):
        """
        Establish and return a connection with the storage layer.
        Will store the connection object also in the 'db' attribute so in the future we can reuse it.
        :return The connection instance if established successfully, otherwise None.
        """
        try:
            import sqlite3
            path = b3.functions.getWritableFilePath(self.dsn[9:])
            self.console.bot("Using database file: %s", path)
            is_new_database = not os.path.isfile(path)
            self.db = sqlite3.connect(path, check_same_thread=False)
            self.db.isolation_level = None  # set autocommit mode
        except Exception as e:
            self.db = None
            self.console.error('Database connection failed: %s', e)
            if self._consoleNotice:
                self.console.screen.write('Connecting to DB : FAILED\n')
                self._consoleNotice = False
        else:
            # import SQL script if necessary
            if path == ':memory:' or is_new_database:
                self.console.info("Importing SQL file: %s...", b3.functions.getAbsolutePath("@b3/sql/sqlite/b3.sql"))
                self.queryFromFile("@b3/sql/sqlite/b3.sql")

            if self._consoleNotice:
                self.console.screen.write('Connecting to DB : OK\n')
                self._consoleNotice = False
        finally:
            return self.db

    def getConnection(self):
        """
        Return the database connection. If the connection has not been established yet, will establish a new one.
        :return The connection instance, or None if no connection can be established.
        """
        if self.db:
            return self.db
        return self.connect()

    def shutdown(self):
        """
        Close the current active database connection.
        """
        if self.db:
            # checking 'open' will prevent exception raising
            self.console.bot('Closing connection with SQLite database...')
            self.db.close()
        self.db = None

    def getTables(self):
        """
        List the tables of the current database.
        :return: List of strings.
        """
        with self.query("SELECT tbl_name FROM sqlite_master WHERE type='table'") as cursor:
            return [row['tbl_name'] for row in cursor]

    def truncateTable(self, table):
        """
        Empty a database table (or a collection of tables)
        :param table: The database table or a collection of tables
        :raise KeyError: If the table is not present in the database
        """
        current_tables = self.getTables()
        if isinstance(table, (tuple, list)):
            for v in table:
                if v not in current_tables:
                    raise KeyError(f"could not find table '{v}' in the database")
                self.query(f"DELETE FROM {v};")
                self.query(f"DELETE FROM sqlite_sequence WHERE name='{v}'")
        else:
            if table not in current_tables:
                raise KeyError(f"could not find table '{table}' in the database")
            self.query(f"DELETE FROM {table}")
            self.query(f"DELETE FROM sqlite_sequence WHERE name='{table}'")

    def status(self):
        """
        Check whether the connection with the storage layer is active or not.
        :return True if the connection is active, False otherwise.
        """
        return self.db is not None
