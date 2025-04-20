from pydantic import BaseModel
from typing import Optional


class UserBase(BaseModel):
    name: str
    surname: str
    patronymic: str
    age: int
    description: Optional[str] = None
    avatar_path: Optional[str] = None
    login: str
    password: str
    type_id: int


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    name: Optional[str] = None
    surname: Optional[str] = None
    patronymic: Optional[str] = None
    age: Optional[int] = None
    description: Optional[str] = None
    avatar_path: Optional[str] = None
    password: Optional[str] = None
    type_id: Optional[int] = None


class UserOut(UserBase):
    id: int

    class Config:
        orm_mode = True
