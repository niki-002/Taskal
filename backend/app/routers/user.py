# APIのURL定義
from fastapi import APIRouter

from app.schemas.user import UserResponse, UserUpdate
from app.services.auth import CurrentUserDep
from app.services.user import UserServiceDep


router = APIRouter(prefix="/users")


@router.get(
    "/me",
    status_code=200,
    response_model=UserResponse
)
def get_me(
    service: UserServiceDep,
    current_user: CurrentUserDep
):
    return service.get_me(current_user)


@router.patch(
    "/me",
    status_code=200,
    response_model=UserResponse
)
def update_me(
    new_data: UserUpdate,
    service: UserServiceDep,
    current_user: CurrentUserDep
):
    return service.update_me(
        new_data,
        current_user
    )
