# AI consensus evaluation utilities
import json
from typing import List, Dict, Optional, Tuple
from app.models.assessment_model import AIModelResponse, ConsensusType

def parse_ai_response(response_text: str, model_id: str) -> Optional[Dict]:
    """Parse a single AI response and extract grade/feedback."""
    if not response_text:
        return None
        
    try:
        # Find JSON in the response text
        start_index = response_text.find('{')
        end_index = response_text.rfind('}') + 1
        if start_index == -1 or end_index == 0:
            print(f"No JSON found in {model_id} response: {response_text[:100]}...")
            return None
        
        json_str = response_text[start_index:end_index]
        parsed = json.loads(json_str)
        
        # Handle both single question and multi-question formats
        if "results" in parsed and isinstance(parsed["results"], list):
            # Multi-question format - take first result
            if parsed["results"]:
                result = parsed["results"][0]
                return {
                    "grade": result.get("grade"),
                    "feedback": result.get("feedback", ""),
                    "raw_response": response_text
                }
        elif "grade" in parsed:
            # Single question format
            return {
                "grade": parsed.get("grade"),
                "feedback": parsed.get("feedback", ""),
                "raw_response": response_text
            }
            
        return None
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error in {model_id}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error parsing {model_id} response: {e}")
        return None

def evaluate_consensus(ai_responses: List[Dict], question_id: str) -> Tuple[Optional[float], Optional[str], ConsensusType, List[AIModelResponse]]:
    """
    Evaluate consensus among 3 AI model responses for a single question.
    
    Returns:
        - final_grade: The consensus grade (None if no consensus)
        - final_feedback: The consensus feedback  
        - consensus_type: Type of consensus achieved
        - structured_responses: List of parsed AI responses
    """
    
    # Parse all responses
    parsed_responses = []
    for response in ai_responses:
        if response.get("success", False):
            parsed = parse_ai_response(response.get("response", ""), response.get("model_id", ""))
            if parsed:
                parsed_responses.append(AIModelResponse(
                    model_id=response.get("model_id", ""),
                    grade=parsed.get("grade"),
                    feedback=parsed.get("feedback", ""),
                    raw_response=parsed.get("raw_response", "")
                ))
        else:
            # Failed response
            parsed_responses.append(AIModelResponse(
                model_id=response.get("model_id", ""),
                grade=None,
                feedback=f"Model error: {response.get('error', 'Unknown error')}",
                raw_response=None
            ))
    
    # We need at least 2 successful responses to make a decision
    successful_responses = [r for r in parsed_responses if r.grade is not None]
    
    if len(successful_responses) < 2:
        return None, None, ConsensusType.NONE, parsed_responses
    
    # Extract grades for comparison
    grades = [float(r.grade) for r in successful_responses if r.grade is not None]
    
    if len(grades) < 2:
        return None, None, ConsensusType.NONE, parsed_responses
        
    # Check for consensus
    if len(set(grades)) == 1:
        # All successful models agree (full consensus)
        consensus_grade = grades[0]
        consensus_feedback = successful_responses[0].feedback
        return consensus_grade, consensus_feedback, ConsensusType.FULL, parsed_responses
    
    elif len(grades) == 3:
        # We have 3 responses, check for majority (2/3)
        from collections import Counter
        grade_counts = Counter(grades)
        
        # Find if any grade appears at least twice
        for grade, count in grade_counts.items():
            if count >= 2:
                # Majority consensus found
                consensus_feedback = next(r.feedback for r in successful_responses if r.grade == grade)
                return grade, consensus_feedback, ConsensusType.MAJORITY, parsed_responses
        
        # All 3 grades are different - no consensus
        return None, None, ConsensusType.NONE, parsed_responses
    
    elif len(grades) == 2:
        # Only 2 successful responses
        if grades[0] == grades[1]:
            # Both agree
            consensus_grade = grades[0] 
            consensus_feedback = successful_responses[0].feedback
            return consensus_grade, consensus_feedback, ConsensusType.MAJORITY, parsed_responses
        else:
            # Two different grades - no consensus
            return None, None, ConsensusType.NONE, parsed_responses
    
    # Fallback - no consensus
    return None, None, ConsensusType.NONE, parsed_responses

def determine_final_status(consensus_type: ConsensusType) -> str:
    """Determine the final status based on consensus type."""
    if consensus_type in [ConsensusType.FULL, ConsensusType.MAJORITY]:
        return "ai_graded"
    else:
        return "pending_review"