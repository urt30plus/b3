__author__ = "ThorN"
__version__ = "1.6"


class Game:
    _mapName = None
    _mapTimeStart = None
    _roundTimeStart = None

    captureLimit = None
    fragLimit = None
    timeLimit = None

    gameName = None
    gameType = None
    modName = None

    rounds = 0

    def __init__(self, console, gameName):
        """
        Object constructor.
        :param console: Console class instance
        :param gameName: The current game name
        """
        self.console = console
        self.gameName = gameName
        self.startRound()

    def __getattr__(self, key):
        return self.__dict__.get(key)

    def __setitem__(self, key, value):
        self.__dict__[key] = value
        return self.__dict__[key]

    @property
    def game_type(self):
        if self.gameType is None:
            try:
                value = self.console.getCvar("g_gametype").getString()
            except Exception:
                self.console.warning("unable to determine current gametype")
            else:
                self.gameType = self.console.defineGameType(value)
        return self.gameType

    @property
    def mapName(self):
        if not self._mapName:
            try:
                # try to get the mapname from the server
                mapname = self.console.getMap()
            except Exception:
                self._mapName = None
            else:
                # set using _set_mapName to generate EVT_GAME_MAP_CHANGE
                self._set_mapName(mapname)
        return self._mapName

    @mapName.setter
    def mapName(self, newmap):
        if self._mapName != newmap:
            # generate EVT_GAME_MAP_CHANGE so plugins can detect that a new game is starting
            event = self.console.getEvent(
                "EVT_GAME_MAP_CHANGE", data={"old": self._mapName, "new": newmap}
            )
            self.console.queueEvent(event)
        self._mapName = newmap

    def mapTime(self):
        """
        Return the time elapsed since map start.
        """
        if self._mapTimeStart:
            return self.console.time() - self._mapTimeStart

    def roundTime(self):
        """
        Return the time elapsed since round start
        """
        return self.console.time() - self._roundTimeStart

    def startRound(self):
        """
        Set variables to mark round start.
        """
        if not self._mapTimeStart:
            self.startMap()
        self._roundTimeStart = self.console.time()
        self.rounds += 1

    def startMap(self, mapName=None):
        """
        Set variables to mark map start.
        """
        if mapName:
            self.mapName = mapName
        self._mapTimeStart = self.console.time()

    def mapEnd(self):
        """
        Set variables to mark map end.
        """
        self._mapTimeStart = None
