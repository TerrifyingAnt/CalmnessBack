from sqlalchemy import Column, BigInteger, ForeignKey
from sqlalchemy.orm import relationship

from core.database import Base

class UserInChat(Base):
    __tablename__ = "user_in_chat_table"
    
    id = Column(BigInteger, primary_key=True)
    chat_id = Column(BigInteger, ForeignKey("chat_table.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("user_table.id"), nullable=False)
    
    chat = relationship("Chat", back_populates="users_in_chat")
    user = relationship("User", back_populates="user_in_chats")