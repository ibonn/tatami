from datetime import date

import pytest
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

from tatami._utils import (HTMLResponse, camel_to_snake, get_request_type,
                           human_friendly_description_from_name,
                           import_from_path, is_path_param, path_to_module,
                           serialize_json, update_dict, with_new_base,
                           wrap_response)
from tatami.router import ConventionRouter


@pytest.fixture
def get_user_model():
    class User(BaseModel):
        name: str = Field(description='The users name')
        birth_date: date = Field(description='The users birth date')

    return User

@pytest.fixture
def get_dummy_endpoint(get_user_model):
    User = get_user_model
    def dummy_endpoint(user: User, user_id: int):
        return {'success': True, 'message': 'User updated'}
    return dummy_endpoint

@pytest.mark.skip('Make HTMLResponse read templates from user specified directory')
def test_HTMLResponse():
    pass

def test_camel_to_snake():
    assert camel_to_snake('ThisIsATest') == 'this_is_a_test'

def test_get_request_type(get_dummy_endpoint, get_user_model):
    assert get_request_type(get_dummy_endpoint) == {'user': get_user_model}

def test_human_friendly_description_from_name(get_dummy_endpoint):
    assert human_friendly_description_from_name(get_dummy_endpoint.__name__) == 'Dummy endpoint'

@pytest.mark.skip('Fix the test so it can read a python file')
def test_import_from_path():
    pass

def test_is_path_param(get_user_model):
    assert is_path_param(int)
    assert is_path_param(str)
    assert not is_path_param(get_user_model)
    assert not is_path_param(bool)
    assert not is_path_param(float)

def test_path_to_module():
    assert path_to_module('path/to/some/module.py') == 'path.to.some.module'

def test_serialize_json(get_user_model):
    assert serialize_json(get_user_model) == get_user_model.model_json_schema()

def test_update_dict():
    dict_a = {'a': 'b', 'c': {'d': 'foo'}}
    dict_b = {'a': 'x', 'c': {'e': 'bar'}}

    update_dict(dict_a, dict_b)

    assert dict_a == {'a': 'x', 'c': {'d': 'foo', 'e': 'bar'}}

def test_with_new_base():
    class X:
        pass

    assert not issubclass(X, ConventionRouter)

    X = with_new_base(X, ConventionRouter)

    assert issubclass(X, ConventionRouter)

def test_wrap_response(get_dummy_endpoint):
    result = get_dummy_endpoint(None, None)
    response = wrap_response(get_dummy_endpoint, result)
    assert isinstance(response, JSONResponse)