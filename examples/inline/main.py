from uuid import UUID, uuid4
from warnings import deprecated

from pydantic import BaseModel, Field

from tatami import Tatami, delete, get, post, put, router, run


# Define some models
class User(BaseModel):
    name: str = Field(description='The user name', examples=['Alice', 'Bob'])
    age: int = Field(description='Age', examples=[23, 42])

# Define a dummy CRUD service to manage users
class UserService:
    def __init__(self):
        self.users = {}

    def add(self, user: User) -> UUID:
        new_user_id = uuid4()
        self.users[new_user_id] = user
        return new_user_id

    def get(self, user_id: UUID) -> User:
        return self.users[user_id]

    def all(self) -> list[User]:
        return [{
            'id': user_id,
            'user': user,
        } for user_id, user in self.users.items()]
    
    def delete(self, user_id: UUID) -> None:
        del self.users[user_id]

    def update(self, user_id: UUID, user: User) -> None:
        if user_id not in self.users:
            raise ValueError('The user does not exist')
        self.users[user_id] = user

class Users(router('/users')):
    """User management endpoints"""
    def __init__(self, users: UserService):
        self.users = users
        super().__init__()

    @get('/all')
    @deprecated('This endpoint is deprecated, use "GET /users" instead')
    def get_users_old(self):
        return self.users.all()

    @get('/')
    def get_users(self):
        return self.users.all()

    @post('/')
    def add_user(self, user: User):
        """Add a new user"""
        user_id = self.users.add(user)
        return {'id': user_id}

    @get('/{user_id}')
    def get_user_by_id(self, user_id: UUID):
        """Get a user"""
        return self.users.get(user_id)

    @put('/{user_id}')
    def update_user(self, user_id: UUID, user: User):
        """Replace a user with another one"""
        self.users.update(user_id, user)
        return {'msg': f"Updated user {user_id} with {user}"}

    @delete('/{user_id}')
    def delete_user(self, user_id: UUID):
        """Delete a user"""
        self.users.delete(user_id)
        return {'msg': f"Deleted user {user_id}"}

    
class Cars(router('/cars')):
    """Manage cars"""
    @get('/')
    def get_cars(self):
        return []


# This is all automatically done when using the `tatami run` command
user_service = UserService()
users = Users(user_service)
cars = Cars()

app = Tatami(title='Car rental API', description='API example for a car rental company')
app.include_router(users)
app.include_router(cars)

# Uncomment to run
run(app, host="127.0.0.1", port=8000)
