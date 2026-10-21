"""AppUser routes."""
from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_app_user_service
from app.schemas.app_user import AppUserCreate, AppUserRead, AppUserUpdate
from app.services.app_user_service import AppUserService

router = APIRouter(prefix="/app-users", tags=["app-users"])


@router.post("", response_model=AppUserRead, status_code=201)
async def create_app_user(
    user_in: AppUserCreate,
    service: AppUserService = Depends(get_app_user_service),
):
    return await service.create(user_in)


@router.get("", response_model=Sequence[AppUserRead])
async def list_app_users(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: AppUserService = Depends(get_app_user_service),
):
    return await service.get_all(limit=limit, offset=offset)


@router.get("/{user_id}", response_model=AppUserRead)
async def get_app_user(
    user_id: int,
    service: AppUserService = Depends(get_app_user_service),
):
    user = await service.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="AppUser not found")
    return user


@router.get("/email/{email}", response_model=AppUserRead | None)
async def get_app_user_by_email(
    email: str,
    service: AppUserService = Depends(get_app_user_service),
):
    user = await service.get_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="AppUser not found")
    return user


@router.patch("/{user_id}", response_model=AppUserRead)
async def update_app_user(
    user_id: int,
    user_in: AppUserUpdate,
    service: AppUserService = Depends(get_app_user_service),
):
    user = await service.update(user_id, user_in)
    if not user:
        raise HTTPException(status_code=404, detail="AppUser not found")
    return user


@router.delete("/{user_id}", status_code=204)
async def delete_app_user(
    user_id: int,
    service: AppUserService = Depends(get_app_user_service),
):
    deleted = await service.delete(user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="AppUser not found")


@router.get("/role/{role_code}", response_model=Sequence[AppUserRead])
async def get_app_users_by_role(
    role_code: int,
    service: AppUserService = Depends(get_app_user_service),
):
    return await service.get_by_role(role_code)


@router.get("/{user_id}/handled-alerts", response_model=Sequence[AppUserRead])
async def get_app_user_handled_alerts(
    user_id: int,
    service: AppUserService = Depends(get_app_user_service),
):
    return await service.get_handled_alerts(user_id)
