// ats-frontend-dev-sheetal/app/src/pages/JobPosts/JobPostsForm.tsx
 
import { useState, useEffect, useCallback, useRef } from "react";
import * as jobApi from "../../api/jobApi";
import FileUpload from "../../components/common/FileUpload";
import SkillList from "../../components/common/SkillList";
import InterviewLevelsConfig from "../../components/common/InterviewLevelsConfig"; 
import AgentRoundConfigEditor from "../../components/common/AgentRoundConfigEditor";
import Button from "../../components/common/Button";
import { ZodError } from "zod";
import { Upload, Loader2, Combine, Home, Building, Globe, FileText, Plus, X, TrendingUp, MapPin, Clock } from "lucide-react";
import { useToast } from "../../context/ModalContext";
import * as validation from "../../utils/validation";
import clsx from "clsx";

const DEFAULT_EXPIRATION_OFFSET_DAYS = 30;
const getDefaultExpirationISO = () => {
  const date = new Date();
  date.setDate(date.getDate() + DEFAULT_EXPIRATION_OFFSET_DAYS);
  return date.toISOString().substring(0, 16);
};
 
export interface InterviewLevel {
  title: string;
  description: string;
  shortlistThreshold: number;
  rejectThreshold: number;
}
 
const DEFAULT_INTERVIEW_LEVELS: InterviewLevel[] = [
  { 
    title: "Initial Screening", 
    description: "Evaluation of the resumes against the job description criteria.",
    shortlistThreshold: 60, 
    rejectThreshold: 40 
  },
  { 
    title: "Technical Interview", 
    description: "60-minute technical session with the hiring manager.",
    shortlistThreshold: 60,
    rejectThreshold: 40
  },
  { 
    title: "Final Interview", 
    description: "45-minute call with the department head.",
    shortlistThreshold: 60,
    rejectThreshold: 40
  }
];

type WorkMode = "office" | "remote" | "wfh";
const LOCATION_OPTIONS = ["Chennai", "Palakkad", "US"] as const;
type LocationOption = typeof LOCATION_OPTIONS[number];
 
interface JobPostsFormProps {
  onCancel: () => void;
  jobId?: string; 
}
 
interface Skill {
  name: string;
  weight: number;
}
 
interface ApiSkill {
  skill: string;
  weightage: number;
}

interface KeyFunctionality {
  type: string;
  description: string;
}
 
const FIELD_MAP: Record<string, string> = {
  'job_title': 'Job Title',
  'job_description': 'Job Description',
  'description_sections': 'Job Description',
  'job_location': 'Job Location',
  'minimum_experience': 'Min Experience',
  'maximum_experience': 'Max Experience',
  'minimum_salary': 'Min Salary',
  'maximum_salary': 'Max Salary',
  'skills_required': 'Skills',
  'interview_levels': 'Interview Levels',
  'interview_rounds': 'Interview Levels',
  'interview_type': 'Interview Type', 
  'expiration_date': 'Expiration Date',
  'active_till': 'Expiration Date',
  'no_of_openings': 'Openings',
  'score_total': 'Scoring Total',
  'key_functionality': 'Additional Descriptions'
}
 
const JobPostsForm = ({ onCancel, jobId }: JobPostsFormProps) => {
  const isEditMode = !!jobId;
  const formTopRef = useRef<HTMLDivElement | null>(null);
  const jobTitleRef = useRef<HTMLInputElement | null>(null);
 
  const [activeTab, setActiveTab] = useState<'manual' | 'upload'>('manual');
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [isDataLoading, setIsDataLoading] = useState<boolean>(isEditMode);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [newSkill, setNewSkill] = useState<string>('');
  const [skills, setSkills] = useState<Skill[]>([]);
  const [keyFunctionalities, setKeyFunctionalities] = useState<KeyFunctionality[]>([]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
 
  const { showToast } = useToast();
 
  const [jobTitle, setJobTitle] = useState<string>('');
  const [jobDescription, setJobDescription] = useState<string>('');
  const [expMin, setExpMin] = useState<number>(0);
  const [expMax, setExpMax] = useState<number>(0);
  const [salaryMin, setSalaryMin] = useState<number>(0);
  const [salaryMax, setSalaryMax] = useState<number>(0);
  const [displaySalaryMin, setDisplaySalaryMin] = useState<string>('');
  const [displaySalaryMax, setDisplaySalaryMax] = useState<string>('');
  const [, setSalaryMinUnit] = useState<'none'|'k'|'l'|'c'>('none');
  const [, setSalaryMaxUnit] = useState<'none'|'k'|'l'|'c'>('none');
  const [salaryMinSuffix, setSalaryMinSuffix] = useState<string>('');
  const [salaryMaxSuffix, setSalaryMaxSuffix] = useState<string>('');
  const [salaryMinOpen, setSalaryMinOpen] = useState<boolean>(false);
  const [salaryMaxOpen, setSalaryMaxOpen] = useState<boolean>(false);
  const salaryMinRef = useRef<HTMLDivElement | null>(null);
  const salaryMaxRef = useRef<HTMLDivElement | null>(null);
  const [jobLocationOpen, setJobLocationOpen] = useState<boolean>(false);
  const jobLocationRef = useRef<HTMLDivElement | null>(null);
  const [careerActivationOpen, setCareerActivationOpen] = useState<boolean>(false);
  const careerActivationRef = useRef<HTMLDivElement | null>(null);
  
  const [workMode, setWorkMode] = useState<WorkMode>('office');
  const [jobLocation, setJobLocation] = useState<LocationOption | string>(LOCATION_OPTIONS[0]);
  
  const [isActive, setIsActive] = useState<boolean>(true);

  const [roleFit, setRoleFit] = useState<number>(45);
  const [potential, setPotential] = useState<number>(45);
  const [jobLocationScore, setJobLocationScore] = useState<number>(10);
  
  const [expirationDate, setExpirationDate] = useState<string>(getDefaultExpirationISO());
  const [openings, setOpenings] = useState<number>(1);

  const [interviewLevels, setInterviewLevels] = useState<InterviewLevel[]>(DEFAULT_INTERVIEW_LEVELS);
  const [agentConfigs, setAgentConfigs] = useState<Array<any>>([]);

  const [, setActivateOnCareer] = useState<boolean>(true);
  const [careerActivationMode, setCareerActivationMode] = useState<'days' | 'shortlist' | 'manual'>('manual');
  const [careerActivationDays, setCareerActivationDays] = useState<number>(DEFAULT_EXPIRATION_OFFSET_DAYS);
  const [careerShortlistThreshold, setCareerShortlistThreshold] = useState<number>(0);

  useEffect(() => {
    if (workMode === 'remote') {
      setJobLocation('Work from home'); 
      setErrors((prev) => ({ ...prev, job_location: "" })); 
    } else if (workMode === 'office') {
      if (!LOCATION_OPTIONS.includes(jobLocation as LocationOption)) {
        setJobLocation(LOCATION_OPTIONS[0]);
      }
    } else if (workMode === 'wfh') {
      if (!LOCATION_OPTIONS.includes(jobLocation as LocationOption)) {
        setJobLocation(LOCATION_OPTIONS[0]);
      }
    }
  }, [workMode, jobLocation]);

  const clearForm = useCallback(() => {
    setJobTitle('');
    setJobDescription('');
    setSkills([]);
    setExpMin(0);
    setExpMax(0);
    setSalaryMin(0);
    setSalaryMax(0);
    setDisplaySalaryMin('');
    setDisplaySalaryMax('');
    setSalaryMinUnit('none');
    setSalaryMaxUnit('none');
    setKeyFunctionalities([]);
    
    setWorkMode('office');
    setJobLocation(LOCATION_OPTIONS[0]);

    setIsActive(true);
    setActivateOnCareer(true);
    setRoleFit(45);
    setPotential(45);
    setJobLocationScore(10);
    setExpirationDate(getDefaultExpirationISO());
    setOpenings(1);
    setInterviewLevels(DEFAULT_INTERVIEW_LEVELS); 
    setErrors({});
    setActiveTab('manual');
  }, []);

  const mapDataToState = useCallback((data: any) => {
    setJobTitle(data.job_title || '');

    const descriptionSections = data.description_sections || [];
    const mainDesc = descriptionSections.find((s: any) => s.type_description === "Job Description" || s.title === "Job Description");
    const otherFuncs = descriptionSections.filter((s: any) => s.type_description !== "Job Description" && s.title !== "Job Description");
    setJobDescription(mainDesc?.context || data.job_description || '');
    
    const mappedKeyFuncs = (otherFuncs.length > 0 ? otherFuncs : (data.key_functionality || [])).map((d: any) => ({
      type: String(d.type ?? d.type_description ?? d.title ?? '').trim(),
      description: String(d.description ?? d.context ?? d.text ?? '').trim(),
    })) || [];
    setKeyFunctionalities(mappedKeyFuncs.filter((d: KeyFunctionality) => d.type || d.description));

    const mappedSkills = data.skills_required?.map((skill: ApiSkill) => ({
      name: skill.skill,
      weight: skill.weightage
    })) || [];
    setSkills(mappedSkills);

    const rawMin = data.minimum_experience ?? data.min_experience ?? 0;
    const rawMax = data.maximum_experience ?? data.max_experience ?? 0;
    const parsedMin = (() => {
      if (typeof rawMin === 'number') return rawMin;
      const digits = String(rawMin).replace(/\D+/g, '');
      const n = parseInt(digits || '0', 10);
      return isNaN(n) ? 0 : n;
    })();
    const parsedMax = (() => {
      if (typeof rawMax === 'number') return rawMax;
      const digits = String(rawMax).replace(/\D+/g, '');
      const n = parseInt(digits || '0', 10);
      return isNaN(n) ? 0 : n;
    })();
    setExpMin(Math.max(0, Math.min(10, parsedMin)));
    setExpMax(Math.max(0, Math.min(10, parsedMax)));

    const rawSalaryMin = data.minimum_salary ?? data.min_salary ?? 0;
    const rawSalaryMax = data.maximum_salary ?? data.max_salary ?? 0;
    const parsedSalaryMin = (() => {
      if (typeof rawSalaryMin === 'number') return rawSalaryMin;
      const s = String(rawSalaryMin).trim().toLowerCase().replace(/,/g, '');
      const match = s.match(/^([0-9]*\.?[0-9]+)\s*([kcl])?$/i);
      if (!match) {
        const n = parseInt(s.replace(/[^0-9]/g, '') || '0', 10);
        return isNaN(n) ? 0 : n;
      }
      const value = parseFloat(match[1]);
      const suffix = (match[2] || '').toLowerCase();
      const multiplier = suffix === 'k' ? 1000 : suffix === 'l' ? 100000 : suffix === 'c' ? 10000000 : 1;
      return Math.round(value * multiplier);
    })();
    const parsedSalaryMax = (() => {
      if (typeof rawSalaryMax === 'number') return rawSalaryMax;
      const s = String(rawSalaryMax).trim().toLowerCase().replace(/,/g, '');
      const match = s.match(/^([0-9]*\.?[0-9]+)\s*([kcl])?$/i);
      if (!match) {
        const n = parseInt(s.replace(/[^0-9]/g, '') || '0', 10);
        return isNaN(n) ? 0 : n;
      }
      const value = parseFloat(match[1]);
      const suffix = (match[2] || '').toLowerCase();
      const multiplier = suffix === 'k' ? 1000 : suffix === 'l' ? 100000 : suffix === 'c' ? 10000000 : 1;
      return Math.round(value * multiplier);
    })();
    setSalaryMin(Math.max(0, parsedSalaryMin));
    setSalaryMax(Math.max(0, parsedSalaryMax));
    setDisplaySalaryMin((parsedSalaryMin && parsedSalaryMin > 0) ? String(parsedSalaryMin) : '');
    setDisplaySalaryMax((parsedSalaryMax && parsedSalaryMax > 0) ? String(parsedSalaryMax) : '');
    
    const apiLocation = data.job_location || LOCATION_OPTIONS[0];
    const apiRemote = data.work_from_home || false;
    const apiWorkMode = data.work_mode || null;

    if (apiWorkMode) {
        setWorkMode(apiWorkMode);
        if (apiWorkMode === 'remote') {
            setJobLocation('Work from home');
        } else {
            setJobLocation(LOCATION_OPTIONS.includes(apiLocation) ? apiLocation : LOCATION_OPTIONS[0]);
        }
    } else {
        if (apiRemote && (apiLocation.toLowerCase() === 'remote' || apiLocation.toLowerCase() === 'work from home')) {
          setWorkMode('remote'); 
          setJobLocation('Work from home');
        } else if (apiRemote) {
          setWorkMode('wfh'); 
          setJobLocation(LOCATION_OPTIONS.includes(apiLocation) ? apiLocation : LOCATION_OPTIONS[0]);
        } else {
          setWorkMode('office');
          setJobLocation(LOCATION_OPTIONS.includes(apiLocation) ? apiLocation : LOCATION_OPTIONS[0]);
        }
    }

    setIsActive(data.is_active ?? true);
    setActivateOnCareer(data.is_active ?? true);

    setRoleFit(data.role_fit ?? 45);
    setPotential(data.potential_fit ?? data.potential ?? 45);
    setJobLocationScore(data.location_fit ?? data.location_score ?? 10);
    
    const dt = data.active_till || data.expiration_date;
    setExpirationDate(dt ? new Date(dt).toISOString().substring(0, 16) : getDefaultExpirationISO());

    setOpenings(
      typeof data.no_of_openings === 'number'
        ? data.no_of_openings
        : Number(data.no_of_openings ?? 1) || 1
    );
    
    const apiLevels = data.interview_rounds;
    const hasApiLevels = apiLevels && Array.isArray(apiLevels) && apiLevels.length > 0;
    
    setInterviewLevels(
      hasApiLevels
        ? apiLevels.map((level: any, index: number) => {
            return { 
              title: level.level_name || level.title || `Round ${index + 1}`,
              description: level.description || "",
              shortlistThreshold: level.shortlisting_threshold ?? 60,
              rejectThreshold: level.rejected_threshold ?? 40,
            };
          })
        : DEFAULT_INTERVIEW_LEVELS
    );

    const apiAgentRounds = data.agentRounds || data.agent_configs || data.agentConfigs || null;
    if (apiAgentRounds && Array.isArray(apiAgentRounds)) {
      setAgentConfigs(apiAgentRounds.map((ac: any) => ({
        round_list_id: ac.round_list_id || ac.roundListId || undefined,
        round_name: ac.round_name || ac.roundName || ac.round_name || undefined,
        interview_mode: (ac.interview_mode || ac.interviewMode || 'agent'),
        interview_time_min: ac.interview_time_min || ac.interviewTimeMin || ac.interview_time || ac.interviewTime || null,
        interview_time_max: ac.interview_time_max || ac.interviewTimeMax || ac.interview_time || ac.interviewTime || null,
        interviewer_id: ac.interviewer_id || ac.interviewerId || null,
        persona: ac.persona || 'alex',
        key_skills: ac.key_skills || ac.keySkills || [],
        custom_questions: ac.custom_questions || ac.customQuestions || [],
        forbidden_topics: ac.forbidden_topics || ac.forbiddenTopics || [],
        coding_enabled: Boolean(ac.coding_enabled ?? ac.codingEnabled ?? false),
        coding_question_mode: ac.coding_question_mode || ac.codingQuestionMode || 'ai',
        coding_difficulty: ac.coding_difficulty || ac.codingDifficulty || 'medium',
        coding_languages: ac.coding_languages || ac.codingLanguages || ['python'],
        provided_coding_question: ac.provided_coding_question || ac.providedCodingQuestion || '',
        coding_test_case_mode: ac.coding_test_case_mode || ac.codingTestCaseMode || 'provided',
        coding_test_cases: ac.coding_test_cases || ac.codingTestCases || [],
        coding_starter_code: ac.coding_starter_code || ac.codingStarterCode || {},
        mcq_enabled: Boolean(ac.mcq_enabled ?? ac.mcqEnabled ?? false),
        mcq_question_mode: ac.mcq_question_mode || ac.mcqQuestionMode || 'provided',
        mcq_difficulty: ac.mcq_difficulty || ac.mcqDifficulty || 'medium',
        mcq_questions: ac.mcq_questions || ac.mcqQuestions || [],
        mcq_passing_score: Number(ac.mcq_passing_score ?? ac.mcqPassingScore ?? 60) || 60,
      })));
    } else {
      const levels = hasApiLevels
        ? apiLevels.map((level: any, index: number) => ({
            round_name: level.level_name || level.title || `Round ${index + 1}`,
          }))
        : DEFAULT_INTERVIEW_LEVELS.map((l) => ({ round_name: l.title }));

      setAgentConfigs(levels.map((_, idx) => ({
        round_list_id: undefined,
        round_name: levels[idx].round_name,
        interview_mode: idx === 0 ? 'screening' : 'agent',
        interview_time_min: idx === 0 ? null : 15,
        interview_time_max: idx === 0 ? null : 30,
        interviewer_id: null,
        persona: 'alex',
        key_skills: [],
        custom_questions: [],
        forbidden_topics: [],
        coding_enabled: false,
        coding_question_mode: 'ai',
        coding_difficulty: 'medium',
        coding_languages: ['python'],
        provided_coding_question: '',
        coding_test_case_mode: 'provided',
        coding_test_cases: [],
        coding_starter_code: {},
        mcq_enabled: false,
        mcq_question_mode: 'provided',
        mcq_difficulty: 'medium',
        mcq_questions: [],
        mcq_passing_score: 60,
      })));
    }

    setCareerActivationMode(data.career_activation_mode ?? 'manual');
    setCareerActivationDays(data.career_activation_days ?? DEFAULT_EXPIRATION_OFFSET_DAYS);
    setCareerShortlistThreshold(data.career_shortlist_threshold ?? 0);

    setErrors({});
  }, []);
 
  useEffect(() => {
    if (isEditMode && jobId) {
      const fetchJobDetails = async () => {
        setIsDataLoading(true);
        try {
          const response = await jobApi.getJobPostById(jobId);
          if (response.success && response.data) {
            mapDataToState(response.data);
          } else {
            const errMsg = (!response.success && (response as any).error) || (response as any)?.error || 'Failed to load job data.';
            showToast(errMsg, 'error');
            onCancel();
          }
        } catch (error) {
          console.error('Failed to fetch job details:', error);
          showToast('Failed to load job data.', 'error');
          onCancel();
        } finally {
          setIsDataLoading(false);
        }
      };
      fetchJobDetails();
    } else if (!isEditMode) {
        clearForm();
        setIsDataLoading(false);
    }
  }, [jobId, isEditMode, mapDataToState, onCancel, showToast, clearForm]);

  const validateSalaryRange = (minVal: number, maxVal: number) => {
    const newErrors = { ...errors };
    delete newErrors.minimum_salary;
    delete newErrors.maximum_salary;
    if (maxVal > 0 && minVal >= maxVal) {
      newErrors.minimum_salary = "Min must be less than Max.";
    }
    if (maxVal > 0 && maxVal <= minVal) {
      newErrors.maximum_salary = "Max must be greater than Min.";
    }
    setErrors(newErrors);
  };

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (salaryMinRef.current && !salaryMinRef.current.contains(e.target as Node)) {
        setSalaryMinOpen(false);
      }
      if (salaryMaxRef.current && !salaryMaxRef.current.contains(e.target as Node)) {
        setSalaryMaxOpen(false);
      }
      if (jobLocationRef.current && !jobLocationRef.current.contains(e.target as Node)) {
        setJobLocationOpen(false);
      }
      if (careerActivationRef.current && !careerActivationRef.current.contains(e.target as Node)) {
        setCareerActivationOpen(false);
      }
    };
    document.addEventListener('click', onDocClick);
    return () => document.removeEventListener('click', onDocClick);
  }, []);
 
  const addSkill = () => {
    const trimmedSkill = newSkill.trim();
    if (trimmedSkill === "" || skills.length >= 10 || skills.some(s => s.name.toLowerCase() === trimmedSkill.toLowerCase())) return;
    setSkills([...skills, { name: trimmedSkill, weight: 5 }]);
    setNewSkill('');
  };
 
  const updateSkillWeight = (idx: number, value: number) => {
    if (value < 1 || value > 10) return;
    const updated = [...skills];
    updated[idx].weight = value;
    setSkills(updated);
  };
 
  const removeSkill = (idx: number) => {
    setSkills(skills.filter((_, i) => i !== idx));
  };

  const addKeyFunctionality = () => {
    if (keyFunctionalities.length >= 10) return;
    setKeyFunctionalities([...keyFunctionalities, { type: '', description: '' }]);
  };

  const updateKeyFunctionality = (idx: number, field: 'type' | 'description', value: string) => {
    const updated = [...keyFunctionalities];
    updated[idx] = { ...updated[idx], [field]: value };
    setKeyFunctionalities(updated);
  };

  const removeKeyFunctionality = (idx: number) => {
    setKeyFunctionalities(keyFunctionalities.filter((_, i) => i !== idx));
  };
 
  const handleUploadSuccess = (extractedData: any) => {
    if (extractedData) {
      mapDataToState(extractedData);
      setTimeout(() => {
        formTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        jobTitleRef.current?.focus();
      }, 150);
    }
    setTimeout(() => {
      setUploadStatus(null);
      setActiveTab('manual');
    }, 100);
  };
 
  const handleFileSelect = async (fileOrFiles: File | File[]) => {
    const file = Array.isArray(fileOrFiles) ? fileOrFiles[0] : fileOrFiles;
    if (!file) return;

  setIsUploading(true);
  setUploadStatus("Uploading...");

    formTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });

    try {
      const result = await jobApi.uploadJobPost(file);
      if (result.success) {
        setUploadStatus("Upload successful! Processing extraction...");
        const payload = result.data || {};

        const extracted =
          payload.job_details ??
          payload.data?.job_details ??
          payload.data?.extracted_details ??
          payload.extracted_details ??
          payload.data?.extractedDetails ??
          payload.extractedDetails ??
          payload.job?.extracted_details ??
          null;

        if (extracted) {
          handleUploadSuccess(extracted);
        } else {
          const createdJob =
            payload.data?.job ?? payload.job ?? payload.data?.job_details ?? payload.job_details ?? null;

          if (createdJob) {
            setUploadStatus("Upload successful. Job created.");
            try { window.localStorage.setItem('career_jobs_refresh', String(Date.now())); } catch {
              // no-op
            }
            try { window.dispatchEvent(new CustomEvent('career_jobs_refresh')); } catch {
              // no-op
            }
            onCancel();
          } else {
            setUploadStatus("Upload successful. No extracted details returned.");
          }
        }
      } else {
        setUploadStatus("Upload failed: " + (result.error || "Unknown error"));
      }
    } catch (error) {
      setUploadStatus(`Upload failed: ${error instanceof Error ? error.message : "An unknown error occurred"}`);
    } finally {
      setIsUploading(false);
    }
  };
 
  const handleAnalyzeJobPost = async () => {
    const functionalityText = keyFunctionalities
      .map(kf => `Additional Descriptions (${kf.type || 'General'}): ${kf.description || ''}`)
      .join('\n\n');
    
    const combinedText = [jobDescription.trim(), functionalityText.trim()]
      .filter(Boolean)
      .join('\n\n---\n\n'); 

    if (!jobTitle.trim()) {
      showToast('Please enter a Job Title before analyzing.', 'info');
      return;
    }

    if (!combinedText) {
      showToast('Please provide a Job Description or Additional Descriptions to analyze.', 'info');
      return;
    }

    const dataToAnalyze = {
      job_description: combinedText, 
      job_title: jobTitle,
    };

    setIsAnalyzing(true);
    try {
      const response = await jobApi.analyzeJobPost(dataToAnalyze);
      if (response.success && response.data.data?.analysis_result?.recommended_skills) {
        const recommendedSkills = response.data.data.analysis_result.recommended_skills.map((skill: any) => ({
          name: skill.skill,
          weight: skill.weightage
        }));
        setSkills(recommendedSkills);
        showToast(`Successfully generated ${recommendedSkills.length} skills!`, 'success');
      } else {
        showToast('No new skill recommendations were returned for this job post.', 'info');
      }
    } catch (error) {
      console.error('Failed to analyze job post:', error);
      showToast('Failed to analyze job post. Please try again.', 'error');
    } finally {
      setIsAnalyzing(false);
    }
  };
 
  const handleSubmitJobPost = async () => {
    setIsSubmitting(true);
    setErrors({});
   
    const normalizedExpiration = expirationDate || getDefaultExpirationISO();
    const expirationISOForValidation = (() => {
      try {
        const d = new Date(normalizedExpiration);
        return isNaN(d.getTime()) ? undefined : d.toISOString();
      } catch {
        return undefined;
      }
    })();
    
    const normalizedOpenings = Number.isFinite(openings) ? Math.max(1, Math.round(openings)) : 1;
    const normalizedSkills = skills.map(skill => ({
      skill: skill.name,
      weightage: skill.weight,
    }));
    
    const normalizedInterviewLevels = interviewLevels.map((l, index) => ({
      level_name: l.title.trim(),
      description: l.description.trim(),
      round_order: index + 1,
      shortlisting_threshold: l.shortlistThreshold,
      rejected_threshold: l.rejectThreshold,
    })).filter(l => l.level_name); 

    const normalizedKeyFunctionalities = keyFunctionalities.map(d => ({
      type: (d.type || '').trim(),
      description: (d.description || '').trim(),
    })).filter((d: KeyFunctionality) => d.type && d.description);
    
    const allDescriptionSections = [
      {
        title: "Job Description",
        content: jobDescription.trim()
      },
      ...normalizedKeyFunctionalities.map(kf => ({
        title: kf.type,
        content: kf.description
      }))
    ].filter(section => section.content);

    const finalJobLocation = workMode === 'remote' ? 'Work from home' : jobLocation;
    const finalRemote = workMode === 'remote' || workMode === 'wfh';

    const validationData = {
      job_id: jobId ? jobId : undefined,
      job_title: jobTitle,
      job_description: jobDescription.trim(), 
      description_sections: allDescriptionSections,
      role_fit: roleFit,
      potential_fit: potential,
      location_fit: jobLocationScore,
      minimum_experience: expMin,
      maximum_experience: expMax,
      // send numeric salary values only when provided, otherwise null
      minimum_salary: salaryMin > 0 ? salaryMin : null,
      maximum_salary: salaryMax > 0 ? salaryMax : null,
      job_location: finalJobLocation, 
      work_from_home: finalRemote,
      is_active: isActive,
      work_mode: workMode,
      career_activation_mode: careerActivationMode,
      career_activation_days: careerActivationDays,
      career_shortlist_threshold: careerShortlistThreshold,
      skills_required: normalizedSkills,
      interview_rounds: normalizedInterviewLevels, 
      active_till: expirationISOForValidation,
      no_of_openings: normalizedOpenings,
    };
   
    try {
      setGeneralError(null);
      validation.jobPostSchema.parse(validationData);

      const payload = {
        ...validationData,
        active_till: expirationISOForValidation,
        // include alternate/backwards-compatible salary keys expected by some backends
        min_salary: validationData.minimum_salary ?? null,
        max_salary: validationData.maximum_salary ?? null,
        agent_configs: agentConfigs.map(ac => ({
          roundListId: ac.round_list_id || ac.roundListId || undefined,
          roundName: ac.round_name || ac.roundName || undefined,
          roundFocus: ac.round_focus || ac.roundFocus || undefined,
          persona: ac.persona || 'alex',
          keySkills: ac.key_skills || ac.keySkills || [],
          customQuestions: ac.custom_questions || ac.customQuestions || [],
          forbiddenTopics: ac.forbidden_topics || ac.forbiddenTopics || [],
          interview_mode: ac.interview_mode || ac.interviewMode || undefined,
          interviewTimeMin: ac.interview_time_min || ac.interviewTimeMin || undefined,
          interviewTimeMax: ac.interview_time_max || ac.interviewTimeMax || undefined,
          interviewerId: ac.interviewer_id || ac.interviewerId || undefined,
          codingEnabled: Boolean(ac.coding_enabled ?? ac.codingEnabled ?? false),
          codingQuestionMode: ac.coding_question_mode || ac.codingQuestionMode || 'ai',
          codingDifficulty: ac.coding_difficulty || ac.codingDifficulty || 'medium',
          codingLanguages: ac.coding_languages || ac.codingLanguages || ['python'],
          providedCodingQuestion: ac.provided_coding_question || ac.providedCodingQuestion || '',
          codingTestCaseMode: ac.coding_test_case_mode || ac.codingTestCaseMode || 'provided',
          codingTestCases: ac.coding_test_cases || ac.codingTestCases || [],
          codingStarterCode: ac.coding_starter_code || ac.codingStarterCode || {},
          mcqEnabled: Boolean(ac.mcq_enabled ?? ac.mcqEnabled ?? false),
          mcqQuestionMode: ac.mcq_question_mode || ac.mcqQuestionMode || 'provided',
          mcqDifficulty: ac.mcq_difficulty || ac.mcqDifficulty || 'medium',
          mcqQuestions: ac.mcq_questions || ac.mcqQuestions || [],
          mcqPassingScore: Number(ac.mcq_passing_score ?? ac.mcqPassingScore ?? 60) || 60,
        })),
      };
      
      const response = await jobApi.updateJobPost(payload);
     
      if (response.success) {
        showToast(`Job post ${isEditMode ? 'updated' : 'created'} successfully!`, 'success');
        
        try {
          window.localStorage.setItem('career_jobs_refresh', String(Date.now()));
        } catch {
          // no-op
        }
        try {
          window.dispatchEvent(new CustomEvent('career_jobs_refresh'));
        } catch {
          // no-op
        }

        setTimeout(() => {
          onCancel();
        }, 500);
      
      } else {
        showToast(response.error || `Failed to ${isEditMode ? 'update' : 'create'} job post.`, "error");
      }
    } catch (error: unknown) {
      if (error instanceof ZodError) {
        const fieldErrors: Record<string, string> = {};
        const messages: string[] = [];
        error.issues.forEach((issue) => {
          const fieldName = issue.path.join('.');
          
          if (fieldName.startsWith('description_sections') || fieldName === 'job_description') {
            fieldErrors['job_description'] = issue.message; 
          }
          else if (fieldName.startsWith('interview_rounds')) {
            fieldErrors['interview_levels'] = issue.message;
          } 
          else if (fieldName.startsWith('active_till')) {
            fieldErrors['expiration_date'] = issue.message;
          }
          else if (fieldName.startsWith('key_functionality')) {
            fieldErrors['key_functionality'] = issue.message;
          } else if (fieldName in FIELD_MAP || fieldName === 'score_total' || fieldName === 'skills_required') {
             if (fieldName === 'skills_required') {
              fieldErrors['skills_required'] = "At least one skill is required.";
            } else {
              fieldErrors[fieldName] = issue.message;
            }
          }
          messages.push(issue.message); 
        });

        setErrors(fieldErrors);
        setGeneralError(messages.join(" "));
        formTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        jobTitleRef.current?.focus();
      } else if (error instanceof Error) {
        console.error('Job post submission failed:', error);
        showToast(error.message || 'Failed to save job post.', 'error');
      } else {
        showToast('An unexpected error occurred while saving the job post.', 'error');
      }
    } finally {
      setIsSubmitting(false);
    }
  };
 
  const renderErrorMessage = (field: string) => {
    return errors[field] ? (
      <span className="text-red-600 text-xs mt-1 block font-medium">
        {errors[field]}
      </span>
    ) : null;
  };
 
  useEffect(() => {
    if (skills.length > 10) {
      setSkills(skills.slice(0, 10));
    }
  }, [skills]);
  
  if (isDataLoading) {
    return (
        <div className="flex flex-col items-center justify-center h-96">
            <Loader2 size={48} className="text-[var(--color-primary-500)] animate-spin" />
            <p className="mt-4 text-gray-500">{isEditMode ? 'Loading job details...' : 'Initializing form...'}</p>
        </div>
    );
  }
 
  return (
    <div className="min-h-screen bg-gray-50/50">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6" ref={formTopRef}>
        {generalError && (
          <div className="mb-6 bg-red-50 border-l-4 border-red-400 text-red-700 p-4 rounded-r-lg shadow-sm">
            <div className="flex items-start gap-3">
              <div className="w-5 h-5 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-red-600 text-xs font-bold">!</span>
              </div>
              <div>
                <h4 className="font-semibold text-red-800">Please fix the following issues:</h4>
                <p className="text-sm mt-1 text-red-700">{generalError}</p>
              </div>
            </div>
          </div>
        )}

        <div className="bg-white rounded-xl shadow-lg border border-gray-200/60 overflow-visible">
          <div className="p-6 lg:p-8">
 
            <div className="border-b border-gray-100 pb-6 mb-8">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">
                    {isEditMode ? "Edit Job Post" : "Create New Job Post"}
                  </h1>
                  <p className="text-gray-600 mt-1">
                    {isEditMode ? "Update your job posting details" : "Fill in the details to create a new job posting"}
                  </p>
                </div>
              </div>
            </div>

            {!isEditMode && (
              <div className="mb-8">
                <div className="border-b border-gray-200">
                  <nav className="-mb-px flex space-x-8">
                    <button
                      onClick={() => { setActiveTab('manual'); }}
                      className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors duration-200 flex items-center gap-2 ${
                          activeTab === 'manual'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      <Building size={16} />
                      Manual Entry
                    </button>
                    <button
                      onClick={() => { setActiveTab('upload'); }}
                      className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors duration-200 flex items-center gap-2 ${
                          activeTab === 'upload'
                          ? 'border-blue-500 text-blue-600'
                          : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                      }`}
                    >
                      <Upload size={16} />
                      Upload Document
                    </button>
                  </nav>
                </div>
              </div>
            )}
 
            {activeTab === 'manual' && (
              <>
                <div className="space-y-8">
                {/* Job Title Section */}
                <div className="bg-gradient-to-br from-gray-50/50 to-white rounded-2xl border border-gray-200/60 p-6 shadow-sm">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                      <Building size={16} className="text-blue-600" />
                    </div>
                    <div>
                      <label className="block text-lg font-semibold text-gray-900">Job Title</label>
                      <p className="text-sm text-gray-500">Enter a clear and specific job title</p>
                    </div>
                    <span className="text-red-500 text-lg">*</span>
                  </div>
                  <input
                    ref={jobTitleRef}
                    type="text"
                    value={jobTitle}
                    onChange={(e) => {
                      setJobTitle(e.target.value);
                      setErrors((prev) => ({ ...prev, job_title: "" }));
                    }}
                    placeholder="e.g. Senior Frontend Developer, Marketing Manager, Data Analyst"
                    className={`w-full bg-white border-2 rounded-xl px-5 py-4 text-base placeholder-gray-400 focus:outline-none focus:ring-0 focus:border-blue-500 shadow-sm transition-all duration-200 ${errors.job_title ? 'border-red-400 bg-red-50/30' : 'border-gray-200 hover:border-gray-300'}`}
                  />
                  {renderErrorMessage("job_title")}
                </div>
 
                {/* Job Description Section */}
                <div className="bg-gradient-to-br from-gray-50/50 to-white rounded-2xl border border-gray-200/60 p-6 shadow-sm">
                  <div className="flex items-start gap-3 mb-4">
                    <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center flex-shrink-0 mt-1">
                      <FileText size={16} className="text-green-600" />
                    </div>
                    <div className="flex-1">
                      <label className="block text-lg font-semibold text-gray-900">Job Description</label>
                      <p className="text-sm text-gray-500">Provide a detailed description of the role, responsibilities, and requirements</p>
                    </div>
                    <span className="text-red-500 text-lg">*</span>
                  </div>
                  <div className="relative">
                    <textarea
                      value={jobDescription}
                      onChange={(e) => {
                        setJobDescription(e.target.value);
                        setErrors((prev) => ({ ...prev, job_description: "" }));
                      }}
                      placeholder="• Role overview and key responsibilities
• Required skills and qualifications  
• Company culture and team structure
• Growth opportunities and benefits
• Any specific requirements or preferences..."
                      rows={10}
                      className={`w-full bg-white border-2 rounded-xl px-5 py-4 text-base placeholder-gray-400 focus:outline-none focus:ring-0 focus:border-blue-500 shadow-sm transition-all duration-200 resize-y ${errors.job_description ? 'border-red-400 bg-red-50/30' : 'border-gray-200 hover:border-gray-300'}`}
                    />
                    <div className="absolute bottom-12 right-3 text-xs text-gray-400 bg-white px-2 py-1 rounded">
                      {jobDescription.length} characters
                    </div>
                  </div>
                  {renderErrorMessage("job_description")}
                </div>

                {/* Additional Descriptions Section */}
                <div className="bg-gradient-to-br from-gray-50/50 to-white rounded-2xl border border-gray-200/60 p-6 shadow-sm">
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                        <Combine size={16} className="text-purple-600" />
                      </div>
                      <div>
                          <label className="block text-lg font-semibold text-gray-900">Additional Descriptions</label>
                          <p className="text-sm text-gray-500">Add structured description sections to organize your job post</p>
                      </div>
                    </div>
                    <Button 
                      type="button" 
                      onClick={addKeyFunctionality} 
                      className="px-4 py-2 bg-gradient-to-r from-purple-500 to-purple-600 text-white rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center gap-2"
                    >
                      <Plus size={16} />
                      Add Section
                    </Button>
                  </div>

                  <div className="space-y-4">
                    {keyFunctionalities.map((d, idx) => (
                      <div key={idx} className="bg-white border-2 border-gray-100 rounded-xl shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden">
                        <div className="bg-gradient-to-r from-gray-50 to-gray-50/50 px-6 py-4 border-b border-gray-100">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-3">
                              <div className="w-6 h-6 bg-purple-100 rounded-md flex items-center justify-center">
                                <span className="text-xs font-semibold text-purple-600">{idx + 1}</span>
                              </div>
                              <h4 className="font-semibold text-gray-800">{d.type || `Section ${idx + 1}`}</h4>
                            </div>
                            <button 
                              type="button" 
                              onClick={() => removeKeyFunctionality(idx)} 
                              className="text-gray-400 hover:text-red-500 rounded-lg p-2 hover:bg-red-50 transition-all duration-200"
                            >
                              <X size={16} />
                            </button>
                          </div>
                        </div>
                        <div className="p-6 space-y-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Section Title</label>
                            <input
                              type="text"
                              value={d.type}
                              onChange={(e) => updateKeyFunctionality(idx, 'type', e.target.value)}
                              placeholder="e.g., Core Responsibilities, Benefits, About the Team"
                              className="w-full bg-gray-50 border-2 border-gray-200 rounded-lg px-4 py-3 text-base outline-none focus:border-purple-400 focus:bg-white transition-all duration-200 placeholder-gray-400"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
                            <textarea
                              value={d.description}
                              onChange={(e) => updateKeyFunctionality(idx, 'description', e.target.value)}
                              placeholder="Provide detailed information for this section..."
                              rows={4}
                              className="w-full bg-gray-50 border-2 border-gray-200 rounded-lg px-4 py-3 text-base outline-none focus:border-purple-400 focus:bg-white transition-all duration-200 resize-y placeholder-gray-400"
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                    
                    {keyFunctionalities.length === 0 && (
                      <div className="text-center py-12 text-gray-500">
                        <Combine size={48} className="mx-auto mb-4 text-gray-300" />
                        <p className="text-lg font-medium mb-2">No sections added yet</p>
                        <p className="text-sm">Add additional description sections to better organize your job post</p>
                      </div>
                    )}
                    
                    {renderErrorMessage('key_functionality')}
                  </div>
                </div>

                {/* Experience Range Section */}
                <div className="bg-gradient-to-br from-gray-50/50 to-white rounded-2xl border border-gray-200/60 p-6 shadow-sm">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center">
                      <TrendingUp size={16} className="text-orange-600" />
                    </div>
                    <div>
                      <label className="block text-lg font-semibold text-gray-900">Experience Range</label>
                      <p className="text-sm text-gray-500">Set the minimum and maximum years of experience required</p>
                    </div>
                  </div>
                  <div className="flex gap-4">
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-2">Minimum Years</label>
                      <input
                        type="number"
                        min={0}
                        max={10}
                        value={String(expMin)}
                        onChange={(e) => {
                          const raw = e.target.value;
                        if (raw === "") {
                          setExpMin(0);
                          setErrors((prev) => ({ ...prev, minimum_experience: "", maximum_experience: "" }));
                          return;
                        }
                        const digits = raw.replace(/\D+/g, '').slice(0, 2).replace(/^0+(?=\d)/, '');
                        let num = parseInt(digits, 10);
                        if (isNaN(num)) num = 0;
                        num = Math.max(0, Math.min(10, num));

                        let newErrors = { ...errors };
                        delete newErrors.minimum_experience;
                        delete newErrors.maximum_experience;

                        if (expMax > 0 && num >= expMax) {
                          newErrors.minimum_experience = "Min must be less than Max.";
                        } else if (expMax > 0 && (expMax - num) > 10) {
                          newErrors.maximum_experience = "Range cannot exceed 10 years.";
                        }

                        setErrors(newErrors);
                        setExpMin(num);
                      }}
                        className={`w-full bg-white border-2 rounded-lg px-4 py-3 text-base focus:outline-none focus:border-orange-400 transition-all duration-200 ${errors.minimum_experience || errors.maximum_experience ? 'border-red-400 bg-red-50/30' : 'border-gray-200 hover:border-gray-300'}`}
                        placeholder="0"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-2">Maximum Years</label>
                      <input
                      type="number"
                      min={0}
                      max={10}
                      value={String(expMax)}
                      onChange={(e) => {
                        const raw = e.target.value;
                         let num = 0; 
                        if (raw !== "") {
                          const digits = raw.replace(/\D+/g, '').slice(0, 2).replace(/^0+(?=\d)/, '');
                          let parsedNum = parseInt(digits, 10);
                          if (!isNaN(parsedNum)) {
                            num = Math.max(0, Math.min(10, parsedNum));
                          }
                        }

                        let newErrors = { ...errors };
                        delete newErrors.minimum_experience;
                        delete newErrors.maximum_experience;

                        if (num > 0 && num <= expMin) {
                          newErrors.maximum_experience = "Max must be greater than Min.";
                        } else if ((num - expMin) > 10) {
                          newErrors.maximum_experience = "Range cannot exceed 10 years.";
                        }
                        
                        setErrors(newErrors);
                        setExpMax(num);
                      }}
                        className={`w-full bg-white border-2 rounded-lg px-4 py-3 text-base focus:outline-none focus:border-orange-400 transition-all duration-200 ${errors.maximum_experience ? 'border-red-400 bg-red-50/30' : 'border-gray-200 hover:border-gray-300'}`}
                        placeholder="10"
                      />
                    </div>
                  </div>
                  {renderErrorMessage("maximum_experience") || renderErrorMessage("minimum_experience")}
                </div>

                {/* Salary Range Section - keeping as is from original */}
                <div className="bg-gradient-to-br from-gray-50/50 to-white rounded-2xl border border-gray-200/60 p-6 shadow-sm">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-8 h-8 bg-emerald-100 rounded-lg flex items-center justify-center">
                      <TrendingUp size={16} className="text-emerald-600" />
                    </div>
                    <div>
                      <label className="block text-lg font-semibold text-gray-900">Salary Range</label>
                      <p className="text-sm text-gray-500">Set the minimum and maximum annual salary (in your currency)</p>
                    </div>
                  </div>
                  <div className="flex gap-4">
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-2">Minimum Salary</label>
                      <div className="flex items-center gap-3">
                        <input
                          type="text"
                          value={displaySalaryMin}
                          onChange={(e) => {
                            const raw = e.target.value;
                            setDisplaySalaryMin(raw);
                            const s = String(raw).trim().toLowerCase().replace(/,/g, '');
                            if (!s) {
                              setSalaryMin(0);
                              validateSalaryRange(0, salaryMax);
                              return;
                            }
                            const match = s.match(/^([0-9]*\.?[0-9]+)\s*([kcl])?$/i);
                            let num = 0;
                            if (match) {
                              const value = parseFloat(match[1]);
                              const suffix = (match[2] || '').toLowerCase();
                              const multiplier = suffix === 'k' ? 1000 : suffix === 'l' ? 100000 : suffix === 'c' ? 10000000 : 1;
                              num = Math.round(value * multiplier);
                              if (suffix) setSalaryMinSuffix('');
                            } else {
                              const digits = s.replace(/[^0-9]/g, '') || '0';
                              const base = parseInt(digits, 10) || 0;
                              const sel = salaryMinSuffix || '';
                              const multiplier = sel === 'k' ? 1000 : sel === 'l' ? 100000 : sel === 'c' ? 10000000 : 1;
                              num = Math.round(base * multiplier);
                            }
                            let newErrors = { ...errors };
                            delete newErrors.minimum_salary;
                            delete newErrors.maximum_salary;
                            if (salaryMax > 0 && num >= salaryMax) {
                              newErrors.minimum_salary = "Min must be less than Max.";
                            }
                            setSalaryMin(num);
                            validateSalaryRange(num, salaryMax);
                          }}
                          className={`flex-1 bg-white border-2 rounded-lg px-4 py-3 text-base focus:outline-none focus:border-emerald-400 transition-all duration-200 ${errors.minimum_salary || errors.maximum_salary ? 'border-red-400 bg-red-50/30' : 'border-gray-200 hover:border-gray-300'}`}
                          placeholder="e.g. 5 or 50000"
                        />
                        <div ref={salaryMinRef} className="relative w-36">
                          <button
                            type="button"
                            aria-haspopup="listbox"
                            aria-expanded={salaryMinOpen}
                            onClick={() => setSalaryMinOpen((v) => !v)}
                            className="w-full text-left bg-white border-2 border-gray-200 rounded-lg px-4 py-3 pr-10 text-base focus:outline-none focus:border-emerald-400 transition-all duration-200 h-12 flex items-center justify-between"
                          >
                            <span className="text-sm">{salaryMinSuffix ? (salaryMinSuffix === 'kPA' ? 'K' : salaryMinSuffix === 'l' ? 'LPA' : 'CPA') : 'None'}</span>
                            <svg className="ml-2 text-gray-400" width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                              <path d="M6 8l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          </button>
                          {salaryMinOpen && (
                            <div role="listbox" aria-label="Minimum salary unit" className="absolute right-0 mt-2 w-full bg-white border border-gray-200 rounded-lg shadow-sm z-50">
                              <div className="px-3 py-2 bg-white text-gray-700 border-b rounded-t-lg font-medium">{salaryMinSuffix ? (salaryMinSuffix === 'k' ? 'KPA' : salaryMinSuffix === 'l' ? 'LPA' : 'CPA') : 'None'}</div>
                              <div className="py-1">
                                {['', 'k', 'l', 'c'].map((opt) => {
                                  if (opt === salaryMinSuffix) return null;
                                  const label = opt === '' ? 'None' : opt === 'k' ? 'KPA' : opt === 'l' ? 'LPA' : 'CPA';
                                  return (
                                    <button
                                      key={opt || 'none'}
                                      type="button"
                                      onClick={() => {
                                        setSalaryMinSuffix(opt);
                                        const s = String(displaySalaryMin).trim().toLowerCase().replace(/,/g, '');
                                        if (!s) {
                                          setSalaryMin(0);
                                          validateSalaryRange(0, salaryMax);
                                        } else {
                                          const match = s.match(/^([0-9]*\.?[0-9]+)\s*([kcl])?$/i);
                                          let base = 0;
                                          if (match) {
                                            base = parseFloat(match[1]) || 0;
                                            if (match[2]) { const newMin = Math.round(base * (match[2] === 'k' ? 1000 : match[2] === 'l' ? 100000 : 10000000)); setSalaryMin(newMin); validateSalaryRange(newMin, salaryMax); setSalaryMinOpen(false); return; }
                                          } else {
                                            base = parseInt(s.replace(/[^0-9]/g, '') || '0', 10) || 0;
                                          }
                                          const multiplier = opt === 'k' ? 1000 : opt === 'l' ? 100000 : opt === 'c' ? 10000000 : 1;
                                          const newMin = Math.round(base * multiplier);
                                          setSalaryMin(newMin);
                                          validateSalaryRange(newMin, salaryMax);
                                        }
                                        setSalaryMinOpen(false);
                                      }}
                                      className="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm text-gray-700 hover:text-blue-700"
                                    >
                                      {label}
                                    </button>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                      {displaySalaryMin && salaryMin > 0 && (
                        <div className="mt-2 text-xs text-gray-500">{salaryMin.toLocaleString()}</div>
                      )}
                    </div>
                    <div className="flex-1">
                      <label className="block text-sm font-medium text-gray-700 mb-2">Maximum Salary</label>
                      <div className="flex items-center gap-3">
                        <input
                          type="text"
                          value={displaySalaryMax}
                          onChange={(e) => {
                            const raw = e.target.value;
                            setDisplaySalaryMax(raw);
                            const s = String(raw).trim().toLowerCase().replace(/,/g, '');
                            if (!s) {
                              setSalaryMax(0);
                              validateSalaryRange(salaryMin, 0);
                              return;
                            }
                            const match = s.match(/^([0-9]*\.?[0-9]+)\s*([kcl])?$/i);
                            let num = 0;
                            if (match) {
                              const value = parseFloat(match[1]);
                              const suffix = (match[2] || '').toLowerCase();
                              const multiplier = suffix === 'k' ? 1000 : suffix === 'l' ? 100000 : suffix === 'c' ? 10000000 : 1;
                              num = Math.round(value * multiplier);
                              if (suffix) setSalaryMaxSuffix('');
                            } else {
                              const digits = s.replace(/[^0-9]/g, '') || '0';
                              const base = parseInt(digits, 10) || 0;
                              const sel = salaryMaxSuffix || '';
                              const multiplier = sel === 'k' ? 1000 : sel === 'l' ? 100000 : sel === 'c' ? 10000000 : 1;
                              num = Math.round(base * multiplier);
                            }
                            let newErrors = { ...errors };
                            delete newErrors.minimum_salary;
                            delete newErrors.maximum_salary;
                            if (num > 0 && num <= salaryMin) {
                              newErrors.maximum_salary = "Max must be greater than Min.";
                            }
                            setSalaryMax(num);
                            validateSalaryRange(salaryMin, num);
                          }}
                          className={`flex-1 bg-white border-2 rounded-lg px-4 py-3 text-base focus:outline-none focus:border-emerald-400 transition-all duration-200 ${errors.maximum_salary ? 'border-red-400 bg-red-50/30' : 'border-gray-200 hover:border-gray-300'}`}
                          placeholder="e.g. 10 or 1000000"
                        />
                        <div ref={salaryMaxRef} className="relative w-36">
                          <button
                            type="button"
                            aria-haspopup="listbox"
                            aria-expanded={salaryMaxOpen}
                            onClick={() => setSalaryMaxOpen((v) => !v)}
                            className="w-full text-left bg-white border-2 border-gray-200 rounded-lg px-4 py-3 pr-10 text-base focus:outline-none focus:border-emerald-400 transition-all duration-200 h-12 flex items-center justify-between"
                          >
                            <span className="text-sm">{salaryMaxSuffix ? (salaryMaxSuffix === 'k' ? 'KPA' : salaryMaxSuffix === 'l' ? 'LPA' : 'CPA') : 'None'}</span>
                            <svg className="ml-2 text-gray-400" width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                              <path d="M6 8l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          </button>
                          {salaryMaxOpen && (
                            <div role="listbox" aria-label="Maximum salary unit" className="absolute right-0 mt-2 w-full bg-white border border-gray-200 rounded-lg shadow-sm z-50">
                              <div className="px-3 py-2 bg-white text-gray-700 border-b rounded-t-lg font-medium">{salaryMaxSuffix ? (salaryMaxSuffix === 'k' ? 'KPA' : salaryMaxSuffix === 'l' ? 'LPA' : 'CPA') : 'None'}</div>
                              <div className="py-1">
                                {['', 'k', 'l', 'c'].map((opt) => {
                                  if (opt === salaryMaxSuffix) return null;
                                  const label = opt === '' ? 'None' : opt === 'k' ? 'KPA' : opt === 'l' ? 'LPA' : 'CPA';
                                  return (
                                    <button
                                      key={opt || 'none'}
                                      type="button"
                                      onClick={() => {
                                        setSalaryMaxSuffix(opt);
                                        const s = String(displaySalaryMax).trim().toLowerCase().replace(/,/g, '');
                                        if (!s) {
                                          setSalaryMax(0);
                                          validateSalaryRange(salaryMin, 0);
                                        } else {
                                          const match = s.match(/^([0-9]*\.?[0-9]+)\s*([kcl])?$/i);
                                          let base = 0;
                                          if (match) {
                                            base = parseFloat(match[1]) || 0;
                                            if (match[2]) { const newMax = Math.round(base * (match[2] === 'k' ? 1000 : match[2] === 'l' ? 100000 : 10000000)); setSalaryMax(newMax); validateSalaryRange(salaryMin, newMax); setSalaryMaxOpen(false); return; }
                                          } else {
                                            base = parseInt(s.replace(/[^0-9]/g, '') || '0', 10) || 0;
                                          }
                                          const multiplier = opt === 'k' ? 1000 : opt === 'l' ? 100000 : opt === 'c' ? 10000000 : 1;
                                          const newMax = Math.round(base * multiplier);
                                          setSalaryMax(newMax);
                                          validateSalaryRange(salaryMin, newMax);
                                        }
                                        setSalaryMaxOpen(false);
                                      }}
                                      className="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm text-gray-700 hover:text-blue-700"
                                    >
                                      {label}
                                    </button>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                      {displaySalaryMax && salaryMax > 0 && (
                        <div className="mt-2 text-xs text-gray-500">{salaryMax.toLocaleString()}</div>
                      )}
                    </div>
                  </div>
                  {renderErrorMessage("maximum_salary") || renderErrorMessage("minimum_salary")}
                </div>

                {/* Work Mode and Location Section */}
                <div className="bg-gradient-to-br from-gray-50/50 to-white rounded-2xl border border-gray-200/60 p-6 shadow-sm">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                      <MapPin size={16} className="text-blue-600" />
                    </div>
                    <div>
                      <label className="block text-lg font-semibold text-gray-900">Work Arrangement</label>
                      <p className="text-sm text-gray-500">Choose the work mode and location preferences</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-3">Work Mode <span className="text-red-500">*</span></label>
                      <div className={clsx(
                        "flex w-full rounded-xl border-2 p-1 bg-gray-50/50",
                        errors.job_location ? 'border-red-400' : 'border-gray-200' 
                      )}>
                        <button
                          type="button"
                          onClick={() => setWorkMode('office')}
                          className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg text-sm font-medium transition-all duration-200 ${
                            workMode === 'office'
                              ? 'bg-white text-blue-700 shadow-md ring-1 ring-blue-100'
                              : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                          }`}
                        >
                          <Building size={16} />
                          Office
                        </button>
                        <button
                          type="button"
                          onClick={() => setWorkMode('wfh')}
                          className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg text-sm font-medium transition-all duration-200 ${
                            workMode === 'wfh'
                              ? 'bg-white text-blue-700 shadow-md ring-1 ring-blue-100'
                              : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                          }`}
                        >
                          <Home size={16} />
                          WFH
                        </button>
                        <button
                          type="button"
                          onClick={() => setWorkMode('remote')}
                          className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg text-sm font-medium transition-all duration-200 ${
                            workMode === 'remote'
                              ? 'bg-white text-blue-700 shadow-md ring-1 ring-blue-100'
                              : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                          }`}
                        >
                          <Globe size={16} />
                          Remote
                        </button>
                      </div>
                  </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-3">
                        Location <span className="text-red-500">*</span>
                      </label>
                      <div ref={jobLocationRef} className="relative">
                        <button
                          type="button"
                          onClick={() => { if (workMode !== 'remote') setJobLocationOpen(v => !v); }}
                          disabled={workMode === 'remote'}
                          className={`w-full text-left bg-white border-2 rounded-lg px-4 py-3 text-base focus:outline-none transition-all duration-200 h-12 flex items-center justify-between ${errors.job_location ? 'border-red-400 bg-red-50/30' : 'border-gray-200 hover:border-gray-300'} ${workMode === 'remote' ? 'opacity-50 cursor-not-allowed bg-gray-100' : ''}`}
                        >
                          <span className="text-sm">{workMode === 'remote' ? 'Work from home' : String(jobLocation)}</span>
                          <svg className="ml-2 text-gray-400" width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                            <path d="M6 8l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                          </svg>
                        </button>

                        {jobLocationOpen && workMode !== 'remote' && (
                          <div className="absolute left-0 mt-2 w-full bg-white border border-gray-200 rounded-lg shadow-sm z-50">
                            <div className="px-3 py-2 bg-white text-gray-700 border-b rounded-t-lg font-medium">Choose location</div>
                            <div className="py-1">
                              {LOCATION_OPTIONS.map((loc) => (
                                <button
                                  key={loc}
                                  type="button"
                                  onClick={() => {
                                    setJobLocation(loc);
                                    setErrors((prev) => ({ ...prev, job_location: "" }));
                                    setJobLocationOpen(false);
                                  }}
                                  className="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm text-gray-700 hover:text-blue-700"
                                >
                                  {loc}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                      {renderErrorMessage("job_location")}
                      {workMode === 'wfh' && ( 
                        <p className="text-xs text-blue-600 mt-2 bg-blue-50 px-3 py-2 rounded-lg">Select the base location for WFH.</p>
                      )}
                    </div>
                  </div>
                </div>
                 
                {/* Skills */}
                <div className={errors.skills_required ? 'p-2 border-2 border-red-500 rounded-lg bg-red-50' : ''}>
                  <SkillList
                    skills={skills}
                    newSkill={newSkill}
                    setNewSkill={setNewSkill}
                    addSkill={addSkill}
                    updateSkillWeight={updateSkillWeight}
                    removeSkill={removeSkill}
                    onGenerate={handleAnalyzeJobPost}
                    isGenerating={isAnalyzing}
                  />
                  {renderErrorMessage("skills_required")}
                </div>

                {/* Interview Levels */}
                <div>
                  <InterviewLevelsConfig
                    levels={interviewLevels}
                    setLevels={setInterviewLevels}
                    error={errors.interview_levels}
                    roleFit={roleFit}
                    setRoleFit={setRoleFit}
                    potential={potential}
                    setPotential={setPotential}
                    jobLocationScore={jobLocationScore}
                    setJobLocationScore={setJobLocationScore}
                    scoreTotalError={errors.score_total}
                    agentConfigs={agentConfigs}
                    setAgentConfigs={setAgentConfigs}
                  />
                </div>

                {/* Full Agent Round Configuration */}
                <div>
                  <AgentRoundConfigEditor
                    rounds={interviewLevels}
                    agentConfigs={agentConfigs}
                    setAgentConfigs={setAgentConfigs}
                  />
                </div>
 
{/* CONSOLIDATED Job Activation & Settings Section */}
<div className="bg-gradient-to-br from-blue-50/50 to-indigo-50/50 rounded-2xl border border-blue-100/60 p-6 shadow-sm">
  <div className="flex items-start gap-4">
    <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
      <Clock size={16} className="text-indigo-600" />
    </div>
    <div className="flex-1">
      {/* Header with Toggle */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-bold text-gray-900">Job Activation & Visibility</h3>
          <p className="text-sm text-gray-600 mt-1">
            Control when and how this job appears on your Career page
          </p>
        </div>
        <label className="flex items-center gap-3 cursor-pointer">
          <span className="text-sm font-medium text-gray-700">Active</span>
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => {
              const val = e.target.checked;
              setIsActive(val);
              setActivateOnCareer(val);
              if (!val) setCareerActivationMode('manual');
            }}
            className="h-6 w-6 rounded-lg border-blue-300 shadow focus:ring-2 focus:ring-blue-400 accent-blue-500 transition"
          />
        </label>
      </div>

      {/* Show settings only when job is active */}
      {isActive && (
        <div className="space-y-6 pt-4 border-t border-blue-100">
          {/* Activation Rule */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-3">
              Activation Rule
            </label>
            <div ref={careerActivationRef} className="relative">
              <button
                type="button"
                onClick={() => setCareerActivationOpen(v => !v)}
                className="w-full text-left bg-white border-2 border-gray-200 rounded-lg px-4 py-3 text-base shadow-sm hover:border-blue-300 transition-all duration-200 flex items-center justify-between focus:outline-none focus:border-blue-400"
              >
                <span className="text-sm">
                  {careerActivationMode === 'manual' 
                    ? 'Manual (stay active until toggled)' 
                    : careerActivationMode === 'days' 
                    ? 'Auto-disable after X days' 
                    : 'Auto-disable after N shortlisted candidates'}
                </span>
                <svg className="ml-2 text-gray-400" width="18" height="18" viewBox="0 0 20 20" fill="none">
                  <path d="M6 8l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
              
              {careerActivationOpen && (
                <div className="absolute left-0 mt-2 w-full bg-white border border-gray-200 rounded-lg shadow-lg z-50">
                  <div className="px-3 py-2 bg-gray-50 text-gray-700 border-b font-medium rounded-t-lg">
                    Choose activation rule
                  </div>
                  <div className="py-1">
                    {[
                      { value: 'manual', label: 'Manual (stay active until toggled)', desc: 'You control when to deactivate' },
                      { value: 'days', label: 'Auto-disable after X days', desc: 'Set a specific time period' },
                      { value: 'shortlist', label: 'Auto-disable after N shortlisted', desc: 'Close when target is reached' },
                    ].map((opt) => (
                      <button
                        key={opt.value}
                        type="button"
                        onClick={() => {
                          setCareerActivationMode(opt.value as any);
                          if (opt.value === 'days') {
                            const now = new Date();
                            now.setDate(now.getDate() + (careerActivationDays || DEFAULT_EXPIRATION_OFFSET_DAYS));
                            setExpirationDate(now.toISOString().substring(0, 16));
                          }
                          setCareerActivationOpen(false);
                        }}
                        className={`w-full text-left px-4 py-3 hover:bg-blue-50 transition-colors ${
                          careerActivationMode === opt.value ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                        }`}
                      >
                        <div className="font-medium text-sm">{opt.label}</div>
                        <div className="text-xs text-gray-500 mt-0.5">{opt.desc}</div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Days Input & Expiration Date (only shown when days mode selected) */}
          {careerActivationMode === 'days' && (
            <div className="bg-blue-50/50 rounded-lg p-4 border border-blue-100 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Number of Days
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="number"
                    min={1}
                    value={careerActivationDays}
                    onChange={(e) => {
                      const val = Math.max(1, Number(e.target.value) || 1);
                      setCareerActivationDays(val);
                      const now = new Date();
                      now.setDate(now.getDate() + val);
                      setExpirationDate(now.toISOString().substring(0, 16));
                    }}
                    className="w-24 bg-white border-2 border-gray-200 rounded-lg px-3 py-2 text-base focus:outline-none focus:border-blue-400"
                  />
                  <span className="text-sm text-gray-600">days on Career page</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-2">
                  Active Till (Expiration Date) <span className="text-red-500">*</span>
                </label>
                <input
                  type="datetime-local"
                  value={expirationDate}
                  onChange={(e) => {
                    setExpirationDate(e.target.value);
                    setErrors((prev) => ({ ...prev, active_till: "" }));
                    // Sync days
                    try {
                      const now = new Date();
                      const then = new Date(e.target.value);
                      const diffDays = Math.max(1, Math.round((then.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)));
                      setCareerActivationDays(diffDays);
                    } catch {
                      // no-op
                    }
                  }}
                  className={`w-full bg-white border-2 rounded-lg px-4 py-3 text-base focus:outline-none focus:border-indigo-400 transition-all duration-200 ${
                    errors.active_till ? 'border-red-400 bg-red-50/30' : 'border-gray-200 hover:border-gray-300'
                  }`}
                />
                <p className="text-xs text-blue-600 mt-2">
                  Auto-calculated from {careerActivationDays} days
                </p>
                {renderErrorMessage('active_till')}
              </div>
            </div>
          )}

          {/* Shortlist Threshold (if shortlist mode selected) */}
          {careerActivationMode === 'shortlist' && (
            <div className="bg-green-50/50 rounded-lg p-4 border border-green-100">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Shortlist Target
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  min={1}
                  value={careerShortlistThreshold}
                  onChange={(e) => setCareerShortlistThreshold(Math.max(1, Number(e.target.value) || 1))}
                  className="w-24 bg-white border-2 border-gray-200 rounded-lg px-3 py-2 text-base focus:outline-none focus:border-green-400"
                />
                <span className="text-sm text-gray-600">shortlisted candidates to auto-close</span>
              </div>
            </div>
          )}

          {/* Info Box */}
          <div className="bg-white rounded-lg p-4 border border-blue-200">
            <div className="flex items-start gap-3">
              <div className="w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-blue-600 text-xs">ℹ️</span>
              </div>
              <div className="text-sm text-gray-600">
                <p className="font-medium text-gray-700 mb-1">How it works:</p>
                <ul className="space-y-1 text-xs">
                  <li>• <strong>Manual:</strong> Job stays active until you manually toggle it off</li>
                  <li>• <strong>Days:</strong> Job auto-deactivates after specified days</li>
                  <li>• <strong>Shortlist:</strong> Job auto-closes when target candidates are shortlisted</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Inactive State Message */}
      {!isActive && (
        <div className="pt-4 border-t border-blue-100">
          <div className="bg-gray-50 rounded-lg p-4 text-center">
            <p className="text-sm text-gray-600">
              This job post is currently <strong>inactive</strong> and will not appear on your Career page.
            </p>
          </div>
        </div>
      )}
    </div>
  </div>
</div>


                </div>

                <div className="flex justify-center pt-8 border-t border-gray-100">
                  <button
                    onClick={handleSubmitJobPost}
                    disabled={isSubmitting}
                    className="inline-flex items-center justify-center gap-3 px-8 py-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl shadow-lg hover:shadow-xl hover:from-blue-700 hover:to-blue-800 transition-all duration-200 disabled:opacity-75 disabled:cursor-not-allowed font-semibold text-base"
                    style={{ minWidth: 220 }}
                  >
                    {isSubmitting ? (
                        <>
                            <Loader2 size={18} className="animate-spin" /> <span>Saving...</span>
                        </>
                    ) : isEditMode ? (
                        "Save Changes"
                    ) : (
                        "Create Job Post"
                    )}
                  </button>
                </div>
              </>
            )}
 
            {activeTab === 'upload' && !isEditMode && (
              <div className="mt-6 space-y-6 flex flex-col items-center justify-center min-h-[400px]">
               
                <FileUpload
                    onFileSelect={handleFileSelect}
                    className="w-full max-w-lg mx-auto p-12 sm:p-20 border-dashed border-2 border-blue-400 rounded-xl text-center text-gray-500 cursor-pointer hover:border-blue-600 transition-colors flex flex-col items-center justify-center hover:shadow-lg"
                >
                    {isUploading ? (
                      <div className="flex items-center justify-center flex-col text-blue-600">
                        <Loader2 size={32} className="animate-spin mb-3" />
                        <span className="text-lg">Uploading and Analyzing...</span>
                      </div>
                    ) : (
                      <>
                        <Upload size={32} className="text-gray-600 mb-3" />
                        <span className="text-blue-600 font-semibold text-lg mb-1">Click or Drag to Upload File</span>
                        <span className="text-sm text-gray-500">(PDF / DOCX Max 5MB)</span>
                      </>
                    )}
                  </FileUpload>
 
                  {uploadStatus && (
                    <div className={`text-center text-sm p-3 rounded-lg w-full max-w-lg ${
                        uploadStatus.includes('failed') ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'
                      }`}>
                      {uploadStatus}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
  );
};

export default JobPostsForm;
