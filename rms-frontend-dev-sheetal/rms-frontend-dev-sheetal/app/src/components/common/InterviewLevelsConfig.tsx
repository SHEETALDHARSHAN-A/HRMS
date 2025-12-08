// src/components/common/InterviewLevelsConfig.tsx
import React, { useState, useEffect } from 'react';
import { 
  Trash2, 
  ListOrdered, 
  Percent, 
  Target, 
  Settings, 
  Minus, 
  Plus, 
  Headset,
  Users,
  Shield
} from 'lucide-react';
import type { InterviewLevel } from '../../pages/JobPosts/JobPostsForm';
import clsx from 'clsx';
// === MODIFICATION: Import the new component ===
import UserSearchCombobox from './UserSearchCombobox'; 
// === END MODIFICATION ===


interface InterviewLevelsConfigProps {
  levels: InterviewLevel[]; 
  setLevels: (levels: InterviewLevel[]) => void; 
  error?: string;
  roleFit: number;
  setRoleFit: (value: number) => void;
  potential: number;
  setPotential: (value: number) => void;
  jobLocationScore: number;
  setJobLocationScore: (value: number) => void;
  scoreTotalError?: string;
  agentConfigs?: Array<any>;
  setAgentConfigs?: (arr: Array<any>) => void;
}

const MAX_LEVELS = 10;
const MIN_LEVELS = 1;
const DEFAULT_THRESHOLDS = {
  shortlistThreshold: 60,
  rejectThreshold: 40,
};

// ... (ScoreInput and ThresholdField components remain unchanged) ...

interface ScoreInputProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  totalScore: number;
  min: number;
  step: number;
}

interface ThresholdFieldProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  color: 'green' | 'red';
  min: number;
}

const ScoreInput: React.FC<ScoreInputProps> = ({ label, value, onChange, totalScore, min, step }) => {
  const [draft, setDraft] = useState(String(value));
  const [blocked, setBlocked] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string>('');

  useEffect(() => {
    setDraft(String(value));
    setBlocked(false);
    setErrorMsg('');
  }, [value]);

  const clampToStep = (raw: number) => {
    if (Number.isNaN(raw)) return value;
    const snapped = Math.round(raw / step) * step;
    return Math.max(min, Math.min(100, snapped));
  };

  const attemptChange = (raw: number) => {
    const next = clampToStep(raw);
    const updatedTotal = totalScore - value + next;
    
    if (next < min) {
      setErrorMsg(`Minimum value is ${min}%`);
      setDraft(String(value));
      return false;
    }
    
    if (updatedTotal > 100) {
      const excess = updatedTotal - 100;
      setErrorMsg(`Would exceed total by ${excess}%`);
      setBlocked(true);
      setDraft(String(value));
      return false;
    }
    
    setBlocked(false);
    setErrorMsg('');
    onChange(next);
    setDraft(String(next));
    return true;
  };

  const handleBlur = () => {
    const parsed = Number(draft);
    if (Number.isNaN(parsed) || draft === '') {
      setErrorMsg('Please enter a valid number');
      setDraft(String(value));
      return;
    }
    attemptChange(parsed);
  };

  const handleStepChange = (direction: 'up' | 'down') => {
    const delta = direction === 'up' ? step : -step;
    attemptChange(value + delta);
  };

  const canIncrease = value < 100 && totalScore - value + value + step <= 100;
  const canDecrease = value > min;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="flex items-center justify-between mb-2">
        <label className="text-xs font-medium text-slate-700">{label}</label>
        <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
          <Percent size={10} />
          {value}%
        </span>
      </div>

      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => handleStepChange('down')}
          disabled={!canDecrease}
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded border border-slate-200 text-slate-600 transition-all hover:border-blue-400 hover:bg-blue-50 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:border-slate-200 disabled:hover:bg-transparent disabled:hover:text-slate-600"
          title={`Decrease by ${step}%`}
        >
          <Minus size={12} />
        </button>
        <input
          type="number"
          inputMode="numeric"
          min={min}
          max={100}
          step={step}
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            setErrorMsg('');
          }}
          onBlur={handleBlur}
          className={clsx(
            "h-8 w-full flex-1 rounded border px-2 text-center text-sm font-semibold outline-none transition-all",
            errorMsg || blocked
              ? "border-rose-300 bg-rose-50 text-rose-700 focus:border-rose-400 focus:ring-2 focus:ring-rose-100"
              : "border-slate-200 bg-white text-slate-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          )}
          aria-label={`${label} percentage`}
        />
        <button
          type="button"
          onClick={() => handleStepChange('up')}
          disabled={!canIncrease}
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded border border-slate-200 text-slate-600 transition-all hover:border-blue-400 hover:bg-blue-50 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:border-slate-200 disabled:hover:bg-transparent disabled:hover:text-slate-600"
          title={`Increase by ${step}%`}
        >
          <Plus size={12} />
        </button>
      </div>

      <div className="mt-1.5 flex items-center justify-between text-[10px] text-slate-400">
        <span>Min {min}%</span>
        <span>Max 90%</span>
      </div>

      {errorMsg && (
        <div className="mt-2 flex items-start gap-1 rounded bg-amber-50 px-2 py-1 text-[10px] font-medium text-amber-700">
          <span className="mt-0.5">⚠️</span>
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
};

const ThresholdField: React.FC<ThresholdFieldProps> = ({ label, value, onChange, color, min }) => {
  const [draft, setDraft] = useState(String(value));
  const [errorMsg, setErrorMsg] = useState<string>('');

  useEffect(() => {
    setDraft(String(value));
    setErrorMsg('');
  }, [value]);

  const chipBg = color === 'green' ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700';

  const clampValue = (raw: number) => {
    if (Number.isNaN(raw)) return value;
    const rounded = Math.round(raw);
    return Math.max(min, Math.min(100, rounded));
  };

  const commitValue = (raw: number) => {
    const next = clampValue(raw);
    
    if (next < min) {
      setErrorMsg(`Must be at least ${min}%`);
      setDraft(String(value));
      return false;
    }
    
    if (next > 100) {
      setErrorMsg(`Cannot exceed 100%`);
      setDraft(String(value));
      return false;
    }
    
    setErrorMsg('');
    onChange(next);
    setDraft(String(next));
    return true;
  };

  const handleBlur = () => {
    const parsed = Number(draft);
    if (Number.isNaN(parsed) || draft === '') {
      setErrorMsg('Please enter a valid number');
      setDraft(String(value));
      return;
    }
    commitValue(parsed);
  };

  const handleStepChange = (direction: 'up' | 'down') => {
    const delta = direction === 'up' ? 5 : -5;
    commitValue(value + delta);
  };

  const canIncrease = value < 100;
  const canDecrease = value > min;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <div className="flex items-center justify-between mb-2">
        <label className="text-xs font-medium text-slate-700">{label}</label>
        <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-semibold ${chipBg}`}>
          <Target size={10} />
          {value}%
        </span>
      </div>

      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => handleStepChange('down')}
          disabled={!canDecrease}
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded border border-slate-200 text-slate-600 transition-all hover:border-blue-400 hover:bg-blue-50 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:border-slate-200 disabled:hover:bg-transparent disabled:hover:text-slate-600"
          title="Decrease by 5%"
        >
          <Minus size={12} />
        </button>
        <input
          type="number"
          inputMode="numeric"
          min={min}
          max={100}
          step={1}
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            setErrorMsg('');
          }}
          onBlur={handleBlur}
          className={clsx(
            "h-8 w-full flex-1 rounded border px-2 text-center text-sm font-semibold outline-none transition-all",
            errorMsg
              ? "border-rose-300 bg-rose-50 text-rose-700 focus:border-rose-400 focus:ring-2 focus:ring-rose-100"
              : "border-slate-200 bg-white text-slate-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          )}
          aria-label={`${label} percentage`}
        />
        <button
          type="button"
          onClick={() => handleStepChange('up')}
          disabled={!canIncrease}
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded border border-slate-200 text-slate-600 transition-all hover:border-blue-400 hover:bg-blue-50 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:border-slate-200 disabled:hover:bg-transparent disabled:hover:text-slate-600"
          title="Increase by 5%"
        >
          <Plus size={12} />
        </button>
      </div>

      <div className="mt-1.5 flex items-center justify-between text-[10px] text-slate-400">
        <span>Min {min}%</span>
        <span>Max 100%</span>
      </div>

      {errorMsg && (
        <div className="mt-2 flex items-start gap-1 rounded bg-amber-50 px-2 py-1 text-[10px] font-medium text-amber-700">
          <span className="mt-0.5">⚠️</span>
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
};


const InterviewLevelsConfig: React.FC<InterviewLevelsConfigProps> = ({
  levels, 
  setLevels, 
  error,
  roleFit,
  setRoleFit,
  potential,
  setPotential,
  jobLocationScore,
  setJobLocationScore,
  scoreTotalError 
  , agentConfigs, setAgentConfigs
}) => {

  const scoreFields = [
    { label: "Role Fit", value: roleFit, set: setRoleFit },
    { label: "Potential", value: potential, set: setPotential },
    { label: "Job Location", value: jobLocationScore, set: setJobLocationScore },
  ];
  const totalScore = scoreFields.reduce((sum, field) => sum + field.value, 0);
  
  const [countInput, setCountInput] = useState(levels.length.toString());

  useEffect(() => {
    setCountInput(levels.length.toString());
  }, [levels.length]);


  const handleLevelChange = (
    index: number, 
    field: 'title' | 'description' | 'shortlistThreshold' | 'rejectThreshold', 
    value: string | number
  ) => {
    const newLevels = [...levels];
    newLevels[index] = {
      ...newLevels[index],
      [field]: value
    };
    setLevels(newLevels);
  };

  const removeLevel = (index: number) => {
    if (levels.length > MIN_LEVELS) {
      setLevels(levels.filter((_, i) => i !== index));
    }
  };
  
  const updateLevels = (newCount: number) => {
    const currentCount = levels.length;

    if (newCount > currentCount) {
      const newLevelsToAdd = newCount - currentCount;
      const newArray = [...levels];
      for (let i = 0; i < newLevelsToAdd; i++) {
        newArray.push({ 
          title: "", 
          description: "", 
          ...DEFAULT_THRESHOLDS 
        });
      }
      setLevels(newArray);
    } else if (newCount < currentCount) {
      setLevels(levels.slice(0, newCount));
    }
  };

  const handleCountInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    const digitsOnly = raw.replace(/\D+/g, '').slice(0, 2);

    if (digitsOnly === '') {
      setCountInput('');
      return;
    }

    let num = Number(digitsOnly);
    if (isNaN(num)) {
      setCountInput('');
      return;
    }

    num = Math.max(MIN_LEVELS, Math.min(MAX_LEVELS, num));

    setCountInput(String(num));
    updateLevels(num);
  };
  
  const handleCountInputBlur = () => {
    let newCount = parseInt(countInput, 10);
    
    if (isNaN(newCount)) newCount = MIN_LEVELS;
    newCount = Math.max(MIN_LEVELS, Math.min(MAX_LEVELS, newCount));

    setCountInput(newCount.toString());
    updateLevels(newCount);
  };


  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-3 mb-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100">
          <ListOrdered size={16} className="text-slate-600" />
        </div>
        <div>
          <label className="block text-lg font-semibold text-slate-900">Interview Configuration</label>
          <p className="text-sm text-slate-500">Define interview rounds and evaluation criteria for candidate assessment.</p>
        </div>
        <span className="ml-auto inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
          <Target size={12} />
          Required
        </span>
      </div>

      {/* Round Count Controls */}
      <div className="mb-6 rounded-xl border border-slate-200 bg-slate-50 p-5">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white">
              <Settings size={16} className="text-slate-600" />
            </div>
            <div>
              <label className="text-base font-semibold text-slate-900">Interview rounds</label>
              <p className="text-sm text-slate-600">Adjust how many stages candidates complete.</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                const newCount = Math.max(MIN_LEVELS, levels.length - 1);
                setCountInput(String(newCount));
                updateLevels(newCount);
              }}
              disabled={levels.length <= MIN_LEVELS}
              className="flex h-10 w-10 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition-colors hover:bg-white disabled:cursor-not-allowed disabled:opacity-40"
              title="Remove round"
            >
              <Minus size={14} />
            </button>
            
            <div className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-4 py-2">
              <label className="text-sm font-medium text-slate-600">Rounds:</label>
              <input
                type="number"
                id="level_count"
                value={countInput}
                onChange={handleCountInputChange}
                onBlur={handleCountInputBlur}
                min={MIN_LEVELS}
                max={MAX_LEVELS}
                onInput={(e) => {
                  const input = e.currentTarget as HTMLInputElement;
                  let sanitized = input.value.replace(/\D+/g, '');
                  if (sanitized.length > 2) sanitized = sanitized.slice(0, 2);
                  const asNum = Number(sanitized);
                  if (!isNaN(asNum) && asNum > MAX_LEVELS) sanitized = String(MAX_LEVELS);
                  input.value = sanitized;
                  setCountInput(sanitized);
                }}
                onPaste={(e) => {
                  const paste = e.clipboardData?.getData('text') ?? (window as any).clipboardData?.getData?.('text') ?? '';
                  const digits = paste.replace(/\D+/g, '').slice(0, 2);
                  const num = Number(digits) || MIN_LEVELS;
                  const final = Math.min(MAX_LEVELS, Math.max(MIN_LEVELS, num));
                  e.preventDefault();
                  setCountInput(String(final));
                  updateLevels(final);
                }}
                className="w-12 border-none bg-transparent text-center text-sm font-semibold text-slate-900 focus:outline-none"
                aria-label="Number of interview rounds"
              />
            </div>
            
            <button
              type="button"
              onClick={() => {
                const newCount = Math.min(MAX_LEVELS, levels.length + 1);
                setCountInput(String(newCount));
                updateLevels(newCount);
              }}
              disabled={levels.length >= MAX_LEVELS}
              className="flex h-10 w-10 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
              title="Add round"
            >
              <Plus size={14} />
            </button>
            
            <span className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 text-sm font-semibold text-slate-700">
              <ListOrdered size={14} className="text-slate-500" />
              {levels.length} configured
            </span>
          </div>
        </div>
        
        {levels.length >= MAX_LEVELS && (
          <div className="mt-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-700">
            Maximum number of interview rounds reached ({MAX_LEVELS})
          </div>
        )}
        
        {levels.length <= MIN_LEVELS && (
          <div className="mt-4 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-700">
            At least {MIN_LEVELS} interview round is required
          </div>
        )}
      </div>
      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2 mb-3">
        <label className="block text-base sm:text-lg font-semibold text-gray-800">
          Interview Levels
        </label>
        
        <div className="flex items-center gap-2 flex-shrink-0">
          <label htmlFor="level_count" className="text-sm font-medium text-gray-700">
            Number of Rounds:
          </label>
          <input
            type="number"
            id="level_count"
            value={countInput}
            onChange={handleCountInputChange}
            onBlur={handleCountInputBlur}
            min={MIN_LEVELS}
            max={MAX_LEVELS}
            onInput={(e) => {
              const input = e.currentTarget as HTMLInputElement;
              let sanitized = input.value.replace(/\D+/g, '');
              if (sanitized.length > 2) sanitized = sanitized.slice(0, 2);
              const asNum = Number(sanitized);
              if (!isNaN(asNum) && asNum > MAX_LEVELS) sanitized = String(MAX_LEVELS);
              input.value = sanitized;
              setCountInput(sanitized);
            }}
            onPaste={(e) => {
              const paste = e.clipboardData?.getData('text') ?? (window as any).clipboardData?.getData?.('text') ?? '';
              const digits = paste.replace(/\D+/g, '').slice(0, 2);
              const num = Number(digits) || MIN_LEVELS;
              const final = Math.min(MAX_LEVELS, Math.max(MIN_LEVELS, num));
              e.preventDefault();
              setCountInput(String(final));
              updateLevels(final);
            }}
            className="w-20 bg-white border border-gray-300 rounded-md px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--color-primary-500)] h-10"
            aria-label="Number of interview rounds"
          />
        </div>
      </div>

      <div className="space-y-4">
        {levels.map((level, index) => {
          const isRoundOne = index === 0;
          const thresholdError = level.rejectThreshold > level.shortlistThreshold;
          const agentCfg = (agentConfigs && agentConfigs[index]) ? agentConfigs[index] : null;
          return (
            <div 
              key={index} 
              className={clsx(
                'overflow-hidden rounded-xl border shadow-sm transition-colors',
                thresholdError ? 'border-rose-300' : 'border-slate-200 hover:border-slate-300'
              )}
            >
              {/* Round Header */}
              <div className="border-b border-slate-200 bg-slate-50 px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white text-sm font-semibold text-slate-700">
                      {index + 1}
                    </div>
                    <div>
                      <h4 className="text-base font-semibold text-slate-900">Round {index + 1}</h4>
                      <p className="text-xs text-slate-500">{isRoundOne ? 'Initial screening' : 'Interview stage'}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="flex h-9 w-9 items-center justify-center rounded-md border border-rose-200 bg-white text-rose-600 transition-all hover:bg-rose-50 hover:border-rose-300 disabled:cursor-not-allowed disabled:opacity-40 disabled:text-slate-400 disabled:border-slate-200 disabled:hover:bg-white"
                    onClick={() => removeLevel(index)}
                    disabled={levels.length <= MIN_LEVELS}
                    title={levels.length <= MIN_LEVELS ? `Cannot remove - minimum ${MIN_LEVELS} round required` : "Remove this round"}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              
              {/* Round Content */}
              <div className="bg-white p-6 space-y-4">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Round title</label>
                  <input
                    type="text"
                    value={level.title}
                    onChange={(e) => handleLevelChange(index, 'title', e.target.value)}
                    placeholder={isRoundOne ? "e.g. Initial Screening" : "e.g. Technical Interview"}
                    className="w-full bg-white border-2 rounded-xl px-4 py-3 text-base placeholder-gray-400 focus:outline-none focus:ring-0 focus:border-blue-500 shadow-sm transition-all duration-200 border-gray-200 hover:border-gray-300"
                  />
                </div>

                {/* Per-round Interview Mode & Metadata */}
                <div className="mt-3">
                  <label className="mb-2 block text-sm font-medium text-slate-700">Interview Mode</label>
                  
                  <div className="flex w-full max-w-md rounded-xl border-2 p-1 bg-gray-50/50 border-gray-200">
                    {isRoundOne ? (
                      // First round: screening or in-person
                      <>
                        <button
                          type="button"
                          onClick={() => {
                            if (!setAgentConfigs) return;
                            const next = agentConfigs ? [...agentConfigs] : [];
                            next[index] = { ...(next[index] || {}), interview_mode: 'screening', interview_time: null, interviewer_id: null };
                            setAgentConfigs(next);
                          }}
                          className={clsx(
                            "flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg text-sm font-medium transition-all duration-200",
                            agentCfg && agentCfg.interview_mode === 'screening'
                              ? 'bg-white text-blue-700 shadow-md ring-1 ring-blue-100'
                              : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                          )}
                        >
                          <Shield size={16} />
                          Screening
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            if (!setAgentConfigs) return;
                            const next = agentConfigs ? [...agentConfigs] : [];
                            next[index] = { ...(next[index] || {}), interview_mode: 'offline' };
                            setAgentConfigs(next);
                          }}
                          className={clsx(
                            "flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg text-sm font-medium transition-all duration-200",
                            agentCfg && (agentCfg.interview_mode === 'offline' || agentCfg.interview_mode === 'in_person')
                              ? 'bg-white text-blue-700 shadow-md ring-1 ring-blue-100'
                              : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                          )}
                        >
                          <Users size={16} />
                          In-person
                        </button>
                      </>
                    ) : (
                      // Other rounds: agent or in-person
                      <>
                        <button
                          type="button"
                          onClick={() => {
                            if (!setAgentConfigs) return;
                            const next = agentConfigs ? [...agentConfigs] : [];
                            next[index] = { ...(next[index] || {}), interview_mode: 'agent', interview_time: (next[index] && next[index].interview_time) || 30 };
                            setAgentConfigs(next);
                          }}
                          className={clsx(
                            "flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg text-sm font-medium transition-all duration-200",
                            agentCfg && agentCfg.interview_mode === 'agent'
                              ? 'bg-white text-blue-700 shadow-md ring-1 ring-blue-100'
                              : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                          )}
                        >
                          <Headset size={16} />
                          Agent
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            if (!setAgentConfigs) return;
                            const next = agentConfigs ? [...agentConfigs] : [];
                            next[index] = { ...(next[index] || {}), interview_mode: 'offline', interview_time: null };
                            setAgentConfigs(next);
                          }}
                          className={clsx(
                            "flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg text-sm font-medium transition-all duration-200",
                            agentCfg && (agentCfg.interview_mode === 'offline' || agentCfg.interview_mode === 'in_person')
                              ? 'bg-white text-blue-700 shadow-md ring-1 ring-blue-100'
                              : 'text-gray-600 hover:text-gray-900 hover:bg-white/50'
                          )}
                        >
                          <Users size={16} />
                          In-person
                        </button>
                      </>
                    )}
                  </div>


                  {/* Interview time for agent mode */}
                  {agentCfg && agentCfg.interview_mode === 'agent' && (
                    <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4 items-end">
                      <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700">Min interview time (minutes)</label>
                        <input
                          type="number"
                          min={1}
                          value={agentCfg.interview_time_min ?? ''}
                          onChange={(e) => {
                            if (!setAgentConfigs) return;
                            const next = agentConfigs ? [...agentConfigs] : [];
                            next[index] = { ...(next[index] || {}), interview_time_min: Number(e.target.value) };
                            setAgentConfigs(next);
                          }}
                          className="w-full bg-white border-2 rounded-xl px-4 py-3 text-base placeholder-gray-400 focus:outline-none focus:ring-0 focus:border-blue-500 shadow-sm transition-all duration-200 border-gray-200 hover:border-gray-300"
                        />
                      </div>
                      <div>
                        <label className="mb-2 block text-sm font-medium text-slate-700">Max interview time (minutes)</label>
                        <input
                          type="number"
                          min={1}
                          value={agentCfg.interview_time_max ?? ''}
                          onChange={(e) => {
                            if (!setAgentConfigs) return;
                            const next = agentConfigs ? [...agentConfigs] : [];
                            next[index] = { ...(next[index] || {}), interview_time_max: Number(e.target.value) };
                            setAgentConfigs(next);
                          }}
                          className="w-full bg-white border-2 rounded-xl px-4 py-3 text-base placeholder-gray-400 focus:outline-none focus:ring-0 focus:border-blue-500 shadow-sm transition-all duration-200 border-gray-200 hover:border-gray-300"
                        />
                      </div>
                    </div>
                  )}

                  {/* === MODIFICATION: Replaced input with UserSearchCombobox === */}
                  {agentCfg && (agentCfg.interview_mode === 'offline' || agentCfg.interview_mode === 'in_person') && (
                    <div className="mt-4">
                      <label className="mb-2 block text-sm font-medium text-slate-700">Interviewer</label>
                      <UserSearchCombobox
                        value={agentCfg.interviewer_id || agentCfg.interviewerId || null}
                        onChange={(userId: string | null) => {
                          if (!setAgentConfigs) return;
                          const next = agentConfigs ? [...agentConfigs] : [];
                          next[index] = { 
                            ...(next[index] || {}), 
                            interviewer_id: userId,
                            interviewerId: userId // Set both for compatibility
                          };
                          setAgentConfigs(next);
                        }}
                      />
                    </div>
                  )}
                  {/* === END MODIFICATION === */}

                </div>

                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">Description</label>
                  <textarea
                    value={level.description}
                    onChange={(e) => handleLevelChange(index, 'description', e.target.value)}
                    placeholder="Add a short description for this round (e.g., goals, duration, interviewers)..."
                    className="w-full bg-white border-2 rounded-xl px-4 py-3 text-base placeholder-gray-400 focus:outline-none focus:ring-0 focus:border-blue-500 shadow-sm transition-all duration-200 border-gray-200 hover:border-gray-300 resize-y"
                    rows={3}
                  />
                </div>
              </div>
              {/* RENDER SCORE DISTRIBUTION FOR ROUND 1 */}
              {isRoundOne && (
                <div className="border-t border-slate-200 bg-slate-50 px-6 py-5">
                  <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between mb-5">
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white shadow-sm">
                        <Percent size={16} className="text-blue-600" />
                      </div>
                      <div>
                        <h5 className="text-base font-semibold text-slate-900">Score distribution</h5>
                        <p className="text-sm text-slate-600">Allocate weight across evaluation criteria.</p>
                      </div>
                    </div>
                    <span
                      className={clsx(
                        'inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-semibold',
                        totalScore === 100
                          ? 'bg-emerald-50 text-emerald-700'
                          : totalScore < 100
                          ? 'bg-amber-50 text-amber-700'
                          : 'bg-rose-50 text-rose-700'
                      )}
                    >
                      Total {totalScore}%
                    </span>
                  </div>
                  
                  {scoreTotalError && (
                    <div className="mb-4 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
                      {scoreTotalError}
                    </div>
                  )}
                  
                  {totalScore !== 100 && !scoreTotalError && (
                    <div
                      className={clsx(
                        'mb-4 rounded-md px-4 py-3 text-sm font-medium',
                        totalScore < 100 ? 'bg-amber-50 text-amber-700' : 'bg-rose-50 text-rose-700'
                      )}
                    >
                      {totalScore < 100
                        ? `Score distribution is incomplete. Remaining ${100 - totalScore}%.`
                        : `Score distribution exceeds 100% by ${totalScore - 100}%.`}
                    </div>
                  )}
                  
                  {totalScore === 100 && !scoreTotalError && (
                    <div className="mb-4 rounded-md bg-emerald-50 px-4 py-3 text-sm font-medium text-emerald-700">
                      Score distribution totals 100%.
                    </div>
                  )}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {scoreFields.map(field => (
                      <ScoreInput
                        key={field.label}
                        label={field.label}
                        value={field.value}
                        onChange={field.set}
                        totalScore={totalScore}
                        min={5}
                        step={5}
                      />
                    ))}
                  </div>
                </div>
              )}
              {/* RENDER THRESHOLDS FOR ALL ROUNDS */}
              <div className="border-t border-slate-200 bg-slate-50 px-6 py-5">
                <div className="mb-5 flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-white shadow-sm">
                    <Target size={16} className="text-emerald-600" />
                  </div>
                  <div>
                    <h5 className="text-base font-semibold text-slate-900">Evaluation thresholds</h5>
                    <p className="text-sm text-slate-600">Define the ranges for advancing or rejecting candidates.</p>
                  </div>
                </div>
                {thresholdError && (
                  <div className="mb-4 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2.5 text-sm font-medium text-rose-700">
                    <span className="mt-0.5">⚠️</span>
                    <span>Reject threshold cannot exceed shortlist threshold.</span>
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  <ThresholdField
                    label="Shortlist threshold"
                    value={level.shortlistThreshold}
                    onChange={(val: number) => handleLevelChange(index, 'shortlistThreshold', val)}
                    color="green"
                    min={10}
                  />
                  <ThresholdField
                    label="Reject threshold"
                    value={level.rejectThreshold}
                    onChange={(val: number) => handleLevelChange(index, 'rejectThreshold', val)}
                    color="red"
                    min={5}
                  />
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-center text-sm text-slate-600">
                    <span className="font-semibold text-slate-700">Under review range</span>
                    <div className="mt-2 text-sm font-medium text-slate-700">
                    {level.rejectThreshold >= level.shortlistThreshold ? (
                      <span className="text-rose-600">Adjust thresholds to create a valid range.</span>
                    ) : (
                      <span>
                        {level.rejectThreshold + 1}% – {level.shortlistThreshold - 1}% remain under manual review.
                      </span>
                    )}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}

      </div>

      {error && (
        <div className="mt-4 rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-medium text-rose-700">
          {error}
        </div>
      )}
    </div>
  );
};

export default InterviewLevelsConfig;