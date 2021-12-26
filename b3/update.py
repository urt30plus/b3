import os
import time

import packaging.version

import b3
import b3.config
import b3.functions
import b3.storage


class B3version(packaging.version.Version):
    """
    Version numbering for BigBrotherBot.
    Compared to version.StrictVersion this class allows version numbers such as :
        1.0dev
        1.0dev2
        1.0d3
        1.0a
        1.0a
        1.0a34
        1.0b
        1.0b1
        1.0b3
    And make sure that any 'dev' prerelease is inferior to any 'alpha' prerelease
    """


class DBUpdate:
    """
    Console database update procedure.
    """

    def __init__(self, config=None):
        """
        Object constructor.
        :param config: The B3 configuration file path
        """
        try:
            self.config = b3.config.get_main_config(config)
            if analysis := self.config.analyze():
                raise b3.config.ConfigFileNotValid(
                    'Invalid configuration file specified: ' +
                    '\n >>> '.join(analysis)
                )
        except b3.config.ConfigFileNotValid as cerr:
            print(cerr)
            b3.functions.console_exit(
                f'ERROR: configuration file not valid ({config})')

    def run(self):
        """
        Run the DB update
        """
        print(r"""
                        _\|/_
                        (o o)    {:>32}
                +----oOO---OOo----------------------------------+
                |                                               |
                |             UPDATING B3 DATABASE              |
                |                                               |
                +-----------------------------------------------+

        """.format('B3 : %s' % b3.__version__))

        input("press any key to start the update...")

        def _update_database(storage, update_version):
            """
            Update a B3 database.
            :param storage: the initialized storage module
            :param update_version: the update version
            """
            if B3version(b3.__version__) >= update_version:
                sql = b3.functions.getAbsolutePath(
                    f'@b3/sql/{storage.protocol}/b3-update-{update_version}.sql')
                if os.path.isfile(sql):
                    try:
                        print(
                            f'>>> updating database to version {update_version}')
                        time.sleep(.5)
                        storage.queryFromFile(sql)
                    except Exception as err:
                        print(
                            f'WARNING: could not update database properly: {err}')
                        time.sleep(3)

        dsn = self.config.get('b3', 'database')
        dsndict = b3.functions.splitDSN(dsn)
        from b3.parser import StubParser
        database = b3.storage.getStorage(dsn, dsndict, StubParser())

        _update_database(database, '3.99.99')

        b3.functions.console_exit('B3 database update completed!')
