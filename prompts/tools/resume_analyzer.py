def get_resume_analyzer_tool_description() -> str:
    return """
## resume_analyzer
Description: This tool is used to analyze a job application and check if it meets all the requirements. It extracts information from the email and attachments, and determines if the application is complete or if additional information is needed.
Parameters:
- email_data: (required) A dictionary containing email data with the following keys:
  - sender_name: The name of the sender
  - sender_email: The email address of the sender
  - subject: The subject of the email
  - body: The body of the email
  - attachments: A list of attachment dictionaries
- conversation_history: (optional) A list of previous conversation messages
Usage:
<resume_analyzer>
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
<conversation_history>
[
  {
    "role": "applicant",
    "content": "Dear Hiring Manager,\\n\\nI am writing to apply for the Software Engineer position at your company.\\n\\nSincerely,\\nJohn Doe"
  },
  {
    "role": "system",
    "content": "Thank you for your interest in the position.\\n\\nWe need some additional information to complete your application:\\n\\n- Phone Number\\n\\nPlease reply to this email with the requested information."
  }
]
</conversation_history>
</resume_analyzer>
"""