import distutils.version
import os
import re
import time

import b3
import b3.config
import b3.functions
import b3.storage


class B3version(distutils.version.StrictVersion):
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
        1.9.0dev7.daily21-20121004
    And make sure that any 'dev' prerelease is inferior to any 'alpha' prerelease
    """
    version = None
    prerelease = None
    build_num = None

    version_re = re.compile(r'''^
(?P<major>\d+)\.(?P<minor>\d+)   # 1.2
(?:\. (?P<patch>\d+))?           # 1.2.45
(?P<prerelease>                  # 1.2.45b2
  (?P<tag>a|b|dev)
  (?P<tag_num>\d+)?
)?                                                                     # 1.2.45b2.devd94d71a-20120901
((?P<daily>\.daily(?P<build_num>\d+?))|(?P<dev>\.dev(?P<dev_num>\w+?)) # 1.2.45b2.daily4-20120901
)?
(?:-(?P<date>20\d\d\d\d\d\d))?   # 1.10.0dev-20150215
$''', re.VERBOSE)
    prerelease_order = {'dev': 0, 'a': 1, 'b': 2}

    def parse(self, vstring):
        """
        Parse the version number from a string.
        :param vstring: The version string
        """
        if not (match := self.version_re.match(vstring)):
            raise ValueError(f"invalid version number '{vstring}'")

        major = match.group('major')
        minor = match.group('minor')

        if patch := match.group('patch'):
            self.version = tuple(map(int, [major, minor, patch]))
        else:
            self.version = tuple(list(map(int, [major, minor])) + [0])

        if prerelease := match.group('tag'):
            prerelease_num = match.group('tag_num')
            self.prerelease = (prerelease, int(prerelease_num if prerelease_num else '0'))
        else:
            self.prerelease = None

        if daily_num := match.group('build_num'):
            self.build_num = int(daily_num if daily_num else '0')
        else:
            self.build_num = None

    def __cmp__(self, other):
        """
        Compare current object with another one.
        :param other: The other object
        """
        if isinstance(other, str):
            other = B3version(other)

        compare = b3.functions.cmp(self.version, other.version)
        if compare != 0:
            return compare

        # we have to compare prerelease
        compare = self.__cmp_prerelease(other)
        if compare != 0:
            return compare

        # we have to compare build num
        return self.__cmp_build(other)

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __cmp_prerelease(self, other):
        # case 1: neither has prerelease; they're equal
        # case 2: self has prerelease, other doesn't; other is greater
        # case 3: self doesn't have prerelease, other does: self is greater
        # case 4: both have prerelease: must compare them!
        if not self.prerelease and not other.prerelease:
            return 0
        elif self.prerelease and not other.prerelease:
            return -1
        elif not self.prerelease and other.prerelease:
            return 1
        elif self.prerelease and other.prerelease:
            return b3.functions.cmp((self.prerelease_order[self.prerelease[0]], self.prerelease[1]),
                                    (self.prerelease_order[other.prerelease[0]], other.prerelease[1]))

    def __cmp_build(self, other):
        # case 1: neither has build_num; they're equal
        # case 2: self has build_num, other doesn't; other is greater
        # case 3: self doesn't have build_num, other does: self is greater
        # case 4: both have build_num: must compare them!
        if not self.build_num and not other.build_num:
            return 0
        elif self.build_num and not other.build_num:
            return -1
        elif not self.build_num and other.build_num:
            return 1
        elif self.build_num and other.build_num:
            return b3.functions.cmp(self.build_num, other.build_num)


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
            b3.functions.console_exit(f'ERROR: configuration file not valid ({config})')

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
                sql = b3.functions.getAbsolutePath(f'@b3/sql/{storage.protocol}/b3-update-{update_version}.sql')
                if os.path.isfile(sql):
                    try:
                        print(f'>>> updating database to version {update_version}')
                        time.sleep(.5)
                        storage.queryFromFile(sql)
                    except Exception as err:
                        print(f'WARNING: could not update database properly: {err}')
                        time.sleep(3)

        dsn = self.config.get('b3', 'database')
        dsndict = b3.functions.splitDSN(dsn)
        from b3.parser import StubParser
        database = b3.storage.getStorage(dsn, dsndict, StubParser())

        _update_database(database, '3.99.99')

        b3.functions.console_exit('B3 database update completed!')
