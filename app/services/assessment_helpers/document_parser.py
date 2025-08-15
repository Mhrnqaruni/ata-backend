# /app/services/assessment_helpers/document_parser.py (FINAL, WITH ID GENERATION FIX)

import io
import json
import asyncio
import uuid # <-- Import the uuid library
from typing import Dict, Optional
from fastapi import UploadFile
import fitz
from PIL import Image

from ...models.assessment_model import AssessmentConfigV2
from .. import ocr_service, gemini_service, prompt_library

async def _process_file(file: Optional[UploadFile]) -> (str, list):
    """Helper function to read, OCR, and convert a single uploaded file."""
    # ... (This helper function is correct and remains unchanged)
    if not file or not file.filename: return "", []
    file_bytes = await file.read()
    content_type = file.content_type
    raw_text = await asyncio.to_thread(ocr_service.extract_text_from_file, file_bytes, content_type)
    image_list = []
    if content_type and 'pdf' in content_type:
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        for page in pdf_document:
            pix = page.get_pixmap(dpi=150); img_bytes = pix.tobytes("png"); image = Image.open(io.BytesIO(img_bytes)); image_list.append(image)
    elif content_type and 'image' in content_type:
        image = Image.open(io.BytesIO(file_bytes)); image_list.append(image)
    return raw_text, image_list

async def parse_document_to_config(
    question_file: UploadFile,
    answer_key_file: Optional[UploadFile],
    class_id: str,
    assessment_name: str
) -> Dict:
    """
    The core specialist for the V2 workflow, now refactored to handle two separate files.
    """
    question_task = _process_file(question_file)
    answer_key_task = _process_file(answer_key_file)
    (question_text, question_images), (answer_key_text, answer_key_images) = await asyncio.gather(question_task, answer_key_task)

    if not question_text or not question_text.strip():
        raise ValueError("The primary Question Document could not be read or is empty.")

    prompt = prompt_library.DOCUMENT_PARSING_PROMPT.format(
        question_document_text=question_text,
        answer_key_document_text=answer_key_text if answer_key_text else "Not provided."
    )
    
    combined_images = question_images + answer_key_images
    
    if combined_images:
        ai_response_str = await gemini_service.generate_multimodal_response(prompt, combined_images)
    else:
        ai_response_str = await gemini_service.generate_text(prompt, temperature=0.1)

    try:
        start_index = ai_response_str.find('{'); end_index = ai_response_str.rfind('}') + 1
        if start_index == -1 or end_index == 0:
            raise json.JSONDecodeError("No JSON object found in AI response.", ai_response_str, 0)
        parsed_json = json.loads(ai_response_str[start_index:end_index])
    except json.JSONDecodeError:
        print(f"Failed to parse AI response for document structuring: {ai_response_str}")
        raise ValueError("The AI was unable to structure the provided document. Please try a different file or format.")

    try:
        # --- [THE FIX IS HERE] ---
        # We now take control of ID generation, making our system more robust.
        # We will iterate through the AI's output and assign our own guaranteed-unique IDs.
        
        if 'sections' in parsed_json and isinstance(parsed_json['sections'], list):
            for section in parsed_json['sections']:
                # Assign a unique ID to the section
                section['id'] = f"sec_{uuid.uuid4().hex[:8]}"
                if 'questions' in section and isinstance(section['questions'], list):
                    for question in section['questions']:
                        # Assign a unique ID to each question, overwriting whatever the AI provided.
                        question['id'] = f"q_{uuid.uuid4().hex[:8]}"
        # --- [END OF FIX] ---

        parsed_json['assessmentName'] = assessment_name
        parsed_json['classId'] = class_id
        
        validated_config = AssessmentConfigV2(**parsed_json)
        
        return validated_config.model_dump()
    except Exception as e:
        print(f"Pydantic validation failed for AI-parsed config: {e}")
        raise ValueError(f"The AI structured the document in an unexpected way. Please check the document's formatting. Details: {e}")