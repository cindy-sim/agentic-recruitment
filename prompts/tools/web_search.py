import json
import logging
import requests
from config.settings import TAVILY_API_KEY

logger = logging.getLogger(__name__)

def get_web_search_description() -> str:
    return f"""
## web_search
Description: This tool is used to search the web for information.
Parameters:
- query: (required) The query to search the web for.

Usage:
<web_search>
<query>
</query>
</web_search>
"""

def perform_web_search(query: str) -> dict:
    """
    Perform a web search using the Tavily API.
    
    Args:
        query: The search query
        
    Returns:
        dict: The search results
    """
    try:
        logger.info(f"Performing web search for query: {query}")
        
        # Tavily API endpoint
        url = "https://api.tavily.com/search"
        
        # Request parameters
        params = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "include_domains": [],
            "exclude_domains": [],
            "max_results": 5
        }
        
        # Make the request
        response = requests.post(url, json=params)
        
        # Check if the request was successful
        if response.status_code == 200:
            results = response.json()
            logger.info(f"Web search successful, found {len(results.get('results', []))} results")
            return results
        else:
            logger.error(f"Web search failed with status code {response.status_code}: {response.text}")
            return {"error": f"Search failed with status code {response.status_code}", "message": response.text}
    
    except Exception as e:
        logger.error(f"Error performing web search: {e}")
        return {"error": str(e)}

def perform_background_check(applicant_name: str, applicant_email: str) -> dict:
    """
    Perform a simple background check on an applicant using web search.
    
    Args:
        applicant_name: The applicant's name
        applicant_email: The applicant's email
        
    Returns:
        dict: The background check results
    """
    try:
        logger.info(f"Performing background check for {applicant_name} ({applicant_email})")
        
        # Create search queries
        name_query = f"{applicant_name} professional background"
        email_query = f"{applicant_email} professional profile"
        
        # Perform searches
        name_results = perform_web_search(name_query)
        email_results = perform_web_search(email_query)
        
        # Generate a summary of the results using OpenAI
        summary = summarize_background_check(name_results, email_results, applicant_name, applicant_email)
        
        # Combine results
        combined_results = {
            "name_search": name_results,
            "email_search": email_results,
            "summary": summary
        }
        
        return combined_results
    
    except Exception as e:
        logger.error(f"Error performing background check: {e}")
        return {"error": str(e)}

def summarize_background_check(name_results: dict, email_results: dict, applicant_name: str, applicant_email: str) -> str:
    """
    Summarize the background check results using OpenAI.
    
    Args:
        name_results: Results from the name search
        email_results: Results from the email search
        applicant_name: The applicant's name
        applicant_email: The applicant's email
        
    Returns:
        str: A summary of the background check results
    """
    try:
        from openai import OpenAI
        from config.settings import OPENAI_API_KEY
        
        # Create OpenAI client
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Extract relevant information from search results
        name_content = []
        if "results" in name_results:
            for result in name_results["results"][:3]:  # Limit to top 3 results
                name_content.append(f"Title: {result.get('title', 'No title')}")
                name_content.append(f"Content: {result.get('content', 'No content')}")
                name_content.append(f"URL: {result.get('url', 'No URL')}")
                name_content.append("---")
        
        email_content = []
        if "results" in email_results:
            for result in email_results["results"][:3]:  # Limit to top 3 results
                email_content.append(f"Title: {result.get('title', 'No title')}")
                email_content.append(f"Content: {result.get('content', 'No content')}")
                email_content.append(f"URL: {result.get('url', 'No URL')}")
                email_content.append("---")
        
        # Create prompt for OpenAI
        name_content_str = "\n".join(name_content)
        email_content_str = "\n".join(email_content)
        
        prompt = f"""
        I need you to analyze the following web search results for a job applicant and provide a brief summary of their professional background.
        
        Applicant Name: {applicant_name}
        Applicant Email: {applicant_email}
        
        Results from name search:
        {name_content_str}
        
        Results from email search:
        {email_content_str}
        
        Please provide a concise summary (3-5 sentences) of the applicant's professional background based on these search results.
        Focus on:
        1. Professional experience and skills
        2. Education background
        3. Online presence
        4. Any red flags or inconsistencies
        
        If there's not enough information, please indicate that.
        """
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an HR assistant helping with background checks for job applicants."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        
        # Extract and return the summary
        summary = response.choices[0].message.content.strip()
        logger.info(f"Generated background check summary: {summary}")
        return summary
    
    except Exception as e:
        logger.error(f"Error summarizing background check: {e}")
        return f"Error summarizing background check: {e}"
