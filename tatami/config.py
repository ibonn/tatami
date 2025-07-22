import difflib
import importlib
import logging
import os
from types import ModuleType, NoneType
from typing import Any, Callable, Coroutine, Optional

import yaml

from tatami._config.database import (db_from_bool, db_from_dict, db_from_none,
                                     db_from_str)

_logger = logging.getLogger('tatami.config')

# Config names and their allowed value types
VALUES = {
    ('database', NoneType): db_from_none,
    ('database', bool): db_from_bool,
    ('database', str): db_from_str,
    ('database', dict): db_from_dict,
}

# Set of valid config names
_VALID_NAMES = set(name for name, _ in VALUES)

def _load_config_from_yaml(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
       return yaml.safe_load(f)
    
def _load_config_from_py(path: str) -> dict:
    path = path.replace('/', '.').replace('\\', '.')[:-3]
    module = importlib.import_module(path)
    
    # Get all non private members and iscard modules/functions/classes/coroutines...
    config_names = [name for name in dir(module) if not name.startswith('_') and not isinstance(getattr(module, name), (type, ModuleType, Callable, Coroutine))]

    _logger.debug('Names found: %s', config_names)
    return {name: load_value(name, getattr(module, name)) for name in config_names}


def load_value(name: str, value: Any) -> Any:
    try:
        loader = VALUES[(name, type(value))]
    except KeyError as e:
        if name in _VALID_NAMES:
            # Name is valid, type is invalid
            valid_types = map(lambda x: x[1].__name__, filter(lambda v: v[0] == name, VALUES))
            raise TypeError(f'Config value "{name}" has an unexpected type ({type(value).__name__}). Valid types are: {", ".join(valid_types)}') from e
        else:
            close_matches = difflib.get_close_matches(name, _VALID_NAMES, n=1)
            if len(close_matches) == 0:
                raise ValueError(f'Unknown config value: "{name}"') from e
            else:
                raise ValueError(f'Unknown config value: "{name}". Did you mean "{close_matches[0]}"?') from e

    return loader(value)

def load_config(project_path: str, mode: Optional[str] = None) -> dict:
    if mode is None:
        yaml_filename = 'config.yaml'
        yml_filename = 'config.yml'
        py_filename = 'config.py'
    else:
        yaml_filename = f'config-{mode}.yaml'
        yml_filename = f'config-{mode}.yml'
        py_filename = f'config-{mode}.py'

    yaml_path = os.path.join(project_path, yaml_filename)
    yml_path = os.path.join(project_path, yml_filename)
    py_path = os.path.join(project_path, py_filename)

    yaml_exists = os.path.isfile(yaml_path)
    yml_exists = os.path.isfile(yml_path)
    py_exists = os.path.isfile(py_path)

    if not yaml_exists and not yml_exists and not py_exists:
        if mode is None:
            _logger.info('No configuration found')
            return {}
        else:
            _logger.error('A configuration has been specified but it could not be found. Aborting...')
            raise RuntimeError(f'No configuration found for "{mode}" mode')

    if yaml_exists and yml_exists:
        _logger.error('Conflict! both %s and %s files are present. Aborting...', yaml_filename, yml_filename)
        raise RuntimeError(f'{yaml_filename} and {yml_filename} cannot exist at the same time')
    
    config = {}

    if yaml_exists:
        _logger.info('Loading %s...', yaml_filename)
        config = _load_config_from_yaml(yaml_path)

    if yml_exists:
        _logger.info('Loading %s...', yml_filename)
        config = _load_config_from_yaml(yml_path)

    _logger.debug('Preliminary config: %s', config)

    if py_exists:
        if yaml_exists or yml_exists:
            _logger.info('Loading additional config from %s...', py_filename)
        else:
            _logger.info('Loading %s...', py_filename)

        additional_config = _load_config_from_py(py_path)

        for k, v in additional_config.items():
            config[k] = v

    _logger.debug('Final config: %s', config)

    return config