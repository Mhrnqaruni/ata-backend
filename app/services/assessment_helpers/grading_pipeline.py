# /app/services/assessment_helpers/grading_pipeline.py

import io
import json
from typing import List, Dict, Optional
import fitz  # PyMuPDF
from PIL import Image

from ..database_service import DatabaseService
from .. import gemini_service

def _safe_float_convert(value) -> Optional[float]:
    """A helper to safely convert grade values to float, returning None if invalid."""
    if value is None or str(value).strip() == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

def _prepare_images_from_answersheet(answer_sheet_path: str, content_type: str) -> List[Image.Image]:
    """
    Specialist for file ingestion.
    Reads a file from disk and converts it into a list of PIL Images, handling PDF conversion.
    """
    with open(answer_sheet_path, "rb") as f:
        file_bytes = f.read()

    image_list = []
    if content_type and 'pdf' in content_type:
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        for page in pdf_document:
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_bytes))
            image_list.append(image)
    else:
        image = Image.open(io.BytesIO(file_bytes))
        image_list.append(image)

    if not image_list:
        raise ValueError(f"Could not extract any images from the file: {answer_sheet_path}")
    
    return image_list

async def _invoke_grading_ai(prompt: str, images: List[Image.Image]) -> str:
    """
    Specialist for AI interaction.
    Calls the gemini_service to get the AI's grading response.
    """
    return await gemini_service.generate_multimodal_response(prompt, images)

def _parse_ai_grading_response(ai_response_str: str) -> Dict:
    """
    Specialist for response parsing.
    Defensively finds and parses the JSON object from the AI's raw string response.
    """
    start_index = ai_response_str.find('{')
    end_index = ai_response_str.rfind('}') + 1
    if start_index == -1 or end_index == 0:
        raise json.JSONDecodeError("No JSON object found in AI response", ai_response_str, 0)
    
    return json.loads(ai_response_str[start_index:end_index])

def _save_grading_results_to_db(db: DatabaseService, job_id: str, student_id: str, parsed_results: Dict):
    """
    Specialist for persistence.
    Loops through the parsed AI results, cleans the data, and saves it to the database.
    """
    for result in parsed_results['results']:
        clean_grade = _safe_float_convert(result.get('grade'))
        clean_feedback = result.get('feedback', 'No feedback provided.')
        
        db.update_student_result_with_grade(
            job_id=job_id,
            student_id=student_id,
            question_id=result['question_id'],
            grade=clean_grade,
            feedback=clean_feedback,
            status="ai_graded"
        )