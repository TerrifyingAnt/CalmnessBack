from sqlalchemy import Column, BigInteger, String, ForeignKey
from sqlalchemy.orm import relationship

from core.database import Base

class UserType(Base):
    __tablename__ = "user_type"
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=False)
    
    users = relationship("User", back_populates="user_type")

class User(Base):
    __tablename__ = "user_table"
    
    id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    patronymic = Column(String, nullable=False)
    age = Column(BigInteger, nullable=False)
    description = Column(String, nullable=True)
    avatar_path = Column(String, nullable=True)
    login = Column(String, nullable=False)
    password = Column(String, nullable=False)
    type_id = Column(BigInteger, ForeignKey("user_type.id"), nullable=False)
    
    user_type = relationship("UserType", back_populates="users")
    user_in_chats = relationship("UserInChat", back_populates="user")
    messages = relationship("Message", back_populates="from_user")