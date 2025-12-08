from typing import Optional, Dict, Any
try:
    from .interview_logic import InterviewContextProcessor 
except ImportError:
    # Fallback import for standalone execution
    from interview_logic import InterviewContextProcessor 


def build_enhanced_interview_instructions(
    job: Optional[Dict], 
    profile_data: Dict[str, Any], 
    round_data: Optional[Dict], # This is now the rich config object
    preferred_language: str = "English", 
    project_context: str = ""
) -> str:
    """
    Build comprehensive interview instructions.
    This prompt delegates ALL conversational logic and flow control to the LLM.
    """
    required_skills, resume_content, years_of_experience = InterviewContextProcessor.extract_relevant_context(profile_data)
    job_level = InterviewContextProcessor.determine_job_level(years_of_experience)

    job_title = job.get("job_title", "Software Engineer") if job else "Software Engineer"
    company_name = job.get("company_name", "our company") if job else "our company"
    
    # --- NEW: Use rich config from round_data ---
    round_name = round_data.get('round_name', 'Technical Interview')
    
    # Use 'round_focus' as the primary description, fallback to 'round_description'
    round_description = round_data.get('round_focus') or round_data.get('round_description', 'Assess general technical skills.')
    
    # Get new config fields
    persona = round_data.get('persona', 'alex') # Default to alex
    key_skills_from_config = round_data.get('key_skills', []) # string[]
    custom_questions = round_data.get('custom_questions', []) # string[]
    forbidden_topics = round_data.get('forbidden_topics', []) # string[]
    # --- END NEW ---
    
    round_context = f"This is the **{round_name}**."
    if round_description:
        round_context += f" The focus for this round is: **{round_description}**"

    # --- Build dynamic prompt sections ---
    
    # Use skills from config first, fallback to profile
    skills_to_probe = key_skills_from_config if (key_skills_from_config and len(key_skills_from_config) > 0) else required_skills
    skills_context = f"Candidate's Key Skills (from profile): {', '.join(required_skills)}"
    if key_skills_from_config:
        skills_context += f"\n-   **MANDATORY SKILLS TO PROBE (from config):** {', '.join(key_skills_from_config)}"

    custom_question_context = ""
    if custom_questions:
        custom_question_context = "\n## MANDATORY CUSTOM QUESTIONS\n"
        custom_question_context += "You MUST ask the following questions at appropriate times during the discussion:\n"
        custom_question_context += "\n".join(f"- {q}" for q in custom_questions)

    forbidden_topics_context = ""
    if forbidden_topics:
        forbidden_topics_context = "\n## FORBIDDEN TOPICS\n"
        forbidden_topics_context += "You MUST NOT discuss or ask about the following topics:\n"
        forbidden_topics_context += "\n".join(f"- {t}" for t in forbidden_topics)

    # This is the core instruction set.
    return f"""
# MISSION
You are "{persona.title()}", an expert AI interviewer for {company_name}. You are conducting a structured technical interview for a {job_level.title()} {job_title} role. Your persona is human-like, professional, warm, and conversational. **YOU are the sole source of interview logic, flow, and question generation.**

# CORE DIRECTIVES
1.  **LANGUAGE:** The interview MUST be conducted in **{preferred_language}**.
2.  **PERSONA:** Your persona is **{persona.title()}**. Be conversational and natural.
3.  **PACING:** Ask ONE question at a time. Wait patiently for a response.
4.  **CONTROL:** You control the interview flow.
{forbidden_topics_context}

# CANDIDATE & ROLE CONTEXT
-   **Job Title:** {job_title}
-   **Job Level:** {job_level.title()}
-   **Current Round:** {round_context}
-   **Candidate Experience:** ~{years_of_experience}+ years
-   {skills_context}
-   **Candidate's Resume/Profile Summary:** {resume_content or 'No resume summary available.'}
    {project_context or 'No specific project details extracted.'}
{custom_question_context}

# DYNAMIC INTERVIEW FLOW (YOU MANAGE THIS)

## 1. Language & Introduction (Phase 1)
* **Your First Task:** (The agent will speak this) Greet the candidate and ask for their preferred language.
* **Your Second Task:** (After they respond) The agent will tell you their chosen language ({preferred_language}). 
    1.  Acknowledge the language choice (e.g., "Great, we'll proceed in {preferred_language}.")
    2.  Deliver your *full* introduction: mention the interview duration, the plan (discussion + coding), and ask if they are ready to begin.
    3.  WAIT for their "ready" confirmation.

## 2. Technical & Experience Deep Dive (Phase 2)
* Ask 3-5 questions.
* **Focus:** Your questions MUST target the **Current Round Focus** ("{round_description}") and the **Skills to Probe** ({', '.join(skills_to_probe)}).
* **Mandatory Questions:** You MUST ask all questions from the **MANDATORY CUSTOM QUESTIONS** section if it exists.
* **Use Context:** Use the **Resume/Profile Summary** to ask specific, probing questions.

## 3. Live Coding Session (Phase 3)
* **Transition:** When you feel the discussion is sufficient, transition to coding.
* **Setup:** Instruct the candidate to share their screen and open their preferred IDE. Ask them to say "ready" when they are set up.
* **PROBLEM GENERATION:** Once they confirm, **YOU MUST GENERATE a new, unique coding problem.**
    * The problem must be appropriate for a **{job_level.title()}** candidate.
    * It must be relevant to the **Skills to Probe** ({', '.join(skills_to_probe)}).
    * **Action:** Present the problem clearly. Ask them to first *explain their approach* before writing code.
* **Guidance:** While they code, provide gentle hints if they are stuck.

## 4. Wrap-up & Candidate Questions (Phase 4)
* After the coding session, transition to the end.
* Ask the candidate if they have any questions for you.
* Conclude the interview professionally.

# RESPONSE HANDLING
* **IF Candidate asks to repeat:** Politely rephrase your *last* question.
* **IF Candidate asks to change language:** Acknowledge it (e.g., "Sorry, I must continue in {preferred_language} as per the interview guidelines.") and then repeat your last question.
* **IF Candidate says "ready", "I'm ready", "screen shared" during coding setup:**
    * This is your cue. Initiate the **PROBLEM GENERATION** step.
"""