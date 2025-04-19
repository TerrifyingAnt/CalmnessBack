from sqlalchemy import Column, BigInteger, String, ForeignKey, Integer, Boolean, Float, Text, DateTime
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
    user_states = relationship("UserState", back_populates="user")
    patient_groups = relationship("PatientGroup", back_populates="psychologist")
    done_tests = relationship("DoneTest", back_populates="user")
    user_in_chats = relationship("UserInChat", back_populates="user")

class UserState(Base):
    __tablename__ = "user_state"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("user_table.id"), nullable=False)
    emotion_state = Column(Float, nullable=False)
    physical_state = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    date = Column(DateTime, nullable=False)
    reasons = Column(String, nullable=False)
    solution = Column(String, nullable=False)

    user = relationship("User", back_populates="user_states")

class Chat(Base):
    __tablename__ = "chat_table"

    id = Column(BigInteger, primary_key=True)
    name = Column(BigInteger, nullable=False)
    last_message_id = Column(BigInteger, nullable=False)
    creation_date = Column(BigInteger, nullable=False)
    message_status = Column(BigInteger, nullable=False)

    messages = relationship("Message", back_populates="chat")
    users_in_chat = relationship("UserInChat", back_populates="chat")

class UserInChat(Base):
    __tablename__ = "user_in_chat_table"

    id = Column(BigInteger, primary_key=True)
    chat_id = Column(BigInteger, ForeignKey("chat_table.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("user_table.id"), nullable=False)

    chat = relationship("Chat", back_populates="users_in_chat")
    user = relationship("User", back_populates="user_in_chats")

class Message(Base):
    __tablename__ = "message_table"

    id = Column(BigInteger, primary_key=True)
    from_user_id = Column(BigInteger, ForeignKey("user_table.id"), nullable=False)
    status = Column(Boolean, nullable=False)
    date = Column(DateTime, nullable=False)
    media = Column(String, nullable=True)
    chat_id = Column(BigInteger, ForeignKey("chat_table.id"), nullable=False)
    text = Column(String, nullable=False)

    chat = relationship("Chat", back_populates="messages")

class Test(Base):
    __tablename__ = "test_table"

    id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    question_amount = Column(BigInteger, nullable=False)

    done_tests = relationship("DoneTest", back_populates="test")

class DoneTest(Base):
    __tablename__ = "done_test_table"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("user_table.id"), nullable=False)
    test_id = Column(BigInteger, ForeignKey("test_table.id"), nullable=False)

    user = relationship("User", back_populates="done_tests")
    test = relationship("Test", back_populates="done_tests")

class Patient(Base):
    __tablename__ = "patient_table"

    id = Column(BigInteger, primary_key=True)
    group_id = Column(BigInteger, ForeignKey("patient_group_table.id"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("user_table.id"), nullable=False)

    patient_group = relationship("PatientGroup", back_populates="patients")
    user = relationship("User")

class PatientGroup(Base):
    __tablename__ = "patient_group_table"

    id = Column(BigInteger, primary_key=True)
    group_type_id = Column(BigInteger, ForeignKey("group_type_table.id"), nullable=False)
    psychologist_id = Column(BigInteger, ForeignKey("user_table.id"), nullable=False)

    patients = relationship("Patient", back_populates="patient_group")
    psychologist = relationship("User", back_populates="patient_groups")
    group_type = relationship("GroupType", back_populates="patient_groups")

class GroupType(Base):
    __tablename__ = "group_type_table"

    id = Column(BigInteger, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)

    patient_groups = relationship("PatientGroup", back_populates="group_type")