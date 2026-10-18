# ログイン中のユーザー自身の情報を扱う処理
from typing import Annotated

from fastapi import Depends
from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError
from app.models.auth import User
from app.repositories.user import UserRepository, UserRepositoryDep
from app.schemas.user import UserResponse, UserUpdate

USERNAME_ALREADY_EXISTS = "このユーザー名は既に使われています。"


class UserService:
    def __init__(self, repository: UserRepository):
        self.repository = repository

    def get_me(self, current_user: User) -> UserResponse:
        return UserResponse.model_validate(current_user)

    def update_me(
            self,
            new_data: UserUpdate,
            current_user: User
    ) -> UserResponse:
        if new_data.username == current_user.username:
            return self.get_me(current_user)

        if self.repository.get_by_username(new_data.username) is not None:
            raise self._username_conflict()

        current_user.username = new_data.username
        try:
            updated = self.repository.save(current_user)
        except IntegrityError:
            # 確認後に他のユーザーが同じ名前を登録した場合
            raise self._username_conflict()
        return self.get_me(updated)

    @staticmethod
    def _username_conflict() -> ConflictError:
        return ConflictError(
            USERNAME_ALREADY_EXISTS,
            details=[{"field": "username", "reason": "already_exists"}]
        )


def get_user_service(repository: UserRepositoryDep) -> UserService:
    return UserService(repository)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
