def get_no_tools_used_section() -> str:
    return f"""
[ERROR] You did not use a tool in your previous response! Please retry with a tool use.

# Reminder: Instructions for Tool Use

Tool uses are formatted using XML-style tags. The tool name is enclosed in opening and closing tags, and each parameter is similarly enclosed within its own set of tags. Here's the structure:

<tool_name>
<parameter1_name>value1</parameter1_name>
<parameter2_name>value2</parameter2_name>
...
</tool_name>

For example:

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

Always adhere to this format for all tool uses to ensure proper parsing and execution.

# Next Steps

If you have completed analyzing the email, use the conversation_manager tool to generate a response.
If you need to classify an email, use the classification tool.
If you need to analyze a resume, use the resume_analyzer tool.
Otherwise, proceed with the next step of the task.
(This is an automated message, so do not respond to it conversationally.)
"""