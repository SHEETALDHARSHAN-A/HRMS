# app/modules/service/Analyze_JD/analyze_jd_service.py
 
import os
import re
import json

from agents import Agent, Runner
from fastapi import HTTPException, status
from typing import List, Dict, Any, Union

from app.config.app_config import AppConfig
from app.schemas.analyze_jd_request import AnalyzeJdRequest
from app.services.job_post.analyze_jd.base import BaseAnalyzeJD
from app.prompts.analyze_jd_prompt import output_structure, prompt_content
 
settings = AppConfig()
 
class AnalyzeJobPost(BaseAnalyzeJD):
    """
    Service responsible for validating job details and invoking the LLM Agent
    directly to extract skill analysis.
    """
    def __init__(self):
        print(f"[INFO] AnalyzeJobPost service initialized.")
        pass
       
    def _create_agent(self) -> Union[Agent, Dict]:
        """Initializes the LLM agent using the configured API key and static prompt."""
        try:
            # Set the environment variable for the LLM SDK/Agent
            os.environ['OPENAI_API_KEY'] = settings.openai_api_key
            print(f"[DEBUG] LLM API key set successfully.")
           
            # The base prompt (PROMPT_CONTENT) is used as the agent's core instructions.
            return Agent(
                name="JD Analyzer",
                instructions=prompt_content,
            )
        except Exception as e:
            print(f"[FATAL] Failed to create LLM agent: {e}")
            return {"error": "Failed to initialize LLM agent."}
 
    async def _get_recommended_skills(self, job_title: str, job_description: str) -> List[Dict[str, Any]]:
        """
        Invokes the Agent Runner asynchronously to get skills, parses the JSON output,
        and extracts the 'recommended_skills' list.
        """
       
        agent = self._create_agent()
        if isinstance(agent, dict) and 'error' in agent:
            print(f"[ERROR] Agent creation failed: {agent['error']}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="we encountered an issue initializing the analysis")
 
        # Format the final prompt with job details and the required output structure
        final_prompt = prompt_content.format(
            output_structure=output_structure,
            job_title=job_title,
            job_description=job_description
        )
        print(f"[INFO] Running Agent for job title: {job_title}")
 
        try:
            result = await Runner.run(agent, [{"role": "user", "content": final_prompt}])
           
            if not result.final_output:
                print("[WARN] Agent returned an empty output.")
                raise ValueError("Agent returned an empty output.")
           
            # Extract JSON from markdown fence (robust parsing)
            json_match = re.search(r'```(?:jsonc?|)\n(.*)```', result.final_output, re.DOTALL)
            json_string = json_match.group(1).strip() if json_match else result.final_output.strip()
           
            print(f"[DEBUG] Raw JSON output received. Attempting parse.")
            llm_output_dict = json.loads(json_string) # Parses the dictionary: {"recommended_skills": [...]}
 
            # FIX: Extract the list from the dictionary key
            recommended_skills_list = llm_output_dict.get("recommended_skills")
 
            if recommended_skills_list is None or not isinstance(recommended_skills_list, list):
                 print(f"[ERROR] LLM output missing or invalid 'recommended_skills' list.")
                 raise ValueError("LLM analysis output is missing the required skill list.")
           
            return recommended_skills_list # Return only the list of skills
 
        except (ValueError, json.JSONDecodeError, Exception) as e:
            print(f"[ERROR] Agent run or JSON parsing failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Agent analysis failed. Error: {e}"
            )
   
    async def analyze_job_details(self, job_details: AnalyzeJdRequest) -> Dict[str, Any]:
        """
        Performs validation and orchestrates the skill extraction.
        """
       
        print(f"[INFO] Starting analysis for '{job_details.job_title}'.")

        if len(job_details.job_title.strip()) < 3:
            raise HTTPException(400, "Job title must be at least 3 characters long.")

        invalid_placeholders = {"string", "test", "sample", "na", "none"}

        if job_details.job_description.strip().lower() in invalid_placeholders or job_details.job_title.strip().lower() in invalid_placeholders:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job description or title appears invalid. Please provide meaningful content."
            )


       
        # --- Validation Logic (Preserved) ---
        if len(job_details.job_description.strip()) < 200:
            print(f"[ERROR] Validation Failed: Job description length < 200.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job description must be at least 200 characters long.")
 
        if not job_details.job_title:
            print(f"[ERROR] Validation Failed: Job title is missing.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job title is required.")
        
        if len(job_details.job_title) > 50:
            print(f"[ERROR] Validation Failed: Job title length > 50.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job title must not exceed 50 characters.")

        if job_details.job_title.isnumeric():
            print(f"[ERROR] Validation Failed: Job title is numeric.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job title must contain alphabetic characters.")

        if not re.match(r'^[\w\s\-\.,&()]+$', job_details.job_title):
            print(f"[ERROR] Validation Failed: Job title contains invalid characters.")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job title contains invalid characters.")

        
        
      
        # --- Core Execution ---
       
        recommended_skills = await self._get_recommended_skills(
            job_title=job_details.job_title,
            job_description=job_details.job_description
        )
       
        print(f"[INFO] Successfully received {len(recommended_skills)} recommended skills.")
       
        return {
            "job_title": job_details.job_title,
            "job_description": job_details.job_description,
            "recommended_skills": recommended_skills
        }
 