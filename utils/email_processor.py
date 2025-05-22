import os
import base64
import logging
import json
import pickle
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from config.settings import (
    GMAIL_CREDENTIALS_FILE,
    GMAIL_TOKEN_FILE,
    GMAIL_SCOPES,
    HR_EMAIL
)

# Configure logging
logger = logging.getLogger(__name__)

def get_gmail_service():
    """
    Authenticate and create a Gmail API service.
    
    Returns:
        service: Authenticated Gmail API service
    """
    creds = None
    if os.path.exists(GMAIL_TOKEN_FILE):
        with open(GMAIL_TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                GMAIL_CREDENTIALS_FILE, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(GMAIL_TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('gmail', 'v1', credentials=creds)

def extract_email_data(msg):
    """
    Extract data from an email message.
    
    Args:
        msg: Email message data from Gmail API
    
    Returns:
        dict: Extracted email data
    """
    try:
        message_id = msg['id']
        thread_id = msg['threadId']
        
        # Extract headers
        headers = msg['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        from_header = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
        
        # Parse sender information
        if '<' in from_header and '>' in from_header:
            sender_name = from_header.split('<')[0].strip()
            sender_email = from_header.split('<')[1].split('>')[0].strip()
        else:
            sender_name = 'Unknown'
            sender_email = from_header
        
        # Extract email body
        body = ''
        
        def get_body_from_part(part):
            """Helper function to extract body text from a message part"""
            if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            elif part.get('mimeType') == 'text/html' and 'data' in part.get('body', {}):
                # For HTML parts, we could use a HTML parser to extract text
                # For now, just decode it as is
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            elif 'parts' in part:
                # Recursively check nested parts
                for subpart in part['parts']:
                    body_text = get_body_from_part(subpart)
                    if body_text:
                        return body_text
            return None
        
        # Try to get body from payload parts
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                body_text = get_body_from_part(part)
                if body_text:
                    body = body_text
                    break
        
        # If still no body, try to get it directly from payload
        if not body and 'body' in msg['payload'] and 'data' in msg['payload']['body']:
            body = base64.urlsafe_b64decode(msg['payload']['body']['data']).decode('utf-8')
        
        # Log the body for debugging
        logger.info(f"Extracted email body (first 100 chars): {body[:100]}...")
        
        # Extract attachments
        attachments = []
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if 'filename' in part and part['filename']:
                    attachment = {
                        'filename': part['filename'],
                        'content_type': part['mimeType'],
                        'attachment_id': part['body'].get('attachmentId', '')
                    }
                    attachments.append(attachment)
        
        # Prepare email data
        email_data = {
            'sender_name': sender_name,
            'sender_email': sender_email,
            'subject': subject,
            'body': body,
            'attachments': attachments,
            'thread_id': thread_id,
            'message_id': message_id
        }
        
        return email_data
    
    except Exception as e:
        logger.error(f"Error extracting email data: {e}")
        return {}

def download_attachment(service, message_id, attachment, output_dir):
    """
    Download an email attachment.
    
    Args:
        service: Authenticated Gmail API service
        message_id: ID of the email message
        attachment: Attachment data dictionary
        output_dir: Directory to save the attachment
    
    Returns:
        str: Path to the downloaded attachment
    """
    try:
        # Download the attachment
        attachment_data = service.users().messages().attachments().get(
            userId='me',
            messageId=message_id,
            id=attachment['attachment_id']
        ).execute()
        
        file_data = base64.urlsafe_b64decode(attachment_data['data'])
        
        # Create a unique filename
        filename = f"{message_id}_{attachment['filename']}"
        file_path = os.path.join(output_dir, filename)
        
        # Save the attachment
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        logger.info(f"Downloaded attachment: {filename}")
        
        return file_path
    
    except Exception as e:
        logger.error(f"Error downloading attachment: {e}")
        return None

def send_email_response(service, email_data, response_text):
    """
    Send an email response to the applicant.
    
    Args:
        service: Authenticated Gmail API service
        email_data: Dictionary containing email data
        response_text: Text of the response
    
    Returns:
        bool: True if the email was sent successfully, False otherwise
    """
    try:
        # Create the message
        message = MIMEText(response_text)
        message['to'] = email_data['sender_email']
        message['subject'] = f"Re: {email_data['subject']}"
        
        # Encode the message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        # Send the message
        service.users().messages().send(
            userId='me',
            body={
                'raw': raw_message,
                'threadId': email_data['thread_id']
            }
        ).execute()
        
        logger.info(f"Sent response to {email_data['sender_email']}")
        return True
    
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False

def mark_as_read(service, message_id):
    """
    Mark an email as read.
    
    Args:
        service: Authenticated Gmail API service
        message_id: ID of the email message
    
    Returns:
        bool: True if the email was marked as read successfully, False otherwise
    """
    try:
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        logger.info(f"Marked email {message_id} as read")
        return True
    
    except Exception as e:
        logger.error(f"Error marking email as read: {e}")
        return False

def get_unread_emails(service):
    """
    Get unread emails.
    
    Args:
        service: Authenticated Gmail API service
    
    Returns:
        list: List of unread email messages
    """
    try:
        # Import HR_EMAIL for comparison
        from config.settings import HR_EMAIL
        
        print(f"HR_EMAIL value: {HR_EMAIL}")
        
        # Get all unread emails first to check what's available
        all_results = service.users().messages().list(
            userId='me',
            q='is:unread'
        ).execute()
        
        all_messages = all_results.get('messages', [])
        
        if all_messages:
            print(f"Found {len(all_messages)} total unread messages")
            
            # Get details for each message to check sender
            for message in all_messages:
                msg = service.users().messages().get(
                    userId='me', id=message['id'], format='full'
                ).execute()
                
                headers = msg['payload']['headers']
                from_header = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
                subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                
                print(f"Unread email from: {from_header}, Subject: {subject}")
                
                # Check if this is from HR
                if HR_EMAIL in from_header:
                    print(f"!!! HR EMAIL DETECTED IN UNREAD MESSAGES: {from_header} !!!")
        else:
            print("No unread messages found at all")
        
        # Try to get unread emails from HR specifically
        hr_query = f'is:unread from:{HR_EMAIL}'
        print(f"Searching for HR emails with query: {hr_query}")
        
        hr_results = service.users().messages().list(
            userId='me',
            q=hr_query
        ).execute()
        
        hr_messages = hr_results.get('messages', [])
        
        if hr_messages:
            logger.info(f"Found {len(hr_messages)} new messages from HR.")
            print(f"!!! FOUND {len(hr_messages)} NEW MESSAGES FROM HR !!!")
            return hr_messages
        else:
            print(f"No unread messages found from HR ({HR_EMAIL})")
        
        # If no HR emails, get all unread emails
        results = service.users().messages().list(
            userId='me',
            q='is:unread'
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            logger.info("No new messages found.")
            return []
        
        logger.info(f"Found {len(messages)} new messages.")
        return messages
    
    except Exception as e:
        logger.error(f"Error getting unread emails: {e}")
        print(f"Error getting unread emails: {e}")
        import traceback
        print(traceback.format_exc())
        return []