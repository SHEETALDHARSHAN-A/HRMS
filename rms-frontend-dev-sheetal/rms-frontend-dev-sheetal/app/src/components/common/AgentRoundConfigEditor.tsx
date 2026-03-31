import React, { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Code2, ListChecks, Plus, Settings2, Trash2, X } from 'lucide-react';
import type { InterviewLevel } from '../../pages/JobPosts/JobPostsForm';
import clsx from 'clsx';

interface AgentRoundConfigEditorProps {
  rounds: InterviewLevel[];
  agentConfigs: Array<any>;
  setAgentConfigs: (next: Array<any>) => void;
}

const personaOptions = [
  { value: 'alex', label: 'Alex (Balanced)' },
  { value: 'dr-evan', label: 'Dr. Evan (Strict)' },
  { value: 'sam', label: 'Sam (Friendly)' },
];

const tagContainerClasses =
  'flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2';

const inputClasses =
  'w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none';

const normalizeConfig = (cfg: any, index: number, rounds: InterviewLevel[]) => {
  const roundTitle = rounds[index]?.title || `Round ${index + 1}`;
  return {
    round_list_id: cfg?.round_list_id ?? cfg?.roundListId ?? undefined,
    round_name: cfg?.round_name ?? cfg?.roundName ?? roundTitle,
    round_focus: cfg?.round_focus ?? cfg?.roundFocus ?? '',
    persona: cfg?.persona ?? 'alex',
    key_skills: cfg?.key_skills ?? cfg?.keySkills ?? [],
    custom_questions: cfg?.custom_questions ?? cfg?.customQuestions ?? [],
    forbidden_topics: cfg?.forbidden_topics ?? cfg?.forbiddenTopics ?? [],
    interview_mode: cfg?.interview_mode ?? cfg?.interviewMode ?? (index === 0 ? 'screening' : 'agent'),
    interview_time_min: cfg?.interview_time_min ?? cfg?.interviewTimeMin ?? (index === 0 ? null : 15),
    interview_time_max: cfg?.interview_time_max ?? cfg?.interviewTimeMax ?? (index === 0 ? null : 30),
    interviewer_id: cfg?.interviewer_id ?? cfg?.interviewerId ?? null,
    coding_enabled: Boolean(cfg?.coding_enabled ?? cfg?.codingEnabled ?? false),
    coding_question_mode: cfg?.coding_question_mode ?? cfg?.codingQuestionMode ?? 'ai',
    coding_difficulty: cfg?.coding_difficulty ?? cfg?.codingDifficulty ?? 'medium',
    coding_languages: cfg?.coding_languages ?? cfg?.codingLanguages ?? ['python'],
    provided_coding_question: cfg?.provided_coding_question ?? cfg?.providedCodingQuestion ?? '',
    coding_test_case_mode: cfg?.coding_test_case_mode ?? cfg?.codingTestCaseMode ?? 'provided',
    coding_test_cases: cfg?.coding_test_cases ?? cfg?.codingTestCases ?? [],
    coding_starter_code: cfg?.coding_starter_code ?? cfg?.codingStarterCode ?? {},
    mcq_enabled: Boolean(cfg?.mcq_enabled ?? cfg?.mcqEnabled ?? false),
    mcq_question_mode: cfg?.mcq_question_mode ?? cfg?.mcqQuestionMode ?? 'provided',
    mcq_difficulty: cfg?.mcq_difficulty ?? cfg?.mcqDifficulty ?? 'medium',
    mcq_questions: cfg?.mcq_questions ?? cfg?.mcqQuestions ?? [],
    mcq_passing_score: Number(cfg?.mcq_passing_score ?? cfg?.mcqPassingScore ?? 60) || 60,
  };
};

const TagInput: React.FC<{
  label: string;
  tags: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
}> = ({ label, tags, onChange, placeholder }) => {
  const [draft, setDraft] = useState('');

  const commitTag = () => {
    const value = draft.trim();
    if (!value) return;
    if (tags.includes(value)) {
      setDraft('');
      return;
    }
    onChange([...tags, value]);
    setDraft('');
  };

  return (
    <div>
      <label className="mb-2 block text-sm font-medium text-slate-700">{label}</label>
      <div className={tagContainerClasses}>
        {tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700"
          >
            {tag}
            <button
              type="button"
              onClick={() => onChange(tags.filter((t) => t !== tag))}
              className="text-slate-500 hover:text-slate-700"
            >
              <X size={12} />
            </button>
          </span>
        ))}
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ',') {
              e.preventDefault();
              commitTag();
            }
          }}
          onBlur={commitTag}
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
  onChange: (value: any) => void;
  format: 'array' | 'object';
  helper?: string;
  rows?: number;
}> = ({ label, value, onChange, format, helper, rows = 6 }) => {
  const [draft, setDraft] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const fallback = format === 'array' ? [] : {};
    try {
      setDraft(JSON.stringify(value ?? fallback, null, 2));
      setError('');
    } catch {
      setDraft(JSON.stringify(fallback, null, 2));
      setError('');
    }
  }, [value, format]);

  const handleBlur = () => {
    const fallback = format === 'array' ? [] : {};
    try {
      const parsed = draft.trim() ? JSON.parse(draft) : fallback;
      if (format === 'array' && !Array.isArray(parsed)) {
        setError('Expected a JSON array.');
        return;
      }
      if (format === 'object' && (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed))) {
        setError('Expected a JSON object.');
        return;
      }
      setError('');
      onChange(parsed);
    } catch {
      setError('Invalid JSON.');
    }
  };

  return (
    <div>
      <label className="mb-2 block text-sm font-medium text-slate-700">{label}</label>
      <textarea
        value={draft}
        onChange={(e) => {
          setDraft(e.target.value);
          setError('');
        }}
        onBlur={handleBlur}
        rows={rows}
        className={clsx(
          'w-full rounded-lg border px-3 py-2 text-xs font-mono text-slate-800 focus:outline-none',
          error ? 'border-rose-300 bg-rose-50' : 'border-slate-200 bg-white'
        )}
      />
      {helper && <p className="mt-1 text-xs text-slate-500">{helper}</p>}
      {error && <p className="mt-1 text-xs text-rose-600">{error}</p>}
    </div>
  );
};

const AgentRoundConfigEditor: React.FC<AgentRoundConfigEditorProps> = ({
  rounds,
  agentConfigs,
  setAgentConfigs,
}) => {
  const [activeIndex, setActiveIndex] = useState(0);
  const [draftQuestions, setDraftQuestions] = useState<Record<number, string>>({});

  useEffect(() => {
    if (!rounds.length) return;
    if (activeIndex >= rounds.length) {
      setActiveIndex(0);
    }
  }, [rounds.length, activeIndex]);

  useEffect(() => {
    if (!rounds.length) return;
    let changed = false;
    const next = [...(agentConfigs || [])];

    for (let i = 0; i < rounds.length; i += 1) {
      if (!next[i]) {
        next[i] = normalizeConfig({}, i, rounds);
        changed = true;
        continue;
      }
      const normalized = normalizeConfig(next[i], i, rounds);
      if (JSON.stringify(normalized) !== JSON.stringify(next[i])) {
        next[i] = normalized;
        changed = true;
      }
    }

    if (next.length > rounds.length) {
      next.length = rounds.length;
      changed = true;
    }

    if (changed) {
      setAgentConfigs(next);
    }
  }, [rounds, agentConfigs, setAgentConfigs]);

  const activeConfig = useMemo(() => {
    if (!rounds.length) return null;
    return normalizeConfig(agentConfigs?.[activeIndex] ?? {}, activeIndex, rounds);
  }, [agentConfigs, activeIndex, rounds]);

  const updateActive = (patch: Record<string, any>) => {
    const next = [...(agentConfigs || [])];
    next[activeIndex] = { ...activeConfig, ...patch };
    setAgentConfigs(next);
  };

  if (!rounds.length || !activeConfig) {
    return null;
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
          <Settings2 size={18} />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Round Question Configuration</h3>
          <p className="text-sm text-slate-500">Configure coding, MCQ, and custom questions per round.</p>
        </div>
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        {rounds.map((round, idx) => (
          <button
            key={`${round.title}-${idx}`}
            type="button"
            onClick={() => setActiveIndex(idx)}
            className={clsx(
              'rounded-full px-3 py-1.5 text-sm font-medium transition-all',
              idx === activeIndex
                ? 'bg-blue-600 text-white shadow'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
            )}
          >
            {round.title || `Round ${idx + 1}`}
          </button>
        ))}
      </div>

      <div className="grid gap-6">
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-700">Round focus</label>
          <textarea
            value={activeConfig.round_focus || ''}
            onChange={(e) => updateActive({ round_focus: e.target.value })}
            rows={3}
            className={inputClasses}
            placeholder="Summarize what this round should focus on."
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-slate-700">Persona</label>
          <div className="flex flex-wrap gap-2">
            {personaOptions.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => updateActive({ persona: opt.value })}
                className={clsx(
                  'rounded-lg border px-3 py-2 text-sm font-medium',
                  activeConfig.persona === opt.value
                    ? 'border-blue-600 bg-blue-50 text-blue-700'
                    : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <TagInput
          label="Key skills to probe"
          tags={activeConfig.key_skills || []}
          onChange={(tags) => updateActive({ key_skills: tags })}
          placeholder="Add a skill and press Enter"
        />

        <TagInput
          label="Forbidden topics"
          tags={activeConfig.forbidden_topics || []}
          onChange={(tags) => updateActive({ forbidden_topics: tags })}
          placeholder="Add a topic to avoid"
        />

        <div>
          <label className="mb-2 block text-sm font-medium text-slate-700">Custom questions</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={draftQuestions[activeIndex] || ''}
              onChange={(e) =>
                setDraftQuestions((prev) => ({
                  ...prev,
                  [activeIndex]: e.target.value,
                }))
              }
              className={inputClasses}
              placeholder="Enter a mandatory question"
            />
            <button
              type="button"
              onClick={() => {
                const draft = (draftQuestions[activeIndex] || '').trim();
                if (!draft) return;
                const nextQuestions = [...(activeConfig.custom_questions || []), draft];
                updateActive({ custom_questions: nextQuestions });
                setDraftQuestions((prev) => ({ ...prev, [activeIndex]: '' }));
              }}
              className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white"
            >
              <Plus size={14} />
              Add
            </button>
          </div>
          <div className="mt-3 space-y-2">
            {(activeConfig.custom_questions || []).map((q: string, idx: number) => (
              <div key={`${q}-${idx}`} className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                <span className="text-sm text-slate-700">{q}</span>
                <button
                  type="button"
                  onClick={() => {
                    const nextQuestions = (activeConfig.custom_questions || []).filter((_: string, i: number) => i !== idx);
                    updateActive({ custom_questions: nextQuestions });
                  }}
                  className="text-rose-500 hover:text-rose-600"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800">
            <Code2 size={16} />
            Coding Challenge
          </div>
          <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <input
              type="checkbox"
              checked={activeConfig.coding_enabled}
              onChange={(e) => updateActive({ coding_enabled: e.target.checked })}
            />
            Enable coding round
          </label>

          {activeConfig.coding_enabled && (
            <div className="mt-4 grid gap-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Question mode</label>
                <div className="flex gap-2">
                  {['ai', 'provided'].map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => updateActive({ coding_question_mode: mode })}
                      className={clsx(
                        'rounded-lg border px-3 py-2 text-sm font-medium',
                        activeConfig.coding_question_mode === mode
                          ? 'border-blue-600 bg-blue-50 text-blue-700'
                          : 'border-slate-200 text-slate-600'
                      )}
                    >
                      {mode === 'ai' ? 'AI Generated' : 'Provided'}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Difficulty</label>
                <select
                  value={activeConfig.coding_difficulty}
                  onChange={(e) => updateActive({ coding_difficulty: e.target.value })}
                  className={inputClasses}
                >
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>

              <TagInput
                label="Allowed coding languages"
                tags={activeConfig.coding_languages || []}
                onChange={(tags) => updateActive({ coding_languages: tags })}
                placeholder="Add language"
              />

              {activeConfig.coding_question_mode === 'provided' && (
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Provided coding question</label>
                  <textarea
                    value={activeConfig.provided_coding_question || ''}
                    onChange={(e) => updateActive({ provided_coding_question: e.target.value })}
                    rows={4}
                    className={inputClasses}
                    placeholder="Paste the exact coding question candidates should solve."
                  />
                </div>
              )}

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Test case mode</label>
                <div className="flex gap-2">
                  {['ai', 'provided'].map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => updateActive({ coding_test_case_mode: mode })}
                      className={clsx(
                        'rounded-lg border px-3 py-2 text-sm font-medium',
                        activeConfig.coding_test_case_mode === mode
                          ? 'border-blue-600 bg-blue-50 text-blue-700'
                          : 'border-slate-200 text-slate-600'
                      )}
                    >
                      {mode === 'ai' ? 'AI Generated' : 'Provided'}
                    </button>
                  ))}
                </div>
              </div>

              {activeConfig.coding_test_case_mode === 'provided' && (
                <JsonEditor
                  label="Coding test cases (JSON array)"
                  value={activeConfig.coding_test_cases}
                  onChange={(val) => updateActive({ coding_test_cases: val })}
                  format="array"
                  helper="Each entry should include input/output examples."
                />
              )}

              <JsonEditor
                label="Starter code (JSON object)"
                value={activeConfig.coding_starter_code}
                onChange={(val) => updateActive({ coding_starter_code: val })}
                format="object"
                helper='Example: { "python": "def solve():" }'
              />
            </div>
          )}
        </div>

        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-800">
            <ListChecks size={16} />
            MCQ / Aptitude
          </div>
          <label className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <input
              type="checkbox"
              checked={activeConfig.mcq_enabled}
              onChange={(e) => updateActive({ mcq_enabled: e.target.checked })}
            />
            Enable MCQ round
          </label>

          {activeConfig.mcq_enabled && (
            <div className="mt-4 grid gap-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Question mode</label>
                <div className="flex gap-2">
                  {['ai', 'provided'].map((mode) => (
                    <button
                      key={mode}
                      type="button"
                      onClick={() => updateActive({ mcq_question_mode: mode })}
                      className={clsx(
                        'rounded-lg border px-3 py-2 text-sm font-medium',
                        activeConfig.mcq_question_mode === mode
                          ? 'border-blue-600 bg-blue-50 text-blue-700'
                          : 'border-slate-200 text-slate-600'
                      )}
                    >
                      {mode === 'ai' ? 'AI Generated' : 'Provided'}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Difficulty</label>
                <select
                  value={activeConfig.mcq_difficulty}
                  onChange={(e) => updateActive({ mcq_difficulty: e.target.value })}
                  className={inputClasses}
                >
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Passing score</label>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={activeConfig.mcq_passing_score}
                  onChange={(e) => updateActive({ mcq_passing_score: Number(e.target.value) || 0 })}
                  className={inputClasses}
                />
              </div>

              {activeConfig.mcq_question_mode === 'provided' && (
                <JsonEditor
                  label="MCQ questions (JSON array)"
                  value={activeConfig.mcq_questions}
                  onChange={(val) => updateActive({ mcq_questions: val })}
                  format="array"
                  helper="Each entry should include question, options, and answer."
                />
              )}
            </div>
          )}
        </div>

        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
          <div className="flex items-center gap-2 font-semibold">
            <CheckCircle2 size={16} />
            These settings will be saved with the job post.
          </div>
          <p className="mt-1 text-xs text-emerald-700">
            They appear under agent configs and can be edited later.
          </p>
        </div>
      </div>
    </div>
  );
};

export default AgentRoundConfigEditor;
