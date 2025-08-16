# /ata-backend/app/db/models/generation_models.py

from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.sql import func
from ..base_class import Base

class Generation(Base):
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    tool_id = Column(String, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    settings_snapshot = Column(JSON, nullable=False)
    generated_content = Column(String, nullable=False)