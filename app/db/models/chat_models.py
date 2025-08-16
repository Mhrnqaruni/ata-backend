# /ata-backend/app/db/models/chat_models.py

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..base_class import Base

class ChatSession(Base):
    __tablename__ = "chatsessions" # Override automatic pluralization
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False) # V2 TODO: Add ForeignKey to a User table
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to Messages
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chatmessages" # Override automatic pluralization
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chatsessions.id"), nullable=False)
    role = Column(String, nullable=False) # 'user' or 'assistant'
    content = Column(String, nullable=False)
    file_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship to Session
    session = relationship("ChatSession", back_populates="messages")