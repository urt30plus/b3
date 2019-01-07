# -*- coding: utf-8 -*-

# ################################################################### #
#                                                                     #
#  BigBrotherBot(B3) (www.bigbrotherbot.net)                          #
#  Copyright (C) 2005 Michael "ThorN" Thornton                        #
#                                                                     #
#  This program is free software; you can redistribute it and/or      #
#  modify it under the terms of the GNU General Public License        #
#  as published by the Free Software Foundation; either version 2     #
#  of the License, or (at your option) any later version.             #
#                                                                     #
#  This program is distributed in the hope that it will be useful,    #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of     #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the       #
#  GNU General Public License for more details.                       #
#                                                                     #
#  You should have received a copy of the GNU General Public License  #
#  along with this program; if not, write to the Free Software        #
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA      #
#  02110-1301, USA.                                                   #
#                                                                     #
# ################################################################### #

__author__ = 'ThorN'
__version__ = '1.8'

import argparse
import os
import sys
import traceback
from time import sleep

import b3
import b3.config
import b3.pkg_handler
from b3 import HOMEDIR
from b3.functions import console_exit
from b3.update import DBUpdate

modulePath = b3.pkg_handler.resource_directory(__name__)


def run_update(config=None):
    """
    Run the B3 update.
    :param config: The B3 configuration file instance
    """
    update = DBUpdate(config)
    update.run()


def run(options):
    """
    Run B3 in console.
    :param options: command line options
    """
    analysis = None  # main config analysis result

    try:

        if options.config:
            config = b3.getAbsolutePath(options.config, True)
            if not os.path.isfile(config):
                console_exit('ERROR: configuration file not found (%s).' % config)
        else:
            config = None
            for p in ('b3.%s', 'conf/b3.%s', 'b3/conf/b3.%s',
                      os.path.join(HOMEDIR, 'b3.%s'), os.path.join(HOMEDIR, 'conf', 'b3.%s'),
                      os.path.join(HOMEDIR, 'b3', 'conf', 'b3.%s'), '@b3/conf/b3.%s'):
                for e in ('ini', 'cfg', 'xml'):
                    path = b3.getAbsolutePath(p % e, True)
                    if os.path.isfile(path):
                        print("Using configuration file: %s" % path)
                        config = path
                        sleep(3)
                        break

            if not config:
                console_exit('ERROR: could not find any valid configuration file.')

        main_config = b3.config.MainConfig(b3.config.load(config))
        analysis = main_config.analyze()
        if analysis:
            raise b3.config.ConfigFileNotValid('invalid configuration file specified')

        b3.start(main_config, options)

    except b3.config.ConfigFileNotValid:
        if analysis:
            print('CRITICAL: invalid configuration file specified:\n')
            for problem in analysis:
                print("  >>> %s\n" % problem)
        else:
            print('CRITICAL: invalid configuration file specified!')
        raise SystemExit(1)
    except SystemExit:
        raise
    except:
        if sys.stdout != sys.__stdout__:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
        traceback.print_exc()
        input("press any key to continue...")


def main():
    p = argparse.ArgumentParser()
    p.add_argument('-c', '--config', dest='config', default=None, metavar='b3.ini',
                   help='B3 config file. Example: -c b3.ini')
    p.add_argument('-u', '--update', action='store_true', dest='update', default=False,
                   help='Update B3 database to latest version')
    p.add_argument('-v', '--version', action='version', default=False, version=b3.getB3versionString(),
                   help='Show B3 version and exit')

    (options, args) = p.parse_known_args()

    if not options.config and len(args) == 1:
        options.config = args[0]

    if options.update:
        run_update(config=options.config)

    run(options)


if __name__ == '__main__':
    main()
