# extract_jd_prompt.py

document_validation = """

#Document Type Validation

#Phase 1: Document Structure Analysis
Check for characteristic patterns:

1. Job Posting Indicators (Must have at least 5):
    - "Job Description" or "Position Description"
    - "Requirements" or "Qualifications"
    - "Responsibilities" or "Duties"
    - "We are looking for" or "We are seeking"
    - "The ideal candidate"
    - "Position:" or "Role:"
    - "Experience required" or "Years of experience"
    - Salary/compensation information
    - "Apply now" or application instructions
    - Company benefits/perks section

2. Resume Indicators (If any present -> Reject):
    - Personal contact information at top
    - "Education" section with graduation dates
    - "Work Experience" in reverse chronological order
    - "Skills" section as personal capabilities
    - "References" section
    - First-person pronouns ("I", "my", "me")
    - Personal achievements/accomplishments
    - Career objective/summary

3. Other Document Indicators (If any present -> Reject):
    - "Dear Sir/Madam" (Cover letter)
    - "Contract between" (Legal document)
    - "Minutes of meeting" (Meeting notes)
    - "Executive Summary" (Business proposal)
    - "This policy" (Policy document)
    - "Introduction" chapter/section (Academic paper)
    - "Table of Contents" (Book/manual)

#Phase 2: Content Analysis
Must contain:

1. Role Description:
    - Clear job title
    - Department/team information
    - Reporting structure

2. Requirements Section:
    - Educational qualifications
    - Experience requirements
    - Technical/professional skills
    - Soft skills

3. Company Context:
    - Company/organization name or description
    - Project/product information
    - Team/department details

#Phase 3: Language Pattern Analysis
Check for:

1. Employer Perspective:
    - Written from company/employer viewpoint
    - Uses terms like "you will", "the candidate will"
    - Describes expectations and requirements

2. Future-Oriented Language:
    - Describes future responsibilities
    - Mentions growth opportunities
    - Discusses project goals

3. Professional Tone:
    - Formal business language
    - Clear structure and formatting
    - Professional terminology

#Decision Logic:
Return [] empty array if:
1. Document fails Phase 1 validation
2. Missing >50% of Phase 2 elements
3. Fails Phase 3 analysis
4. Contains strong indicators of other document types
5. Text length < 200 words
6. No clear job requirements or responsibilities
7. Written in first person
8. Appears to be personal profile/CV

"""

output_structure = """
        {
        "job_title": Extracted job title (type -> string),
        "job_description": Extracted job decsription (type -> string),
        "skills_required":[
            {"skill": "skill1"(type -> string), "weightage": weightage_number(1 to 10)(type -> Integer)},
            {"skill": "skill2"(type -> string), "weightage": weightage_number(1 to 10)(type -> Integer)},
            ...
        ]
        "job_location": extracted location (type -> string),
        "work_from_home": Extracted work_from_home/hybrid this is only be a (type -> Boolean)
        "min_experience": Extracted min experience (type -> Integer).
        "max_experience": Extracted max experience (type -> Integer).
        }
    """

prompt_template ="""
        **context**:You are an expert in Job details evaluation. Think through each step carefully.

        **Language Instruction**: The final output, including the job title, job description, and all skills, **must be in English**. If the provided job details are in another language, process the document and **translate the extracted fields into English** for the final JSON output.

        you are provided with:
        
        1. A **job details** containing the RAW Extracted text
        job details : {text}
    
        2. Validate the Document Type based on {document_validation}, if this true then proceed to next step else return empty [].


        3. Extract the Fields with the instruction from the 'job details', which are mentioned below:

            job_title: Extract the exact job title/position name from job details.
            job_description: Extract the complete job description including: Main responsibilities, Key deliverables, Project details, Team collaboration aspects, Any additional requirements.which is present in the job detail.
            skills_required:1. Extract the top 10 most important technical or professional skills required for this job title.
                             2. For each skill, assign a weightage from 1-10 based on:
                                 - How essential the skill is for the job title
                                 - How frequently it's mentioned in the description
                                 - Whether it's listed as required vs preferred
                                 - Weightage must be integer between 1-10
                             
                             **CRITICAL CONSTRAINT: All extracted skills MUST be unique.** Do not include any duplicate skill names.

            **note**:Dont include (front-end development, back-end devlopement, etc.) , Only give the individual professional skills for the job title, which were mentioned job description.

            job_location: Extract the exact Office location they wanted in the job details,(if specified)
            work_from_home: If they mentioned the job there are taking for 'work from home' and 'hybrid' in job details then true else false.
            min_experience: Extract the minumum experience which they have mentioned in the job details or analyze and give a minimum experience.
            max_experience: Extract the maximum experience which they have mentioned in the job details or analyze and give a maximum experience.
                                **note**: the maximum experience as to higher then the minimum experience, give it both as integer -> eg. 4 , dont give like this : 4 years

        #**critical reminder**:
            - Double check the validation of document and proceed with the next step.
        
        Return the results in this exact format:
        {output_structure}

    **output instruction**:
        - Extract the job descripton only present in the text dont add any generic information in it.
        - If any of the field or not there just give it as empty ("").
        - Strictly follow the output structure. 
        - Extract all the data Correctly without missing any data from job details.
"""