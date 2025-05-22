def get_vision_to_json_tool_description():
    """
    Returns the description for the vision_to_json tool.
    
    Returns:
        str: The tool description.
    """
    return """
## vision_to_json

The vision_to_json tool allows you to analyze images using OpenAI's vision capabilities and extract structured information in JSON format.

### Parameters:
- `image_data` (required): Base64-encoded image data, a file path, or a URL to the image.
- `schema` (optional): A JSON schema that defines the structure of the output.
- `prompt` (optional): A custom prompt to guide the vision model in extracting specific information.

### Example:
```xml
<vision_to_json>
    <image_data>/data/attachment_images/image.jpg</image_data>
    <schema>
    {
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
    </schema>
    <prompt>Analyze this image and extract information about the person and the location.</prompt>
</vision_to_json>
```

### Response:
```xml
<vision_json_result>
    <status>success</status>
    <json_data>
        {
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
    </json_data>
</vision_json_result>
```

Use this tool to Analyze this resume image and extract personal information, education, work experience, skills, and certifications in the specified structure.
"""