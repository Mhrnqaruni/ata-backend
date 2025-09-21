# Multi-model AI grading extension for gemini_service
import asyncio
from typing import List, Dict
from PIL import Image
import google.generativeai as genai

# Import the existing GEMINI_PRO_MODEL constant
GEMINI_PRO_MODEL = 'gemini-2.5-flash'

async def generate_multi_model_responses(prompt: str, images: List[Image.Image]) -> List[Dict]:
    """
    Calls 3 Gemini 2.5-flash models concurrently with the same prompt and images.
    Returns a list of 3 responses with model identifiers.
    """
    
    async def single_model_call(model_id: str) -> Dict:
        """Helper function to call a single model and return structured response."""
        try:
            model = genai.GenerativeModel(GEMINI_PRO_MODEL)
            content = [prompt, *images]
            response = await model.generate_content_async(content)
            
            if not response.parts:
                raise ValueError(f"AI model {model_id} returned an empty response.")
                
            return {
                "model_id": model_id,
                "response": response.text,
                "success": True,
                "error": None
            }
        except Exception as e:
            print(f"ERROR in {model_id} with Gemini API: {e}")
            return {
                "model_id": model_id,
                "response": None,
                "success": False,
                "error": str(e)
            }
    
    # Create 3 concurrent tasks for the same prompt
    tasks = [
        single_model_call("gemini_1"),
        single_model_call("gemini_2"), 
        single_model_call("gemini_3")
    ]
    
    # Execute all 3 calls concurrently
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle any exceptions from gather
    cleaned_responses = []
    for i, response in enumerate(responses):
        if isinstance(response, Exception):
            cleaned_responses.append({
                "model_id": f"gemini_{i+1}",
                "response": None,
                "success": False,
                "error": str(response)
            })
        else:
            cleaned_responses.append(response)
    
    return cleaned_responses