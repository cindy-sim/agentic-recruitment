# Resume Screening System

An automated system for screening job applications using XML-style tool architecture.

## System Architecture

The Resume Screening System follows a modular, event-driven architecture with XML-style tool usage for processing job applications. The system automatically checks for new emails, classifies them, processes resumes, analyzes requirements, and maintains conversations with applicants until all required information is collected.

### Key Components

1. **Email Monitoring**
   - Checks for new emails every 60 seconds using the Gmail API
   - Automatically filters out emails from the HR manager
   - Marks processed emails to avoid duplicate processing

2. **Email Classification**
   - Uses OpenAI's GPT-3.5 model to determine if an email is a job application
   - Ignores non-job application emails
   - Processes job applications for further analysis

3. **Resume Processing**
   - Converts PDF attachments to images using pdf2image
   - Extracts text from images using the vision_to_json tool
   - Logs extracted content for monitoring

4. **Requirements Analysis**
   - Analyzes applications against predefined job requirements
   - Uses OpenAI's GPT-4 model to determine if all required information is present
   - Identifies missing information if requirements are not met

5. **Response Generation**
   - Sends confirmation emails when all requirements are met
   - Requests specific missing information when requirements are not met
   - Maintains conversation threads for future responses

6. **Conversation Loop**
   - Processes new responses from applicants
   - Combines new information with previous conversation history
   - Re-analyzes applications to check if all requirements are now met

7. **Thread Management**
   - Maintains active conversation threads in memory
   - Removes complete applications from active tracking
   - Saves conversation history to files for persistence

### XML-Style Tool Architecture

The system uses a structured XML approach for tool invocation:

1. **Tag-Based Tool Invocation**
   ```xml
   <tool_name>
   <parameter1_name>value1</parameter1_name>
   <parameter2_name>value2</parameter2_name>
   </tool_name>
   ```

2. **Available Tools**
   - **classification**: Determines if an email is a job application
   - **resume_analyzer**: Analyzes job applications against requirements
   - **conversation_manager**: Manages conversations with applicants
   - **vision_to_json**: Extracts text from images using vision models

3. **Response Processing**
   - Tool responses are extracted using BeautifulSoup
   - Different handling for different tool responses
   - Thinking tags are removed from final output

## Setup Instructions

### Prerequisites

- Python 3.8+
- Poppler (for PDF conversion)
- Gmail API credentials
- OpenAI API key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/resume-screening.git
   cd resume-screening
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Set up environment variables**
   Create a `.env` file in the root directory with the following variables:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ```

6. **Set up Gmail API credentials**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the Gmail API
   - Create OAuth 2.0 credentials
   - Download the credentials JSON file and save it as `client_secret_*.apps.googleusercontent.com.json` in the root directory

7. **Install Poppler**
   - Windows: Download from [poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases/)
   - macOS: `brew install poppler`
   - Linux: `apt-get install poppler-utils`

8. **Update Poppler path**
   - Open `main.py`
   - Update the `POPPLER_PATH` variable with the path to your Poppler installation

### Running the System

```bash
python main.py
```

The first time you run the system, it will open a browser window for Gmail authentication. After authentication, the system will start checking for new emails every 60 seconds.

## Configuration

### Job Requirements

You can customize the job requirements by editing the `config/job_requirements.py` file. The requirements are divided into three categories:

1. **Required Information**: Information that must be provided by the applicant
2. **Optional Information**: Information that is not required but may be helpful
3. **Disqualifying Factors**: Factors that would disqualify an application

### Email Settings

You can customize the email settings by editing the `config/settings.py` file:

- `EMAIL_CHECK_INTERVAL`: How often to check for new emails (in seconds)
- `HR_EMAIL`: Email address of the HR manager to filter out
- `CLASSIFICATION_MODEL`: OpenAI model to use for email classification
- `ANALYSIS_MODEL`: OpenAI model to use for resume analysis

## Logs and Data

- Logs are stored in the `logs` directory
- Processed emails are tracked in `data/processed_emails.json`
- Conversation history is stored in `data/conversation_cache`
- Attachment images are stored in `data/attachment_images`

## Architecture Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Email Checking │────▶│ Classification  │────▶│ Resume Processing│
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│Thread Management│◀────│Response Generation◀────│Requirements Analysis
└─────────────────┘     └─────────────────┘     └─────────────────┘
         │                      ▲
         │                      │
         ▼                      │
┌─────────────────┐             │
│Conversation Loop│─────────────┘
└─────────────────┘