def get_job_requirements():
    """
    Define the requirements for job applications
    
    Returns:
        dict: Dictionary containing job requirements
    """
    return {
        "required_information": [
            {
                "name": "Full Name",
                "description": "Applicant's complete name (first and last name)"
            },
            {
                "name": "Email Address",
                "description": "Valid email address for communication"
            },
            {
                "name": "Phone Number",
                "description": "Valid phone number"
            },
            {
                "name": "Resume/CV",
                "description": "Detailed resume or CV as an attachment"
            },
            {
                "name": "Work Experience",
                "description": "Any work experience"
            },
            {
                "name": "Education",
                "description": "Highest level of education and field of study"
            },
            # {
            #     "name": "Project",
            #     "description": "Project that you have worked on that aligns with the job requirements"
            # }
        ],
        "optional_information": [
            {
                "name": "Portfolio",
                "description": "Link to online portfolio or work samples"
            },
            {
                "name": "LinkedIn Profile",
                "description": "Link to LinkedIn profile"
            },
            {
                "name": "GitHub Profile",
                "description": "Link to GitHub profile for technical positions"
            },
            {
                "name": "Cover Letter",
                "description": "Personalized cover letter explaining interest in the position"
            },
            {
                "name": "Salary Expectations",
                "description": "Expected salary range"
            },
            {
                "name": "Availability",
                "description": "Earliest start date and notice period"
            },
            {
                "name": "References",
                "description": "Professional references with contact information"
            }
        ],
        "disqualifying_factors": [
            {
                "name": "Incomplete Application",
                "description": "Missing any of the required information"
            },
            {
                "name": "Insufficient Experience",
                "description": "Less than 2 years of relevant work experience"
            },
            {
                "name": "No Resume",
                "description": "No resume or CV provided"
            }
        ]
    }