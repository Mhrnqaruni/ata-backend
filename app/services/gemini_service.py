# /app/services/gemini_service.py (CLEANED AND FINAL VERSION)

import os
import io
from dotenv import load_dotenv
from typing import List, Dict
import json
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from PIL import Image
from fastapi import WebSocket

# --- Local Imports ---
from .prompt_library import GEMINI_OCR_PROMPT

# --- CONFIGURATION (STABLE) ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("FATAL ERROR: GOOGLE_API_KEY environment variable is not set.")

GEMINI_PRO_MODEL = 'gemini-2.5-flash' # Correct model for multi-modal
GEMINI_FLASH_MODEL = 'gemini-2.5-flash'
genai.configure(api_key=API_KEY)


# --- CORE GENERATIVE FUNCTIONS ---

async def generate_text(prompt: str, temperature: float = 0.5) -> str:
    """The workhorse for text-only, non-streaming tasks."""
    try:
        model = genai.GenerativeModel(GEMINI_FLASH_MODEL)
        config = GenerationConfig(temperature=temperature)
        response = await model.generate_content_async(prompt, generation_config=config)
        if not response.parts:
            raise ValueError("AI model returned an empty response.")
        return response.text
    except Exception as e:
        print(f"ERROR in generate_text with Gemini API: {e}")
        raise

async def generate_multimodal_response(prompt: str, images: List[Image.Image]) -> str:
    """
    The specialist for multi-modal requests. It accepts a LIST of Pillow Image objects.
    """
    try:
        model = genai.GenerativeModel(GEMINI_PRO_MODEL)
        content = [prompt, *images]
        response = await model.generate_content_async(content)
        if not response.parts:
            raise ValueError("AI model returned an empty response for the multi-modal request.")
        return response.text
    except Exception as e:
        print(f"ERROR in generate_multimodal_response with Gemini API ({len(images)} images): {e}")
        raise

async def generate_text_streaming(prompt: str, websocket: WebSocket) -> str:
    """
    Generates text, streams the response token-by-token over a WebSocket,
    AND returns the final, complete string for persistence.
    """
    full_response = []
    try:
        model = genai.GenerativeModel(GEMINI_FLASH_MODEL)
        stream = await model.generate_content_async(prompt, stream=True)
        
        is_stream_started = False
        async for chunk in stream:
            if chunk.text:
                full_response.append(chunk.text)
                if not is_stream_started:
                    await websocket.send_json({"type": "stream_start", "payload": {}})
                    is_stream_started = True
                await websocket.send_json({"type": "stream_token", "payload": {"token": chunk.text}})

        if is_stream_started:
            await websocket.send_json({"type": "stream_end", "payload": {}})

    except Exception as e:
        print(f"ERROR during streaming generation: {e}")
        try:
            await websocket.send_json({
                "type": "error", 
                "payload": {"message": "Sorry, an error occurred while generating the response."}
            })
        except Exception as ws_error:
            print(f"Failed to send streaming error over WebSocket: {ws_error}")
    
    return "".join(full_response)

async def generate_json(prompt: str, temperature: float = 0.1) -> Dict:
    """
    Generates a response and GUARANTEES the output is a parsable JSON object
    by using the Gemini API's JSON Mode.
    """
    try:
        model = genai.GenerativeModel(GEMINI_FLASH_MODEL)
        config = GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json"
        )
        response = await model.generate_content_async(prompt, generation_config=config)
        if not response.text:
            raise ValueError("AI model returned an empty response.")
        return json.loads(response.text)
    except Exception as e:
        print(f"ERROR in generate_json with Gemini API: {e}")
        raise ValueError(f"Failed to get a valid JSON response from the AI. Error: {e}")

async def generate_multimodal_json(prompt: str, images: List[Image.Image]) -> Dict:
    """
    Generates a JSON response from a multimodal request (text + images),
    guaranteeing a parsable JSON object by using the Gemini API's JSON Mode.
    """
    try:
        model = genai.GenerativeModel(GEMINI_PRO_MODEL)
        config = GenerationConfig(
            temperature=0.1,
            response_mime_type="application/json"
        )
        content = [prompt, *images]
        response = await model.generate_content_async(content, generation_config=config)
        if not response.text:
            raise ValueError("AI model returned an empty response.")
        return json.loads(response.text)
    except Exception as e:
        print(f"ERROR in generate_multimodal_json with Gemini API: {e}")
        raise ValueError(f"Failed to get a valid JSON response from the multimodal AI. Error: {e}")

async def process_file_with_vision(file_bytes: bytes, mime_type: str, prompt: str, temperature: float = 0.1) -> str:
    """
    Processes a file (PDF or image) using Gemini's vision capabilities.
    The AI will OCR, analyze, and respond according to the prompt.
    This replaces traditional OCR with AI vision for better handwriting recognition.
    """
    import tempfile
    temp_file_path = None
    try:
        # Create a temporary file to upload to Gemini
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf' if 'pdf' in mime_type else '.png') as temp_file:
            temp_file.write(file_bytes)
            temp_file_path = temp_file.name

        # Upload file to Gemini File API for processing
        uploaded_file = genai.upload_file(
            path=temp_file_path,
            display_name="vision_temp_file",
            mime_type=mime_type
        )

        model = genai.GenerativeModel(GEMINI_FLASH_MODEL)
        config = GenerationConfig(temperature=temperature)

        # Send both the prompt and the file to the AI
        response = await model.generate_content_async(
            [prompt, uploaded_file],
            generation_config=config
        )

        if not response.text:
            raise ValueError("AI model returned an empty response.")

        return response.text
    except Exception as e:
        print(f"ERROR in process_file_with_vision: {e}")
        raise
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass

async def process_file_with_vision_json(file_bytes: bytes, mime_type: str, prompt: str, temperature: float = 0.1, log_context: str = "") -> Dict:
    """
    Processes a file (PDF or image) using Gemini's vision capabilities and returns JSON.
    The AI will OCR, analyze, and structure the response as JSON according to the prompt.

    Args:
        file_bytes: The file content as bytes
        mime_type: The MIME type of the file
        prompt: The prompt to send to the AI
        temperature: Temperature setting for the AI
        log_context: Optional context string for token logging (e.g., "PARSE-QUESTION", "GRADE-STUDENT")

    Returns:
        Dict with two keys: 'data' (the parsed JSON) and 'tokens' (usage metadata)
    """
    import tempfile
    temp_file_path = None
    try:
        # Create a temporary file to upload to Gemini
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf' if 'pdf' in mime_type else '.png') as temp_file:
            temp_file.write(file_bytes)
            temp_file_path = temp_file.name

        # Upload file to Gemini File API for processing
        uploaded_file = genai.upload_file(
            path=temp_file_path,
            display_name="vision_json_temp_file",
            mime_type=mime_type
        )

        model = genai.GenerativeModel(GEMINI_FLASH_MODEL)
        config = GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json"
        )

        # Send both the prompt and the file to the AI with JSON mode
        response = await model.generate_content_async(
            [prompt, uploaded_file],
            generation_config=config
        )

        if not response.text:
            raise ValueError("AI model returned an empty response.")

        # Extract token usage data
        tokens_used = {
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0
        }

        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            tokens_used['prompt_tokens'] = getattr(response.usage_metadata, 'prompt_token_count', 0)
            tokens_used['completion_tokens'] = getattr(response.usage_metadata, 'candidates_token_count', 0)
            tokens_used['total_tokens'] = getattr(response.usage_metadata, 'total_token_count', 0)

            # Log token usage
            if log_context:
                print(f"[TOKEN-USAGE] {log_context} - Prompt: {tokens_used['prompt_tokens']}, Completion: {tokens_used['completion_tokens']}, Total: {tokens_used['total_tokens']}")

        return {
            'data': json.loads(response.text),
            'tokens': tokens_used
        }
    except Exception as e:
        print(f"ERROR in process_file_with_vision_json: {e}")
        raise ValueError(f"Failed to get a valid JSON response from the vision AI. Error: {e}")
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
    





async def generate_text_streaming(prompt: str, websocket: WebSocket) -> str:
    """
    Generates text, streams the response token-by-token over a WebSocket,
    AND returns the final, complete string for persistence.
    """
    full_response = []
    try:
        model = genai.GenerativeModel(GEMINI_FLASH_MODEL)
        stream = await model.generate_content_async(prompt, stream=True)
        
        is_stream_started = False
        async for chunk in stream:
            if chunk.text:
                full_response.append(chunk.text)
                if not is_stream_started:
                    # Send a start message the moment the first token arrives
                    await websocket.send_json({"type": "stream_start", "payload": {}})
                    is_stream_started = True
                await websocket.send_json({"type": "stream_token", "payload": {"token": chunk.text}})

        if is_stream_started:
            # Always send an end message if the stream was started
            await websocket.send_json({"type": "stream_end", "payload": {}})

    except Exception as e:
        print(f"ERROR during streaming generation: {e}")
        try:
            await websocket.send_json({
                "type": "error", 
                "payload": {"message": "Sorry, an error occurred while generating the response."}
            })
        except Exception as ws_error:
            print(f"Failed to send streaming error over WebSocket: {ws_error}")
    
    return "".join(full_response)