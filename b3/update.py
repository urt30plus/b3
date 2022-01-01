import functools
import os
import time

import b3
import b3.config
import b3.functions
import b3.storage


@functools.total_ordering
class B3version:

    def __init__(self, version: str) -> None:
        self._version_info = list(map(int, version.split('.')))
        if len(self._version_info) == 2:
            self._version_info.append(0)

    def __eq__(self, other):
        if isinstance(other, B3version):
            return other._version_info == self._version_info
        elif isinstance(other, list):
            return other == self._version_info
        else:
            return NotImplemented

    def __lt__(self, other):
        if isinstance(other, B3version):
            return self._version_info < other._version_info
        elif isinstance(other, list):
            return self._version_info < other
        else:
            return NotImplemented

    def __repr__(self):
        return f'B3Version<{".".join(map(str, self._version_info))}'


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
