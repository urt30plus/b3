from b3.plugins.abc import WeaponKillPlugin

__author__ = 'SvaRoX'
__version__ = '0.3'


class KniferPlugin(WeaponKillPlugin):

    def __init__(self, console, config=None):
        super().__init__(console, config)
        self._weapons = (
            console.UT_MOD_KNIFE,
            console.UT_MOD_KNIFE_THROWN,
        )

    @property
    def cmd_msg_prefix(self) -> str:
        return 'kn'

    @property
    def weapon_name(self) -> str:
        return 'knife'

    @property
    def weapon_action(self) -> str:
        return 'slice'

    @property
    def weapons_handled(self) -> tuple[int, ...]:
        return self._weapons
