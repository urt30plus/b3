"""
Prints the supported game types for maps.

Given a map file or a path to where map files exist, will print to stdout
the map name and the supported game types. It looks in the 'scripts' path
in each map file (.pk3) and pulls the game types from the 'type' line in the
arena files.

"""
import sys
import zipfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def open_arena_file(map_path):
    with zipfile.ZipFile(map_path) as pk3:
        for info in pk3.infolist():
            if info.filename.startswith('scripts') and \
                    info.filename.endswith('.arena'):
                with pk3.open(info) as arena:
                    yield arena
                break


def parse_arena_file(map_path):
    with open_arena_file(map_path) as arena:
        for line in arena:
            line = line.decode(encoding='latin-1').strip()
            if line.startswith('type'):
                modes = line[5:].replace('"', '').split()
                return modes
    return ['None']


def game_types_for(map_path):
    try:
        return parse_arena_file(map_path)
    except Exception as ex:
        return [f'{ex!r}']


def map_modes(map_path):
    if map_path.is_file():
        return {
            map_path.name: game_types_for(map_path)
        }
    else:
        return {
            p.name: game_types_for(p)
            for p in map_path.iterdir()
            if p.is_file() and p.suffix == '.pk3'
        }


def main():
    map_path = Path(sys.argv[1])
    for name, modes in map_modes(map_path).items():
        print(name, end='\n\t')
        print('\n\t'.join(modes))


if __name__ == '__main__':
    main()
