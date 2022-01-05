import glob
import graphlib
import importlib
import os
import sys
import types
from collections.abc import Callable
from typing import Any, Optional, Union

import b3.config
import b3.functions
import b3.plugin
from b3 import __version__ as b3_version
from b3.update import B3version

B3ConfigType = Union[b3.config.XmlConfigParser, b3.config.CfgConfigParser]
B3PluginType = Callable[[Any, B3ConfigType], b3.plugin.Plugin]


class PluginData:
    """
    Class used to hold plugin data needed for plugin instance initialization.
    """

    def __init__(
            self,
            name: str,
            module: types.ModuleType,
            clazz: B3PluginType,
            conf: Optional[B3ConfigType] = None,
            disabled: bool = False,
    ) -> None:
        self.name = name.lower()
        self.module = module
        self.clazz = clazz
        self.conf = conf
        self.disabled = disabled

    def __repr__(self) -> str:
        return f"PluginData<{self.name}>"


def _import_plugin(console, name: str, path: str = None) -> types.ModuleType:
    if path is not None:
        console.info('Loading plugin from specified path: %s', path)
        if path not in sys.path:
            console.warning('Appending path %s to sys.path', path)
            sys.path.append(path)
        return importlib.import_module(name)

    try:
        return importlib.import_module(f'b3.plugins.{name}')
    except ImportError as m:
        ext_plugin_dir = console.config.get_external_plugins_dir()
        console.info('%s is not a built-in plugin (%s)', name.title(), m)
        console.info('Trying external plugin directory : %s', ext_plugin_dir)
        if ext_plugin_dir not in sys.path:
            console.warning('Appending external directory %s to sys.path',
                            ext_plugin_dir)
            sys.path.append(ext_plugin_dir)
        return importlib.import_module(name)


def _search_config_file(match: str, ext_plugins_dir: str = None) -> list[str]:
    # first look in the built-in plugins directory
    base_conf_path = b3.functions.getAbsolutePath('@conf\\', decode=True)
    collection = glob.glob(f'{base_conf_path}{os.path.sep}*{match}*')
    if not collection and ext_plugins_dir:
        ext_conf_path = os.path.join(
            b3.functions.getAbsolutePath(ext_plugins_dir, decode=True),
            match,
            '../conf'
        )
        collection = glob.glob(f'{ext_conf_path}{os.path.sep}*{match}*')
    return collection


def _get_plugin_config(
        console,
        p_name: str,
        p_clazz: b3.plugin.Plugin,
        p_config_path: str = None,
) -> Optional[B3ConfigType]:
    ext_plugins_dir = console.config.get_external_plugins_dir()
    console.bot('Loading plugins (external plugin directory: %s)',
                ext_plugins_dir)

    if p_config_path is None:
        # no plugin configuration file path specified: we can still load the
        # plugin if there is non need for a configuration file, otherwise we
        # will look up one
        if not p_clazz.requiresConfigFile:
            return None

        # lookup a configuration file for this plugin
        console.warning('No configuration file specified for plugin %s: '
                        'searching a valid configuration file...', p_name)

        search_path = _search_config_file(p_name, ext_plugins_dir)
        if len(search_path) == 0:
            # raise an exception so the plugin will not be loaded
            # (since we miss the needed config file)
            raise b3.config.ConfigFileNotFound(
                f'could not find any configuration file for plugin {p_name}'
            )
        if len(search_path) > 1:
            # log all the configuration files found so users can decide to
            # remove some of them on the next B3 startup
            console.warning(
                'Multiple configuration files found for plugin %s: %s',
                p_name, ', '.join(search_path)
            )

        # if load fails, an exception is raised and the plugin won't be loaded
        console.bot('Loading configuration file %s for plugin %s',
                    search_path[0], p_name)

        return b3.config.load(search_path[0])
    else:
        # configuration file specified: load it if it's found. If we are not
        # able to find the configuration file, then keep loading the plugin if
        # such a plugin doesn't require a configuration file (optional)
        # otherwise stop loading the plugin and log an error message.
        p_config_absolute_path = b3.functions.getAbsolutePath(p_config_path,
                                                              decode=True)
        if os.path.exists(p_config_absolute_path):
            console.bot('Loading configuration file %s for plugin %s',
                        p_config_absolute_path, p_name)
            return b3.config.load(p_config_absolute_path)

        # notice missing configuration file
        console.warning(
            'Could not find specified configuration file %s for plugin %s',
            p_config_absolute_path, p_name
        )

        if p_clazz.requiresConfigFile:
            raise b3.config.ConfigFileNotFound(
                f'plugin {p_name} cannot be '
                'loaded without a configuration file'
            )

        console.warning(
            'Not loading a configuration file for plugin %s: '
            'plugin %s can work also without a configuration file',
            p_name, p_name
        )
        return None


def _check_plugin_version(p_data: PluginData) -> None:
    if (
            p_data.clazz.requiresVersion and
            B3version(p_data.clazz.requiresVersion) > B3version(b3_version)
    ):
        raise b3.config.MissingRequirement(
            f'plugin {p_data.name} requires B3 version '
            f'{p_data.clazz.requiresVersion} (you have version {b3_version}) '
            ': please update your B3 if you want to run this plugin'
        )


def _check_plugin_game(p_data: PluginData, game_name: str) -> None:
    if (
            p_data.clazz.requiresParsers and
            game_name not in p_data.clazz.requiresParsers
    ):
        raise b3.config.MissingRequirement(
            f'plugin {p_data.name} is not compatible with '
            f'{game_name} parser : supported games are :'
            f' {", ".join(p_data.clazz.requiresParsers)}'
        )


def _check_plugin_storage(p_data: PluginData, storage_proto: str) -> None:
    if (
            p_data.clazz.requiresStorage and
            storage_proto not in p_data.clazz.requiresStorage
    ):
        raise b3.config.MissingRequirement(
            f'plugin {p_data.name} is not compatible with the '
            f'storage protocol being used ({storage_proto}) : '
            f'supported protocols are : '
            f'{", ".join(p_data.clazz.requiresStorage)}'
        )


def _check_plugin_requirements(
        console,
        all_plugins: dict[str, PluginData],
        p_data: PluginData,
) -> True:
    try:
        _check_plugin_version(p_data)
        _check_plugin_game(p_data, console.gameName)
        _check_plugin_storage(p_data, console.storage.protocol)
        if p_data.clazz.requiresPlugins:
            for r in p_data.clazz.requiresPlugins:
                if r not in all_plugins:
                    raise b3.config.MissingRequirement(
                        f'missing required plugin: {r}'
                    )
    except b3.config.MissingRequirement as err:
        console.error('Could not load plugin %s', p_data.name, exc_info=err)
        return False
    else:
        return True


def _filter_missing_requirements(console, plugins) -> dict[str, PluginData]:
    return {
        name: data
        for name, data in plugins.items()
        if _check_plugin_requirements(console, plugins, data)
    }


def _get_plugins_from_config(console) -> dict[str, PluginData]:
    # will parse the plugin section of b3.ini, looking for plugins to be
    # loaded. we will import needed python classes and generate
    # configuration file instances for plugins.
    plugins = {}
    for p in console.config.get_plugins():
        plugin_name = p['name']
        if plugin_name in plugins:
            console.warning(
                'Plugin %s already loaded: '
                'avoid multiple entries of the same plugin',
                plugin_name
            )
            continue
        try:
            mod = _import_plugin(console, plugin_name, p['path'])
            clz = getattr(mod, f'{plugin_name.title()}Plugin')
            cfg = _get_plugin_config(console, plugin_name, clz, p['conf'])
            plugin_data = PluginData(name=plugin_name,
                                     module=mod,
                                     clazz=clz,
                                     conf=cfg,
                                     disabled=p['disabled'])
        except Exception as err:
            console.error('Could not load plugin %s', plugin_name, exc_info=err)
        else:
            plugins[plugin_name] = plugin_data

    return _filter_missing_requirements(console, plugins)


def _sort_plugins(console, plugin_data: dict[str, PluginData]) -> list:
    console.bot('Sorting plugins according to their dependency tree...')

    # Ensure admin plugin is always listed first
    sorted_plugin_list = [plugin_data.pop('admin')]
    plugin_graph = {
        name: set(
            plugin.clazz.requiresPlugins +
            [z for z in plugin.clazz.loadAfterPlugins if z in plugin_data]
        )
        for name, plugin in plugin_data.items()
    }
    sorted_plugin_list += [
        plugin_data[x]
        for x in graphlib.TopologicalSorter(plugin_graph).static_order()
    ]
    return sorted_plugin_list


def _create_plugin_instances(console, plugins: list[PluginData]) -> None:
    console.bot('Ready to create plugin instances: %s',
                ', '.join([x.name for x in plugins]))

    plugin_num = 1
    for plugin_data in plugins:
        if plugin_data.conf is None:
            plugin_conf_path = '--'
        else:
            plugin_conf_path = plugin_data.conf.fileName

        console.bot('Loading plugin #%s : %s [%s]',
                    plugin_num, plugin_data.name, plugin_conf_path)
        try:
            plugin_instance = plugin_data.clazz(console, plugin_data.conf)
            if plugin_data.disabled:
                console.info("Disabling plugin %s", plugin_data.name)
                plugin_instance.disable()
            console.addPlugin(plugin_data.name, plugin_instance)
        except Exception as err:
            console.error('Could not load plugin %s', plugin_data.name,
                          exc_info=err)
            console.screen.write('x')
        else:
            plugin_num += 1
            version = getattr(plugin_data.module, '__version__',
                              'Unknown Version')
            author = getattr(plugin_data.module, '__author__', 'Unknown Author')
            console.bot('Plugin %s (%s - %s) loaded',
                        plugin_data.name, version, author)
            console.screen.write('.')
        finally:
            console.screen.flush()


def import_plugins(console) -> None:
    plugins = _get_plugins_from_config(console)
    if 'admin' not in plugins:
        console.critical(
            'Plugin admin is essential and MUST be loaded! '
            'Cannot continue without admin plugin'
        )

    sorted_plugins = _sort_plugins(console, plugins)
    _create_plugin_instances(console, sorted_plugins)
