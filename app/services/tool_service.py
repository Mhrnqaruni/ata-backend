# /app/services/tool_service.py

from typing import Dict, Any, Optional
from pydantic import ValidationError
from fastapi import UploadFile
import asyncio
import os

from ..models.tool_model import ToolId, QuestionGeneratorSettings, SlideGeneratorSettings, RubricGeneratorSettings
from ..services import gemini_service, history_service, prompt_library, ocr_service
from .database_service import DatabaseService

# --- Tool-Specific Logic Functions (All Unchanged) ---

async def _handle_question_generator(settings: Dict[str, Any]) -> str:
    try:
        validated_settings = QuestionGeneratorSettings(**settings)
    except ValidationError as e:
        raise ValueError(f"Invalid question settings provided. Details: {e}")
    if not validated_settings.source_text or len(validated_settings.source_text) < 20:
        raise ValueError("A valid source must be provided (Text, File, or Library Chapters) with sufficient content.")
    plan_lines = [f"- Generate {config.count} {config.difficulty.value} '{config.label}'." for config in validated_settings.question_configs]
    generation_plan_string = "\n".join(plan_lines)
    prompt = prompt_library.QUESTION_GENERATOR_PROMPT_V2.format(
        grade_level=validated_settings.grade_level,
        source_text=validated_settings.source_text,
        generation_plan_string=generation_plan_string
    )
    return await gemini_service.generate_text(prompt, temperature=0.7)


async def _handle_slide_generator(settings: Dict[str, Any]) -> str:
    try:
        validated_settings = SlideGeneratorSettings(**settings)
    except ValidationError as e:
        raise ValueError(f"Invalid slide settings provided. Details: {e}")
    if not validated_settings.source_text or len(validated_settings.source_text) < 10:
        raise ValueError("A valid source must be provided (Text, File, or Library Chapters) with sufficient content.")
    prompt = prompt_library.SLIDE_GENERATOR_PROMPT_V2.format(
        grade_level=validated_settings.grade_level,
        num_slides=validated_settings.num_slides,
        slide_style=validated_settings.slide_style.value,
        include_speaker_notes=validated_settings.include_speaker_notes,
        source_text=validated_settings.source_text
    )
    return await gemini_service.generate_text(prompt, temperature=0.6)


async def _handle_rubric_generator(settings: Dict[str, Any]) -> str:
    try:
        validated_settings = RubricGeneratorSettings(**settings)
    except ValidationError as e:
        raise ValueError(f"Invalid rubric settings provided. Details: {e}")
    assignment_context_text = validated_settings.assignment_text or ""
    rubric_guidance_text = validated_settings.guidance_text or "None provided."
    if not assignment_context_text:
         raise ValueError("An 'Assignment Context' must be provided from Text, a File, or the Library.")
    criteria_string = ", ".join(validated_settings.criteria)
    levels_string = ", ".join(validated_settings.levels)
    prompt = prompt_library.RUBRIC_GENERATOR_PROMPT_V2.format(
        grade_level=validated_settings.grade_level,
        criteria_string=criteria_string,
        levels_string=levels_string,
        assignment_context_text=assignment_context_text,
        rubric_guidance_text=rubric_guidance_text
    )
    return await gemini_service.generate_text(prompt, temperature=0.5)


# --- Tool Handler Dispatcher (Unchanged) ---
TOOL_HANDLERS = {
    ToolId.QUESTION_GENERATOR: _handle_question_generator,
    ToolId.SLIDE_GENERATOR: _handle_slide_generator,
    ToolId.RUBRIC_GENERATOR: _handle_rubric_generator,
}


# --- Main Orchestration Function (UPGRADED) ---
async def generate_content_for_tool(
    settings_payload: Dict[str, Any],
    source_file: Optional[UploadFile],
    db: DatabaseService
) -> Dict[str, Any]:
    
    # This entire section is unchanged and correct
    tool_id_str = settings_payload.get("tool_id")
    settings_dict = settings_payload.get("settings")
    if not tool_id_str or settings_dict is None:
        raise ValueError("Payload must include 'tool_id' and 'settings'.")

    if source_file:
        if ("source_text" in settings_dict and settings_dict["source_text"]) or \
           ("selected_chapter_paths" in settings_dict and settings_dict["selected_chapter_paths"]):
             raise ValueError("Cannot provide a source file simultaneously with source text or library chapters.")
        file_bytes = await source_file.read()
        extracted_text = await asyncio.to_thread(
            ocr_service.extract_text_from_file, file_bytes, source_file.content_type
        )
        if not extracted_text:
            raise ValueError("Could not extract any readable text from the uploaded file.")
        settings_dict["source_text"] = extracted_text
    elif "selected_chapter_paths" in settings_dict and settings_dict["selected_chapter_paths"]:
        if "source_text" in settings_dict and settings_dict["source_text"]:
            raise ValueError("Cannot provide source text simultaneously with library chapters.")
        combined_text = []
        for path_str in settings_dict["selected_chapter_paths"]:
            abs_path = os.path.abspath(path_str)
            if not abs_path.startswith(os.path.abspath("Books")):
                raise ValueError(f"Invalid chapter path provided: {path_str}")
            try:
                with open(abs_path, 'r', encoding='utf-8') as f:
                    combined_text.append(f.read())
            except FileNotFoundError:
                raise ValueError(f"Could not find chapter file at path: {path_str}")
        settings_dict["source_text"] = "\n\n--- END OF CHAPTER ---\n\n".join(combined_text)

    tool_id = ToolId(tool_id_str)
    handler = TOOL_HANDLERS.get(tool_id)
    if not handler:
        raise ValueError(f"Invalid or not-yet-implemented toolId: {tool_id}")
    generated_content = await handler(settings_dict)
    
    # --- [START] CRITICAL AND FINAL FIX ---
    # We now pass the filename to the history service, fulfilling the new contract.
    history_record = history_service.save_generation(
        db=db,
        tool_id=tool_id.value,
        settings=settings_dict,
        generated_content=generated_content,
        source_filename=source_file.filename if source_file else None
    )
    # --- [END] CRITICAL AND FINAL FIX ---
    
    return {
        "generation_id": history_record.id,
        "tool_id": history_record.tool_id.value,
        "content": history_record.generated_content
    }