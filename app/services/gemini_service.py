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

async def ocr_file_with_gemini(file_bytes: bytes, mime_type: str) -> str:
    """
    DEPRECATED in favor of a dedicated OCR service. This is a temporary solution.
    Uploads a file in memory to the Gemini API and extracts text.
    """
    try:
        # The File API is a good approach for this.
        uploaded_file = genai.upload_file(
            contents=file_bytes,
            display_name="ocr_temp_file",
            mime_type=mime_type
        )
        model = genai.GenerativeModel(GEMINI_FLASH_MODEL) # Using Flash for speed
        response = await model.generate_content_async([GEMINI_OCR_PROMPT, uploaded_file])
        return response.text
    except Exception as e:
        print(f"ERROR in ocr_file_with_gemini with API: {e}")
        raise