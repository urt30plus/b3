__author__ = "Courgette"
__version__ = "1.2"

PROTOCOLS = ("sqlite",)


class Storage:
    console = None
    protocol = None

    def connect(self):
        raise NotImplementedError

    def shutdown(self):
        raise NotImplementedError

    def getConnection(self):
        raise NotImplementedError

    def getCounts(self):
        raise NotImplementedError

    def getClient(self, client):
        raise NotImplementedError

    def getClientsMatching(self, match):
        raise NotImplementedError

    def setClient(self, client):
        raise NotImplementedError

    def setClientAlias(self, alias):
        raise NotImplementedError

    def getClientAlias(self, alias):
        raise NotImplementedError

    def getClientAliases(self, client):
        raise NotImplementedError

    def setClientIpAddress(self, ipalias):
        raise NotImplementedError

    def getClientIpAddress(self, ipalias):
        raise NotImplementedError

    def getClientIpAddresses(self, client):
        raise NotImplementedError

    def getLastPenalties(self, types="Ban", num=5):
        raise NotImplementedError

    def setClientPenalty(self, penalty):
        raise NotImplementedError

    def getClientPenalty(self, penalty):
        raise NotImplementedError

    def getClientPenalties(self, client, type="Ban"):
        raise NotImplementedError

    def getClientLastPenalty(self, client, type="Ban"):
        raise NotImplementedError

    def getClientFirstPenalty(self, client, type="Ban"):
        raise NotImplementedError

    def disableClientPenalties(self, client, type="Ban"):
        raise NotImplementedError

    def numPenalties(self, client, type="Ban"):
        raise NotImplementedError

    def getGroups(self):
        raise NotImplementedError

    def getGroup(self, group):
        raise NotImplementedError

    def getTables(self):
        raise NotImplementedError

    def truncateTable(self, table):
        raise NotImplementedError

    def status(self):
        raise NotImplementedError


from .sqlite import SqliteStorage  # noqa: E402,F401


def getStorage(dsn, dsnDict, console):
    """
    Return an initialized storage module instance (not connected with the underlying storage layer).
    Every exception raised by this function should make B3 non-operational since we won't have storage support.
    :param dsn: The database connection string.
    :param dsnDict: The database connection string parsed into a dict.
    :param console: The console instance.
    :raise AttributeError: If we don't manage to setup a valid storage module.
    :raise ImportError: If the system misses the necessary libraries needed to setup the storage module.
    :return: The storage module object instance connected with the underlying storage layer.
    """
    if not dsnDict:
        raise AttributeError(f"invalid database configuration specified: {dsn}")

    if dsnDict["protocol"] not in PROTOCOLS:
        raise AttributeError(
            f"invalid storage protocol specified: {dsnDict['protocol']}: supported storage "
            f"protocols are: {','.join(PROTOCOLS)}"
        )

    construct = globals()[f"{dsnDict['protocol'].title()}Storage"]
    return construct(dsn, dsnDict, console)
