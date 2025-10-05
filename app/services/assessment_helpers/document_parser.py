# /app/services/assessment_helpers/document_parser.py (HYBRID: Vision for PDF/Images, OCR for DOCX)

import json
import uuid
import io
from typing import Dict, Optional
from fastapi import UploadFile
import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from ...models.assessment_model import AssessmentConfigV2
from .. import gemini_service, prompt_library, ocr_service

async def parse_document_to_config(
    question_file: UploadFile,
    answer_key_file: Optional[UploadFile],
    class_id: str,
    assessment_name: str
) -> Dict:
    """
    Hybrid document parser:
    - For PDF/Images: Uses AI vision directly for better accuracy
    - For DOCX: Uses OCR text extraction + AI (vision API doesn't support DOCX)
    """
    # Read question file
    question_bytes = await question_file.read()
    question_content_type = question_file.content_type

    if not question_bytes:
        raise ValueError("The Question Document is empty.")

    # Read answer key file if provided
    answer_key_bytes = None
    answer_key_content_type = None
    if answer_key_file and answer_key_file.filename:
        answer_key_bytes = await answer_key_file.read()
        answer_key_content_type = answer_key_file.content_type

    # Check if files are DOCX (vision doesn't support DOCX)
    is_question_docx = 'wordprocessing' in (question_content_type or '') or question_file.filename.endswith('.docx')
    is_answer_key_docx = answer_key_bytes and ('wordprocessing' in (answer_key_content_type or '') or (answer_key_file and answer_key_file.filename.endswith('.docx')))

    # Use appropriate prompt based on file type
    if is_question_docx or is_answer_key_docx:
        # DOCX files - use OCR + text-based AI prompt
        prompt = prompt_library.DOCUMENT_PARSING_PROMPT
    else:
        # PDF/Image files - use vision-optimized prompt
        prompt = prompt_library.VISION_DOCUMENT_PARSING_PROMPT

    try:
        total_tokens_used = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}

        # Handle DOCX files with OCR + text-based AI
        if is_question_docx or is_answer_key_docx:
            # Extract text from DOCX files
            question_text = ocr_service.extract_text_from_file(question_bytes, question_content_type)
            answer_key_text = ""
            if answer_key_bytes:
                answer_key_text = ocr_service.extract_text_from_file(answer_key_bytes, answer_key_content_type)

            # Combine texts and send to AI with text-based prompt
            combined_text = f"QUESTION DOCUMENT:\n{question_text}\n\n"
            if answer_key_text:
                combined_text += f"ANSWER KEY DOCUMENT:\n{answer_key_text}"

            full_prompt = prompt.format(raw_document_text=combined_text)

            # Use generate_json for text-based parsing
            result = await gemini_service.generate_json(full_prompt, temperature=0.1)
            parsed_json = result  # generate_json returns the JSON directly, not wrapped

            # Log token usage for DOCX parsing (note: generate_json may not return tokens, use estimate)
            print(f"[TOKEN-USAGE] PARSE-DOCUMENT (DOCX - Text-based) - File processed successfully")

        # Handle PDF/Image files with Vision API
        elif answer_key_bytes:
            # Upload both files using temporary files
            import tempfile
            import os
            question_temp_path = None
            answer_key_temp_path = None

            try:
                # Create temporary files for both documents
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf' if 'pdf' in question_content_type else '.png') as temp_file:
                    temp_file.write(question_bytes)
                    question_temp_path = temp_file.name

                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf' if 'pdf' in answer_key_content_type else '.png') as temp_file:
                    temp_file.write(answer_key_bytes)
                    answer_key_temp_path = temp_file.name

                # Upload both files to Gemini
                question_upload = genai.upload_file(
                    path=question_temp_path,
                    display_name="question_doc",
                    mime_type=question_content_type
                )

                answer_key_upload = genai.upload_file(
                    path=answer_key_temp_path,
                    display_name="answer_key_doc",
                    mime_type=answer_key_content_type
                )

                # Send both files to the model with JSON mode
                model = genai.GenerativeModel(gemini_service.GEMINI_FLASH_MODEL)
                config = GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json"
                )

                response = await model.generate_content_async(
                    [prompt, question_upload, answer_key_upload],
                    generation_config=config
                )

                parsed_json = json.loads(response.text)

                # Track token usage for dual file parsing
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    total_tokens_used['prompt_tokens'] = getattr(response.usage_metadata, 'prompt_token_count', 0)
                    total_tokens_used['completion_tokens'] = getattr(response.usage_metadata, 'candidates_token_count', 0)
                    total_tokens_used['total_tokens'] = getattr(response.usage_metadata, 'total_token_count', 0)
                    print(f"[TOKEN-USAGE] PARSE-DOCUMENT (Question + Answer Key) - Prompt: {total_tokens_used['prompt_tokens']}, Completion: {total_tokens_used['completion_tokens']}, Total: {total_tokens_used['total_tokens']}")

            finally:
                # Clean up temporary files
                if question_temp_path and os.path.exists(question_temp_path):
                    try:
                        os.unlink(question_temp_path)
                    except Exception:
                        pass
                if answer_key_temp_path and os.path.exists(answer_key_temp_path):
                    try:
                        os.unlink(answer_key_temp_path)
                    except Exception:
                        pass

        else:
            # Only question file - use single file vision processing
            result = await gemini_service.process_file_with_vision_json(
                file_bytes=question_bytes,
                mime_type=question_content_type,
                prompt=prompt,
                temperature=0.1,
                log_context="PARSE-DOCUMENT (Question Only)"
            )
            parsed_json = result['data']
            total_tokens_used = result['tokens']

    except json.JSONDecodeError as e:
        print(f"Failed to parse AI vision response: {e}")
        raise ValueError("The AI was unable to structure the provided document. Please try a different file or format.")
    except Exception as e:
        print(f"Error in vision-based document parsing: {e}")
        raise ValueError(f"Error processing document with AI vision: {e}")

    try:
        # Generate unique IDs for sections and questions
        if 'sections' in parsed_json and isinstance(parsed_json['sections'], list):
            for section in parsed_json['sections']:
                # Defensive: Ensure section title is never null
                if section.get('title') is None or section.get('title') == '':
                    section['title'] = 'Main Section'
                    print(f"[WARNING] AI returned null/empty section title, using 'Main Section' as fallback")

                # Assign a unique ID to the section
                section['id'] = f"sec_{uuid.uuid4().hex[:8]}"
                if 'questions' in section and isinstance(section['questions'], list):
                    for question in section['questions']:
                        # Assign a unique ID to each question
                        question['id'] = f"q_{uuid.uuid4().hex[:8]}"

        # Add assessment metadata
        parsed_json['assessmentName'] = assessment_name
        parsed_json['classId'] = class_id

        # Validate with Pydantic
        validated_config = AssessmentConfigV2(**parsed_json)

        return validated_config.model_dump()

    except Exception as e:
        print(f"Pydantic validation failed for AI-parsed config: {e}")
        raise ValueError(f"The AI structured the document in an unexpected way. Please check the document's formatting. Details: {e}")
