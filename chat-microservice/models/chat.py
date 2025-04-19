from sqlalchemy import Column, BigInteger, ForeignKey
from sqlalchemy.orm import relationship

from core.database import Base

class Chat(Base):
    __tablename__ = "chat_table"
    
    id = Column(BigInteger, primary_key=True)
    name = Column(BigInteger, nullable=False)
    last_message_id = Column(BigInteger, nullable=False)
    creation_date = Column(BigInteger, nullable=False)
    message_status = Column(BigInteger, nullable=False)
    
    messages = relationship("Message", back_populates="chat")
    users_in_chat = relationship("UserInChat", back_populates="chat")