# /ata-backend/app/services/database_helpers/generation_repository_sql.py

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.db.models.generation_models import Generation

class GenerationRepositorySQL:
    def __init__(self, db_session: Session):
        self.db = db_session

    def add_generation_record(self, record: Dict):
        new_generation = Generation(**record)
        self.db.add(new_generation)
        self.db.commit()
        return new_generation

    def get_all_generations(self) -> List[Generation]:
        return self.db.query(Generation).order_by(Generation.created_at.desc()).all()