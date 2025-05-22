def getSharedToolUseSection() -> str:
    return """
====
TOOL USE

You have access to a set of tools that are executed upon the user's approval. You can use one tool per message, and will receive the result of that tool use in the user's response. You use tools step-by-step to accomplish a given task, with each tool use informed by the result of the previous tool use.

# Tool Use Formatting

Tool use is formatted using XML-style tags. The tool name is enclosed in opening and closing tags, and each parameter is similarly enclosed within its own set of tags. Here's the structure:

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

Always adhere to this format for the tool use to ensure proper parsing and execution."""