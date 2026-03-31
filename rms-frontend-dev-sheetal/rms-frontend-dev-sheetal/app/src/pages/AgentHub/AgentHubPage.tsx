import React, { useEffect, useMemo, useState } from 'react';
import Layout from '../../components/layout/Layout';
import {
  Bot,
  Search,
  Briefcase,
  Save,
  Plus,
  X,
  Mic,
  Brain,
  MessageSquare,
  Sparkles,
  ChevronDown,
  Loader2,
} from 'lucide-react';
import clsx from 'clsx';
import { getMyAgentJobs, saveAgentConfig } from '../../api/jobApi';
import { useToast } from '../../context/ToastContext';

// --- INTERFACES ---

interface AgentRoundConfig {
  id: string;
  roundListId: string;
  jobId: string;
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

interface JobRound {
  id: string;
  name: string;
  order: number;
  description: string;
}

interface AgentEnabledJob {
  id: string;
  title: string;
  department: string | null;
  interview_rounds: JobRound[];
  agentRounds: AgentRoundConfig[];
}

// --- STYLING CONSTANTS ---
const cardClasses =
  'relative rounded-2xl border border-slate-200/80 bg-white/85 shadow-[0_24px_70px_-46px_rgba(15,118,110,0.55)] backdrop-blur';
const inputClasses =
  'w-full rounded-xl border border-slate-200 bg-white/90 px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:border-sky-500 focus:outline-none focus:ring-2 focus:ring-sky-200';
const labelClasses =
  'block text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500 mb-2';
const buttonClasses = {
  primary:
    'inline-flex items-center justify-center gap-2 rounded-xl bg-sky-600 px-4 py-2 text-sm font-semibold text-white shadow-[0_14px_30px_-20px_rgba(2,132,199,0.9)] transition hover:bg-sky-700 focus:outline-none focus:ring-2 focus:ring-sky-200 disabled:opacity-50 disabled:cursor-not-allowed',
  secondary:
    'inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-200',
  icon: 'p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg',
};
const badgeClasses =
  'inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-700';
const tabsTriggerClasses = (isActive: boolean) =>
  `w-full rounded-xl border px-3 py-2 text-left text-sm font-semibold transition
  ${
    isActive
      ? 'border-slate-900 bg-slate-900 text-white shadow'
      : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300 hover:bg-slate-50'
  }`;

// --- SUB-COMPONENTS ---

const JobList: React.FC<{
  jobs: AgentEnabledJob[];
  selectedJobId: string | null;
  onSelectJob: (id: string) => void;
  onSearch: (term: string) => void;
}> = ({ jobs, selectedJobId, onSelectJob, onSearch }) => {
  return (
    <div className={`${cardClasses} h-full flex flex-col`}>
      <div className="p-5 border-b border-slate-200/70">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold text-slate-900 flex items-center">
              <Briefcase className="w-5 h-5 mr-2 text-emerald-500" />
              Agent Job Library
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Pick a job to configure rounds, coding, and MCQ in one place.
            </p>
          </div>
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-center text-xs font-semibold text-emerald-700">
            {jobs.length} job{jobs.length === 1 ? '' : 's'}
          </div>
        </div>

        <div className="relative mt-4">
          <input
            type="text"
            placeholder="Search by job title or department"
            className={`${inputClasses} pl-10`}
            onChange={(e) => onSearch(e.target.value)}
          />
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
          <span className="rounded-full bg-slate-100 px-3 py-1">Round-based configs</span>
          <span className="rounded-full bg-slate-100 px-3 py-1">Coding & MCQ toggles</span>
          <span className="rounded-full bg-slate-100 px-3 py-1">Saved per job</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {jobs.length > 0 ? (
          jobs.map((job) => {
            const roundCount = job.interview_rounds.length;
            const hasCoding = (job.agentRounds || []).some((r) => r.codingEnabled);
            const hasMcq = (job.agentRounds || []).some((r) => r.mcqEnabled);

            return (
              <button
                key={job.id}
                onClick={() => onSelectJob(job.id)}
                className={clsx(
                  'w-full text-left rounded-xl border px-4 py-3 transition-all',
                  selectedJobId === job.id
                    ? 'border-slate-900 bg-slate-900 text-white shadow-[0_16px_30px_-22px_rgba(15,23,42,0.45)]'
                    : 'border-transparent hover:border-slate-200 hover:bg-slate-50'
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="text-base font-semibold">{job.title}</h3>
                    <p className={clsx('text-xs', selectedJobId === job.id ? 'text-slate-200' : 'text-slate-500')}>
                      {job.department || 'No Department'}
                    </p>
                  </div>
                  <span
                    className={clsx(
                      'rounded-full px-2.5 py-1 text-xs font-semibold',
                      selectedJobId === job.id ? 'bg-white/15 text-white' : 'bg-slate-100 text-slate-600'
                    )}
                  >
                    {roundCount} round{roundCount === 1 ? '' : 's'}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                  <span
                    className={clsx(
                      'inline-flex items-center gap-1 rounded-full px-2 py-0.5',
                      selectedJobId === job.id ? 'bg-white/15 text-white' : 'bg-emerald-50 text-emerald-700'
                    )}
                  >
                    <Bot className="w-3 h-3" />
                    Agent ready
                  </span>
                  {hasCoding && (
                    <span
                      className={clsx(
                        'rounded-full px-2 py-0.5',
                        selectedJobId === job.id ? 'bg-white/15 text-white' : 'bg-sky-50 text-sky-700'
                      )}
                    >
                      Coding
                    </span>
                  )}
                  {hasMcq && (
                    <span
                      className={clsx(
                        'rounded-full px-2 py-0.5',
                        selectedJobId === job.id ? 'bg-white/15 text-white' : 'bg-amber-50 text-amber-700'
                      )}
                    >
                      MCQ
                    </span>
                  )}
                </div>
              </button>
            );
          })
        ) : (
          <div className="p-4 text-center text-slate-500">
            No agent-enabled jobs found.
          </div>
        )}
      </div>
    </div>
  );
};

const TagInput: React.FC<{
  label: string;
  tags: string[];
  setTags: (tags: string[]) => void;
  placeholder: string;
}> = ({ label, tags, setTags, placeholder }) => {
  const [draft, setDraft] = useState('');

  const commit = () => {
    const value = draft.trim();
    if (!value) return;
    if (tags.includes(value)) {
      setDraft('');
      return;
    }
    setTags([...tags, value]);
    setDraft('');
  };

  return (
    <div>
      <label className={labelClasses}>{label}</label>
      <div className="flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2">
        {tags.map((tag) => (
          <span key={tag} className={badgeClasses}>
            {tag}
            <button type="button" onClick={() => setTags(tags.filter((t) => t !== tag))}>
              <X className="w-3 h-3" />
            </button>
          </span>
        ))}
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ',') {
              e.preventDefault();
              commit();
            }
          }}
          onBlur={commit}
          placeholder={placeholder}
          className="min-w-[120px] flex-1 border-0 bg-transparent text-sm outline-none"
        />
      </div>
    </div>
  );
};

const JsonEditor: React.FC<{
  label: string;
  value: any;
  format: 'array' | 'object';
  onChange: (value: any) => void;
  helperText?: string;
  rows?: number;
}> = ({ label, value, format, onChange, helperText, rows = 8 }) => {
  const [draft, setDraft] = useState('');
  const [parseError, setParseError] = useState('');

  useEffect(() => {
    const fallback = format === 'array' ? [] : {};
    try {
      setDraft(JSON.stringify(value ?? fallback, null, 2));
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
      if (format === 'array' && !Array.isArray(parsed)) {
        setParseError('Expected a JSON array.');
        return;
      }
      if (format === 'object' && (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed))) {
        setParseError('Expected a JSON object.');
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
        className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-mono text-xs text-slate-800 focus:border-sky-500 focus:outline-none"
      />
      {helperText && <p className="mt-1.5 text-xs text-slate-500">{helperText}</p>}
      {parseError && <p className="mt-1.5 text-xs text-rose-600">{parseError}</p>}
    </div>
  );
};

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
  } as const;

  const selectedPersona = personas[persona as keyof typeof personas] || personas.alex;
  const Icon = selectedPersona.icon;

  return (
    <div>
      <label className={labelClasses}>Agent Persona</label>
      <div className="relative">
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          className={`${inputClasses} flex items-center justify-between text-left`}
        >
          <span className="flex items-center">
            <Icon className="w-5 h-5 mr-2 text-sky-500" />
            <span className="text-slate-900">{selectedPersona.name}</span>
          </span>
          <ChevronDown
            className={`w-5 h-5 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          />
        </button>
        {isOpen && (
          <div className="absolute z-10 w-full mt-1 bg-white border border-slate-200 rounded-xl shadow-lg">
            {Object.entries(personas).map(([key, p]) => (
              <button
                key={key}
                type="button"
                onClick={() => {
                  setPersona(key as 'alex' | 'dr-evan' | 'sam');
                  setIsOpen(false);
                }}
                className="w-full text-left px-4 py-3 hover:bg-slate-50 flex items-start"
              >
                <p.icon className="w-5 h-5 mr-3 mt-0.5 text-sky-500" />
                <div>
                  <p className="font-medium text-slate-900">{p.name}</p>
                  <p className="text-xs text-slate-500">{p.desc}</p>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const AgentConfigurator: React.FC<{
  job: AgentEnabledJob;
  onSave: (updatedConfigs: AgentRoundConfig[]) => void;
}> = ({ job, onSave }) => {
  const toast = useToast();
  const addToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const maybeAdd = (toast as unknown as { addToast?: (msg: string, variant?: string) => void }).addToast;
    if (maybeAdd) {
      maybeAdd(message, type);
    } else {
      if (type === 'error') console.error(message);
      else console.log(message);
    }
  };

  const [config, setConfig] = useState<AgentEnabledJob>(job);
  const [activeRoundTab, setActiveRoundTab] = useState<string>(
    job.interview_rounds?.[0]?.id || ''
  );
  const [isSaving, setIsSaving] = useState(false);

  const buildAgentRounds = (source: AgentEnabledJob): AgentRoundConfig[] => {
    return (source.interview_rounds || []).map((jobRound) => {
      const savedConfig = (source.agentRounds || []).find(
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

      return {
        id: `new_${jobRound.id}`,
        roundListId: jobRound.id,
        jobId: source.id,
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
    });
  };

  useEffect(() => {
    const agentRoundsWithDefaults = buildAgentRounds(job);
    setConfig({
      ...job,
      agentRounds: agentRoundsWithDefaults,
    });
    setActiveRoundTab(job.interview_rounds?.[0]?.id || '');
  }, [job]);

  const handleSave = async () => {
    setIsSaving(true);
    const result = await saveAgentConfig(config.id, config.agentRounds);

    if (result.success) {
      const savedConfigs = result.data.agentRounds;
      addToast('Configuration saved successfully!', 'success');
      onSave(savedConfigs);
    } else {
      addToast(`Error saving: ${result.error}`, 'error');
    }

    setIsSaving(false);
  };

  const handleReset = () => {
    const agentRoundsWithDefaults = buildAgentRounds(job);
    setConfig({
      ...job,
      agentRounds: agentRoundsWithDefaults,
    });
    setActiveRoundTab(job.interview_rounds?.[0]?.id || '');
  };

  const updateRoundConfig = (
    roundListId: string,
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

  const activeRoundConfig = config.agentRounds.find(
    (r) => r.roundListId === activeRoundTab
  );

  const totalRounds = config.interview_rounds?.length || 0;
  const codingRounds = config.agentRounds.filter((r) => r.codingEnabled).length;
  const mcqRounds = config.agentRounds.filter((r) => r.mcqEnabled).length;

  return (
    <div className="relative h-full">
      <div className="pointer-events-none absolute inset-0 rounded-3xl bg-[radial-gradient(circle_at_top,_rgba(14,116,144,0.16),_transparent_60%),radial-gradient(circle_at_bottom,_rgba(251,191,36,0.16),_transparent_55%)]" />
      <div
        className={`${cardClasses} h-full flex flex-col overflow-hidden`}
        style={{ fontFamily: '"IBM Plex Sans", "Trebuchet MS", sans-serif' }}
      >
        <div className="relative border-b border-slate-200/70 bg-white/70 px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-slate-400">Agent workspace</p>
              <h2
                className="mt-2 text-2xl font-semibold text-slate-900"
                style={{ fontFamily: '"DM Serif Display", "Georgia", serif' }}
              >
                {job.title}
              </h2>
              <p className="mt-1 text-sm text-slate-500">{job.department || 'No department'}</p>
              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-600">
                  {totalRounds} round{totalRounds === 1 ? '' : 's'}
                </span>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-emerald-700">
                  {codingRounds} coding enabled
                </span>
                <span className="rounded-full bg-amber-100 px-3 py-1 text-amber-700">
                  {mcqRounds} MCQ enabled
                </span>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button type="button" className={buttonClasses.secondary} onClick={handleReset} disabled={isSaving}>
                Reset
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={isSaving}
                className={buttonClasses.primary}
              >
                {isSaving ? (
                  <>
                    <Loader2 className="animate-spin h-4 w-4" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4" />
                    Save Configuration
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        <div className="grid flex-1 grid-cols-1 gap-6 overflow-hidden p-6 xl:grid-cols-[260px_1fr]">
          <aside className="space-y-4">
            <div className="rounded-2xl border border-slate-200 bg-white/90 p-4 shadow-sm">
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Rounds</p>
              <div className="mt-3 space-y-2">
                {(config.interview_rounds || []).map((round) => {
                  const roundConfig = config.agentRounds.find((r) => r.roundListId === round.id);
                  const hasCoding = Boolean(roundConfig?.codingEnabled);
                  const hasMcq = Boolean(roundConfig?.mcqEnabled);
                  return (
                    <button
                      key={round.id}
                      onClick={() => setActiveRoundTab(round.id)}
                      className={tabsTriggerClasses(activeRoundTab === round.id)}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div>
                          <p className="text-sm font-semibold">{round.name}</p>
                          <p className="text-xs text-slate-400">Round {round.order}</p>
                        </div>
                        <div className="flex flex-col items-end gap-1 text-[10px]">
                          {hasCoding && <span className="rounded-full bg-sky-100 px-2 py-0.5 text-sky-700">Coding</span>}
                          {hasMcq && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-amber-700">MCQ</span>}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white/90 p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Tips</p>
              <ul className="mt-3 space-y-2 text-xs text-slate-600">
                <li>Define a clear focus for each round.</li>
                <li>Use provided questions for strict control.</li>
                <li>Keep MCQ passing scores aligned with thresholds.</li>
              </ul>
            </div>
          </aside>

          <section className="space-y-6 overflow-y-auto pr-1">
            {!activeRoundConfig ? (
              <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-slate-200 bg-white/60 p-10 text-center text-slate-500">
                <div>
                  <Bot className="mx-auto h-12 w-12 text-slate-300" />
                  <p className="mt-3 text-sm font-semibold">Select a round to configure</p>
                  <p className="text-xs text-slate-400">Pick a round from the list to begin editing.</p>
                </div>
              </div>
            ) : (
              <>
                <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Active round</p>
                      <h3 className="mt-2 text-xl font-semibold text-slate-900">
                        {activeRoundConfig.roundName}
                      </h3>
                    </div>
                    <span className="rounded-full bg-slate-900 px-3 py-1 text-xs font-semibold text-white">
                      Round {config.interview_rounds.find((r) => r.id === activeRoundConfig.roundListId)?.order || 1}
                    </span>
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm space-y-5">
                  <PersonaSelector
                    persona={activeRoundConfig.persona}
                    setPersona={(p) =>
                      updateRoundConfig(activeRoundConfig.roundListId, 'persona', p)
                    }
                  />

                  <div>
                    <label htmlFor="roundFocus" className={labelClasses}>
                      Round focus (main prompt)
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
                    <p className="mt-1.5 text-xs text-slate-500">
                      This is the main instruction for the agent's objective in this round.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <TagInput
                      label="Key skills to probe"
                      tags={activeRoundConfig.keySkills}
                      setTags={(newTags) =>
                        updateRoundConfig(activeRoundConfig.roundListId, 'keySkills', newTags)
                      }
                      placeholder="Add skill and press Enter..."
                    />
                    <TagInput
                      label="Forbidden topics"
                      tags={activeRoundConfig.forbiddenTopics}
                      setTags={(newTags) =>
                        updateRoundConfig(activeRoundConfig.roundListId, 'forbiddenTopics', newTags)
                      }
                      placeholder="Add topic and press Enter..."
                    />
                  </div>

                  <div>
                    <label className={labelClasses}>Mandatory custom questions</label>
                    <div className="space-y-2">
                      {activeRoundConfig.customQuestions.map((q, index) => (
                        <div key={index} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                          <MessageSquare className="w-4 h-4 text-slate-400 flex-shrink-0" />
                          <p className="flex-1 text-sm text-slate-700">{q}</p>
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
                </div>

                <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-900">Coding Challenge</h4>
                      <p className="text-xs text-slate-500">
                        Language control, starter code, and test-case evaluation.
                      </p>
                    </div>
                    <label className="inline-flex items-center gap-2 text-sm text-slate-700">
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
                          <label className={labelClasses}>Question mode</label>
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
                          <label className={labelClasses}>Test case mode</label>
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
                        label="Allowed coding languages"
                        tags={activeRoundConfig.codingLanguages}
                        setTags={(newTags) =>
                          updateRoundConfig(activeRoundConfig.roundListId, 'codingLanguages', newTags)
                        }
                        placeholder="Add language and press Enter..."
                      />

                      <JsonEditor
                        label="Starter code (JSON object keyed by language)"
                        value={activeRoundConfig.codingStarterCode}
                        format="object"
                        onChange={(parsed) =>
                          updateRoundConfig(activeRoundConfig.roundListId, 'codingStarterCode', parsed)
                        }
                        helperText='Example: {"python":"def solve(input_data):\n    return None"}'
                        rows={7}
                      />

                      {activeRoundConfig.codingQuestionMode === 'provided' && (
                        <div>
                          <label className={labelClasses}>Provided coding question</label>
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
                          label="Preconfigured coding test cases"
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

                <div className="rounded-2xl border border-slate-200 bg-white/90 p-5 shadow-sm space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-semibold text-slate-900">MCQ Challenge</h4>
                      <p className="text-xs text-slate-500">
                        Objective MCQ round with configurable passing score and question bank.
                      </p>
                    </div>
                    <label className="inline-flex items-center gap-2 text-sm text-slate-700">
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
                          <label className={labelClasses}>Question mode</label>
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
                          <label className={labelClasses}>Passing score (%)</label>
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
                          label="Preconfigured MCQ questions"
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
          </section>
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

const AgentHubPageInner: React.FC = () => {
  const [allJobs, setAllJobs] = useState<AgentEnabledJob[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const toast = useToast();
  const addToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const maybeAdd = (toast as unknown as { addToast?: (msg: string, variant?: string) => void }).addToast;
    if (maybeAdd) {
      maybeAdd(message, type);
    } else {
      if (type === 'error') console.error(message);
      else console.log(message);
    }
  };

  const fetchAgentJobs = async () => {
    setIsLoading(true);
    const result = await getMyAgentJobs();
    if (result.success) {
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
          ...j,
          id: String(j.job_id || j.id || j.jobId || ''),
          title: j.title || j.job_title || j.jobTitle || 'Untitled Job',
          department: j.department || j.department_name || null,
          interview_rounds: normalizedRounds,
          agentRounds: normalizedAgentRounds,
        } as AgentEnabledJob;
      });
      setAllJobs(normalized);
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

  const stats = useMemo(() => {
    const totalJobs = allJobs.length;
    const totalRounds = allJobs.reduce(
      (sum, job) => sum + (job.interview_rounds?.length || 0),
      0
    );
    const codingRounds = allJobs.reduce(
      (sum, job) => sum + job.agentRounds.filter((r) => r.codingEnabled).length,
      0
    );
    const mcqRounds = allJobs.reduce(
      (sum, job) => sum + job.agentRounds.filter((r) => r.mcqEnabled).length,
      0
    );

    return {
      totalJobs,
      totalRounds,
      codingRounds,
      mcqRounds,
    };
  }, [allJobs]);

  const handleSaveConfig = (updatedAgentRounds: AgentRoundConfig[]) => {
    setAllJobs((prevJobs) =>
      prevJobs.map((job) =>
        job.id === selectedJobId ? { ...job, agentRounds: updatedAgentRounds } : job
      )
    );
  };

  return (
    <div className="relative">
      <div className="pointer-events-none absolute -top-24 right-8 h-64 w-64 rounded-full bg-sky-200/40 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-24 left-8 h-72 w-72 rounded-full bg-amber-200/40 blur-3xl" />

      <div className="relative space-y-6">
        <section
          className="rounded-3xl border border-slate-200 bg-white/85 p-6 shadow-[0_30px_80px_-60px_rgba(14,116,144,0.45)]"
          style={{ fontFamily: '"IBM Plex Sans", "Trebuchet MS", sans-serif' }}
        >
          <div className="flex flex-wrap items-center justify-between gap-6">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">Interview Agent Hub</p>
              <h1
                className="mt-2 text-3xl font-semibold text-slate-900"
                style={{ fontFamily: '"DM Serif Display", "Georgia", serif' }}
              >
                Build the interview flow, round by round.
              </h1>
              <p className="mt-2 max-w-xl text-sm text-slate-600">
                Configure coding, MCQ, and custom questions in one workspace. Every change stays attached to the job post.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-center">
                <p className="text-xs text-slate-400">Jobs</p>
                <p className="text-lg font-semibold text-slate-900">{stats.totalJobs}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-center">
                <p className="text-xs text-slate-400">Rounds</p>
                <p className="text-lg font-semibold text-slate-900">{stats.totalRounds}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-center">
                <p className="text-xs text-slate-400">Coding</p>
                <p className="text-lg font-semibold text-slate-900">{stats.codingRounds}</p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-center">
                <p className="text-xs text-slate-400">MCQ</p>
                <p className="text-lg font-semibold text-slate-900">{stats.mcqRounds}</p>
              </div>
            </div>
          </div>
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 h-full min-h-[600px]">
            <JobList
              jobs={filteredJobs}
              selectedJobId={selectedJobId}
              onSelectJob={setSelectedJobId}
              onSearch={setSearchTerm}
            />
          </div>

          <div className="lg:col-span-2 h-full min-h-[600px]">
            {isLoading ? (
              <div className={`${cardClasses} h-full flex items-center justify-center`}>
                <Loader2 className="w-8 h-8 text-sky-500 animate-spin" />
                <p className="ml-3 text-slate-600">Loading agent jobs...</p>
              </div>
            ) : selectedJob ? (
              <AgentConfigurator job={selectedJob} onSave={handleSaveConfig} />
            ) : (
              <div className={`${cardClasses} h-full flex items-center justify-center`}>
                <div className="text-center p-8">
                  <Briefcase className="w-12 h-12 text-slate-300 mx-auto" />
                  <h3 className="mt-2 text-lg font-semibold text-slate-900">
                    No agent-enabled jobs found
                  </h3>
                  <p className="mt-1 text-sm text-slate-500">
                    Create a job and enable "Agent Interview" to configure it here.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
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
