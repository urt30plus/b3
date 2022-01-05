import collections
import importlib
import os
import re
import sys
import tempfile
import threading

__author__ = 'ThorN, xlr8or, courgette'
__version__ = '1.23'

try:
    import pkg_resources
except ImportError:
    def resource_directory(module):
        """
        Use this if pkg_resources is NOT installed
        """
        return os.path.dirname(sys.modules[module].__file__)
else:
    def resource_directory(module):
        """
        Use this if pkg_resources is installed
        """
        return pkg_resources.resource_filename(module, '')


def decode_text(text):
    """
    Return a copy of text decoded using the default system encoding.
    :param text: the text to decode
    :return: string
    """
    if hasattr(text, 'decode'):
        return text.decode(sys.getfilesystemencoding())
    return text


def is_windows():
    return sys.platform.startswith('win')


def getModule(name):
    """
    Return a module given its name.
    :param name: The module name
    """
    return importlib.import_module(name)


def getCmd(instance, cmd):
    """
    Return a command function given the command name.
    :param instance: The plugin class instance.
    :param cmd: The command name.
    :return The command function reference.
    """
    return getattr(instance, f"cmd_{cmd}", None)


def splitDSN(url):
    """
    Return a dict containing the database connection
    arguments specified in the given input url.
    """
    m = re.match(r'^(?:(?P<protocol>[a-z]+)://)?'
                 r'(?:(?P<user>[^:]+)'
                 r'(?::'
                 r'(?P<password>[^@]*?))?@)?'
                 r'(?P<host>[^/:]+)?(?::'
                 r'(?P<port>\d+))?'
                 r'(?P<path>.*)', url)

    if not m:
        return None

    g = m.groupdict()

    if not g['protocol']:
        g['protocol'] = 'file'
    if g['protocol'] == 'file':
        if g['host'] and g['path']:
            g['path'] = f"{g['host']}{g['path']}"
            g['host'] = None
        elif g['host']:
            g['path'] = g['host']
            g['host'] = None
    elif g['protocol'] == 'exec':
        if g['host'] and g['path']:
            g['path'] = f"{g['host']}/{g['path']}"
            g['host'] = None
        elif g['host']:
            g['path'] = g['host']
            g['host'] = None

    if g['port']:
        g['port'] = int(g['port'])
    elif g['protocol'] == 'ftp':
        g['port'] = 21
    elif g['protocol'] == 'sftp':
        g['port'] = 22
    return g


def minutes2int(mins):
    """
    Convert a given string to a float value which represents it.
    """
    if re.match('^[0-9.]+$', mins):
        return round(float(mins), 2)
    return 0


def time2minutes(timestr):
    """
    Return the amount of minutes the given string represent.
    :param timestr: A time string
    """
    if not timestr:
        return 0
    elif type(timestr) is int:
        return timestr

    timestr = str(timestr)
    if not timestr:
        return 0
    elif timestr[-1:] == 'h':
        return minutes2int(timestr[:-1]) * 60
    elif timestr[-1:] == 'm':
        return minutes2int(timestr[:-1])
    elif timestr[-1:] == 's':
        return minutes2int(timestr[:-1]) / 60
    elif timestr[-1:] == 'd':
        return minutes2int(timestr[:-1]) * 60 * 24
    elif timestr[-1:] == 'w':
        return minutes2int(timestr[:-1]) * 60 * 24 * 7
    else:
        return minutes2int(timestr)


def minutesStr(timestr):
    """
    Convert the given value in a string representing a duration.
    """
    mins = float(time2minutes(timestr))

    if mins < 1:
        num = round(mins * 60, 1)
        s = '%s second'
    elif mins < 60:
        num = round(mins, 1)
        s = '%s minute'
    elif mins < 1440:
        num = round(mins / 60, 1)
        s = '%s hour'
    elif mins < 10080:
        num = round((mins / 60) / 24, 1)
        s = '%s day'
    elif mins < 525600:
        num = round(((mins / 60) / 24) / 7, 1)
        s = '%s week'
    else:
        num = round(((mins / 60) / 24) / 365, 1)
        s = '%s year'

    # convert to int if num is whole
    num = int(num) if num % 1 == 0 else num

    if num >= 2:
        s += 's'

    return s % num


def vars2printf(inputstr):
    if inputstr is not None and inputstr != '':
        return re.sub(r'\$([a-zA-Z_]+)', r'%(\1)s', inputstr)
    else:
        return ''


def clamp(value, minv=None, maxv=None):
    """
    Clamp a value so it's bounded within min and max
    :param value: the value to be clamped
    :param minv: the minimum value
    :param maxv: the maximum value
    :return: a value which fits between the imposed limits
    """
    if minv is not None:
        value = max(value, minv)
    if maxv is not None:
        value = min(value, maxv)
    return value


def console_exit(message=''):
    """
    Terminate the current console application displaying the given message.
    Will make sure that the user is able to see the exit message.
    :param message: the message to prompt to the user
    """
    raise SystemExit(message)


def levenshteinDistance(a, b):
    """
    Return the levenshtein distance between 2 strings.
    :param a: The 1st string to match.
    :param b: The second string to match
    :return The levenshtein distance between a and b
    """
    c = {}
    n = len(a)
    m = len(b)

    for i in range(0, n + 1):
        c[i, 0] = i
    for j in range(0, m + 1):
        c[0, j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            x = c[i - 1, j] + 1
            y = c[i, j - 1] + 1
            if a[i - 1] == b[j - 1]:
                z = c[i - 1, j - 1]
            else:
                z = c[i - 1, j - 1] + 1
            c[i, j] = min(x, y, z)
    return c[n, m]


def soundex(s1):
    """
    Return the soundex value to a string argument.
    """
    ignore = r"~!@#$%^&*()_+=-`[]\|;:'/?.,<>\" \t\f\v"
    table = str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', '01230120022455012623010202', ignore)

    s1 = s1.upper().strip()
    if not s1:
        return "Z000"
    s2 = s1[0]
    s1 = s1.translate(table)
    if not s1:
        return "Z000"
    prev = s1[0]
    for x in s1[1:]:
        if x != prev and x != "0":
            s2 = s2 + x
        prev = x
    # pad with zeros
    s2 += "0000"
    return s2[:4]


def meanstdv(x):
    """
    Calculate mean and standard deviation of data x[]:
        mean = {sum_i x_i over n}
        std = sqrt(sum_i (x_i - mean)^2 over n-1)
    credit: http://www.physics.rutgers.edu/~masud/computing/WPark_recipes_in_python.html
    """
    from math import sqrt
    n, mean, std = len(x), 0, 0
    for a in x:
        mean = mean + a
    try:
        mean /= float(n)
    except ZeroDivisionError:
        mean = 0
    for a in x:
        std += (a - mean) ** 2
    try:
        std = sqrt(std / float(n - 1))
    except ZeroDivisionError:
        std = 0
    return mean, std


def fuzzyGuidMatch(a, b):
    """
    Matches guid using the levenshtein distance if necessary,
    so it's possible to match truncated GUIDs
    """
    a = a.upper()
    b = b.upper()

    if a == b:
        return True

    # put the longest first
    if len(b) > len(a):
        a, b = b, a

    if len(a) == 32 and len(b) == 31:
        # Looks like a truncated id, check using levenshtein
        # Use levenshtein_distance to find GUIDs off by 1 char
        distance = levenshteinDistance(a, b)
        if distance <= 1:
            return True

    return False


def getStuffSoundingLike(stuff, expected_stuff):
    """
    Found matching stuff for the given expected_stuff list.
    If no exact match is found, then return close candidates using by substring match.
    If no subtring matches, then use soundex and then LevenshteinDistance algorithms
    """
    re_not_text = re.compile("[^a-z0-9]", re.IGNORECASE)

    def clean(txt):
        """
        Return a lowercased copy of the given string
        with non-alpha characters removed.
        """
        return re.sub(re_not_text, '', txt.lower())

    clean_stuff = clean(stuff)
    soundex1 = soundex(stuff)

    clean_expected_stuff = collections.OrderedDict()
    for i in expected_stuff:
        clean_expected_stuff[clean(i)] = i

    match = []
    # given stuff could be the exact match
    if stuff in expected_stuff:
        match = [stuff]
    elif clean_stuff in clean_expected_stuff:
        match = [clean_expected_stuff[clean_stuff]]
    else:
        # stuff could be a substring of one of the expected value
        matching_subset = list([x for x in list(clean_expected_stuff.keys()) if x.lower().find(clean_stuff) >= 0])
        if len(matching_subset) == 1:
            match = [clean_expected_stuff[matching_subset[0]]]
        elif len(matching_subset) > 1:
            match = [clean_expected_stuff[i] for i in matching_subset]
        else:
            # no luck with subset lookup, fallback on soundex magic
            for m in clean_expected_stuff.keys():
                s = soundex(m)
                if s == soundex1:
                    match.append(clean_expected_stuff[m])

    if not match:
        match = sorted(list(expected_stuff))
        match.sort(key=lambda _map: levenshteinDistance(clean_stuff, _map.strip()))

    # create a set and keep the order
    match_set = collections.OrderedDict.fromkeys(match)
    return list(match_set.keys())


def corrent_spell(c_word, wordbook):
    """
    Simplified spell checker from Peter Norvig.
    http://www.norvig.com/spell-correct.html
    """

    def words(text):
        return re.findall('[a-z]+', text.lower())

    def train(features):
        model = collections.defaultdict(lambda: 1)
        for f in features:
            model[f] += 1
        return model

    nwords = train(words(wordbook))
    alphabet = 'abcdefghijklmnopqrstuvwxyz'

    def edits1(word):
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        deletes = [a + b[1:] for a, b in splits if b]
        transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1]
        replaces = [a + c + b[1:] for a, b in splits for c in alphabet if b]
        inserts = [a + c + b for a, b in splits for c in alphabet]
        return set(deletes + transposes + replaces + inserts)

    def known_edits2(word):
        return set(e2 for e1 in edits1(word) for e2 in edits1(e1) if e2 in nwords)

    def known(word):
        return set(w for w in word if w in nwords)

    def correct(word):
        candidates = known([word]) or known(edits1(word)) or known_edits2(word) or [word]
        return max(candidates, key=nwords.get)

    result = correct(c_word)
    if result == c_word:
        result = False

    return result


def prefixText(prefixes, text):
    """
    Add prefixes to a given text.
    :param prefixes: list[basestring] the list of prefixes to preprend to the text
    :param text: basestring the text to be prefixed
    :return basestring

    >>> prefixText(None, None)
    ''
    >>> prefixText(None, 'f00')
    'f00'
    >>> prefixText([], 'f00')
    'f00'
    >>> prefixText(['p1'], 'f00')
    'p1 f00'
    >>> prefixText(['p1', 'p2'], 'f00')
    'p1 p2 f00'
    >>> prefixText(['p1'], None)
    ''
    >>> prefixText(['p1'], '')
    ''
    """
    buff = ''
    if text:
        if prefixes:
            for prefix in prefixes:
                if prefix:
                    buff += prefix + ' '
        buff += text
    return buff


def getBytes(size):
    """
    Convert the given size in the correspondent amount of bytes.
    :param size: The size we want to convert in bytes
    :raise TypeError: If an invalid input is given
    :return: The given size converted in bytes
    >>> getBytes(10)
    10
    >>> getBytes('10')
    10
    >>> getBytes('1KB')
    1024
    >>> getBytes('1K')
    1024
    >>> getBytes('1MB')
    1048576
    >>> getBytes('1M')
    1048576
    >>> getBytes('1GB')
    1073741824
    >>> getBytes('1G')
    1073741824
    """
    size = str(size).upper()
    r = re.compile(r'''^(?P<size>\d+)\s*(?P<mult>KB|MB|GB|TB|K|M|G|T?)$''')
    m = r.match(size)
    if not m:
        raise TypeError(f'invalid input given: {size}')

    multipliers = {
        'K': 1024, 'KB': 1024,
        'M': 1048576, 'MB': 1048576,
        'G': 1073741824, 'GB': 1073741824,
        'T': 1099511627776, 'TB': 1099511627776,
    }

    try:
        return int(m.group('size')) * multipliers[m.group('mult')]
    except KeyError:
        return int(m.group('size'))


def start_daemon_thread(target, args=(), kwargs=None, name=None):
    """Start a new daemon thread"""
    opts = {
        'target': target,
        'daemon': True,
        'args': args,
        'kwargs': kwargs,
    }
    if name:
        opts['name'] = name
    t = threading.Thread(**opts)
    t.start()
    return t


_escape_table = [chr(x) for x in range(128)]
_escape_table[0] = u'\\0'
_escape_table[ord('\\')] = u'\\\\'
_escape_table[ord('\n')] = u'\\n'
_escape_table[ord('\r')] = u'\\r'
_escape_table[ord('\032')] = u'\\Z'
_escape_table[ord('"')] = u'\\"'
_escape_table[ord("'")] = u"\\'"


def escape_string(value):
    """
    escape_string escapes *value* but not surround it with quotes.
    Value should be bytes or unicode.
    """
    return value.translate(_escape_table)


def loadParser(pname):
    """
    Load the parser module given it's name.
    :param pname: The parser name
    :return The parser module
    """
    mod = getModule(f'b3.parsers.{pname}')
    return getattr(mod, f'{pname.title()}Parser')


def get_home_path(create=True):
    """
    Return the path to the B3 home directory.
    """
    path = os.path.normpath(os.path.expanduser('~/.b3'))
    if create and not os.path.isdir(path):
        os.mkdir(path)
    return path


def getB3Path(decode=False):
    """
    Return the path to the main B3 directory.
    :param decode: if True will decode the path string using the default file system encoding before returning it
    """
    modulePath = resource_directory(__name__)
    path = os.path.normpath(os.path.expanduser(modulePath))
    return path if not decode else decode_text(path)


def getAbsolutePath(path, decode=False, conf=None):
    """
    Return an absolute path name and expand the user prefix (~).
    :param path: the relative path we want to expand
    :param decode: if True will decode the path string using the default file system encoding before returning it
    :param conf: the current configuration being used :type XmlConfigParser|CfgConfigParser|MainConfig|str:
    """
    if path.startswith('@'):
        if path[1:4] in ('b3\\', 'b3/'):
            path = os.path.join(getB3Path(decode=False), path[4:])
        elif path[1:6] in ('conf\\', 'conf/'):
            import b3.config
            path = os.path.join(b3.config.getConfPath(decode=False, conf=conf), path[6:])
        elif path[1:6] in ('home\\', 'home/'):
            home_dir = get_home_path(create=True)
            path = os.path.join(home_dir, path[6:])
    path = os.path.normpath(os.path.expanduser(path))
    return path if not decode else decode_text(path)


def getWritableFilePath(filepath, decode=False):
    """
    Return an absolute file path making sure the current user can write it.
    If the given path is not writable by the current user, the path will be converted
    into an absolute path pointing inside the B3 home directory (defined in the `get_home_path`
    which is assumed to be writable.

    :param filepath: the relative path we want to expand
    :param decode: if True will decode the path string using the default file system encoding before returning it
    """
    filepath = getAbsolutePath(filepath, decode)
    home_dir = get_home_path(create=False)
    if not filepath.startswith(home_dir):
        try:
            with tempfile.TemporaryFile(dir=os.path.dirname(filepath)) as tf:
                pass
        except (OSError, IOError):
            # no need to decode again since home_dir is already decoded
            # and os.path.join will handle everything itself
            home_dir = get_home_path(create=True)
            filepath = os.path.join(home_dir, os.path.basename(filepath))
    return filepath


def getShortPath(filepath, decode=False, first_time=True):
    """
    Convert the given absolute path into a short path.
    Will replace path string with proper tokens (such as @b3, @conf, ~, ...)
    :param filepath: the path to convert
    :param decode: if True will decode the path string using the default file system encoding before returning it
    :param first_time: whether this is the first function call attempt or not
    :return: string
    """
    # NOTE: make sure to have os.path.sep at the end otherwise also files starting with 'b3' will be matched
    homepath = getAbsolutePath('@home/', decode) + os.path.sep
    if filepath.startswith(homepath):
        return filepath.replace(homepath, '@home' + os.path.sep)
    confpath = getAbsolutePath('@conf/', decode) + os.path.sep
    if filepath.startswith(confpath):
        return filepath.replace(confpath, '@conf' + os.path.sep)
    b3path = getAbsolutePath('@b3/', decode) + os.path.sep
    if filepath.startswith(b3path):
        return filepath.replace(b3path, '@b3' + os.path.sep)
    userpath = getAbsolutePath('~', decode) + os.path.sep
    if filepath.startswith(userpath):
        return filepath.replace(userpath, '~' + os.path.sep)
    if first_time:
        return getShortPath(filepath, not decode, False)
    return filepath
