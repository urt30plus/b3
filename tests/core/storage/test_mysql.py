import os
import unittest

from b3.functions import splitDSN
from b3.storage.mysql import MysqlStorage
from tests import B3TestCase
from tests.core.storage.common import StorageAPITest

"""
    NOTE: you can customize the MySQL host, database and credential using the following
    environment variables :
        MYSQL_TEST_HOST
        MYSQL_TEST_USER
        MYSQL_TEST_PASSWORD
        MYSQL_TEST_DB
"""
MYSQL_TEST_HOST = os.environ.get('MYSQL_TEST_HOST', 'localhost')
MYSQL_TEST_USER = os.environ.get('MYSQL_TEST_USER', 'b3test')
MYSQL_TEST_PASSWORD = os.environ.get('MYSQL_TEST_PASSWORD', 'test')
MYSQL_TEST_DB = os.environ.get('MYSQL_TEST_DB', 'b3_test')

# ===============================================================================
# 
# Test if we can run the MySQL tests
#
# ===============================================================================

is_mysql_ready = True
no_mysql_reason = ''

try:
    import pymysql as driver
except ImportError:
    try:
        import mysql.connector as driver
    except ImportError:
        driver = None
        is_mysql_ready = False
        no_mysql_reason = "no pymysql or mysql.connector module available"
if is_mysql_ready:
    try:
        driver.connect(host=MYSQL_TEST_HOST, user=MYSQL_TEST_USER, passwd=MYSQL_TEST_PASSWORD)
    except driver.Error as err:
        is_mysql_ready = False
        no_mysql_reason = "%s" % err.args[1]
    except Exception as err:
        is_mysql_ready = False
        no_mysql_reason = "%s" % err


# ===============================================================================
# 
# Load the tests
# 
# ===============================================================================

@unittest.skipIf(not is_mysql_ready, no_mysql_reason)
class Test_MySQL(B3TestCase, StorageAPITest):

    def setUp(self):
        """this method is called before each test"""

        B3TestCase.setUp(self)

        try:
            db = driver.connect(host=MYSQL_TEST_HOST, user=MYSQL_TEST_USER, password=MYSQL_TEST_PASSWORD)
        except driver.OperationalError as message:
            self.fail("Error %d:\n%s" % (message[0], message[1]))

        db.query("DROP DATABASE IF EXISTS `%s`" % MYSQL_TEST_DB)
        db.query("CREATE DATABASE `%s` CHARACTER SET utf8;" % MYSQL_TEST_DB)

        dsn = "mysql://%s:%s@%s/%s" % (MYSQL_TEST_USER, MYSQL_TEST_PASSWORD, MYSQL_TEST_HOST, MYSQL_TEST_DB)
        self.storage = self.console.storage = MysqlStorage(dsn, splitDSN(dsn), self.console)
        self.storage.connect()

    def tearDown(self):
        """this method is called after each test"""
        B3TestCase.tearDown(self)
        self.storage.query("DROP DATABASE `%s`" % MYSQL_TEST_DB)
        self.storage.shutdown()

    def test_getTables(self):
        self.assertSetEqual(set(
            ['aliases',
             'ipaliases',
             'clients',
             'groups',
             'penalties',
             'data',
             'plugin_hof',
             'xlr_actionstats',
             'xlr_playerstats',
             'xlr_playeractions',
             'xlr_history_weekly',
             'ctime',
             'xlr_history_monthly',
             'xlr_bodyparts',
             'xlr_playerbody',
             'xlr_opponents',
             'xlr_weaponstats',
             'xlr_playermaps',
             'xlr_mapstats',
             'xlr_weaponusage'
             ]), set(self.storage.getTables()))


if __name__ == '__main__':
    unittest.main()
