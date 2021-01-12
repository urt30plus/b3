import argparse
import os
import signal
import sys

import b3
import b3.config
import b3.functions
import b3.update

__author__ = 'ThorN'
__version__ = '1.8'


def stdout_write(message, flush=True):
    sys.stdout.write(message)
    if flush:
        sys.stdout.flush()


def start(mainconfig, options):
    """
    Main B3 startup.
    :param mainconfig: The B3 configuration file instance :type: b3.config.MainConfig
    :param options: command line options
    """
    b3.confdir = os.path.dirname(mainconfig.fileName)

    stdout_write(f'Starting B3      : {b3.getB3versionString()}\n')

    # not real loading but the user will get what's configuration he is using
    stdout_write(f'Loading config   : {b3.functions.getShortPath(mainconfig.fileName, True)}\n')

    parsertype = mainconfig.get('b3', 'parser')
    stdout_write(f'Loading parser   : {parsertype}\n')

    parser = b3.functions.loadParser(parsertype)
    b3.console = parser(mainconfig, options)

    def termSignalHandler(signum, frame):
        """
        Define the signal handler so to handle B3 shutdown properly.
        """
        b3.console.bot("TERM signal received: shutting down")
        b3.console.shutdown()

    try:
        # necessary if using the functions profiler,
        # because signal.signal cannot be used in threads
        signal.signal(signal.SIGTERM, termSignalHandler)
    except Exception:
        pass

    try:
        b3.console.start()
    except KeyboardInterrupt:
        b3.console.shutdown()


def run_update(config=None):
    """
    Run the B3 update.
    :param config: The B3 configuration file instance
    """
    b3.update.DBUpdate(config).run()


def run(options):
    """
    Run B3 in console.
    :param options: command line options
    """
    main_config = b3.config.get_main_config(options.config)
    if analysis := main_config.analyze():
        raise b3.config.ConfigFileNotValid(
            'Invalid configuration file specified: ' +
            '\n >>> '.join(analysis)
        )

    start(main_config, options)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('-c', '--config', dest='config', default=None, metavar='b3.ini',
                   help='B3 config file. Example: -c b3.ini')
    p.add_argument('-u', '--update', action='store_true', dest='update', default=False,
                   help='Update B3 database to latest version')
    p.add_argument('-v', '--version', action='version', default=False, version=b3.getB3versionString(),
                   help='Show B3 version and exit')

    options, args = p.parse_known_args()

    if not options.config and len(args) == 1:
        options.config = args[0]

    if options.update:
        run_update(config=options.config)

    run(options)


if __name__ == '__main__':
    main()
