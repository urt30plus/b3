from b3.plugins.abc import WeaponKillPlugin

__author__ = "SvaRoX"
__version__ = "0.3"


class NaderPlugin(WeaponKillPlugin):
    def __init__(self, console, config=None):
        super().__init__(console, config)
        self._weapons = (console.UT_MOD_HEGRENADE,)

    @property
    def cmd_msg_prefix(self) -> str:
        return "he"

    @property
    def weapon_name(self) -> str:
        return "HE grenade"

    @property
    def weapon_action(self) -> str:
        return "nade"

    @property
    def weapons_handled(self) -> tuple[int, ...]:
        return self._weapons
