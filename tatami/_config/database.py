from dataclasses import dataclass
from typing import Optional, Union

@dataclass
class ConnectionString:
    dialect: str
    db_name: str
    driver: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None

    def __str__(self) -> str:
        if self.host is None and self.port is None:
            host_port = ''

        elif self.port is None:
            host_port = self.host

        else:
            host_port = f'{self.host}:{self.port}'

        conn_str = f'{host_port}/{self.db_name}'

        if self.driver is None:
            schema = self.dialect
        else:
            schema = f'{self.driver}+{self.dialect}'

        if self.username is None and self.password is None:
            user_and_pass = ''
        else:
            user_and_pass = f'{self.username}:{self.password}@'
        
        return f'{schema}://{user_and_pass}{conn_str}'


def db_from_none(_: None) -> None:
    return None

def db_from_bool(has_database: bool) -> Union[ConnectionString, None]:
    if has_database:
        # TODO use default database backend
        return ConnectionString(
            driver='psycopg',
            dialect='postgresql',
            username='postgres',
            password='postgres',
            host='localhost',
            port=5432,
            db_name='postgres'
        )

    # No database
    return None

def _db_from_db_type(db_type: str) -> Union[ConnectionString, None]:
    if db_type == '':
        return None
    
    if db_type in {'postgres', 'postgresql'}:
        return ConnectionString(
            driver='psycopg',
            dialect='postgresql',
            username='postgres',
            password='postgres',
            host='localhost',
            port=5432,
            db_name='postgres'
        )
    
    if db_type in {'sqlite'}:
        return ConnectionString(
            dialect='sqlite',
            db_name='local.db'
        )
    
    raise RuntimeError(f'{db_type} is not a valid database type')

def _db_from_conn_str(conn_str: str) -> Union[ConnectionString, None]:
    if conn_str == '':
        return None

    # TODO validate connection string?
    return conn_str

def db_from_str(conn_str_or_db_type: str) -> Union[ConnectionString, None]:
    db_type_candidate = conn_str_or_db_type.strip()

    if db_type_candidate in {'', 'postgres', 'postgresql', 'sqlite', 'mysql'}:
        return _db_from_db_type(db_type_candidate)
    
    return _db_from_conn_str(conn_str_or_db_type)

def db_from_dict(db_config: dict) -> Union[str, None]:
    if len(db_config) == 0:
        return None
    
    try:
        config = _db_from_db_type(db_config['dialect'])
    except KeyError as e:
        raise ValueError('You must at least specify the database dialect') from e
    
    config.driver = db_config.get('driver', config.driver) 
    config.username = db_config.get('username', config.username)
    config.password = db_config.get('password', config.password)
    config.db_name = db_config.get('name', config.db_name)
    config.host = db_config.get('host', config.host)
    config.port = db_config.get('port', config.port)

    return config

