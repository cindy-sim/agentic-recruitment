def get_classification_tool_description() -> str:
    return """
## classification
Description: This tool is used to classify if an email is a job application. It analyzes the email subject, content, and attachments to determine if it's a job application.
Parameters:
- email_data: (required) A dictionary containing email data with the following keys:
  - sender_name: The name of the sender
  - sender_email: The email address of the sender
  - subject: The subject of the email
  - body: The body of the email
  - attachments: A list of attachment dictionaries
Usage:
<classification>
<email_data>
{
  "sender_name": "John Doe",
  "sender_email": "john.doe@example.com",
  "subject": "Job Application for Software Engineer Position",
  "body": "Dear Hiring Manager,\\n\\nI am writing to apply for the Software Engineer position at your company.\\n\\nSincerely,\\nJohn Doe",
  "attachments": [
    {
      "filename": "resume.pdf",
      "content_type": "application/pdf"
    }
  ]
}
</email_data>
</classification>
"""