# app/services/job_post/upload_jd/uplod_job_post.py

import os
import re
import json
import base64
import asyncio
import hashlib
import asyncio
import traceback
import redis.asyncio as redis

from io import BytesIO
from docx import Document
from datetime import datetime
from agents import Agent, Runner

from typing import Dict, Union, Any
from pdf2image import convert_from_bytes
from fastapi import UploadFile, File, HTTPException, status
 
from app.config.app_config import AppConfig
# removed unused imports: fitz and compute_json_hash
from app.prompts.extract_jd_prompt import prompt_template
from app.services.job_post.upload_jd.base import BaseUploadJobPost
 
settings = AppConfig()
 
class UploadJobPost(BaseUploadJobPost):
    """
    Handles the extraction of job details from PDF and DOCX files using an LLM agent
    and a Redis cache to avoid redundant API calls.
    """
    def __init__(self, redis_store: redis.Redis):
        """Initializes the service with a Redis client instance."""
        self.redis_store = redis_store

    def create_agent(self) -> Union[Agent, Dict]:
        """Initializes and returns the LLM agent by setting the OPENAI_API_KEY environment variable."""
        try:
            os.environ['OPENAI_API_KEY'] = settings.openai_api_key
            return Agent(
                name="JD Extractor",
                instructions=prompt_template,
            )
        except Exception as e:
            error_str = str(e)
            if "api key" in error_str.lower() or "authentication" in error_str.lower() or "unauthorized" in error_str.lower():
                return {"error": "LLM API key is invalid or unauthorized. Please check your credentials."}
            return {"error": "we "}
 
    def extract_text_from_docx(self, docx_bytes: bytes) -> str:
        """Extracts text content from a DOCX file."""
        try:
            docx_stream = BytesIO(docx_bytes)
            doc = Document(docx_stream)
            text_content = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text_content.append(cell.text.strip())
            full_text = "\n".join(text_content)
            if full_text.strip():
                return full_text

            else:
                return None

        except Exception as e:
            return None
 
    async def extract_job_details_with_text(self, text_content: str) -> Dict:
        """Processes text content with the LLM agent."""
        agent = self.create_agent()
        if isinstance(agent, dict) and 'error' in agent:
            return agent
        try:
            result = await Runner.run(agent, [{"role": "user", "content": f"Extract complete job description with skills and their weightage from the following text:\n\n{text_content}"}])
            if not result.final_output:
                return { "error": "We couldn’t extract job details from the text content. Please check the file and try again."}

            json_match = re.search(r'```(?:jsonc?|)\n(.*)```', result.final_output, re.DOTALL)

            json_string = json_match.group(1).strip() if json_match else result.final_output.strip()

            try:

                return json.loads(json_string)

            except json.JSONDecodeError as e:
                return {"error": "Failed to parse extracted job details."}

        except Exception as e:

            error_str = str(e)
            if "429" in error_str and "insufficient_quota" in error_str:

                return {"error": "Our extraction limit has been reached. Please try again in a few minutes."}

            if "api key" in error_str.lower() or "authentication" in error_str.lower() or "unauthorized" in error_str.lower():

                return {"error": "LLM API key is invalid or unauthorized. Please check your credentials."}

            return {"error": "Failed to extract job details."}

 
    async def extract_job_details_with_agent_image(self, file_content: bytes) -> Dict:

        """Converts a PDF to images and processes with the LLM agent."""
        print(f"[INFO] Processing PDF. Converting to images for LLM analysis.")
        try:
            images = convert_from_bytes(file_content, poppler_path=r"C:\Users\gomathishanmugam\Downloads\poppler-25.07.0\Library\bin", fmt="jpeg", dpi=200)
        except Exception as e:
            print(f"[ERROR] PDF to image conversion failed: {e}")
            return {"error": "We couldn’t read the uploaded PDF. Please ensure the file is not corrupted and try again."}

        total_pages = len(images)
        if total_pages > settings.max_pdf_pages:
            print(f"[WARN] PDF has {total_pages} pages which exceeds the maximum allowed {settings.max_pdf_pages} pages.")
            return {"error": "The uploaded PDF exceeds the page limit, Please upload a smaller file with minimum of 3 pages."}

        if not images:
            print(f"[WARN] No images extracted from PDF.")
            return {"error": "We couldn’t extract any readable content from your PDF. Please check the file and try again."}

        agent = self.create_agent()

        if isinstance(agent, dict) and 'error' in agent:
            return {"error": "We’re having trouble setting up the extraction service. Please try again later."}

        all_results = []

        for i, image in enumerate(images):

            buffer = BytesIO()

            image.save(buffer, format="JPEG", optimize=True)

            image_url = f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode()}"

            try:
                print(f"[INFO] Calling agent for PDF page {i+1}.")
                result = await Runner.run(agent, [{"role": "user", "content": [

                    {"type": "input_image", "image_url": image_url},

                    {"type": "input_text", "text": "Extract the complete job description with skills and their weightage from this image. Output ONLY a valid JSON object. Do not include any text, explanations, or markdown code fences."}

                ]}], timeout = 45)

                if not result.final_output:
                    print(f"[WARN] Agent returned empty output for PDF page {i+1}. Skipping.")
                    continue

                json_match = re.search(r'```(?:jsonc?|)\n(.*)```', result.final_output, re.DOTALL)

                json_string = json_match.group(1).strip() if json_match else result.final_output.strip()

                parsed_data = json.loads(json_string)

                if isinstance(parsed_data, dict):

                    all_results.append(parsed_data)

            except asyncio.TimeoutError:
                print(f"[WARN] Page {i+1} processing timed out.")
                continue

            except Exception as e:

                error_str = str(e)
                print(f"[ERROR] Agent call for page {i+1} failed. Error: {e}")
                if "429" in error_str and "insufficient_quota" in error_str:
                    return {"error": "Our extraction limit has been reached. Please try again in a few minutes."}


                if "api key" in error_str.lower() or "authentication" in error_str.lower() or "unauthorized" in error_str.lower():
                    return {"error": "There was an issue connecting to the extraction service. Please try again shortly."}

                return {"error": "Something went wrong while processing the file. Please try again later."}


        if not all_results:
            print(f"[WARN] No valid data extracted from any PDF page.")
            return {"error": "We couldn’t extract job details from the uploaded document. Please check the content and try again."}

        merged_result = {}

        for page_json in all_results:

            if isinstance(page_json, dict):

                for key, value in page_json.items():

                    if key not in merged_result:

                        merged_result[key] = value

                    elif isinstance(value, list) and isinstance(merged_result[key], list):

                        merged_result[key].extend(value)

                    elif isinstance(value, str) and isinstance(merged_result[key], str):

                        merged_result[key] += " " + value

        print(f"[INFO] Merged results from all PDF pages successfully.")
        return merged_result
 
    async def job_details_file_upload(self, file: UploadFile = File(...)) -> Dict:
        """
        The main function to handle job description file uploads.
        It checks the cache before performing expensive extraction.
        
        NOTE: job_id is intentionally NOT accepted here as it's not used in caching or extraction.
        """
        print(f"[INFO] Starting JD upload and extraction.")

       
        try:
            file_content = await file.read()
        except Exception:
            return {"error": "Please upload a proper job description file (PDF or DOCX)"}
        
        if len(file_content) == 0:
            return {"error": "Empty file uploaded. Please upload a valid job description file."}

        file_hash = hashlib.sha256(file_content).hexdigest()
        print(f"[INFO] Generated hash for file: {file_hash}")
        
        # 2. Check the cache for the hash
        try:
            cached_data = await self.redis_store.hgetall(file_hash)
            if cached_data:
                print(f"[INFO] Cache hit for hash '{file_hash}'.")
                cached_content = cached_data.get("extracted_content")
                
                if cached_content is not None:
                    # Safely decode if it's bytes, otherwise assume it's a string
                    if isinstance(cached_content, bytes):
                         cached_content = cached_content.decode('utf-8')
                         
                    print(f"[INFO] Returning cached job details.")
                    return {"job_details": json.loads(cached_content)}
                else:
                    print(f"[WARN] Cached data for hash '{file_hash}' is missing 'extracted_content'. Re-processing.")
        
        except Exception as e:
            print(f"[ERROR] Redis cache lookup failed (Critical exception during retrieval): {e}")
            # The function will proceed to the LLM extraction path.

        print(f"[INFO] Cache miss for hash '{file_hash}'. Proceeding with LLM extraction.")
        
        file_type = file.content_type

        job_details = None
 
        if file_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':

            if(len(file_content) > settings.max_file_size_docx):
                return {"error": "The uploaded DOCX file exceeds the maximum allowed size of 5 MB. Please upload a smaller file."}

            text_content = self.extract_text_from_docx(file_content)

            if not text_content:

                return {"error": "We couldn’t extract details from the uploaded file. Please make sure it’s a clear and readable job description (PDF or DOCX) and try again."}

            job_details = await self.extract_job_details_with_text(text_content)

        elif file_type == 'application/pdf':

            if(len(file_content) > settings.max_file_size_pdf):

                return {"error": "The uploaded PDF file exceeds the maximum allowed size of 10 MB. Please upload a smaller file."}
            
            job_details = await self.extract_job_details_with_agent_image(file_content)

        else:
            print(f"[ERROR] Unsupported file type: {file_type}.")
            return {"error": "Unsupported file type. Please upload your job description as a PDF or DOCX file."}
 
        if job_details and "error" in job_details:
            return {"error": "We couldn’t process the job description right now. Please upload a clear and readable JD file (PDF or DOCX) and try again later."}
 
        if not job_details:
            print("[ERROR] Final job details extraction failed. Check the file content.")
            return {"error": "We couldn’t process the job description right now. Please try again later."}
 
        if isinstance(job_details, dict) and job_details.get("job_description"):
            job_details['job_description'] = job_details['job_description'].replace('\n', ' ')
        
        # 3. Store the successful result in the cache
        try:
            hash_data = {
                "file_name": file.filename,
                "extracted_content": json.dumps(job_details),
                "timestamp": str(datetime.now())
            }
            await self.redis_store.hset(file_hash, mapping=hash_data)
            print(f"[INFO] Stored new job details in cache for hash: {file_hash}")
        except Exception as e:
            print(f"[ERROR] Failed to store data in Redis cache: {e}")
            pass # Failed to store in Redis, but we still return the successful result
        
        print("[INFO] Job details extracted successfully.")
        # Return a consistent dictionary format for success
        return {"job_details": job_details}