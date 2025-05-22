import json
import logging
from bs4 import BeautifulSoup

from prompts.sections.noToolsUsed import get_no_tools_used_section

# Configure logging
logger = logging.getLogger(__name__)

def extract_tool_response(response: str) -> dict:
    """
    Extract tool response from the LLM response.
    
    Args:
        response: LLM response
    
    Returns:
        dict: Extracted tool response
    """
    try:
        # Check if the response is XML-formatted
        if '<' in response and '>' in response:
            soup = BeautifulSoup(response, "html.parser")
            
            # Remove thinking tags
            for thinking_tag in soup.find_all(["thinking"]):
                thinking_tag.decompose()
            
            # Extract classification result
            classification_result = extract_classification_result(soup)
            if classification_result:
                return classification_result
            
            # Extract resume analysis result
            resume_analysis_result = extract_resume_analysis_result(soup)
            if resume_analysis_result:
                return resume_analysis_result
            
            # Extract conversation manager result
            conversation_manager_result = extract_conversation_manager_result(soup)
            if conversation_manager_result:
                return conversation_manager_result
            
            # Extract vision to JSON result
            vision_json_result = extract_vision_json_result(soup)
            if vision_json_result:
                return vision_json_result
            
            logger.warning("No tool response found in LLM response")
            return {"error": "No tool response found", "message": get_no_tools_used_section()}
        else:
            # Handle plain text response
            # For resume analysis, create a simple response
            if "resume" in response.lower() or "application" in response.lower():
                # Check if the response indicates the application is complete
                is_complete = "complete" in response.lower() and not "incomplete" in response.lower()
                
                return {
                    "application_complete": is_complete,
                    "response_text": response,
                    "extracted_information": {
                        "summary": "Extracted from plain text response"
                    }
                }
            # For conversation manager, create a response with the text
            else:
                return {
                    "response_text": response,
                    "application_complete": False
                }
    
    except Exception as e:
        logger.error(f"Error extracting tool response: {e}")
        return {"error": str(e)}

def extract_classification_result(soup):
    """
    Extract classification result from the soup.
    
    Args:
        soup: BeautifulSoup object
    
    Returns:
        dict: Classification result or None
    """
    classification_tag = soup.find('classification_result')
    if classification_tag:
        is_job_application = classification_tag.find('is_job_application')
        confidence = classification_tag.find('confidence')
        reason = classification_tag.find('reason')
        
        result = {"is_job_application": False}
        
        if is_job_application and is_job_application.get_text().lower() == 'true':
            result["is_job_application"] = True
        
        if confidence:
            try:
                result["confidence"] = float(confidence.get_text())
            except ValueError:
                result["confidence"] = 0.0
        
        if reason:
            result["reason"] = reason.get_text()
        
        return result
    
    return None

def extract_resume_analysis_result(soup):
    """
    Extract resume analysis result from the soup.
    
    Args:
        soup: BeautifulSoup object
    
    Returns:
        dict: Resume analysis result or None
    """
    resume_analysis_tag = soup.find('resume_analysis_result')
    if resume_analysis_tag:
        missing_requirements = resume_analysis_tag.find('missing_requirements')
        application_complete = resume_analysis_tag.find('application_complete')
        extracted_information = resume_analysis_tag.find('extracted_information')
        
        result = {}
        
        if missing_requirements:
            try:
                result['missing_requirements'] = json.loads(missing_requirements.get_text())
            except json.JSONDecodeError:
                # If not valid JSON, treat as text
                result['missing_requirements'] = missing_requirements.get_text()
        
        if application_complete and application_complete.get_text().lower() == 'true':
            result['application_complete'] = True
        else:
            result['application_complete'] = False
        
        if extracted_information:
            try:
                result['extracted_information'] = json.loads(extracted_information.get_text())
            except json.JSONDecodeError:
                # If not valid JSON, treat as text
                result['extracted_information'] = extracted_information.get_text()
        
        return result
    
    return None

def extract_conversation_manager_result(soup):
    """
    Extract conversation manager result from the soup.
    
    Args:
        soup: BeautifulSoup object
    
    Returns:
        dict: Conversation manager result or None
    """
    conversation_manager_tag = soup.find('conversation_manager_result')
    if conversation_manager_tag:
        response_text = conversation_manager_tag.find('response_text')
        application_complete = conversation_manager_tag.find('application_complete')
        next_steps = conversation_manager_tag.find('next_steps')
        
        result = {}
        
        if response_text:
            result['response_text'] = response_text.get_text()
        
        if application_complete and application_complete.get_text().lower() == 'true':
            result['application_complete'] = True
        else:
            result['application_complete'] = False
        
        if next_steps:
            try:
                result['next_steps'] = json.loads(next_steps.get_text())
            except json.JSONDecodeError:
                # If not valid JSON, treat as text
                result['next_steps'] = next_steps.get_text()
        
        return result
    
    return None

def extract_vision_json_result(soup):
    """
    Extract vision JSON result from the soup.
    
    Args:
        soup: BeautifulSoup object
    
    Returns:
        dict: Vision JSON result or None
    """
    vision_json_result_tag = soup.find('vision_json_result')
    if vision_json_result_tag:
        status = vision_json_result_tag.find('status')
        json_data = vision_json_result_tag.find('json_data')
        
        result = {}
        
        if status:
            result['status'] = status.get_text()
        
        if json_data:
            try:
                result['json_data'] = json.loads(json_data.get_text())
            except json.JSONDecodeError:
                # If not valid JSON, treat as text
                result['json_data'] = json_data.get_text()
        
        return result
    
    return None