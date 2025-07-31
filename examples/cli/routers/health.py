import random
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field
from starlette.requests import Request
from tatami import get, post, router
from tatami.di import Inject, Scope
from tatami.param import Query

from cli.models.user import User
from tatami.param import Header
from cli.services import UserService


def get_start(some_header: Annotated[str, Header('x-some-header')]) -> str:
    return f'This is the auth with number {random.randint(0, 100)} and header {some_header}'

def get_auth(request: Request, start: Annotated[str, Inject(factory=get_start, scope=Scope.REQUEST)], user_agent: Annotated[str, Header()]):
    return f'{start}: {request.headers.get("user-agent")} (from request); {user_agent} (from headers)'


class Post(BaseModel):
    title: str = Field(description='The post title', examples=['Test post'])
    author: str = Field(description='Author name', examples=['John Doe'])
    body: str = Field(description='Post body', examples=['Lorem ipsum, dolor sit amet'])

class Health(router('/health')):
    @get
    def get_health(self):
        """Get app status"""
        return 'OK'
    
class PostRouter(router('/post')):
    @get('/{post_id}')
    def get_post(self, post_id: int, get_comments: Annotated[bool, Query('show_comments')] = False):
        result = {'content': 'lorem ipsum', 'id': post_id}
        if get_comments:
            result['comments'] = [
                {'comment_id': 'foo', 'author': 'bar'}
            ]
        return result
    
    @post
    def create_post(self, p: Post, auth: Annotated[str, Inject(factory=get_auth, scope=Scope.REQUEST)]):
        return {'success': True, 'post': p, 'auth': auth}
    
    @get('/error')
    def raise_exception(self):
        raise RuntimeError('This endpoint fails')


class UserRouter(router('/users')):
    def __init__(self, users: UserService):
        super().__init__()
        self.users = users

    @get
    def get_all(self):
        return self.users.all()
        
    @get('/{user_id}')
    def get_user(self, user_id: UUID) -> User:
        return self.users.get_user(user_id)
    
    @post('/{user_id}')
    def save_user(self, user_id: UUID, user: User) -> str:
        self.users.set_user(user_id, user)
        return 'ADDED'


class NonRouter:
    def get_nothing(self):
        return 'THIS IS NOT AN ENDPOINT'
    
    def get_non_router(self):
        return 'THIS SHOULD BE AN ENDPOINT'