import argparse
import os
import sys
import traceback
from time import sleep

import b3
import b3.config
import b3.functions
import b3.update

__author__ = 'ThorN'
__version__ = '1.8'

modulePath = b3.functions.resource_directory(__name__)


def run_update(config=None):
    """
    Run the B3 update.
    :param config: The B3 configuration file instance
    """
    update = b3.update.DBUpdate(config)
    update.run()


def run(options):
    """
    Run B3 in console.
    :param options: command line options
    """
    analysis = None

    try:

        if options.config:
            config = b3.getAbsolutePath(options.config, True)
            if not os.path.isfile(config):
                b3.functions.console_exit(f'ERROR: configuration file not found ({config}).')
        else:
            config = None
            for p in ('b3.%s', 'conf/b3.%s', 'b3/conf/b3.%s',
                      os.path.join(b3.HOMEDIR, 'b3.%s'), os.path.join(b3.HOMEDIR, 'conf', 'b3.%s'),
                      os.path.join(b3.HOMEDIR, 'b3', 'conf', 'b3.%s'), '@b3/conf/b3.%s'):
                for e in ('ini', 'cfg', 'xml'):
                    path = b3.getAbsolutePath(p % e, True)
                    if os.path.isfile(path):
                        print(f"Using configuration file: {path}")
                        config = path
                        sleep(3)
                        break

            if not config:
                b3.functions.console_exit('ERROR: could not find any valid configuration file.')

        main_config = b3.config.MainConfig(b3.config.load(config))
        analysis = main_config.analyze()
        if analysis:
            raise b3.config.ConfigFileNotValid('Invalid configuration file specified')

        b3.start(main_config, options)

    except b3.config.ConfigFileNotValid:
        if analysis:
            print('CRITICAL: invalid configuration file specified:\n')
            for problem in analysis:
                print(f"  >>> {problem}\n")
        else:
            print('CRITICAL: invalid configuration file specified')
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
