from typing import Annotated

from pydantic import BaseModel, Field

from tatami import get, post, router
from uuid import UUID
from tatami.param import Query

from cli.services import UserService
from cli.models.user import User


class Post(BaseModel):
    title: str = Field(description='The post title', examples=['Test post'])
    author: str = Field(description='Author name', examples=['John Doe'])
    body: str = Field(description='Post body', examples=['Lorem ipsum, dolor sit amet'])

class Health(router('/health')):
    @get
    def get_health(self):
        """Get app status"""
        return 'OK'
    
class Post(router('/post')):
    @get('/{post_id}')
    def get_post(self, post_id: int, get_comments: Annotated[bool, Query('show_comments')] = False):
        result = {'content': 'lorem ipsum', 'id': post_id}
        if get_comments:
            result['comments'] = [
                {'comment_id': 'foo', 'author': 'bar'}
            ]
        return result
    
    @post
    def create_post(self, p: Post):
        return {'success': True, 'post': p}
    
    @get('/error')
    def raise_exception(self):
        raise RuntimeError('This endpoint fails')


class UserRouter(router('/users')):
    def __init__(self, users: UserService):
        super().__init__()
        self.users = users
        
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