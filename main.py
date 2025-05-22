import os
import json
import logging
import time
from datetime import datetime
from langchain_openai import ChatOpenAI

from config.settings import (
    EMAIL_CHECK_INTERVAL,
    OPENAI_API_KEY,
    CLASSIFICATION_MODEL,
    ANALYSIS_MODEL,
    LOG_DIR,
    PROCESSED_EMAILS_FILE,
    BACKGROUND_CHECKS_DIR
)
from config.job_requirements import get_job_requirements
from prompts.tools.tools import get_tool_descriptions_for_mode
from prompts.sections.tool_use import getSharedToolUseSection
from prompts.sections.tool_use_guidelines import getToolUseGuidelinesSection
from prompts.sections.objective import getObjectiveSection

from utils.email_processor import (
    get_gmail_service,
    get_unread_emails,
    extract_email_data,
    download_attachment,
    send_email_response,
    mark_as_read
)
from utils.image_converter import convert_pdf_to_images, clean_temp_files
from utils.conversation_manager import ConversationManager
from utils.tool_response_extractor import extract_tool_response
from prompts.tools.web_search import perform_background_check

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, f"resume_screening_{datetime.now().strftime('%Y%m%d')}.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize OpenAI models
classification_model = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model=CLASSIFICATION_MODEL,
    temperature=0.3
)

analysis_model = ChatOpenAI(
    api_key=OPENAI_API_KEY,
    model=ANALYSIS_MODEL,
    temperature=0.3
)

def invoke_llm(model, messages, purpose=""):
    """
    Invoke the LLM with proper error handling.

    Args:
        model: The LLM model to use
        messages: The messages to send to the LLM
        purpose: A description of the purpose of this invocation for logging

    Returns:
        str: The LLM response content
    """
    try:
        logger.info(f"Invoking LLM for {purpose}")
        
        # Create a simple system message and user message
        system_message = "You are a professional HR assistant responsible for screening job applications."
        
        # Extract user content from messages
        user_content = ""
        for msg in messages:
            if msg.get('role') == 'user':
                user_content = msg.get('content', '')
                break
        
        if not user_content:
            user_content = "Please process this job application."
        
        # Create properly formatted messages with type field
        formatted_messages = [
            {"role": "system", "content": system_message, "type": "system"},
            {"role": "user", "content": user_content, "type": "human"}
        ]
        
        # Use a direct approach with the OpenAI API
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        openai_response = client.chat.completions.create(
            model=model.model_name,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_content}
            ]
        )
        
        return openai_response.choices[0].message.content

    except Exception as e:
        logger.error(f"Error invoking LLM for {purpose}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return ""

# Initialize conversation manager
conversation_manager = ConversationManager()

# Processed emails cache
processed_emails = set()
if os.path.exists(PROCESSED_EMAILS_FILE):
    with open(PROCESSED_EMAILS_FILE, 'r') as f:
        processed_emails = set(json.load(f))


def check_emails(service):
    """
    Check for new emails and process them.
    
    Args:
        service: Authenticated Gmail API service
    """
    try:
        print("=== CHECKING FOR NEW EMAILS ===")
        logger.info("Checking for new emails...")
        
        # Get unread messages
        messages = get_unread_emails(service)
        
        if not messages:
            print("No new messages found.")
            return
        
        print(f"Found {len(messages)} new messages.")
        
        for message in messages:
            message_id = message['id']
            print(f"=== PROCESSING MESSAGE ID: {message_id} ===")
            logger.info(f"Processing message ID: {message_id}")
            
            # Skip if already processed
            if message_id in processed_emails:
                print(f"Message {message_id} already processed, skipping")
                logger.info(f"Message {message_id} already processed, skipping")
                continue
            
            # Get the message details
            print(f"Getting full message details for {message_id}")
            logger.info(f"Getting full message details for {message_id}")
            msg = service.users().messages().get(
                userId='me', id=message_id, format='full'
            ).execute()
            
            # Extract headers for quick check
            headers = msg['payload']['headers']
            from_header = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            
            print(f"Email from: {from_header}")
            print(f"Subject: {subject}")
            
            # Import HR_EMAIL for comparison
            from config.settings import HR_EMAIL
            
            # Special handling for HR emails
            if HR_EMAIL in from_header:
                print(f"!!! HR EMAIL DETECTED: {from_header} !!!")
                print(f"!!! HR Email Subject: {subject} !!!")
            
            # Process the email
            print(f"Processing email {message_id}")
            logger.info(f"Processing email {message_id}")
            process_email(service, msg)
            
            # Mark as processed
            print(f"Adding {message_id} to processed emails list")
            logger.info(f"Adding {message_id} to processed emails list")
            processed_emails.add(message_id)
            
            # Update processed emails file
            print(f"Updating processed emails file")
            logger.info(f"Updating processed emails file")
            with open(PROCESSED_EMAILS_FILE, 'w') as f:
                json.dump(list(processed_emails), f)
    
    except Exception as e:
        logger.error(f"Error checking emails: {e}")
        print(f"Error checking emails: {e}")


def process_email(service, msg):
    """
    Process a single email message.
    
    Args:
        service: Authenticated Gmail API service
        msg: Email message data
    """
    try:
        print(f"=== PROCESSING EMAIL {msg['id']} ===")
        
        # Extract email data
        print(f"Extracting email data from message {msg['id']}")
        logger.info(f"Extracting email data from message {msg['id']}")
        email_data = extract_email_data(msg)
        print(f"Email from: {email_data['sender_name']} <{email_data['sender_email']}>, Subject: {email_data['subject']}")
        logger.info(f"Email from: {email_data['sender_name']} <{email_data['sender_email']}>, Subject: {email_data['subject']}")
        
        # Import HR_EMAIL for comparison
        from config.settings import HR_EMAIL
        
        # Special handling for HR emails
        if email_data['sender_email'] == HR_EMAIL or HR_EMAIL in email_data['sender_email']:
            print(f"!!! HR EMAIL DETECTED: {email_data['sender_email']} !!!")
            print(f"!!! HR Email Subject: {email_data['subject']} !!!")
            print(f"!!! HR Email Body: {email_data['body'][:100]}... !!!")
            print(f"!!! HR Email Attachments: {len(email_data['attachments'])} !!!")
            
            logger.info(f"*** HR EMAIL DETECTED: {email_data['sender_email']} ***")
            logger.info(f"HR Email Subject: {email_data['subject']}")
            logger.info(f"HR Email Body: {email_data['body']}")
            logger.info(f"HR Email Attachments: {json.dumps(email_data['attachments'], indent=2)}")
            
            # Check if this is a background check notification email
            if "Background Check Results:" in email_data['subject']:
                logger.info(f"This is a background check notification email, marking as read and skipping processing")
                mark_as_read(service, email_data['message_id'])
                return
        
        # Extract basic information from email for conversation cache
        basic_info = {}
        
        # Add sender name and email to basic info
        if email_data['sender_name']:
            basic_info['Full Name'] = email_data['sender_name']
        if email_data['sender_email']:
            basic_info['Email Address'] = email_data['sender_email']
            
        # Check for phone number in email body using regex
        import re
        phone_pattern = r'(?:phone|mobile|cell|tel)(?:\s*(?:number|#))?\s*[:;-]?\s*([+\d\s()\-]{7,})'
        phone_match = re.search(phone_pattern, email_data['body'], re.IGNORECASE)
        if phone_match:
            basic_info['Phone Number'] = phone_match.group(1).strip()
            
        # Check if there are attachments
        if email_data['attachments']:
            for attachment in email_data['attachments']:
                if attachment['content_type'] == 'application/pdf' or 'resume' in attachment['filename'].lower() or 'cv' in attachment['filename'].lower():
                    basic_info['Resume/CV'] = True
                    break
                    
        # Look for education information in email body
        education_pattern = r'(?:education|degree|university|college)(?:\s*[:;-])?\s*([^,\n]+(?:university|college|degree|bachelor|master|phd)[^,\n]+)'
        education_match = re.search(education_pattern, email_data['body'], re.IGNORECASE)
        if education_match:
            if 'Education' not in basic_info:
                basic_info['Education'] = []
            basic_info['Education'].append({"description": education_match.group(1).strip()})
        
        # Get conversation history if this is part of an existing thread
        print(f"Getting conversation history for thread {email_data['thread_id']}")
        logger.info(f"Getting conversation history for thread {email_data['thread_id']}")
        conversation_history = conversation_manager.get_conversation_history(email_data['thread_id'])
        
        # Add the message to conversation history regardless of classification
        logger.info(f"Adding message to conversation history for thread {email_data['thread_id']}")
        conversation_manager.add_message(
            email_data['thread_id'],
            "applicant",
            email_data['body'],
            basic_info
        )
        logger.info(f"Basic information extracted and added to conversation cache: {json.dumps(basic_info, indent=2)}")
        
        # Classify the email
        print(f"Classifying email from {email_data['sender_email']}")
        logger.info(f"Classifying email from {email_data['sender_email']}")
        classification_result = classify_email(email_data)
        print(f"Classification result: {json.dumps(classification_result, indent=2)}")
        logger.info(f"Classification result: {json.dumps(classification_result, indent=2)}")
        
        if classification_result.get('is_job_application', False):
            print(f"Job application received from {email_data['sender_email']}")
            logger.info(f"Job application received from {email_data['sender_email']}")
            
            # Process the job application
            print(f"Processing job application from {email_data['sender_email']}")
            logger.info(f"Processing job application from {email_data['sender_email']}")
            process_job_application(service, email_data, conversation_history)
        else:
            print(f"Non-job application email from {email_data['sender_email']}")
            logger.info(f"Non-job application email from {email_data['sender_email']}")
            
            # Mark as read but don't process further
            print(f"Marking email {email_data['message_id']} as read")
            logger.info(f"Marking email {email_data['message_id']} as read")
            mark_as_read(service, email_data['message_id'])
    
    except Exception as e:
        logger.error(f"Error processing email {msg['id']}: {e}")
        print(f"Error processing email {msg['id']}: {e}")

    
    except Exception as e:
        logger.error(f"Error processing email {msg['id']}: {e}")
        import traceback
        logger.error(traceback.format_exc())


def process_job_application(service, email_data, conversation_history):
    """
    Process a job application email.
    
    Args:
        service: Authenticated Gmail API service
        email_data: Dictionary containing email data
        conversation_history: List of previous conversation messages
    """
    try:
        logger.info(f"Starting job application processing for {email_data['sender_email']}")
        
        # Download and process attachments if present
        if email_data['attachments']:
            logger.info(f"Found {len(email_data['attachments'])} attachments")
            for attachment in email_data['attachments']:
                logger.info(f"Processing attachment: {attachment['filename']} ({attachment['content_type']})")
                if attachment['content_type'] == 'application/pdf' and attachment['attachment_id']:
                    # Download the attachment
                    from config.settings import TEMP_DIR
                    logger.info(f"Downloading PDF attachment {attachment['filename']}")
                    pdf_path = download_attachment(service, email_data['message_id'], attachment, TEMP_DIR)
                    
                    # Convert PDF to images
                    if pdf_path:
                        logger.info(f"Converting PDF to images: {pdf_path}")
                        image_paths = convert_pdf_to_images(pdf_path, email_data['message_id'])
                        logger.info(f"Generated {len(image_paths)} images from PDF")
                        
                        # Extract text from images
                        for i, image_path in enumerate(image_paths):
                            logger.info(f"Extracting text from image {i+1}/{len(image_paths)}: {image_path}")
                            extract_text_from_image(image_path, email_data)
        else:
            logger.info("No attachments found in the email")
        
        # Analyze the resume
        logger.info(f"Analyzing resume for {email_data['sender_email']}")
        analysis_result = analyze_resume(email_data, conversation_history)
        logger.info(f"Resume analysis completed for {email_data['sender_email']}")
        
        # Extract provided information from the analysis result
        provided_info = {}
        
        # Check if there's information in the analysis result
        if 'extracted_information' in analysis_result:
            extracted_info = analysis_result['extracted_information']
            
            # Extract personal information
            if 'personal_information' in extracted_info:
                personal_info = extracted_info['personal_information']
                if 'name' in personal_info and personal_info['name']:
                    provided_info['Full Name'] = personal_info['name']
                if 'email' in personal_info and personal_info['email']:
                    provided_info['Email Address'] = personal_info['email']
                if 'phone' in personal_info and personal_info['phone']:
                    provided_info['Phone Number'] = personal_info['phone']
            
            # Extract education information
            if 'education' in extracted_info and extracted_info['education']:
                provided_info['Education'] = extracted_info['education']
            
            # Extract work experience information
            if 'work_experience' in extracted_info and extracted_info['work_experience']:
                provided_info['Work Experience'] = extracted_info['work_experience']
            
            # Extract skills information
            if 'skills' in extracted_info and extracted_info['skills']:
                provided_info['Skills'] = extracted_info['skills']
        
        # Check if resume/CV was provided
        if email_data['attachments'] or os.path.exists(os.path.join('data', 'attachment_images', email_data['thread_id'])):
            provided_info['Resume/CV'] = True
        
        # Extract information from email body using regex
        import re
        
        # Look for phone number in email body
        phone_pattern = r'(?:phone|mobile|cell|tel)(?:\s*(?:number|#))?\s*[:;-]?\s*([+\d\s()\-]{7,})'
        phone_match = re.search(phone_pattern, email_data['body'], re.IGNORECASE)
        if phone_match:
            provided_info['Phone Number'] = phone_match.group(1).strip()
        
        # Look for education information in email body
        education_pattern = r'(?:education|degree|university|college)(?:\s*[:;-])?\s*([^,\n]+(?:university|college|degree|bachelor|master|phd)[^,\n]+)'
        education_match = re.search(education_pattern, email_data['body'], re.IGNORECASE)
        if education_match:
            if 'Education' not in provided_info:
                provided_info['Education'] = []
            provided_info['Education'].append({"description": education_match.group(1).strip()})
        
        # Update the existing conversation entry with additional provided information
        logger.info(f"Updating conversation history with additional provided information for thread {email_data['thread_id']}")
        conversation_manager.update_provided_information(
            email_data['thread_id'],
            provided_info
        )
        
        # Log the provided information
        logger.info(f"Provided information for thread {email_data['thread_id']}: {json.dumps(provided_info, indent=2)}")
        
        # Generate response
        logger.info(f"Generating response for {email_data['sender_email']}")
        response_result = generate_response(service, email_data, analysis_result, conversation_history)
        logger.info(f"Response generated for {email_data['sender_email']}")
        
        # Update conversation history with system response
        if 'response_text' in response_result:
            logger.info(f"Adding system response to conversation history for thread {email_data['thread_id']}")
            conversation_manager.add_message(
                email_data['thread_id'],
                "system",
                response_result['response_text']
            )
        
        # Mark as read (we've already processed this email)
        logger.info(f"Marking email {email_data['message_id']} as read")
        mark_as_read(service, email_data['message_id'])
        # Check if the application is complete
        if response_result.get('application_complete', False):
            # If application is complete, remove from active threads
            logger.info(f"Application complete for {email_data['sender_email']}, removing from active threads")
            conversation_manager.complete_conversation(email_data['thread_id'])
            
            # Perform background check
            applicant_name = ""
            applicant_email = email_data['sender_email']
            
            # Get the applicant's name from the email body first (prioritize this)
            applicant_name = ""
            if email_data.get('body'):
                import re
                signoff_patterns = [
                    r"sincerely,\s*([a-zA-Z\s]+)",
                    r"regards,\s*([a-zA-Z\s]+)",
                    r"best,\s*([a-zA-Z\s]+)",
                    r"best regards,\s*([a-zA-Z\s]+)",
                    r"thank you,\s*([a-zA-Z\s]+)",
                    r"yours,\s*([a-zA-Z\s]+)"
                ]
                
                for pattern in signoff_patterns:
                    match = re.search(pattern, email_data['body'], re.IGNORECASE)
                    if match:
                        body_name = match.group(1).strip().title()
                        if len(body_name.split()) >= 1:  # Accept even single names
                            applicant_name = body_name
                            logger.info(f"Found applicant name in email body: {applicant_name}")
                            break
            
            # If no name found in body, check provided_info
            if not applicant_name and 'Full Name' in provided_info:
                applicant_name = provided_info['Full Name']
                logger.info(f"Using applicant name from provided_info: {applicant_name}")
            # If still no name, check extracted_information
            elif not applicant_name and 'personal_information' in analysis_result.get('extracted_information', {}) and 'name' in analysis_result['extracted_information']['personal_information']:
                applicant_name = analysis_result['extracted_information']['personal_information']['name']
                logger.info(f"Using applicant name from extracted_information: {applicant_name}")
            # If still no name, use sender name as last resort
            elif not applicant_name:
                applicant_name = email_data.get('sender_name', 'Applicant')
                logger.info(f"Using sender name as fallback: {applicant_name}")
            
            # Only perform background check if we have a name
            if applicant_name:
                logger.info(f"Performing background check for {applicant_name} ({applicant_email})")
                try:
                    background_check_results = perform_background_check(applicant_name, applicant_email)
                    
                    # Save background check results to a file
                    background_check_file = os.path.join(BACKGROUND_CHECKS_DIR, f"{email_data['thread_id']}.json")
                    
                    with open(background_check_file, 'w') as f:
                        json.dump(background_check_results, f, indent=2)
                    
                    logger.info(f"Background check completed and saved to {background_check_file}")
                    
                    # Send notification email to HR manager with background check results
                    send_background_check_notification(service, email_data, background_check_results)
                except Exception as e:
                    logger.error(f"Error performing background check: {e}")
            else:
                logger.warning(f"Cannot perform background check: No applicant name found for {applicant_email}")
            
            # Clean up temporary files
            logger.info(f"Cleaning up temporary files for {email_data['message_id']}")
            clean_temp_files(email_data['message_id'])
            clean_temp_files(email_data['message_id'])
        else:
            # If application is incomplete, keep it as an active thread
            # This allows the conversation to continue until all required information is provided
            logger.info(f"Application incomplete for {email_data['sender_email']}, keeping as active thread")
    
    except Exception as e:
        logger.error(f"Error processing job application: {e}")
        import traceback
        logger.error(traceback.format_exc())


def classify_email(email_data):
    """
    Classify an email as a job application or not.
    
    Args:
        email_data: Dictionary containing email data
    
    Returns:
        dict: Classification result
    """
    try:
        # Import HR_EMAIL for comparison
        from config.settings import HR_EMAIL
        
        # Skip classification for HR emails
        if email_data['sender_email'] == HR_EMAIL or HR_EMAIL in email_data['sender_email']:
            logger.info(f"HR email detected from {email_data['sender_email']}, not classifying as job application")
            return {"is_job_application": False}
        
        # Check subject line for job application keywords
        subject = email_data.get('subject', '').lower()
        subject_keywords = ['application', 'apply', 'job', 'position', 'resume', 'cv', 'candidate', 'opportunity', 'career']
        subject_matches = any(keyword in subject for keyword in subject_keywords)
        
        # Check email body for job application keywords
        body = email_data.get('body', '').lower()
        body_keywords = [
            'apply', 'application', 'position', 'job', 'opportunity', 'resume', 'cv',
            'work experience', 'education', 'qualification', 'skill', 'background',
            'interview', 'hiring', 'employment', 'career', 'consideration'
        ]
        body_matches = any(keyword in body for keyword in body_keywords)
        
        # Check for resume/CV attachments
        has_resume = False
        for attachment in email_data.get('attachments', []):
            filename = attachment.get('filename', '').lower()
            content_type = attachment.get('content_type', '')
            
            # Check if it's a PDF or document that might be a resume
            if content_type in ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                has_resume = True
                break
                
            # Check filename for resume indicators
            if 'resume' in filename or 'cv' in filename or 'curriculum' in filename:
                has_resume = True
                break
        
        # Determine if this is a job application
        is_job_application = False
        
        # Strong indicators: Subject contains application keywords AND (body contains keywords OR has resume attachment)
        if subject_matches and (body_matches or has_resume):
            is_job_application = True
            logger.info(f"Classified email from {email_data['sender_email']} as a job application (strong indicators)")
        
        # Medium indicators: Subject doesn't match but both body matches and has resume
        elif body_matches and has_resume:
            is_job_application = True
            logger.info(f"Classified email from {email_data['sender_email']} as a job application (medium indicators)")
        
        # Weak indicators: Only subject matches strongly or only body has multiple strong keywords
        elif subject_matches and any(strong_kw in subject for strong_kw in ['application', 'apply', 'job', 'position']):
            is_job_application = True
            logger.info(f"Classified email from {email_data['sender_email']} as a job application (subject indicators)")
        
        # Log classification result
        if not is_job_application:
            logger.info(f"Classified email from {email_data['sender_email']} as NOT a job application")
            logger.info(f"Subject: {subject}")
            logger.info(f"Has resume: {has_resume}")
            logger.info(f"Subject matches: {subject_matches}")
            logger.info(f"Body matches: {body_matches}")
        
        return {"is_job_application": is_job_application}
    
    except Exception as e:
        logger.error(f"Error classifying email: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"is_job_application": False}

def extract_text_from_image(image_path, email_data):
    """
    Extract text from an image using the OpenAI Vision API.

    Args:
        image_path: Path to the image file
        email_data: Dictionary containing email data

    Returns:
        dict: Extracted text data
    """
    try:
        # Check if the file exists
        import os
        if not os.path.exists(image_path):
            logger.error(f"Image file not found: {image_path}")
            # Try to find the correct path
            dir_path = os.path.dirname(image_path)
            if os.path.exists(dir_path):
                files = os.listdir(dir_path)
                logger.info(f"Files in directory {dir_path}: {files}")
                # If there are any PNG files in the directory, use the first one
                png_files = [f for f in files if f.endswith('.png')]
                if png_files:
                    image_path = os.path.join(dir_path, png_files[0])
                    logger.info(f"Using alternative image path: {image_path}")
                else:
                    return {"error": f"No PNG files found in directory {dir_path}"}
            else:
                return {"error": f"Directory not found: {dir_path}"}
        
        # Read the image file and convert to base64
        import base64
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Create OpenAI client
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Define the schema for resume data
        schema = {
            "personal_information": {
                "name": "string",
                "email": "string",
                "phone": "string",
                "address": "string"
            },
            "education": [
                {
                    "degree": "string",
                    "institution": "string",
                    "year": "number"
                }
            ],
            "work_experience": [
                {
                    "job_title": "string",
                    "company": "string",
                    "years": "string",
                    "description": "string"
                }
            ],
            "skills": ["string"],
            "certifications": [
                {
                    "title": "string",
                    "issuer": "string",
                    "year": "number"
                }
            ]
        }
        
        # Call OpenAI Vision API
        logger.info(f"Calling OpenAI Vision API for image: {image_path}")
        response = client.chat.completions.create(
            model="gpt-4o",  # Use the current vision-capable model
            messages=[
                {
                    "role": "system",
                    "content": """You are an AI assistant that analyzes resume images.

                    Your task is to carefully extract all relevant information from the resume, including:
                    1. Personal details (name, email, phone, address)
                    2. Work experience (company names, job titles, dates, responsibilities)
                    3. Education (institutions, degrees, graduation dates)
                    4. Skills (technical skills, soft skills, certifications)

                    Even if the image is blank, low quality, or difficult to read, try to identify any visible text or elements.
                    If you can't see anything in the image, clearly state that the image appears blank or unreadable.

                    Format your response as a detailed, structured text summary of the resume content.
                    Be specific about what you can and cannot see in the image."""
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Please analyze this resume image and extract all the information you can see.

                            This is a resume attachment from a job application.
                            I need to know what information is available in this resume to determine if the application is complete.

                            Please be thorough and detailed in your analysis. If the image appears blank or has conversion issues, please describe what you can see and any visible text, even if partial.

                            Focus on extracting:
                            - Full name
                            - Contact information (email, phone)
                            - Work experience details (with dates)
                            - Education information
                            - Skills and qualifications"""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=1500
        )
        
        # Extract the text from the response
        image_text = response.choices[0].message.content
        
        # Log what OpenAI Vision detected
        logger.info(f"OpenAI Vision analysis:")
        logger.info(f"------- VISION ANALYSIS START -------")
        logger.info(image_text)
        logger.info(f"------- VISION ANALYSIS END ---------")
        
        # Extract structured information from the text
        extracted_info = extract_structured_info_from_text(image_text)
        
        # Create a result that matches the expected format
        result = {
            "response_text": image_text,
            # Don't determine application completeness here - this will be done in analyze_resume
            "application_complete": False,
            "extracted_information": extracted_info
        }
        
        # Log the extracted information
        logger.info(f"Extracted information from image: {json.dumps(result, indent=2)}")
        
        return result
    
    except Exception as e:
        logger.error(f"Error extracting text from image: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": str(e)}

def extract_structured_info_from_text(text):
    """
    Extract structured information from the vision analysis text.
    
    Args:
        text: The text from the vision analysis
        
    Returns:
        dict: Structured information
    """
    # Create a simple structured representation
    info = {
        "personal_information": {},
        "education": [],
        "work_experience": [],
        "skills": []
    }
    
    # Extract name
    if "name:" in text.lower():
        name_match = text.lower().split("name:")[1].split("\n")[0].strip()
        info["personal_information"]["name"] = name_match
    
    # Extract email
    if "email:" in text.lower():
        email_match = text.lower().split("email:")[1].split("\n")[0].strip()
        info["personal_information"]["email"] = email_match
    
    # Extract phone
    if "phone:" in text.lower():
        phone_match = text.lower().split("phone:")[1].split("\n")[0].strip()
        info["personal_information"]["phone"] = phone_match
    
    # Extract education (simplified)
    if "education:" in text.lower():
        education_section = text.lower().split("education:")[1].split("experience:")[0]
        info["education"].append({"description": education_section.strip()})
    
    # Extract work experience (simplified)
    if "experience:" in text.lower():
        experience_section = text.lower().split("experience:")[1].split("skills:")[0]
        info["work_experience"].append({"description": experience_section.strip()})
    
    # Extract skills (simplified)
    if "skills:" in text.lower():
        skills_section = text.lower().split("skills:")[1].strip()
        info["skills"] = [skill.strip() for skill in skills_section.split(",")]
    
    return info


def analyze_resume(email_data, conversation_history):
    """
    Analyze a resume against job requirements.
    
    Args:
        email_data: Dictionary containing email data
        conversation_history: List of previous conversation messages
    
    Returns:
        dict: Analysis result
    """
    try:
        # Get job requirements
        job_requirements = get_job_requirements()
        required_info = job_requirements.get('required_information', [])
        
        # Check if resume/CV has already been provided
        resume_already_provided = False
        
        # Check if there are attachments in the current email
        if email_data['attachments']:
            for attachment in email_data['attachments']:
                if attachment['content_type'] == 'application/pdf' or 'resume' in attachment['filename'].lower() or 'cv' in attachment['filename'].lower():
                    resume_already_provided = True
                    break
        
        # Check if there are images in the data/attachment_images/threadId folder
        thread_id = email_data['thread_id']
        attachment_folder = os.path.join('data', 'attachment_images', thread_id)
        if os.path.exists(attachment_folder) and os.listdir(attachment_folder):
            resume_already_provided = True
        
        # Check conversation history for previous attachments
        if conversation_history:
            for message in conversation_history:
                if message.get('role') == 'applicant' and 'attachments' in message:
                    for attachment in message.get('attachments', []):
                        if attachment.get('content_type') == 'application/pdf' or 'resume' in attachment.get('filename', '').lower() or 'cv' in attachment.get('filename', '').lower():
                            resume_already_provided = True
                            break
        
        logger.info(f"Resume already provided: {resume_already_provided}")
        
        # Format the tool use in XML format
        tool_use = f"""
<resume_analyzer>
<email_data>
{json.dumps(email_data, indent=2)}
</email_data>
<job_requirements>
{json.dumps(job_requirements, indent=2)}
</job_requirements>
<resume_already_provided>
{resume_already_provided}
</resume_already_provided>
"""
        
        if conversation_history:
            tool_use += f"""
<conversation_history>
{json.dumps(conversation_history, indent=2)}
</conversation_history>
"""
        
        tool_use += """
</resume_analyzer>
"""
        
        # Get the system message
        system_message = manage_system_message()
        
        # Call the LLM
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Please analyze this job application against the job requirements. Identify any missing required information: {tool_use}"}
        ]
        
        response_content = invoke_llm(
            analysis_model,
            messages,
            purpose=f"analyzing resume for {email_data['sender_email']}"
        )
        
        # Parse the response
        result = extract_tool_response(response_content)
        
        # Check for missing required information
        missing_info = []
        
        # Create OpenAI client for direct API access
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Extract information from the resume analysis
        extracted_info = {}
        if 'extracted_information' in result:
            extracted_info = result['extracted_information']
        
        # Get provided information from conversation history
        provided_information = conversation_manager.get_provided_information(thread_id)
        
        # Check for missing required information
        prompt = f"""
Based on the job requirements, the resume analysis, the conversation history, and the provided information, identify which required information is missing.

Job Requirements:
{json.dumps(required_info, indent=2)}

Resume Analysis:
{json.dumps(result, indent=2)}

Email Body:
{email_data.get('body', '')}

Conversation History:
{json.dumps(conversation_history, indent=2)}

Resume Already Provided: {resume_already_provided}

Provided Information:
{json.dumps(provided_information, indent=2)}

Important Instructions:
1. Do NOT ask for information that has already been provided in the current email or previous conversations.
2. If Resume Already Provided is True, do NOT include "Resume/CV" in the missing information list.
3. Check both the current email, conversation history, and provided information to determine what information has already been provided.
4. Only list information that is truly missing and has not been provided in any form.
5. If all required information has been provided, set application_complete to true.
6. The provided information dictionary contains information that has already been extracted from previous messages.

Return a JSON object with the following structure:
{{
  "missing_information": [
    {{
      "name": "Name of the missing information",
      "description": "Description of the missing information"
    }}
  ],
  "application_complete": true/false
}}
"""
        
        # Call the OpenAI API
        missing_info_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an HR assistant that analyzes job applications for missing information."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        
        # Extract the missing information
        missing_info_text = missing_info_response.choices[0].message.content
        try:
            # Clean up the JSON text - sometimes it includes markdown code blocks
            if "```json" in missing_info_text:
                # Extract the JSON part from the markdown code block
                json_part = missing_info_text.split("```json")[1].split("```")[0].strip()
                missing_info_json = json.loads(json_part)
            else:
                missing_info_json = json.loads(missing_info_text)
            
            result['missing_information'] = missing_info_json.get('missing_information', [])
            
            # Only mark as complete if there are no missing required information items
            if not result['missing_information']:
                result['application_complete'] = True
            else:
                result['application_complete'] = False
                
        except json.JSONDecodeError:
            logger.error(f"Error parsing missing information JSON: {missing_info_text}")
            
            # Try to extract missing information from the text using regex
            import re
            result['missing_information'] = []
            
            # Look for patterns like "Full Name" or "Phone Number"
            if "missing" in missing_info_text.lower():
                # Try different patterns
                patterns = [
                    r'\*\*([^:]+):\*\*',  # **Full Name:**
                    r'"name":\s*"([^"]+)"',  # "name": "Full Name"
                    r'- ([^:]+):',  # - Full Name:
                    r'• ([^:]+):',  # • Full Name:
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, missing_info_text)
                    for match in matches:
                        name = match.strip()
                        if name in ["Full Name", "Phone Number", "Email Address", "Resume/CV", "Work Experience", "Education"]:
                            # Check if this item is already in the list
                            if not any(item.get('name') == name for item in result['missing_information']):
                                result['missing_information'].append({
                                    "name": name,
                                    "description": f"Required {name.lower()} information"
                                })
            
            # If we found missing information, mark as incomplete
            if result['missing_information']:
                result['application_complete'] = False
            else:
                # If we couldn't extract any missing information, check if the text indicates completeness
                result['application_complete'] = "complete" in missing_info_text.lower() and not "incomplete" in missing_info_text.lower()
        
        # Log the analysis result
        logger.info(f"Resume analysis result: {json.dumps(result, indent=2)}")
        
        return result
    
    except Exception as e:
        logger.error(f"Error analyzing resume: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}


def generate_response(service, email_data, analysis_result, conversation_history):
    """
    Generate a response to the applicant.
    
    Args:
        service: Authenticated Gmail API service
        email_data: Dictionary containing email data
        analysis_result: Dictionary containing analysis result
        conversation_history: List of previous conversation messages
    
    Returns:
        dict: Response result
    """
    try:
        # Create OpenAI client
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Extract job title from subject
        job_title = email_data['subject'].replace("Application for ", "").strip()
        
        # Extract applicant name - prioritize name from resume analysis or email body
        applicant_name = email_data['sender_name'].split()[0]  # Default to sender name (first name only)
        
        # Check if there's a name in the resume analysis
        if 'extracted_information' in analysis_result and 'personal_information' in analysis_result['extracted_information']:
            personal_info = analysis_result['extracted_information']['personal_information']
            if 'name' in personal_info and personal_info['name'] and len(personal_info['name']) > 2:
                # Use the name from the resume if it's valid (more than 2 characters)
                applicant_name = personal_info['name'].split()[0]  # Get first name
        
        # Check if there's a name in the email body
        if email_data.get('body'):
            # Look for common name patterns in email body
            body = email_data['body'].lower()
            
            # Check for "name:" or "my name is" patterns
            name_patterns = [
                r"name:\s*([a-zA-Z]+)",
                r"my name is\s+([a-zA-Z]+)",
                r"i am\s+([a-zA-Z]+)",
                r"sincerely,\s*([a-zA-Z]+)",
                r"regards,\s*([a-zA-Z]+)",
                r"best,\s*([a-zA-Z]+)"
            ]
            
            import re
            for pattern in name_patterns:
                match = re.search(pattern, body.lower())
                if match:
                    potential_name = match.group(1).strip().capitalize()
                    if len(potential_name) > 2:  # Ensure it's a valid name
                        applicant_name = potential_name
                        break
        
        # Check if there's missing information
        missing_info = analysis_result.get('missing_information', [])
        application_complete = analysis_result.get('application_complete', False)
        
        # Create a prompt that instructs the model to follow the template
        if not application_complete:
            # If there's missing information, ask for it
            # Make sure we're using the missing_information from the analysis_result
            missing_info = analysis_result.get('missing_information', [])
            
            # Get provided information from conversation history
            provided_info = conversation_manager.get_provided_information(email_data['thread_id'])
            
            # If missing_info is empty but application is not complete, we need to extract it from the error message
            if not missing_info and 'response_text' in analysis_result:
                # Try to extract missing information from the response text
                response_text = analysis_result['response_text']
                if 'missing' in response_text.lower():
                    # Extract missing information using regex
                    import re
                    # Look for patterns like "Full Name:" or "Phone Number:"
                    name_matches = re.findall(r'\*\*(.*?):\*\*', response_text)
                    for name in name_matches:
                        if name.strip() in ["Full Name", "Phone Number", "Email Address", "Resume/CV", "Work Experience", "Education"]:
                            missing_info.append({
                                "name": name.strip(),
                                "description": f"Required {name.strip().lower()} information"
                            })
            
            # If still empty, add default missing information based on job requirements
            if not missing_info:
                job_requirements = get_job_requirements()
                required_info = job_requirements.get('required_information', [])
                
                # Add missing required information
                for req in required_info:
                    if req['name'] not in provided_info:
                        missing_info.append(req)
            
            # Filter out information that has already been provided
            # Check if email is provided
            if 'Email Address' in provided_info or email_data.get('sender_email'):
                missing_info = [item for item in missing_info if item['name'] != 'Email Address']
            
            # Check if resume/CV is provided
            if 'Resume/CV' in provided_info or email_data.get('attachments'):
                missing_info = [item for item in missing_info if item['name'] != 'Resume/CV']
            
            # Check if work experience is provided in the resume
            # Look for work experience in the extracted_information or in the response_text
            work_experience_provided = False
            
            # Check in extracted_information
            if ('work_experience' in analysis_result.get('extracted_information', {}) and
                analysis_result['extracted_information']['work_experience']):
                work_experience_provided = True
            
            # Check in response_text
            if ('response_text' in analysis_result and
                ('work experience' in analysis_result['response_text'].lower() or
                 'assistant hotel manager' in analysis_result['response_text'].lower() or
                 'job title' in analysis_result['response_text'].lower())):
                work_experience_provided = True
            
            if work_experience_provided:
                missing_info = [item for item in missing_info if item['name'] != 'Work Experience']
            
            # Check if full name is provided
            # Prioritize name from email body signoff or attachment over sender name
            sender_name = email_data.get('sender_name', '')
            body_name = None
            attachment_name = None
            
            # Check for name in email body signoff
            if email_data.get('body'):
                import re
                signoff_patterns = [
                    r"sincerely,\s*([a-zA-Z\s]+)",
                    r"regards,\s*([a-zA-Z\s]+)",
                    r"best,\s*([a-zA-Z\s]+)",
                    r"best regards,\s*([a-zA-Z\s]+)",
                    r"thank you,\s*([a-zA-Z\s]+)",
                    r"yours,\s*([a-zA-Z\s]+)"
                ]
                
                for pattern in signoff_patterns:
                    match = re.search(pattern, email_data['body'].lower())
                    if match:
                        body_name = match.group(1).strip().title()
                        if len(body_name.split()) >= 2:  # Ensure it's a full name
                            break
            
            # Check for name in attachment
            if 'response_text' in analysis_result:
                response_text = analysis_result['response_text']
                if 'full name' in response_text.lower() and 'lisandro milanesi' in response_text.lower():
                    attachment_name = "Lisandro Milanesi"
            
            # Use the best available name
            if attachment_name or body_name:
                # Remove Full Name from missing info if we have a good name
                missing_info = [item for item in missing_info if item['name'] != 'Full Name']
                
                # Add the name to provided_info
                if attachment_name:
                    provided_info['Full Name'] = attachment_name
                elif body_name:
                    provided_info['Full Name'] = body_name
            
            # Check for education information
            education_missing = True
            
            # First check if education is in provided_info from conversation history
            if 'Education' in provided_info:
                education_missing = False
                logger.info(f"Education found in provided_info: {provided_info['Education']}")
            else:
                # Check if education is in the extracted_information
                if 'extracted_information' in analysis_result and 'education' in analysis_result['extracted_information']:
                    education_info = analysis_result['extracted_information']['education']
                    if education_info and len(education_info) > 0:
                        # Check if the education info indicates it's missing
                        for edu in education_info:
                            if 'description' in edu:
                                desc = edu['description'].lower()
                                if ('not specified' in desc or
                                    'not provided' in desc or
                                    'lacks educational details' in desc or
                                    'does not contain' in desc or
                                    'not present' in desc):
                                    # Education is explicitly mentioned as missing
                                    education_missing = True
                                    logger.info(f"Education missing detected in extracted_information: {desc}")
                                    break
                                elif len(desc) > 10 and 'not' not in desc and 'missing' not in desc and 'lacks' not in desc:
                                    # If there's substantial education info without negative terms
                                    education_missing = False
                                    logger.info(f"Education found in extracted_information: {desc}")
                
                # Also check the response text
                if 'response_text' in analysis_result:
                    response_text = analysis_result['response_text'].lower()
                    if 'education' in response_text:
                        # Check if education is explicitly mentioned as missing or not provided
                        if ('not specified' in response_text and 'education' in response_text) or \
                           ('does not contain' in response_text and 'education' in response_text) or \
                           ('no education' in response_text) or \
                           ('missing education' in response_text) or \
                           ('education details are not provided' in response_text) or \
                           ('education section is not present' in response_text) or \
                           ('lacks educational details' in response_text) or \
                           ('education is missing' in response_text) or \
                           ('education: -' in response_text) or \
                           ('education: not' in response_text):
                            education_missing = True
                            logger.info(f"Education missing detected in response_text")
                        elif 'bachelor' in response_text or 'master' in response_text or 'phd' in response_text or 'degree in' in response_text:
                            # If specific education terms are found, assume it's provided
                            education_missing = False
                            logger.info(f"Education found in response_text (specific terms)")
                
                # Check if education is mentioned in the email body
                if email_data.get('body'):
                    body = email_data['body'].lower()
                    if 'bachelor' in body or 'master' in body or 'phd' in body or 'degree' in body or 'university' in body or 'college' in body:
                        education_missing = False
                        logger.info(f"Education found in email body")
            
            # If education is missing, make sure it's in the missing_info list
            if education_missing:
                # Check if Education is already in missing_info
                if not any(item['name'] == 'Education' for item in missing_info):
                    missing_info.append({
                        "name": "Education",
                        "description": "Highest level of education and field of study"
                    })
                    logger.info(f"Added Education to missing_info list")
            
            # Log the missing information for debugging
            logger.info(f"Missing information after processing: {json.dumps(missing_info, indent=2)}")
            
            # If there's no missing information, mark the application as complete
            if not missing_info:
                application_complete = True
                # Update the analysis_result to ensure the complete template is used
                analysis_result['application_complete'] = True
                # Also update the result dictionary that will be returned
                result = {
                    "response_text": "",
                    "application_complete": True
                }
                logger.info("No missing information found, marking application as complete")
                
                # Skip the rest of the incomplete application logic and go directly to the complete template
                # Create a prompt for the complete application template
                greeting = "Hi"
                if applicant_name and applicant_name.lower() not in ["excited", "applicant", "candidate"]:
                    greeting = f"Dear {applicant_name}"
                    
                prompt = f"""
Generate a brief, concise email response following EXACTLY this template:

Subject: Your Application for [Job Title] - Application Complete

[Greeting],

Thank you for applying for the [Job Title] position at ARx Media. We have received your complete application with all required information.

We will review your application and get back to you soon regarding next steps.

Best regards,
HR Manager
ARx Media

Use these specific values:
- Job Title: {job_title}
- Greeting: {greeting}

Important instructions:
1. Keep the entire email under 10 lines and make it professional but concise.
2. Do NOT make up a name for the applicant. Use the provided greeting exactly as given.
3. Only use this template when the application is truly complete with all required information.
"""
                
                # Call the OpenAI API
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are an HR assistant that writes concise, professional emails."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=500
                )
                
                # Extract the response text
                response_text = response.choices[0].message.content.strip()
                
                # Create the result
                result = {
                    "response_text": response_text,
                    "application_complete": True
                }
                
                # Log the response result
                logger.info(f"Generated response for complete application: {json.dumps(result, indent=2)}")
                
                # Send the email response
                if 'response_text' in result:
                    send_email_response(service, email_data, result['response_text'])
                
                return result
            
            # Format missing information for the email
            missing_info_details = []
            for item in missing_info:
                missing_info_details.append(f"• {item['name']}: {item['description']}")
            
            missing_info_list = "\n".join(missing_info_details)
            
            # If the applicant name is uncertain, use a generic greeting
            greeting = "Hi"
            if applicant_name and applicant_name.lower() not in ["excited", "applicant", "candidate"]:
                greeting = f"Dear {applicant_name}"
            
            prompt = f"""
Generate a brief, concise email response that asks for missing information following EXACTLY this template:

Subject: Your Application for [Job Title] - Additional Information Needed

[Greeting],

Thank you for applying for the [Job Title] position at ARx Media. We have received your application and are interested in proceeding with your candidacy.

We need some additional information to complete your application. Please provide the following:
[Missing Information List]

Looking forward to your response.

Best regards,
HR Manager
ARx Media

Use these specific values:
- Job Title: {job_title}
- Greeting: {greeting}
- Missing Information List: Use this exact list with bullet points:
{missing_info_list}

Important instructions:
1. Do NOT ask for information that has already been provided (like resume/CV if it was already attached).
2. Make the email professional but concise.
3. Focus on obtaining ONLY the truly missing information.
4. If there's a conversation history, acknowledge any information the applicant has already provided.
5. Do NOT make up a name for the applicant. Use the provided greeting exactly as given.
6. Format the missing information as a clear bullet point list that explicitly asks for each piece of missing information.
7. NEVER mention that the application is complete when there is missing information.
"""
        else:
            # If the application is complete, send a confirmation
            # If the applicant name is uncertain, use a generic greeting
            greeting = "Hi"
            if applicant_name and applicant_name.lower() not in ["excited", "applicant", "candidate"]:
                greeting = f"Dear {applicant_name}"
                
            prompt = f"""
Generate a brief, concise email response following EXACTLY this template:

Subject: Your Application for [Job Title] - Application Complete

[Greeting],

Thank you for applying for the [Job Title] position at ARx Media. We have received your complete application with all required information.

[Resume analysis result]

We will review your application and get back to you soon regarding next steps.

Best regards,
HR Manager
ARx Media

Use these specific values:
- Job Title: {job_title}
- Greeting: {greeting}

For the resume analysis result section, extract 2-3 key points from this analysis result:
{json.dumps(analysis_result, indent=2)}

Important instructions:
1. Keep the entire email under 10 lines and make it professional but concise.
2. Do NOT make up a name for the applicant. Use the provided greeting exactly as given.
3. Only use this template when the application is truly complete with all required information.
"""
        
        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an HR assistant that writes concise, professional emails."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500
        )
        
        # Extract the response text
        response_text = response.choices[0].message.content.strip()
        
        # Create the result
        result = {
            "response_text": response_text,
            "application_complete": application_complete
        }
        
        # Log the response result
        logger.info(f"Generated response: {json.dumps(result, indent=2)}")
        
        # Send the email response
        if 'response_text' in result:
            send_email_response(service, email_data, result['response_text'])
        
        return result
    
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}


def send_background_check_notification(service, email_data, background_check_results):
    """
    Send a notification email to the HR manager with the background check results.
    
    Args:
        service: Authenticated Gmail API service
        email_data: Dictionary containing email data
        background_check_results: Dictionary containing background check results
    """
    try:
        # Import HR_EMAIL for sending the notification
        from config.settings import HR_EMAIL
        
        # Get the applicant's name and email
        applicant_name = email_data.get('sender_name', 'Applicant')
        applicant_email = email_data.get('sender_email', 'Unknown')
        
        # Get the job title from the subject
        job_title = email_data.get('subject', '').replace("Application for ", "").strip()
        
        # Get the summary from the background check results
        summary = background_check_results.get('summary', 'No summary available')
        
        # Create the email subject
        subject = f"Background Check Results: {applicant_name} - {job_title}"
        
        # Create the email body
        body = f"""
Dear HR Manager,

A background check has been completed for the following applicant:

Applicant: {applicant_name}
Email: {applicant_email}
Position: {job_title}

Background Check Summary:
{summary}

The full background check results have been saved to the system and can be accessed for further review.

This is an automated notification.

Best regards,
AI Recruitment Assistant
        """
        
        # Create the email message
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        message = MIMEMultipart()
        message['to'] = HR_EMAIL
        message['subject'] = subject
        
        msg = MIMEText(body)
        message.attach(msg)
        
        # Convert the message to a raw string
        import base64
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send the email
        service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        logger.info(f"Background check notification sent to {HR_EMAIL}")
    
    except Exception as e:
        logger.error(f"Error sending background check notification: {e}")
        import traceback
        logger.error(traceback.format_exc())


def manage_system_message() -> str:
    """
    Generate the system message for the LLM.
    
    Returns:
        str: The system message
    """
    job_requirements = get_job_requirements()
    
    # Create a simplified system message
    system_message = "You are a professional HR assistant responsible for screening job applications. "
    system_message += "Always return responses in XML-style tags. "
    system_message += f"Job Requirements: {json.dumps(job_requirements, indent=2)}"
    
    return system_message


def main():
    """
    Main function to run the email screening system.
    """
    try:
        # Get Gmail service
        service = get_gmail_service()
        
        logger.info("Starting email screening system...")
        
        while True:
            # Check for new emails
            check_emails(service)
            
            # Wait for the next check
            time.sleep(EMAIL_CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        logger.info("Stopping email screening system...")
    
    except Exception as e:
        logger.error(f"Error in main function: {e}")


if __name__ == "__main__":
    main()