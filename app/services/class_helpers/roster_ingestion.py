# /app/services/class_helpers/roster_ingestion.py (CORRECTED)

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
    """
    initial_class_data = class_model.ClassCreate(name=name, description=f"Roster uploaded from {file.filename}")
    # crud.create_class now returns a SQLAlchemy Class object
    new_class_object = crud.create_class(class_data=initial_class_data, db=db)
    
    students_to_create = []
    try:
        # ... (The entire middle section of this function is correct and remains unchanged) ...
        file_bytes = await file.read()
        content_type = file.content_type

        # Smart Ingestion Routing
        if content_type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.ms-excel"]:
            students_to_create = file_processors.extract_students_from_tabular(file_bytes, is_excel=True)
        elif content_type == "text/csv":
            students_to_create = file_processors.extract_students_from_tabular(file_bytes, is_excel=False)
        else:
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

            # AI Structuring Step
            ai_response_str = ""
            if image_bytes_for_ai:
                example_json = '{\n  "students": [\n    { "name": "Alice Johnson", "studentId": "S-1001" },\n    { "name": "Bob Williams", "studentId": "S-1002" }\n  ]\n}'
                prompt = prompt_library.MULTIMODAL_ROSTER_EXTRACTION_PROMPT.format(raw_ocr_text=raw_text, example_json=example_json)
                ai_response_str = await gemini_service.generate_multimodal_response(prompt, image_bytes_for_ai)
            else:
                prompt = prompt_library.ROSTER_EXTRACTION_PROMPT.format(raw_ocr_text=raw_text)
                ai_response_str = await gemini_service.generate_text(prompt, temperature=0.1)

            # Robust JSON Parsing
            parsed_response = None
            try:
                json_start, json_end = ai_response_str.find('{'), ai_response_str.rfind('}') + 1
                if json_start != -1 and json_end != 0:
                    parsed_response = json.loads(ai_response_str[json_start:json_end])
                else: 
                    raise ValueError("No JSON object found in the AI response.")
            except Exception:
                raise ValueError("The AI could not structure the data from the document.")
            
            students_to_create = parsed_response.get("students", [])

        # Save Students to Database
        if students_to_create:
            for student_data in students_to_create:
                if 'studentId' not in student_data or pd.isna(student_data.get('studentId')):
                    student_data['studentId'] = 'N/A'
                
                validated_student = student_model.StudentCreate(**student_data)
                crud.add_student_to_class(class_id=new_class_object.id, student_data=validated_student, db=db)

    except Exception as e:
        print(f"ERROR processing upload for class {new_class_object.id}: {e}")
        # Transactional Rollback
        db.delete_class(new_class_object.id)
        raise ValueError(str(e))
    
    # --- [THE FIX IS HERE] ---
    # We now construct the response dictionary using attribute access on the SQLAlchemy object.
    return {
        "message": "Upload successful. Roster created.",
        "class_info": {
            "id": new_class_object.id,
            "name": new_class_object.name,
            "description": new_class_object.description,
            "studentCount": len(students_to_create)
    }
}
    # --- [END OF FIX] ---