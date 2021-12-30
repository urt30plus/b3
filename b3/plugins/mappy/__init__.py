import io
import zipfile
from contextlib import contextmanager
from pathlib import Path

import b3.functions
import b3.plugin

__author__ = '|30+|money'
__version__ = '0.9.0'

# Map info for bundled maps
MAP_MODES = {
    'ut4_abbey': {
        'modes': ['ffa', 'ctf'],
    },
    'ut4_casa': {
        'modes': ['ffa', 'ctf'],
    },
}


class MappyPlugin(b3.plugin.Plugin):

    def __init__(self, console, config=None) -> None:
        super().__init__(console, config)

    def onLoadConfig(self) -> None:
        pass

    def onStartup(self) -> None:
        self.register_commands_from_config()

    def cmd_mapmodes(self, data, client, cmd=None):
        """
        <mapname> - show modes for a given map, or the current map if no map
                    name is provided
        """
        if data:
            match = self.console.getMapsSoundingLike(data)
            if isinstance(match, str):
                map_name = match
            elif isinstance(match, list):
                client.message(f'do you mean : {", ".join(match[:5])} ?')
                return
            else:
                client.message(f'^7cannot find any map like [^4{data}^7]')
                return
        else:
            map_name = self.console.game.mapName

        b3.functions.start_daemon_thread(
            self._map_modes,
            (client, cmd, map_name),
        )

    def _map_paths(self) -> list[Path]:
        paths = []
        if home_path := self.console.game.fs_homepath:
            paths.append(Path(home_path) / 'q3ut4')
            paths.append(Path(home_path) / 'q3ut4' / 'download')
        if base_path := self.console.game.fs_basepath:
            paths.append(Path(base_path) / 'q3ut4')
            paths.append(Path(base_path) / 'q3ut4' / 'download')
        return paths

    def _map_modes(self, client, cmd, map_name):
        if map_data := MAP_MODES.get(map_name):
            modes = map_data.get('modes', [])
        else:
            map_filename = f'{map_name}.pk3'
            for map_path in self._map_paths():
                map_file = map_path / map_filename
                if map_file.exists():
                    break
            else:
                client.message(f'^7{map_filename} not found')
                return

            self.info('Looking up map modes in file: %s', map_file)
            data = self.parse_arena_file(map_file)
            modes = data.get('modes', ['unable to parse map modes'])

        map_modes = ' '.join([m.removeprefix('ut_') for m in modes])
        cmd.sayLoudOrPM(client, f'[{map_name}]: {map_modes}')

    @contextmanager
    def open_arena_file(self, map_path):
        with zipfile.ZipFile(map_path) as pk3:
            for info in pk3.infolist():
                if (
                        info.filename.startswith('scripts') and
                        info.filename.endswith('.arena')
                ):
                    with pk3.open(info) as arena:
                        yield arena
                    break
            else:
                self.error('%s: arena file not found', map_path)
                yield io.BytesIO()

    def parse_arena_file(self, map_path) -> dict[str, ...]:
        rv = {}
        with self.open_arena_file(map_path) as arena:
            for line in arena:
                line = line.decode(encoding='latin-1').strip()
                if line.startswith('type'):
                    modes = line[5:].replace('"', '').split()
                    rv['modes'] = modes
        return rv
