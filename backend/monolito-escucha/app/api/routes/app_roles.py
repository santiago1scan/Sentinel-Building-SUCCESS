"""AppRole routes."""
from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_app_role_service
from app.schemas.app_role import AppRoleCreate, AppRoleRead, AppRoleUpdate
from app.services.app_role_service import AppRoleService

router = APIRouter(prefix="/app-roles", tags=["app-roles"])


@router.post("", response_model=AppRoleRead, status_code=201)
async def create_app_role(
    role_in: AppRoleCreate,
    service: AppRoleService = Depends(get_app_role_service),
):
    return await service.create(role_in)


@router.get("", response_model=Sequence[AppRoleRead])
async def list_app_roles(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: AppRoleService = Depends(get_app_role_service),
):
    return await service.get_all(limit=limit, offset=offset)


@router.get("/{role_code}", response_model=AppRoleRead)
async def get_app_role(
    role_code: int,
    service: AppRoleService = Depends(get_app_role_service),
):
    role = await service.get(role_code)
    if not role:
        raise HTTPException(status_code=404, detail="AppRole not found")
    return role


@router.get("/code/{role_code}", response_model=AppRoleRead | None)
async def get_app_role_by_code(
    role_code: int,
    service: AppRoleService = Depends(get_app_role_service),
):
    role = await service.get_by_code(role_code)
    if not role:
        raise HTTPException(status_code=404, detail="AppRole not found")
    return role


@router.patch("/{role_code}", response_model=AppRoleRead)
async def update_app_role(
    role_code: int,
    role_in: AppRoleUpdate,
    service: AppRoleService = Depends(get_app_role_service),
):
    role = await service.update(role_code, role_in)
    if not role:
        raise HTTPException(status_code=404, detail="AppRole not found")
    return role


@router.delete("/{role_code}", status_code=204)
async def delete_app_role(
    role_code: int,
    service: AppRoleService = Depends(get_app_role_service),
):
    deleted = await service.delete(role_code)
    if not deleted:
        raise HTTPException(status_code=404, detail="AppRole not found")


@router.get("/{role_code}/users", response_model=Sequence[AppRoleRead])
async def get_app_role_users(
    role_code: int,
    service: AppRoleService = Depends(get_app_role_service),
):
    return await service.get_users(role_code)
