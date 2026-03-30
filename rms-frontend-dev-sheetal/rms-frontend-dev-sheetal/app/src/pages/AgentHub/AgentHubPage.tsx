import React, { useState, useMemo, useEffect } from 'react';
import Layout from '../../components/layout/Layout';
import {
  Bot,
  Search,
  Briefcase,
  Settings2,
  Save,
  Plus,
  X,
  Mic,
  Brain,
  MessageSquare,
  Sparkles,
  ChevronDown,
  Loader2, // For loading spinners
} from 'lucide-react';
// --- Import API functions ---
import { getMyAgentJobs, saveAgentConfig } from '../../api/jobApi';
import { useToast } from '../../context/ToastContext'; // Assuming you have a Toast context

// --- INTERFACES ---

// This is the configuration for a *single round*
interface AgentRoundConfig {
  id: string; // This will be the AgentRoundConfig.id from the DB
  roundListId: string; // This is the RoundList.id (the round definition)
  jobId: string; // The JobDetails.id
  roundName: string;
  roundFocus: string;
  persona: 'alex' | 'dr-evan' | 'sam';
  keySkills: string[];
  customQuestions: string[];
  forbiddenTopics: string[];
  codingEnabled: boolean;
  codingQuestionMode: 'ai' | 'provided';
  codingDifficulty: 'easy' | 'medium' | 'hard';
  codingLanguages: string[];
  providedCodingQuestion: string;
  codingTestCaseMode: 'ai' | 'provided';
  codingTestCases: any[];
  codingStarterCode: Record<string, string>;
  mcqEnabled: boolean;
  mcqQuestionMode: 'ai' | 'provided';
  mcqDifficulty: 'easy' | 'medium' | 'hard';
  mcqQuestions: any[];
  mcqPassingScore: number;
}

// This is the *job definition* for a single round
interface JobRound {
  id: string; // RoundList.id
  name: string;
  order: number;
  description: string;
}

// This is the main Job object we fetch and list
interface AgentEnabledJob {
  id: string; // JobDetails.id
  title: string;
  department: string;
  // This is the list of *defined* rounds for the job (from round_list)
  interview_rounds: JobRound[];
  // This is the list of *saved configurations* for those rounds
  agentRounds: AgentRoundConfig[];
}

// --- STYLING CONSTANTS (for shadcn-like components) ---
const cardClasses =
  'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-sm';
const inputClasses =
  'w-full px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-500';
const labelClasses =
  'block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5';
const buttonClasses = {
  primary:
    'inline-flex items-center justify-center px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed',
  secondary:
    'inline-flex items-center justify-center px-4 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 text-sm font-medium rounded-md shadow-sm hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500',
  icon: 'p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md',
};
const badgeClasses =
  'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
const tabsTriggerClasses = (isActive: boolean) =>
  `px-4 py-2.5 text-sm font-medium rounded-md transition-colors
  ${
    isActive
      ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
      : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
  }`;

// --- SUB-COMPONENTS (All in one file) ---

/**
 * Left-hand list of agent-enabled jobs
 */
const JobList: React.FC<{
  jobs: AgentEnabledJob[];
  selectedJobId: string | null;
  onSelectJob: (id: string) => void;
  onSearch: (term: string) => void;
}> = ({ jobs, selectedJobId, onSelectJob, onSearch }) => {
  return (
    <div className={`${cardClasses} h-full flex flex-col`}>
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
          <Briefcase className="w-5 h-5 mr-2 text-blue-500" />
          Agent-Enabled Jobs
        </h2>
        <div className="relative mt-3">
          <input
            type="text"
            placeholder="Search jobs..."
            className={`${inputClasses} pl-10`}
            onChange={(e) => onSearch(e.target.value)}
          />
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 dark:text-gray-500" />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {jobs.length > 0 ? (
          jobs.map((job) => (
            <button
              key={job.id}
              onClick={() => onSelectJob(job.id)}
              className={`
                w-full text-left p-3 rounded-lg transition-colors
                ${
                  selectedJobId === job.id
                    ? 'bg-blue-50 dark:bg-blue-900/50'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                }
              `}
            >
              <h3
                className={`font-medium ${
                  selectedJobId === job.id
                    ? 'text-blue-600 dark:text-blue-300'
                    : 'text-gray-800 dark:text-gray-100'
                }`}
              >
                {job.title}
              </h3>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {job.department || 'No Department'}
              </p>
              <span className="mt-2 text-xs text-gray-400 dark:text-gray-500 flex items-center">
                <Bot className="w-3.5 h-3.5 mr-1.5" />
                {job.interview_rounds.length} Agent Round
                {job.interview_rounds.length !== 1 ? 's' : ''}
              </span>
            </button>
          ))
        ) : (
          <div className="p-4 text-center text-gray-500 dark:text-gray-400">
            No agent-enabled jobs found.
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Tag input component for skills and topics
 */
const TagInput: React.FC<{
  label: string;
  tags: string[];
  setTags: (newTags: string[]) => void;
  placeholder: string;
}> = ({ label, tags, setTags, placeholder }) => {
  const [inputValue, setInputValue] = useState('');

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const newTag = inputValue.trim();
      if (newTag && !tags.includes(newTag)) {
        setTags([...tags, newTag]);
      }
      setInputValue('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    setTags(tags.filter((tag) => tag !== tagToRemove));
  };

  return (
    <div>
      <label className={labelClasses}>{label}</label>
      <div
        className={`${inputClasses} h-auto min-h-[40px] flex flex-wrap items-center gap-1.5 p-2`}
      >
        {tags.map((tag) => (
          <span
            key={tag}
            className={`${badgeClasses} flex items-center gap-1 cursor-default`}
          >
            {tag}
            <button
              type="button"
              onClick={() => removeTag(tag)}
              className="text-blue-600 dark:text-blue-300 hover:text-blue-800 dark:hover:text-blue-100"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </span>
        ))}
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="flex-1 bg-transparent text-sm outline-none focus:ring-0 border-0 p-0 min-w-[120px]"
        />
      </div>
    </div>
  );
};

const JsonEditor: React.FC<{
  label: string;
  value: any;
  onChange: (value: any) => void;
  format: 'array' | 'object';
  helperText?: string;
  rows?: number;
}> = ({ label, value, onChange, format, helperText, rows = 8 }) => {
  const [draft, setDraft] = useState('');
  const [parseError, setParseError] = useState('');

  useEffect(() => {
    const fallback = format === 'array' ? [] : {};
    try {
      const next = value ?? fallback;
      setDraft(JSON.stringify(next, null, 2));
      setParseError('');
    } catch {
      setDraft(JSON.stringify(fallback, null, 2));
      setParseError('');
    }
  }, [value, format]);

  const handleBlur = () => {
    const fallback = format === 'array' ? [] : {};
    try {
      const parsed = draft.trim() ? JSON.parse(draft) : fallback;
      const validArray = format === 'array' && Array.isArray(parsed);
      const validObject =
        format === 'object' && typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed);

      if (!validArray && !validObject) {
        setParseError(`Expected a JSON ${format}.`);
        return;
      }

      onChange(parsed);
      setParseError('');
    } catch {
      setParseError('Invalid JSON. Fix syntax before saving.');
    }
  };

  return (
    <div>
      <label className={labelClasses}>{label}</label>
      <textarea
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={handleBlur}
        rows={rows}
        spellCheck={false}
        className={`${inputClasses} font-mono text-xs`}
      />
      {helperText && <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">{helperText}</p>}
      {parseError && <p className="mt-1.5 text-xs text-red-600">{parseError}</p>}
    </div>
  );
};

/**
 * Custom Dropdown for Persona Selection
 */
const PersonaSelector: React.FC<{
  persona: string;
  setPersona: (persona: 'alex' | 'dr-evan' | 'sam') => void;
}> = ({ persona, setPersona }) => {
  const [isOpen, setIsOpen] = useState(false);
  const personas = {
    alex: {
      name: 'Alex (Friendly & Professional)',
      icon: Sparkles,
      desc: 'Balanced, warm, and goal-oriented. The default choice.',
    },
    'dr-evan': {
      name: 'Dr. Evan (Formal & In-Depth)',
      icon: Brain,
      desc: 'Technical, precise, and analytical. Best for senior roles.',
    },
    sam: {
      name: 'Sam (Casual & Energetic)',
      icon: Mic,
      desc: 'Enthusiastic and conversational. Good for culture-fit rounds.',
    },
  };

  const selectedPersona = personas[persona as keyof typeof personas] || personas.alex;
  const Icon = selectedPersona.icon;

  return (
    <div>
      <label className={labelClasses}>Agent Persona</label>
      <div className="relative">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className={`${inputClasses} flex items-center justify-between text-left`}
        >
          <span className="flex items-center">
            <Icon className="w-5 h-5 mr-2 text-blue-500" />
            <span className="text-gray-900 dark:text-white">
              {selectedPersona.name}
            </span>
          </span>
          <ChevronDown
            className={`w-5 h-5 text-gray-400 transition-transform ${
              isOpen ? 'rotate-180' : ''
            }`}
          />
        </button>
        {isOpen && (
          <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md shadow-lg">
            {Object.entries(personas).map(([key, p]) => (
              <button
                key={key}
                type="button"
                onClick={() => {
                  setPersona(key as 'alex' | 'dr-evan' | 'sam');
                  setIsOpen(false);
                }}
                className="w-full text-left px-4 py-3 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-start"
              >
                <p.icon className="w-5 h-5 mr-3 mt-0.5 text-blue-500" />
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {p.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {p.desc}
                  </p>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Right-hand panel for configuring the selected job's agent
 */
const AgentConfigurator: React.FC<{
  job: AgentEnabledJob;
  onSave: (updatedConfigs: AgentRoundConfig[]) => void;
}> = ({ job, onSave }) => {
// Use the toast context but guard against varying context shapes
const toast = useToast();
const addToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const maybeAdd = (toast as unknown as { addToast?: (msg: string, variant?: string) => void }).addToast;
    if (maybeAdd) {
        maybeAdd(message, type);
    } else {
        // Fallback for environments where the toast API differs — keep a minimal fallback
        if (type === 'error') console.error(message);
        else console.log(message);
    }
};
  // Local state for the form, initialized from the prop
  const [config, setConfig] = useState<AgentEnabledJob>(job);
  // Active tab is the *RoundList.id* of the defined round
  const [activeRoundTab, setActiveRoundTab] = useState<string>(
    job.interview_rounds?.[0]?.id || ''
  );
  const [isSaving, setIsSaving] = useState(false);

  // This effect syncs the local state with the selected job from the parent
  // It also creates default "in-memory" configs for rounds that don't have one
  React.useEffect(() => {
    // Transform the job data into the state shape
    // We need to create config objects for rounds that don't have one yet
    const agentRoundsWithDefaults: AgentRoundConfig[] = (job.interview_rounds || []).map(
      (jobRound) => {
        // Find the saved config for this round
        const savedConfig = (job.agentRounds || []).find(
          (c) => c.roundListId === jobRound.id
        );

        if (savedConfig) {
          return {
            ...savedConfig,
            codingEnabled: Boolean(savedConfig.codingEnabled ?? false),
            codingQuestionMode: (savedConfig.codingQuestionMode || 'ai') as 'ai' | 'provided',
            codingDifficulty: (savedConfig.codingDifficulty || 'medium') as 'easy' | 'medium' | 'hard',
            codingLanguages: savedConfig.codingLanguages || ['python'],
            providedCodingQuestion: savedConfig.providedCodingQuestion || '',
            codingTestCaseMode: (savedConfig.codingTestCaseMode || 'provided') as 'ai' | 'provided',
            codingTestCases: Array.isArray(savedConfig.codingTestCases) ? savedConfig.codingTestCases : [],
            codingStarterCode:
              savedConfig.codingStarterCode && typeof savedConfig.codingStarterCode === 'object'
                ? savedConfig.codingStarterCode
                : {},
            mcqEnabled: Boolean(savedConfig.mcqEnabled ?? false),
            mcqQuestionMode: (savedConfig.mcqQuestionMode || 'provided') as 'ai' | 'provided',
            mcqDifficulty: (savedConfig.mcqDifficulty || 'medium') as 'easy' | 'medium' | 'hard',
            mcqQuestions: Array.isArray(savedConfig.mcqQuestions) ? savedConfig.mcqQuestions : [],
            mcqPassingScore: Number(savedConfig.mcqPassingScore ?? 60) || 60,
          } as AgentRoundConfig;
        }

        // No saved config, create a default one
        return {
          id: `new_${jobRound.id}`, // Temporary ID
          roundListId: jobRound.id,
          jobId: job.id,
          roundName: jobRound.name,
          roundFocus: jobRound.description || `Focus on ${jobRound.name}`,
          persona: 'alex',
          keySkills: [],
          customQuestions: [],
          forbiddenTopics: [],
          codingEnabled: false,
          codingQuestionMode: 'ai',
          codingDifficulty: 'medium',
          codingLanguages: ['python'],
          providedCodingQuestion: '',
          codingTestCaseMode: 'provided',
          codingTestCases: [],
          codingStarterCode: {},
          mcqEnabled: false,
          mcqQuestionMode: 'provided',
          mcqDifficulty: 'medium',
          mcqQuestions: [],
          mcqPassingScore: 60,
        } as AgentRoundConfig;
      }
    );

    setConfig({
      ...job,
      agentRounds: agentRoundsWithDefaults,
    });
    
    // Set active tab to the first round
    setActiveRoundTab(job.interview_rounds?.[0]?.id || '');

  }, [job]);

  const handleSave = async () => {
    setIsSaving(true);
    
    // --- API CALL ---
    // We send the `config.agentRounds` array to the backend
    const result = await saveAgentConfig(config.id, config.agentRounds);

    if (result.success) {
      // API returns the saved configs (with real DB IDs)
      const savedConfigs = result.data.agentRounds;
      addToast('Configuration saved successfully!', 'success');
      onSave(savedConfigs); // Pass new configs up to parent state
    } else {
      addToast(`Error saving: ${result.error}`, 'error');
    }
    // --- END API CALL ---
    
    setIsSaving(false);
  };

  // --- Form Update Handlers ---
  const updateRoundConfig = (
    roundListId: string, // <-- Key is the RoundList.id
    field: keyof AgentRoundConfig,
    value: any
  ) => {
    setConfig((prevConfig) => ({
      ...prevConfig,
      agentRounds: prevConfig.agentRounds.map((round) =>
        round.roundListId === roundListId ? { ...round, [field]: value } : round
      ),
    }));
  };

  const addCustomQuestion = (roundListId: string, question: string) => {
    const newQuestion = question.trim();
    if (!newQuestion) return;

    setConfig((prevConfig) => ({
      ...prevConfig,
      agentRounds: prevConfig.agentRounds.map((round) =>
        round.roundListId === roundListId
          ? {
              ...round,
              customQuestions: [...round.customQuestions, newQuestion],
            }
          : round
      ),
    }));
  };

  const removeCustomQuestion = (roundListId: string, indexToRemove: number) => {
    setConfig((prevConfig) => ({
      ...prevConfig,
      agentRounds: prevConfig.agentRounds.map((round) =>
        round.roundListId === roundListId
          ? {
              ...round,
              customQuestions: round.customQuestions.filter(
                (_, i) => i !== indexToRemove
              ),
            }
          : round
      ),
    }));
  };
  // --- End Handlers ---

  // Find the active config *object* based on the active tab (which is a roundListId)
  const activeRoundConfig = config.agentRounds.find(
    (r) => r.roundListId === activeRoundTab
  );

  return (
    <div className={`${cardClasses} h-full flex flex-col`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
          <Settings2 className="w-5 h-5 mr-2 text-blue-500" />
          Configure Agent
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">{job.title}</p>
      </div>

      {/* Round Tabs - Iterate over DEFINED rounds */}
      <div className="p-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center space-x-1 p-1 bg-gray-200 dark:bg-gray-900 rounded-lg">
          {(config.interview_rounds || []).map((round) => (
            <button
              key={round.id}
              onClick={() => setActiveRoundTab(round.id)}
              className={tabsTriggerClasses(activeRoundTab === round.id)}
            >
              {round.name}
            </button>
          ))}
        </div>
      </div>

      {/* Configuration Form */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {!activeRoundConfig ? (
          <div className="text-center text-gray-500 dark:text-gray-400 p-8">
            <Bot className="w-12 h-12 mx-auto text-gray-400" />
            <p className="mt-2 font-medium">No round selected</p>
            <p className="text-sm">Select a round from the tabs above to configure it.</p>
          </div>
        ) : (
          <>
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
              {activeRoundConfig.roundName}
            </h3>

            {/* Persona Selector */}
            <PersonaSelector
              persona={activeRoundConfig.persona}
              setPersona={(p) =>
                updateRoundConfig(activeRoundConfig.roundListId, 'persona', p)
              }
            />

            {/* Round Focus */}
            <div>
              <label htmlFor="roundFocus" className={labelClasses}>
                Round Focus (Main Prompt)
              </label>
              <textarea
                id="roundFocus"
                rows={3}
                className={inputClasses}
                placeholder="e.g., Focus on core Python, data structures, and algorithms."
                value={activeRoundConfig.roundFocus}
                onChange={(e) =>
                  updateRoundConfig(
                    activeRoundConfig.roundListId,
                    'roundFocus',
                    e.target.value
                  )
                }
              />
              <p className="mt-1.5 text-xs text-gray-500 dark:text-gray-400">
                This is the main instruction for the agent's objective in this
                round.
              </p>
            </div>

            {/* Key Skills */}
            <TagInput
              label="Key Skills to Probe"
              tags={activeRoundConfig.keySkills}
              setTags={(newTags) =>
                updateRoundConfig(activeRoundConfig.roundListId, 'keySkills', newTags)
              }
              placeholder="Add skill and press Enter..."
            />

            {/* Forbidden Topics */}
            <TagInput
              label="Forbidden Topics"
              tags={activeRoundConfig.forbiddenTopics}
              setTags={(newTags) =>
                updateRoundConfig(activeRoundConfig.roundListId, 'forbiddenTopics', newTags)
              }
              placeholder="Add topic and press Enter..."
            />

            {/* Custom Questions */}
            <div>
              <label className={labelClasses}>Mandatory Custom Questions</label>
              <div className="space-y-2">
                {activeRoundConfig.customQuestions.map((q, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <MessageSquare className="w-5 h-5 text-gray-400 flex-shrink-0" />
                    <p className="flex-1 text-sm text-gray-800 dark:text-gray-200">
                      {q}
                    </p>
                    <button
                      type="button"
                      onClick={() =>
                        removeCustomQuestion(activeRoundConfig.roundListId, index)
                      }
                      className={buttonClasses.icon}
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
              <CustomQuestionAdder
                onAdd={(q) => addCustomQuestion(activeRoundConfig.roundListId, q)}
              />
            </div>

            <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-white">Coding Challenge</h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Enable coding challenge with language control, starter code, and test-case evaluation.
                  </p>
                </div>
                <label className="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input
                    type="checkbox"
                    checked={activeRoundConfig.codingEnabled}
                    onChange={(e) =>
                      updateRoundConfig(activeRoundConfig.roundListId, 'codingEnabled', e.target.checked)
                    }
                  />
                  Enabled
                </label>
              </div>

              {activeRoundConfig.codingEnabled && (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                      <label className={labelClasses}>Question Mode</label>
                      <select
                        value={activeRoundConfig.codingQuestionMode}
                        onChange={(e) =>
                          updateRoundConfig(
                            activeRoundConfig.roundListId,
                            'codingQuestionMode',
                            e.target.value as 'ai' | 'provided'
                          )
                        }
                        className={inputClasses}
                      >
                        <option value="ai">AI Generated</option>
                        <option value="provided">Admin Provided</option>
                      </select>
                    </div>
                    <div>
                      <label className={labelClasses}>Difficulty</label>
                      <select
                        value={activeRoundConfig.codingDifficulty}
                        onChange={(e) =>
                          updateRoundConfig(
                            activeRoundConfig.roundListId,
                            'codingDifficulty',
                            e.target.value as 'easy' | 'medium' | 'hard'
                          )
                        }
                        className={inputClasses}
                      >
                        <option value="easy">Easy</option>
                        <option value="medium">Medium</option>
                        <option value="hard">Hard</option>
                      </select>
                    </div>
                    <div>
                      <label className={labelClasses}>Test Case Mode</label>
                      <select
                        value={activeRoundConfig.codingTestCaseMode}
                        onChange={(e) =>
                          updateRoundConfig(
                            activeRoundConfig.roundListId,
                            'codingTestCaseMode',
                            e.target.value as 'ai' | 'provided'
                          )
                        }
                        className={inputClasses}
                      >
                        <option value="provided">Preconfigured</option>
                        <option value="ai">AI Generated</option>
                      </select>
                    </div>
                  </div>

                  <TagInput
                    label="Allowed Coding Languages"
                    tags={activeRoundConfig.codingLanguages}
                    setTags={(newTags) =>
                      updateRoundConfig(activeRoundConfig.roundListId, 'codingLanguages', newTags)
                    }
                    placeholder="Add language and press Enter..."
                  />

                  <JsonEditor
                    label="Starter Code (JSON object keyed by language)"
                    value={activeRoundConfig.codingStarterCode}
                    format="object"
                    onChange={(parsed) =>
                      updateRoundConfig(activeRoundConfig.roundListId, 'codingStarterCode', parsed)
                    }
                    helperText='Example: {"python":"def solve(input_data):\\n    return None"}'
                    rows={7}
                  />

                  {activeRoundConfig.codingQuestionMode === 'provided' && (
                    <div>
                      <label className={labelClasses}>Provided Coding Question</label>
                      <textarea
                        rows={5}
                        className={inputClasses}
                        placeholder="Paste the exact coding question candidates should solve."
                        value={activeRoundConfig.providedCodingQuestion}
                        onChange={(e) =>
                          updateRoundConfig(
                            activeRoundConfig.roundListId,
                            'providedCodingQuestion',
                            e.target.value
                          )
                        }
                      />
                    </div>
                  )}

                  {activeRoundConfig.codingTestCaseMode === 'provided' && (
                    <JsonEditor
                      label="Preconfigured Coding Test Cases"
                      value={activeRoundConfig.codingTestCases}
                      format="array"
                      onChange={(parsed) =>
                        updateRoundConfig(activeRoundConfig.roundListId, 'codingTestCases', parsed)
                      }
                      helperText='Example item: {"input":"1 2","expectedOutput":"3","isHidden":false,"weight":2}'
                      rows={8}
                    />
                  )}
                </>
              )}
            </div>

            <div className="rounded-lg border border-gray-200 dark:border-gray-700 p-4 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-semibold text-gray-900 dark:text-white">MCQ Challenge</h4>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Enable objective MCQ round with configurable passing score and question bank.
                  </p>
                </div>
                <label className="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <input
                    type="checkbox"
                    checked={activeRoundConfig.mcqEnabled}
                    onChange={(e) =>
                      updateRoundConfig(activeRoundConfig.roundListId, 'mcqEnabled', e.target.checked)
                    }
                  />
                  Enabled
                </label>
              </div>

              {activeRoundConfig.mcqEnabled && (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div>
                      <label className={labelClasses}>Question Mode</label>
                      <select
                        value={activeRoundConfig.mcqQuestionMode}
                        onChange={(e) =>
                          updateRoundConfig(
                            activeRoundConfig.roundListId,
                            'mcqQuestionMode',
                            e.target.value as 'ai' | 'provided'
                          )
                        }
                        className={inputClasses}
                      >
                        <option value="provided">Preconfigured</option>
                        <option value="ai">AI Generated</option>
                      </select>
                    </div>

                    <div>
                      <label className={labelClasses}>Difficulty</label>
                      <select
                        value={activeRoundConfig.mcqDifficulty}
                        onChange={(e) =>
                          updateRoundConfig(
                            activeRoundConfig.roundListId,
                            'mcqDifficulty',
                            e.target.value as 'easy' | 'medium' | 'hard'
                          )
                        }
                        className={inputClasses}
                      >
                        <option value="easy">Easy</option>
                        <option value="medium">Medium</option>
                        <option value="hard">Hard</option>
                      </select>
                    </div>

                    <div>
                      <label className={labelClasses}>Passing Score (%)</label>
                      <input
                        type="number"
                        min={0}
                        max={100}
                        value={activeRoundConfig.mcqPassingScore}
                        onChange={(e) => {
                          const raw = Number(e.target.value);
                          const next = Number.isFinite(raw) ? Math.max(0, Math.min(100, raw)) : 60;
                          updateRoundConfig(activeRoundConfig.roundListId, 'mcqPassingScore', next);
                        }}
                        className={inputClasses}
                      />
                    </div>
                  </div>

                  {activeRoundConfig.mcqQuestionMode === 'provided' && (
                    <JsonEditor
                      label="Preconfigured MCQ Questions"
                      value={activeRoundConfig.mcqQuestions}
                      format="array"
                      onChange={(parsed) =>
                        updateRoundConfig(activeRoundConfig.roundListId, 'mcqQuestions', parsed)
                      }
                      helperText='Example item: {"question":"...","options":["A","B","C","D"],"answer":"A"}'
                      rows={10}
                    />
                  )}
                </>
              )}
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
        <div className="flex justify-end space-x-3">
          <button type="button" className={buttonClasses.secondary} disabled={isSaving}>
            Reset Changes
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={isSaving}
            className={buttonClasses.primary}
          >
            {isSaving ? (
              <>
                <Loader2 className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                Save Configuration
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

const CustomQuestionAdder: React.FC<{
  onAdd: (question: string) => void;
}> = ({ onAdd }) => {
  const [question, setQuestion] = useState('');

  const handleAdd = () => {
    if (question.trim()) {
      onAdd(question);
      setQuestion('');
    }
  };

  return (
    <div className="flex items-center gap-2 mt-3">
      <input
        type="text"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
        placeholder="Add a mandatory question..."
        className={inputClasses}
      />
      <button
        type="button"
        onClick={handleAdd}
        className={`${buttonClasses.primary} px-3`}
      >
        <Plus className="w-5 h-5" />
      </button>
    </div>
  );
};

/**
 * Main Page Component
 */
const AgentHubPageInner: React.FC = () => {
  const [allJobs, setAllJobs] = useState<AgentEnabledJob[]>([]); // <-- Real state
  const [isLoading, setIsLoading] = useState(true); // <-- Loading state
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  // Use the toast context but guard against varying context shapes
  const toast = useToast();
  const addToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const maybeAdd = (toast as unknown as { addToast?: (msg: string, variant?: string) => void }).addToast;
    if (maybeAdd) {
      maybeAdd(message, type);
    } else {
      // Fallback for environments where the toast API differs — keep a minimal fallback
      if (type === 'error') console.error(message);
      else console.log(message);
    }
  };

  // --- Data Fetching Function ---
  const fetchAgentJobs = async () => {
    setIsLoading(true);
    const result = await getMyAgentJobs();
    if (result.success) {
      // Normalize backend shape to frontend expectations.
      const rawJobs = result.data.jobs || [];
      const normalized = rawJobs.map((j: any) => {
        const normalizedRounds = (j.interview_rounds || j.interviewRounds || j.rounds || []).map((r: any) => ({
          id: String(r.id || r.round_id || r.roundId || ''),
          name: r.name || r.round_name || r.roundName || 'Round',
          order: Number(r.order || r.round_order || r.roundOrder || 1),
          description: r.description || r.round_description || r.roundFocus || '',
        }));

        const normalizedAgentRounds = (j.agentRounds || j.agent_rounds || j.agent_configs || []).map((r: any) => ({
          id: String(r.id || `new_${r.roundListId || r.round_list_id || ''}`),
          roundListId: String(r.roundListId || r.round_list_id || ''),
          jobId: String(r.jobId || r.job_id || j.job_id || j.id || ''),
          roundName: r.roundName || r.round_name || 'Configured Round',
          roundFocus: r.roundFocus || r.round_focus || '',
          persona: (r.persona || 'alex') as 'alex' | 'dr-evan' | 'sam',
          keySkills: r.keySkills || r.key_skills || [],
          customQuestions: r.customQuestions || r.custom_questions || [],
          forbiddenTopics: r.forbiddenTopics || r.forbidden_topics || [],
          codingEnabled: Boolean(r.codingEnabled ?? r.coding_enabled ?? false),
          codingQuestionMode: (r.codingQuestionMode || r.coding_question_mode || 'ai') as 'ai' | 'provided',
          codingDifficulty: (r.codingDifficulty || r.coding_difficulty || 'medium') as 'easy' | 'medium' | 'hard',
          codingLanguages: r.codingLanguages || r.coding_languages || ['python'],
          providedCodingQuestion: r.providedCodingQuestion || r.provided_coding_question || '',
          codingTestCaseMode: (r.codingTestCaseMode || r.coding_test_case_mode || 'provided') as 'ai' | 'provided',
          codingTestCases: r.codingTestCases || r.coding_test_cases || [],
          codingStarterCode: r.codingStarterCode || r.coding_starter_code || {},
          mcqEnabled: Boolean(r.mcqEnabled ?? r.mcq_enabled ?? false),
          mcqQuestionMode: (r.mcqQuestionMode || r.mcq_question_mode || 'provided') as 'ai' | 'provided',
          mcqDifficulty: (r.mcqDifficulty || r.mcq_difficulty || 'medium') as 'easy' | 'medium' | 'hard',
          mcqQuestions: r.mcqQuestions || r.mcq_questions || [],
          mcqPassingScore: Number(r.mcqPassingScore ?? r.mcq_passing_score ?? 60) || 60,
        }));

        return {
          // keep any other fields for backward compatibility
          ...j,
          id: String(j.job_id || j.id || j.jobId || ''),
          title: j.title || j.job_title || j.jobTitle || 'Untitled Job',
          department: j.department || j.department_name || null,
          interview_rounds: normalizedRounds,
          agentRounds: normalizedAgentRounds,
        };
      });
      setAllJobs(normalized);
      // Select the first job by default
      if (normalized.length > 0) {
        setSelectedJobId(normalized[0].id);
      } else {
        setSelectedJobId(null);
      }
    } else {
      addToast(`Error fetching agent jobs: ${result.error}`, 'error');
      setAllJobs([]);
    }
    setIsLoading(false);
  };

  // --- Fetch on Mount ---
  useEffect(() => {
    fetchAgentJobs();
  }, []);

  const filteredJobs = useMemo(() => {
    const term = (searchTerm || '').toString().toLowerCase();
    if (!term) return allJobs;

    return allJobs.filter((job) => {
      const title = (job.title || '').toString().toLowerCase();
      const dept = (job.department || '').toString().toLowerCase();
      return title.includes(term) || dept.includes(term);
    });
  }, [allJobs, searchTerm]);

  const selectedJob = useMemo(() => {
    return allJobs.find((job) => job.id === selectedJobId) || null;
  }, [allJobs, selectedJobId]);

  // This function is called by the child configurator AFTER a successful save
  const handleSaveConfig = (updatedAgentRounds: AgentRoundConfig[]) => {
    // Update the local state for the job that was just saved
    setAllJobs(prevJobs =>
      prevJobs.map(job =>
        job.id === selectedJobId
          ? { ...job, agentRounds: updatedAgentRounds }
          : job
      )
    );
  };

  const content = (
    <>
      <div className="mb-4">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center">
          <Bot className="w-8 h-8 mr-3 text-blue-600" />
          Interview Agent Hub
        </h1>
        <p className="mt-1 text-base text-gray-600 dark:text-gray-400">
          Configure and manage your AI interview agents for each job post.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Job List */}
        <div className="lg:col-span-1 h-full min-h-[600px]">
          <JobList
            jobs={filteredJobs}
            selectedJobId={selectedJobId}
            onSelectJob={setSelectedJobId}
            onSearch={setSearchTerm}
          />
        </div>

        {/* Right Column: Configurator */}
        <div className="lg:col-span-2 h-full min-h-[600px]">
          {isLoading ? (
            <div className={`${cardClasses} h-full flex items-center justify-center`}>
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
              <p className="ml-3 text-gray-600 dark:text-gray-300">Loading Agent Jobs...</p>
            </div>
          ) : selectedJob ? (
            <AgentConfigurator 
              job={selectedJob} 
              onSave={handleSaveConfig} 
            />
          ) : (
            <div
              className={`${cardClasses} h-full flex items-center justify-center`}
            >
              <div className="text-center p-8">
                <Briefcase className="w-12 h-12 text-gray-400 mx-auto" />
                <h3 className="mt-2 text-lg font-medium text-gray-900 dark:text-white">
                  No Agent-Enabled Jobs Found
                </h3>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  Create a job and enable "Agent Interview" to configure it here.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  );

  return content;
};

const AgentHubPage: React.FC = () => {
  return (
    <Layout
      bannerTitle="Interview Agent Hub"
      bannerSubtitle="Configure and manage your AI interview agents for each job post."
      searchPlaceholder="Search jobs..."
    >
      <AgentHubPageInner />
    </Layout>
  );
};

export default AgentHubPage;