# /ata-backend/app/services/database_helpers/chat_repository_sql.py

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.db.models.chat_models import ChatSession, ChatMessage

class ChatRepositorySQL:
    def __init__(self, db_session: Session):
        self.db = db_session

    # --- Chat Session Methods ---
    def create_session(self, record: Dict):
        new_session = ChatSession(**record)
        self.db.add(new_session)
        self.db.commit()
        return new_session

    def get_sessions_by_user_id(self, user_id: str) -> List[ChatSession]:
        return self.db.query(ChatSession).filter(ChatSession.user_id == user_id).order_by(ChatSession.created_at.desc()).all()

    def get_session_by_id(self, session_id: str) -> Optional[ChatSession]:
        return self.db.query(ChatSession).filter(ChatSession.id == session_id).first()

    def delete_session_by_id(self, session_id: str) -> bool:
        session = self.get_session_by_id(session_id)
        if session:
            self.db.delete(session)
            self.db.commit()
            return True
        return False

    # --- Chat Message Methods ---
    def add_message(self, record: Dict):
        new_message = ChatMessage(**record)
        self.db.add(new_message)
        self.db.commit()

    def get_messages_by_session_id(self, session_id: str) -> List[ChatMessage]:
        return self.db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()