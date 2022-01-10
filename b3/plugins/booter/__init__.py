from b3.plugins.abc import WeaponKillPlugin

__author__ = '|30+|money'
__version__ = '1.0'


class BooterPlugin(WeaponKillPlugin):

    def __init__(self, console, config=None):
        super().__init__(console, config)
        self._weapons = (
            console.UT_MOD_KICKED,
            console.UT_MOD_GOOMBA,
        )

    @property
    def cmd_msg_prefix(self) -> str:
        return 'boot'

    @property
    def weapon_name(self) -> str:
        return 'boot'

    @property
    def weapon_action(self) -> str:
        return 'boot'

    @property
    def weapons_handled(self) -> tuple[int, ...]:
        return self._weapons
