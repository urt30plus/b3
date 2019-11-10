__author__ = 'ThorN'
__version__ = '1.1'


class Cvar:

    def __init__(self, name, **kwargs):
        """
        Object constructor.
        :param name: The CVAR name.
        :param kwargs: A dict containing optional value and default.
        """
        self.name = name
        self.value = kwargs.get("value")
        self.default = kwargs.get("default")

    def __getitem__(self, key):
        """
        Used to get CVAR attributes using dict keys:
            - name = cvar['name']
            - value = cvar['value']
            - default = cvar['default']
            - value = cvar[0]
            - default = cvar[1]
        """
        if isinstance(key, int):
            if key == 0:
                return self.value
            elif key == 1:
                return self.default
            else:
                raise KeyError(f"no key {key}")
        else:
            return self.__dict__[key]

    def __repr__(self):
        """
        String object representation.
        :return A string representing this CVAR.
        """
        return '<%s name: "%s", value: "%s", default: "%s">' % (self.__class__.__name__,
                                                                self.name,
                                                                self.value,
                                                                self.default)

    def getString(self):
        """
        Return the CVAR value as a string.
        :return basestring
        """
        return str(self.value)

    def getInt(self):
        """
        Return the CVAR value as an integer.
        :return int
        """
        return int(self.value)

    def getFloat(self):
        """
        Return the CVAR value as a floating point number.
        :return float
        """
        return float(self.value)

    def getBoolean(self):
        """
        Return the CVAR value as a boolean value.
        :return boolean
        """
        if self.value in ('yes', '1', 'on', 'true'):
            return True
        elif self.value in ('no', '0', 'off', 'false'):
            return False
        else:
            raise ValueError(f"{self.value} is not a boolean value")

    def save(self, console):
        """
        Set the CVAR current value.
        :param console: The console to be used to send the cvar set command.
        """
        console.setCvar(self.name, self.value)
