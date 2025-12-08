# app/prompts/analyze_jd_prompt.py

output_structure = """
{
    "recommended_skills": [
        {"skill": "skill_name1", "weightage": weightage_number(0 to 10)},
        {"skill": "skill_name2", "weightage": weightage_number(0 to 10)},
        ...
    ]
}
"""

prompt_content = """
Analyze the following job description and provide a list of recommended skills.

**Output Structure & Requirements:**
1. **List of Skills:** Extract the top 10 most important technical or professional skills required for this position.
2. **Weightage:** For each skill, assign a weightage from 1-10 based on:
    - How essential the skill is for the job title
    - How frequently it's mentioned in the description
    - Whether it's listed as required vs preferred

**Rules:**
- Only include specific, concrete skills (e.g., "Python", "Project Management", "AWS").
- Exclude generic traits which are not directly align with the job title (e.g., "team player").
- If no specific skills found, the `recommended_skills` array should be an empty list `[]`.
- Maximum 10 skills.
- Weightage must be an integer between 1 and 10.

Return the results in this **exact JSON object format**:
{output_structure}

Job Title: {job_title}
Job Description: {job_description}
"""
