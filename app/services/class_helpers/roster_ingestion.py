# /app/services/class_helpers/roster_ingestion.py (FINAL, CORRECTED VERSION)

import json
import asyncio
import pandas as pd
from typing import Dict
from fastapi import UploadFile

from ...models import class_model, student_model
from ..database_service import DatabaseService
from .. import ocr_service, gemini_service, prompt_library

# Import from the new specialist modules
from . import file_processors
from . import crud

async def create_class_from_upload(name: str, file: UploadFile, db: DatabaseService) -> Dict:
    """
    Orchestrates the advanced AI pipeline for creating a class from a roster file.
    This version handles pre-existing students and provides an accurate count.
    """
    initial_class_data = class_model.ClassCreate(name=name, description=f"Roster uploaded from {file.filename}")
    new_class_object = crud.create_class(class_data=initial_class_data, db=db)
    
    students_to_process = []
    newly_created_student_count = 0
    
    try:
        file_bytes = await file.read()
        content_type = file.content_type

        # --- Smart Ingestion Routing (Unchanged) ---
        if content_type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
            students_to_process = file_processors.extract_students_from_tabular(file_bytes, is_excel=True)
        elif content_type == "text/csv":
            students_to_process = file_processors.extract_students_from_tabular(file_bytes, is_excel=False)
        else:
            # ... (The entire text/image/AI processing block is unchanged and correct) ...
            raw_text = ""
            image_bytes_for_ai = None
            if content_type in ["image/jpeg", "image/png", "application/pdf"]:
                raw_text = await asyncio.to_thread(ocr_service.extract_text_from_file, file_bytes, content_type)
                image_bytes_for_ai = await asyncio.to_thread(file_processors.convert_pdf_first_page_to_png_bytes, file_bytes) if content_type == "application/pdf" else file_bytes
            elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                raw_text = file_processors.extract_text_from_docx(file_bytes)
            else: 
                raise ValueError(f"Unsupported file type: {content_type}")

            if not raw_text or not raw_text.strip():
                raise ValueError("Could not extract any text from the document.")

            prompt = prompt_library.ROSTER_EXTRACTION_PROMPT.format(raw_ocr_text=raw_text)
            ai_response_str = await gemini_service.generate_text(prompt, temperature=0.1)

            try:
                json_start, json_end = ai_response_str.find('{'), ai_response_str.rfind('}') + 1
                parsed_response = json.loads(ai_response_str[json_start:json_end])
            except Exception:
                raise ValueError("The AI could not structure the data from the document.")
            
            students_to_process = parsed_response.get("students", [])

        # --- [THE FIX IS HERE: Save Students to Database with check] ---
        if students_to_process:
            for student_data in students_to_process:
                if 'studentId' not in student_data or pd.isna(student_data.get('studentId')):
                    student_data['studentId'] = 'N/A'
                
                # Skip students with invalid IDs
                if student_data['studentId'] == 'N/A':
                    print(f"WARNING: Skipping student with missing ID: {student_data.get('name')}")
                    continue

                validated_student = student_model.StudentCreate(**student_data)
                
                # The crud function now returns a tuple: (record, was_created_boolean)
                _ , was_created = crud.add_student_to_class_with_status(
                    class_id=new_class_object.id, 
                    student_data=validated_student, 
                    db=db
                )
                
                # Only increment the count if a new student was actually created
                if was_created:
                    newly_created_student_count += 1

    except Exception as e:
        print(f"ERROR processing upload for class {new_class_object.id}: {e}")
        # Transactional Rollback: If anything fails, delete the class we just made.
        db.delete_class(new_class_object.id)
        raise ValueError(str(e))
    
    # Construct the final response dictionary using the accurate count
    return {
        "message": "Upload successful. Roster processed.",
        "class_info": {
            "id": new_class_object.id,
            "name": new_class_object.name,
            "description": new_class_object.description,
            "studentCount": newly_created_student_count
        }
    }