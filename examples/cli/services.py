import random
import string
from typing import Annotated
from uuid import UUID

from cli.models.user import User

from tatami.di import Inject, Scope, injectable


def random_string(length: int = 5) -> str:
    return ''.join(random.choice(string.printable) for _ in range(length))

# This class gets injected with singleton scope, so the random_string function will only be called once even if it has a request scope
@injectable
class UserService:
    def __init__(self, prefix: Annotated[str, Inject(factory=random_string, scope=Scope.REQUEST)]):
        self.prefix = prefix

        # This should be a database
        self.users = {}

    def get_user(self, user_id: UUID) -> User:
        return self.users[user_id]
    
    def set_user(self, uuid: UUID, user: User) -> None:
        user.prefix = self.prefix
        self.users[uuid] = user

    def delete_user(self, uuid: UUID) -> None:
        del self.users[uuid]

    def all(self) -> dict[User]:
        return self.users