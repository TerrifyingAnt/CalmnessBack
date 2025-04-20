from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List, Optional
from fastapi import HTTPException

from models.user import User
from schemas.user import UserCreate, UserUpdate

from models.user import PatientGroup

from models.user import Patient, UserInChat, DoneTest, UserState, Message, UserInChat


class UserService:
    @staticmethod
    async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
        result = await db.execute(select(User).filter(User.id == user_id))
        return result.scalars().first()

    @staticmethod
    async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
        result = await db.execute(select(User).offset(skip).limit(limit))
        return result.scalars().all()

    @staticmethod
    async def create_user(db: AsyncSession, user: UserCreate) -> User:
        result = await db.execute(select(User).where(User.login == user.login))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")

        new_user = User(**user.dict())
        db.add(new_user)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(status_code=400, detail="Не удалось создать пользователя (возможно, логин занят)")
        return new_user

    @staticmethod
    async def update_user(db: AsyncSession, user_id: int, user_update: UserUpdate) -> Optional[User]:
        user = await UserService.get_user(db, user_id)
        if not user:
            return None

        update_data = user_update.dict(exclude_unset=True)

        await db.execute(
            update(User).where(User.id == user_id).values(**update_data)
        )
        await db.commit()
        return await UserService.get_user(db, user_id)

    @staticmethod
    async def delete_user(db: AsyncSession, user_id: int) -> bool:
        user = await UserService.get_user(db, user_id)
        if not user:
            return False

        # Удаление всех зависимых записей из patient_table
        await db.execute(delete(Patient).where(Patient.user_id == user_id))

        # Удаление всех зависимых записей из patient_group_table
        # Сначала находим все группы, в которых пользователь является психологом
        patient_groups = await db.execute(select(PatientGroup).where(PatientGroup.psychologist_id == user_id))
        patient_groups = patient_groups.scalars().all()

        # Удаляем всех пациентов из этих групп
        for group in patient_groups:
            await db.execute(delete(Patient).where(Patient.group_id == group.id))

        # Теперь удаляем сами группы
        await db.execute(delete(PatientGroup).where(PatientGroup.psychologist_id == user_id))

        # Удаление всех зависимых записей из user_in_chat_table
        await db.execute(delete(UserInChat).where(UserInChat.user_id == user_id))

        # Удаление всех зависимых записей из done_test_table
        await db.execute(delete(DoneTest).where(DoneTest.user_id == user_id))

        # Удаление всех зависимых записей из user_state
        await db.execute(delete(UserState).where(UserState.user_id == user_id))

        # Удаление всех зависимых записей из message_table
        await db.execute(delete(Message).where(Message.from_user_id == user_id))

        # Теперь удаляем самого пользователя
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()

        return True