import sys

__author__ = 'ThorN'
__version__ = '1.2'

if sys.version_info < (3, 6):
    raise SystemExit("B3 is not compatible with Python versions <3.6")


def main():
    import b3.run
    b3.run.main()


if __name__ == "__main__":
    main()
