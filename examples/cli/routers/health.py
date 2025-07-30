from typing import Annotated

from pydantic import BaseModel, Field

from tatami import get, post, router
from tatami.param import Query


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
    

class NonRouter:
    def get_nothing(self):
        return 'THIS IS NOT AN ENDPOINT'
    
    def get_non_router(self):
        return 'THIS SHOULD BE AN ENDPOINT'