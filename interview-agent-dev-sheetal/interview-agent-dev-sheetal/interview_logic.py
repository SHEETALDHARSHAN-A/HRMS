import re
import time
from typing import List, Dict, Any, Optional, Tuple

class InterviewContextProcessor:
    """Provides utility functions to process candidate profile data from PostgreSQL JSONB."""

    @staticmethod
    def extract_relevant_context(candidate_profile_data: Dict[str, Any]) -> Tuple[List[str], str, int]:
        """
        Extracts key elements from the 'extracted_content' JSONB field.
        We assume 'candidate_profile_data' IS the 'extracted_content' blob.
        """
        if not candidate_profile_data:
            return ['Programming', 'Problem Solving'], "No profile data provided.", 2

        match_summary = candidate_profile_data.get('summary', '')

        # Get skills. This might be a list of strings or list of objects.
        raw_skills = candidate_profile_data.get('skills', [])
        skills = []
        if raw_skills and isinstance(raw_skills, list):
            # Check if list is not empty before accessing index 0
            if raw_skills and isinstance(raw_skills[0], dict):
                # e.g., [{"skill": "Python", "level": "Expert"}]
                skills = [s.get('skill') for s in raw_skills if s.get('skill')]
            elif raw_skills and isinstance(raw_skills[0], str):
                # e.g., ["Python", "React"]
                skills = raw_skills
        
        # Get years of experience
        raw_years = candidate_profile_data.get('years_of_experience') 
        years_of_experience = 0
        try:
            if isinstance(raw_years, (int, float)):
                years_of_experience = int(raw_years)
            elif isinstance(raw_years, str) and raw_years.strip():
                # Try to find a number
                match = re.search(r'(\d+\.?\d*|\d+)', raw_years)
                if match:
                    years_of_experience = int(float(match.group(1)))
            else:
                years_of_experience = 0 
        except (ValueError, TypeError):
            years_of_experience = 0

        if not skills:
            skills = ['Programming', 'Problem Solving']

        return skills[:10], match_summary, years_of_experience

    @staticmethod
    def determine_job_level(years_of_experience: int) -> str:
        """Heuristic to set a general level for the LLM's persona."""
        if years_of_experience >= 6:
            return "senior"
        elif years_of_experience <= 2 and years_of_experience > 0:
            return "junior"
        return "mid"

class CodingSessionAnalyzer:
    """Analyzes screen content and provides pure observational data to the LLM. (No Change)"""
    
    def __init__(self):
        self.suspicious_activities = []
        self.progress_checkpoints = []
        self.last_analysis = None
        
    def analyze_screen_content(self, frame_analysis: str) -> Dict[str, Any]:
        """Analyze screen content for coding progress and potential cheating (unchanged)"""
        analysis = {
            'timestamp': time.time(),
            'ide_detected': False,
            'code_editor_active': False,
            'browser_tabs_detected': False,
            'suspicious_activity': False,
            'progress_indicators': [],
            'cheating_indicators': [],
            'suggestions': []
        }
        
        frame_lower = frame_analysis.lower()
        
        # Check for IDE/Editor
        ides = ['visual studio code', 'vscode', 'intellij', 'eclipse', 'sublime', 'atom', 'notepad++', 'vim', 'emacs', 'pycharm', 'webstorm']
        analysis['ide_detected'] = any(ide in frame_lower for ide in ides)
        analysis['code_editor_active'] = any(term in frame_lower for term in ['code', 'editor', 'syntax', 'function', 'class', 'import'])
        
        # Check for potential cheating indicators
        cheating_terms = [
            'chatgpt', 'chat gpt', 'openai', 'claude', 'gemini', 'copilot', 'github copilot',
            'stackoverflow', 'stack overflow', 'leetcode', 'hackerrank', 'geeksforgeeks',
            'google search', 'search results', 'tutorial', 'solution', 'answer'
        ]
        
        detected_cheating = [term for term in cheating_terms if term in frame_lower]
        if detected_cheating:
            analysis['suspicious_activity'] = True
            analysis['cheating_indicators'] = detected_cheating
            self.suspicious_activities.append({
                'timestamp': time.time(),
                'indicators': detected_cheating,
                'severity': 'high' if any(ai in detected_cheating for ai in ['chatgpt', 'copilot', 'claude']) else 'medium'
            })
        
        # Check for browser activity
        browser_terms = ['chrome', 'firefox', 'safari', 'browser', 'tab', 'url', 'address bar']
        analysis['browser_tabs_detected'] = any(term in frame_lower for term in browser_terms)
        
        # Progress indicators
        progress_terms = ['function', 'method', 'class', 'variable', 'loop', 'if', 'else', 'return', 'print', 'console.log']
        analysis['progress_indicators'] = [term for term in progress_terms if term in frame_lower]
        
        self.last_analysis = analysis
        return analysis
    
    def should_ask_question(self, last_question_time: float, min_interval: float = 120) -> bool:
        """Determine if enough time has passed to ask another question (Kept as heuristic safety)"""
        return (time.time() - last_question_time) > min_interval
    
    def get_cheating_warning_message(self) -> Optional[str]:
        """Get appropriate warning message if cheating is detected (Kept as safety fallback)"""
        if not self.suspicious_activities:
            return None
        
        recent_activities = [a for a in self.suspicious_activities if (time.time() - a['timestamp']) < 300]  # Last 5 minutes
        
        if not recent_activities:
            return None
        
        high_severity = [a for a in recent_activities if a['severity'] == 'high']
        
        if high_severity:
            return "I notice you might be using external AI tools or searching for solutions. For this interview, please rely on your own knowledge and problem-solving skills. Would you like to restart this problem?"
        else:
            return "I see you're browsing or looking up information. Please focus on solving the problem using your own knowledge. Feel free to ask me if you need clarification on the requirements."