from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from models.user import User
from schemas.user import UserOut, UserCreate, UserUpdate
from core.database import get_db
from services.user import UserService
from typing import List

router = APIRouter()

@router.get("/", response_model=List[UserOut])
async def read_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    return await UserService.get_users(db, skip, limit)

@router.get("/{user_id}", response_model=UserOut)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/", response_model=UserOut)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    return await UserService.create_user(db, user)

@router.put("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, user_update: UserUpdate, db: AsyncSession = Depends(get_db)):
    user = await UserService.update_user(db, user_id, user_update)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/{user_id}", response_model=bool)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    success = await UserService.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return True