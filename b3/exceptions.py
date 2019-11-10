import configparser

NoOptionError = configparser.NoOptionError
NoSectionError = configparser.NoSectionError


class ConfigFileNotFound(Exception):
    """
    Raised whenever the configuration file can't be found.
    """

    def __init__(self, message):
        Exception.__init__(self, message)

    def __str__(self):
        return repr(self.args[0])


class ConfigFileNotValid(Exception):
    """
    Raised whenever we are parsing an invalid configuration file.
    """

    def __init__(self, message):
        Exception.__init__(self, message)

    def __str__(self):
        return repr(self.args[0])


class MissingRequirement(Exception):
    """
    Raised whenever we can't initialize a functionality because some modules are missing.
    """

    def __init__(self, message, throwable=None):
        Exception.__init__(self, message)
        self.throwable = throwable

    def __str__(self):
        if self.throwable:
            return '%s - %r' % (self.args[0], repr(self.throwable))
        return repr(self.args[0])


class ProgrammingError(Exception):
    """
    Raised whenever a programming error is detected.
    """

    def __init__(self, message):
        Exception.__init__(self, message)

    def __str__(self):
        return repr(self.args[0])


class DatabaseError(Exception):
    """
    Raised whenever there are inconsistences with the database schema.
    """

    def __init__(self, message):
        Exception.__init__(self, message)

    def __str__(self):
        return repr(self.args[0])


class UpdateError(Exception):
    """
    Raised whenever we fail in updating B3 sources.
    """

    def __init__(self, message, throwable=None):
        Exception.__init__(self, message)
        self.throwable = throwable

    def __str__(self):
        if self.throwable:
            return '%s - %r' % (self.args[0], repr(self.throwable))
        return repr(self.args[0])
