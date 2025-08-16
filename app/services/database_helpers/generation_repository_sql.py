# /ata-backend/app/services/database_helpers/generation_repository_sql.py (FINAL, WITH DELETE METHOD)

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.db.models.generation_models import Generation

class GenerationRepositorySQL:
    def __init__(self, db_session: Session):
        self.db = db_session

    def add_generation_record(self, record: Dict):
        """Creates a new Generation record in the database from a dictionary."""
        new_generation = Generation(**record)
        self.db.add(new_generation)
        self.db.commit()
        self.db.refresh(new_generation)
        return new_generation

    def get_all_generations(self) -> List[Generation]:
        """Retrieves all generation records, ordered by most recent first."""
        return self.db.query(Generation).order_by(Generation.created_at.desc()).all()

    # --- [THIS IS THE NEWLY ADDED METHOD] ---
    def delete_generation_record(self, generation_id: str) -> bool:
        """Deletes a single generation record by its ID."""
        record = self.db.query(Generation).filter(Generation.id == generation_id).first()
        if record:
            self.db.delete(record)
            self.db.commit()
            return True
        return False
    # --- [END OF NEW METHOD] ---