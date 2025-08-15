# /app/services/gemini_service.py (FINAL AND CORRECTED)

import os
import io
from dotenv import load_dotenv
from typing import List
import json
from typing import Dict, Optional
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from PIL import Image
from fastapi import WebSocket

# --- Local Imports ---
########################################################################
#  Now its 8/8/2025 and we import prompt as a just temporary solution here
#  it should be originally in OCR_Service.py file so we can use the gemeni-2.5-flash-light for other things also
#  but for now we just keep here, so later when we are cleaning the codes, we do this :)
#
########################################################################
from .prompt_library import GEMINI_OCR_PROMPT # Import our new prompt

# --- CONFIGURATION (STABLE) ---
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("FATAL ERROR: GOOGLE_API_KEY environment variable is not set.")

GEMINI_PRO_MODEL = 'gemini-2.5-flash'
GEMINI_FLASH_MODEL = 'gemini-2.5-flash'
GEMINI_FLASH_LITE_MODEL = 'gemini-2.5-flash-lite'
genai.configure(api_key=API_KEY)


# --- CORE GENERATIVE FUNCTIONS ---
async def generate_text(prompt: str, temperature: float = 0.5) -> str:
    """The workhorse for text-only, non-streaming tasks."""
    try:
        model = genai.GenerativeModel(GEMINI_FLASH_MODEL)
        config = GenerationConfig(temperature=temperature)
        response = await model.generate_content_async(prompt, generation_config=config)
        if not response.parts: raise ValueError("AI model returned an empty response.")
        return response.text
    except Exception as e:
        print(f"ERROR in generate_text with Gemini API: {e}")
        raise

async def generate_multimodal_response(prompt: str, images: List[Image.Image]) -> str:
    """
    REFACTORED: The specialist for multi-modal requests. It now accepts a LIST
    of Pillow Image objects to handle multi-page documents correctly.
    """
    try:
        model = genai.GenerativeModel(GEMINI_PRO_MODEL)
        
        # --- CRITICAL FIX ---
        # The content payload is now constructed by adding the prompt
        # and then unpacking the list of all provided Pillow Image objects.
        content = [prompt, *images]
        # --------------------
        
        response = await model.generate_content_async(content)
        
        if not response.parts:
            raise ValueError("AI model returned an empty response for the multi-modal request.")
        return response.text
    except Exception as e:
        # The error message now includes the number of images for better debugging.
        print(f"ERROR in generate_multimodal_response with Gemini API ({len(images)} images): {e}")
        raise

async def generate_text_streaming(prompt: str, websocket: WebSocket):
    """The communicator for the Chatbot, streaming tokens over a WebSocket."""
    try:
        model = genai.GenerativeModel(GEMINI_FLASH_MODEL)
        stream = await model.generate_content_async(prompt, stream=True)
        is_stream_started = False
        async for chunk in stream:
            if chunk.text:
                if not is_stream_started:
                    await websocket.send_json({"type": "stream_start"})
                    is_stream_started = True
                await websocket.send_json({"type": "stream_token", "payload": {"token": chunk.text}})
        if is_stream_started:
            await websocket.send_json({"type": "stream_end"})
    except Exception as e:
        print(f"ERROR during streaming generation: {e}")
        try:
            await websocket.send_json({ "type": "error", "payload": {"message": "An error occurred."} })
        except Exception as ws_error:
            print(f"Failed to send streaming error over WebSocket: {ws_error}")







async def ocr_file_with_gemini(file_bytes: bytes, mime_type: str) -> str:
    """
    Uploads a file in memory to the Gemini API and extracts text.
    This version includes a fallback for older library versions.
    """
    try:
        print(f"INFO: Uploading file ({mime_type}) to Gemini File API for OCR...")
        
        # --- THE FALLBACK IS HERE ---
        # We wrap the bytes in an io.BytesIO object to make it behave
        # like a file-like object, which older versions of the library
        # might handle correctly when passed to the 'path' argument.
        # This is a bit of a hack.
        in_memory_file = io.BytesIO(file_bytes)

        # We now pass this file-like object to the 'path' argument.
        uploaded_file = genai.upload_file(
            path=in_memory_file,
            display_name="ocr_temp_file",
            mime_type=mime_type
        )
        # --------------------

        print("INFO: File upload complete.")

        model = genai.GenerativeModel(GEMINI_FLASH_LITE_MODEL)

        print("INFO: Sending file to Gemini for text extraction...")
        response = await model.generate_content_async(
            [GEMINI_OCR_PROMPT, uploaded_file]
        )
        print("INFO: Text extraction complete.")

        return response.text

    except Exception as e:
        print(f"ERROR in ocr_file_with_gemini with API: {e}")
        raise
# --- [END] FALLBACK OCR FUNCTION ---



async def generate_text_streaming(prompt: str, websocket: WebSocket) -> str:
    """
    Generates text from a prompt, streams the response token-by-token
    over a WebSocket, AND returns the final, complete string.
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
    Generates a response from a prompt and GUARANTEES the output is a parsable JSON object.

    Args:
        prompt: The fully formatted prompt string that instructs the AI to generate JSON.
        temperature: The generation temperature.

    Returns:
        The generated content as a parsed Python dictionary.
    
    Raises:
        ValueError: If the API call fails or the model produces an empty/invalid response.
    """
    try:
        model = genai.GenerativeModel(GEMINI_FLASH_MODEL)
        
        # Configure generation to use JSON Mode
        config = GenerationConfig(
            temperature=temperature,
            response_mime_type="application/json" # This enables JSON Mode
        )

        response = await model.generate_content_async(prompt, generation_config=config)

        if not response.text:
            raise ValueError("AI model returned an empty response.")
        
        # The response.text is now a guaranteed JSON string, so we can parse it directly.
        return json.loads(response.text)
        
    except Exception as e:
        print(f"ERROR in generate_json with Gemini API: {e}")
        # Re-raise for the calling service to handle, providing more context.
        raise ValueError(f"Failed to get a valid JSON response from the AI. Error: {e}")