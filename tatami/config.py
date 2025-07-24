import glob
import importlib.util
import logging
import os
import re
from typing import Any, Literal, Optional, Union

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

from tatami._utils import import_from_path

logger = logging.getLogger('tatami.config')

class ConfigError(Exception):
    pass

class MissingEnvVarError(ConfigError):
    pass

class ConfigConflictError(ConfigError):
    pass

class InvalidFileError(ConfigError):
    pass


class DatabaseConfig(BaseModel):
    db_type: Literal['postgres', 'postgresql', 'sqlite'] = Field(description='Database type', default='sqlite')
    driver: Optional[Literal['psycopg']] = Field(default=None, description='Database driver')
    connection_string: str = Field(description='Database connection string', default='sqlite:///tatami.db')


class Config(BaseModel):
    app_name: str = Field(default='Tatami', description='The application name')
    version: str = Field(default='0.0.0', description='The application version')
    database: Union[bool, str, DatabaseConfig] = Field(default=False, description='Does the application have a database? If so, how do we connect to it? All that info is stored here')

    @field_validator('*')
    @classmethod
    def set_env_vars(cls, value: Any) -> Any:
        if isinstance(value, str):
            variables = re.findall(r'\${env:([^ }]+)}', value)
            try:
                for variable in variables:
                    value = value.replace(f'${{env:{variable}}}', os.environ[variable])
            except KeyError as e:
                raise MissingEnvVarError(f'The environment variable {e.args[0]} is not defined') from e
        return value


def load_dotenv_files(path: str) -> None:
    """Load all the dotenv (.env) files found in a given directory.
    Files whose name starts with an underscore will be excluded.

    This function is internally used by Tatami to load all the files
    on the project directory

    Example usage

    Supposing we have three files
    
    * path/to/project/secrets.env
    * path/to/project/_ignore.env
    * path/to/project/.env

    Calling the function
    .. code-block:: python
        load_dotenv_files('path/to/project')

    would load the values found at ``path/to/project/secrets.env`` and ``path/to/project/.env``
    but would ignore the values at ``path/to/project/_ignore.env`` as it starts with an underscore

    Args:
        path (str): The path where the files will be searched
    """
    dotenv_glob = os.path.join(path, '*.env')
    dotenv_paths = glob.glob(dotenv_glob)

    for dotenv_path in dotenv_paths:
        if os.path.basename(dotenv_paths).startswith('_'):
            logger.debug('Environment file %s starts with "_", it will be ignored', dotenv_path)
        else:
            if load_dotenv(dotenv_path):
                logger.debug('Environment variables loaded from %s')
            else:
                logger.error('Failed to load environment variables from %s', dotenv_path)


def find_config(project_path: str, mode: Optional[str] = None) -> Optional[str]:
    """Find the configuration file for the given project

    Args:
        project_path (str): Path to the project
        mode (Optional[str]): The config mode (dev, prod, test...). If `None` the default config will be looked for. Defaults to None. 

    Returns:
        Optional[str]: The path to the config if found, None if no config file was found
    """
    filename = f'config-{mode}' if mode else 'config'
    
    yaml_path = os.path.join(project_path, f'{filename}.yaml')
    yml_path = os.path.join(project_path, f'{filename}.yml')
    py_path = os.path.join(project_path, f'{filename}.py')

    yaml_exists = os.path.isfile(yaml_path)
    yml_exists = os.path.isfile(yml_path)
    py_exists = os.path.isfile(py_path)

    if sum([yaml_exists, yml_exists, py_exists]) > 1:
        raise ConfigConflictError('Multiple config files found')

    if yaml_exists:
        return yaml_path

    if yml_exists:
        return yml_path
    
    if py_exists:
        return py_path
    
    # No config found
    return None


def _load_config_from_yaml(path: str) -> Config:
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return Config(**data)


def _load_config_from_py(path: str) -> Union[Config, None]:
    module = import_from_path(path)

    logger.debug('Looking for a variable called "config"...')
    config = getattr(module, 'config', None)

    if config is None or not isinstance(config, Config):
        logger.debug('Variable "config" was not found or it contains an invalid value. Trying to find any "Config" object...')
        
        candidates = []
        for name in dir(module):
            value = getattr(module, name)
            if isinstance(value, Config):
                logger.debug('"Config" object found at variable with name %s', name)
                candidates.append(name)

        if len(candidates) == 0:
            logger.debug('No config objects found')
            return None

        if len(candidates) > 1:
            logger.exception('Conflict: Multiple configuration objects found (%s objects: %s)', len(candidates), ', '.join(candidates))
            raise ConfigConflictError('Multiple configuration objects found')
        
        config_name = candidates[0]
        logger.debug('Config found at variable with name "%s"', config_name)
        return getattr(module, config_name)

    else:
        logger.debug('Config found in config variable')
        return config


def load_config(path: str) -> Config:
    """Load a config file

    Args:
        path (str): Path to the config file

    Returns:
        Config: The config object
    """

    _, ext = os.path.splitext(path.lower())

    if ext in {'.yaml', '.yml'}:
        return _load_config_from_yaml(path)

    elif ext == '.py':
        return _load_config_from_py(path)

    else:
        raise InvalidFileError(f'Invalid config extension: {ext}')
