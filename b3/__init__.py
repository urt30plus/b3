__author__ = 'ThorN'
__version__ = '3.31.21'

versionEdition = "WindyCity"
versionId = f'v{__version__}'
version = f'^0(^8b3^0) ^9{versionId} ^9[{versionEdition}^9]^3'

confdir = None
console = None

# TEAMS
TEAM_UNKNOWN = -1
TEAM_FREE = 0
TEAM_SPEC = 1
TEAM_RED = 2
TEAM_BLUE = 3

# PLAYER STATE
STATE_DEAD = 1
STATE_ALIVE = 2
STATE_UNKNOWN = 3

# CUSTOM TYPES FOR DYNAMIC CASTING
STRING = STR = 1
INTEGER = INT = 2
BOOLEAN = BOOL = 3
FLOAT = 4
LEVEL = 5  # b3.clients.Group level
DURATION = 6  # b3.functions.time2minutes conversion
PATH = 7  # b3.functions.getAbsolutePath path conversion
TEMPLATE = 8  # b3.functions.vars2printf conversion
LIST = 9  # string split into list of tokens


def getB3versionString():
    """
    Return the B3 version as a string.
    """
    import re
    return re.sub(r'\^[0-9a-z]', '', version)
