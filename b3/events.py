import functools
import re
import time
from collections import defaultdict, deque

from b3.functions import meanstdv

__author__ = "ThorN, xlr8or, Courgette"
__version__ = "1.8.2"


class Events:
    def __init__(self):
        self._events = {}
        self._event_names = {}

        self.loadEvents(
            (
                ("EVT_EXIT", "Program Exit"),
                ("EVT_STOP", "Stop Process"),
                ("EVT_UNKNOWN", "Unknown Event"),
                ("EVT_CUSTOM", "Custom Event"),
                ("EVT_PLUGIN_ENABLED", "Plugin Enabled"),
                ("EVT_PLUGIN_DISABLED", "Plugin Disabled"),
                ("EVT_PLUGIN_LOADED", "Plugin Loaded"),
                ("EVT_PLUGIN_UNLOADED", "Plugin Unloaded"),
                ("EVT_CLIENT_SAY", "Say"),
                ("EVT_CLIENT_TEAM_SAY", "Team Say"),
                ("EVT_CLIENT_SQUAD_SAY", "Squad Say"),
                ("EVT_CLIENT_PRIVATE_SAY", "Private Message"),
                ("EVT_CLIENT_CONNECT", "Client Connect"),
                ("EVT_CLIENT_AUTH", "Client Authenticated"),
                ("EVT_CLIENT_DISCONNECT", "Client Disconnect"),
                ("EVT_CLIENT_UPDATE", "Client Update"),
                ("EVT_CLIENT_KILL", "Client Kill"),
                ("EVT_CLIENT_GIB", "Client Gib"),
                ("EVT_CLIENT_GIB_TEAM", "Client Gib Team"),
                ("EVT_CLIENT_GIB_SELF", "Client Gib Self"),
                ("EVT_CLIENT_SUICIDE", "Client Suicide"),
                ("EVT_CLIENT_KILL_TEAM", "Client Team Kill"),
                ("EVT_CLIENT_DAMAGE", "Client Damage"),
                ("EVT_CLIENT_DAMAGE_SELF", "Client Damage Self"),
                ("EVT_CLIENT_DAMAGE_TEAM", "Client Team Damage"),
                ("EVT_CLIENT_JOIN", "Client Join Team"),
                ("EVT_CLIENT_NAME_CHANGE", "Client Name Change"),
                (
                    "EVT_CLIENT_TEAM_CHANGE",
                    "Client Team Change",
                ),  # provides only the new team
                (
                    "EVT_CLIENT_TEAM_CHANGE2",
                    "Client Team Change 2",
                ),  # provides the previous and new team
                ("EVT_CLIENT_ITEM_PICKUP", "Client Item Pickup"),
                ("EVT_CLIENT_ACTION", "Client Action"),
                ("EVT_CLIENT_KICK", "Client Kicked"),
                ("EVT_CLIENT_BAN", "Client Banned"),
                ("EVT_CLIENT_BAN_TEMP", "Client Temp Banned"),
                ("EVT_CLIENT_UNBAN", "Client Unbanned"),
                ("EVT_CLIENT_WARN", "Client Warned"),
                ("EVT_CLIENT_NOTICE", "Client given a notice"),
                ("EVT_GAME_ROUND_START", "Game Round Start"),
                ("EVT_GAME_ROUND_END", "Game Round End"),
                ("EVT_GAME_WARMUP", "Game Warmup"),
                ("EVT_GAME_EXIT", "Game Exit"),
                ("EVT_GAME_MAP_CHANGE", "map changed"),
                ("EVT_GAME_FLAG_RETURNED", "Flag returned"),
                ("EVT_CLIENT_GEAR_CHANGE", "Client gear change"),
                ("EVT_SURVIVOR_WIN", "Survivor Winner"),
                ("EVT_BOMB_EXPLODED", "Bomb exploded"),
                ("EVT_SENTRY_KILL", "Mr Sentry kill"),
                ("EVT_CLIENT_RADIO", "Event client radio"),
                ("EVT_GAME_FLAG_HOTPOTATO", "Event game hotpotato"),
                ("EVT_CLIENT_CALLVOTE", "Event client call vote"),
                ("EVT_CLIENT_VOTE", "Event client vote"),
                ("EVT_VOTE_PASSED", "Event vote passed"),
                ("EVT_VOTE_FAILED", "Event vote failed"),
                ("EVT_FLAG_CAPTURE_TIME", "Event flag capture time"),
                ("EVT_CLIENT_JUMP_RUN_START", "Event client jump run started"),
                ("EVT_CLIENT_JUMP_RUN_STOP", "Event client jump run stopped"),
                ("EVT_CLIENT_JUMP_RUN_CANCEL", "Event client jump run canceled"),
                ("EVT_CLIENT_POS_SAVE", "Event client position saved"),
                ("EVT_CLIENT_POS_LOAD", "Event client position loaded"),
                ("EVT_CLIENT_GOTO", "Event client goto"),
                ("EVT_CLIENT_SPAWN", "Event client spawn"),
                ("EVT_CLIENT_SURVIVOR_WINNER", "Event client survivor winner"),
                ("EVT_CLIENT_FREEZE", "Event client freeze"),
                ("EVT_CLIENT_THAWOUT_STARTED", "Event client thawout started"),
                ("EVT_CLIENT_THAWOUT_FINISHED", "Event client thawout finished"),
                ("EVT_CLIENT_MELTED", "Event client melted"),
                ("EVT_ASSIST", "Event assist"),
            )
        )

    def createEvent(self, key, name=None):
        """
        Create an event.
        :param key: The event key
        :param name: An optional name to associate to the event
        """
        g = globals()

        try:
            _id = self._events[key] = g[key]
        except KeyError:
            _id = self._events[key] = len(self._events) + 1

        self._event_names[_id] = name or f"Unnamed ({key})"

        g[key] = _id
        return _id

    def getId(self, key):
        """
        Return an event ID given its key.
        :param key: The event key
        """
        if re.match("^[0-9]+$", str(key)):
            return int(key)
        return self._events.get(key)

    @functools.cache  # noqa: B019
    def getKey(self, event_id):
        """
        Get the key of a given event ID.
        :param event_id: The event ID
        """
        matching_keys = [k for k, v in self._events.items() if v == event_id]
        if not matching_keys:
            raise KeyError(f"could not find any B3 event with ID {event_id}")
        assert (
            len(matching_keys) == 1
        ), f"expecting only one event key per event ID: {matching_keys!r}"
        return matching_keys[0]

    def getName(self, key):
        """
        Return an event name given its key.
        :param key: The event key
        """
        return self._event_names.get(self.getId(key), f"Unknown ({key})")

    def loadEvents(self, events):
        """
        Load default events.
        :param events: A collection of Event tuples
        """
        for k, n in events:
            self.createEvent(k, n)

    @property
    def events(self):
        """
        Return the Event dict.
        """
        return self._events


class Event:
    def __init__(self, type, data, client=None, target=None):
        """
        Object constructor.
        :param type: The event ID
        :param data: Event data
        :param client: The client source of this event
        :param target: The target of this event
        """
        self.time = int(time.time())
        self.type = type
        self.data = data
        self.client = client
        self.target = target
        self.key = eventManager.getKey(type)

    def __str__(self):
        return f"Event<{self.key}>({self.data!r}, {self.client}, {self.target})"


class EventsStats:
    def __init__(self, console, max_samples=100):
        """
        Object constructor.
        :param console: The console class instance
        :param max_samples: The size of the event queue
        """
        self.console = console
        deque_with_max = functools.partial(deque, maxlen=max_samples)
        dict_deque = functools.partial(defaultdict, deque_with_max)
        self._handling_timers = defaultdict(dict_deque)

    def add_event_handled(self, plugin_name, event_name, elapsed):
        """
        Add an event to the dict of handled ones.
        :param plugin_name: The name of the plugin which handled the event
        :param event_name: The event name
        :param elapsed: The amount of milliseconds necessary to handle the event
        """
        self._handling_timers[plugin_name][event_name].append(elapsed)

    def dump_stats(self):
        """
        Print event stats in the log file.
        """
        self.console.info("***** Event Stats *****")
        for plugin_name, plugin_timers in self._handling_timers.items():
            for event_name, event_timers in plugin_timers.items():
                if event_timers:
                    mean, stdv = meanstdv(event_timers)
                    self.console.info(
                        "%s %s : min(%0.4f), max(%0.4f), mean(%0.4f), stddev(%0.4f)",
                        plugin_name,
                        event_name,
                        min(event_timers),
                        max(event_timers),
                        mean,
                        stdv,
                    )


class VetoEvent(Exception):
    """
    Raised to cancel event processing.
    """


eventManager = Events()
