import type { FC } from "react";
import { Sparkles, Plus, Eraser, Trash2, Minus, Loader2 } from "lucide-react";

interface Skill {
  name: string;
  weight: number;
}

interface SkillListProps {
  skills: Skill[];
  newSkill: string;
  setNewSkill: (value: string) => void;
  addSkill: () => void;
  updateSkillWeight: (idx: number, value: number) => void;
  removeSkill: (idx: number) => void;
  onGenerate?: () => void;
  isGenerating?: boolean;
}

const SkillList: FC<SkillListProps> = ({
  skills,
  newSkill,
  setNewSkill,
  addSkill,
  updateSkillWeight,
  removeSkill,
  onGenerate,
  isGenerating = false,
}) => {
  const isMaxSkills = skills.length >= 10;
  
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center gap-3 mb-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100">
          <Sparkles size={16} className="text-slate-600" />
        </div>
        <div>
          <label className="block text-lg font-semibold text-slate-900">Skills & Weightage</label>
          <p className="text-sm text-slate-500">Define the key skills and their importance for this role.</p>
        </div>
        <div className="ml-auto inline-flex items-center gap-3">
          <button
            type="button"
            onClick={() => onGenerate && onGenerate()}
            aria-label="Generate skills with AI"
            title="Generate skills with AI"
            disabled={isGenerating || !onGenerate}
            className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-md border ${isGenerating || !onGenerate ? 'border-slate-200 bg-slate-100 text-slate-400 cursor-not-allowed' : 'border-slate-200 bg-white text-slate-600 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300'} text-sm font-medium transition`}
          >
            {isGenerating ? <Loader2 className="animate-spin" size={14} /> : <Sparkles size={14} />}
            <span>Generate skills with AI</span>
          </button>

          <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
            <Sparkles size={12} />
            {skills.length}/10 skills
          </span>
        </div>
      </div>

      {/* Add Skills Section */}
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-5 mb-4">
        <div className="flex flex-col gap-4">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700">Add New Skill</label>
            <div className="flex flex-col gap-3 sm:flex-row">
              <div className="relative flex-1">
                <input
                  type="text"
                  placeholder="e.g. React, Python, Digital Marketing, Data Analysis"
                  value={newSkill}
                  onChange={(e) => setNewSkill(e.target.value)}
                  className="w-full rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none transition-all placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-50 disabled:cursor-not-allowed"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && newSkill.trim() && !isMaxSkills) addSkill();
                  }}
                  disabled={isMaxSkills}
                />
                {isMaxSkills && (
                  <span className="absolute inset-y-0 right-3 flex items-center text-xs font-semibold text-rose-500">Maximum reached</span>
                )}
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={addSkill}
                  aria-label="Add skill"
                  className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-green-200 bg-white text-green-600 transition-all hover:bg-green-50 hover:border-green-300 disabled:cursor-not-allowed disabled:opacity-40 disabled:border-slate-200 disabled:text-slate-400 disabled:hover:bg-white"
                  disabled={isMaxSkills || !newSkill.trim()}
                >
                  <Plus size={16} />
                </button>
                <button
                  type="button"
                  onClick={() => setNewSkill("")}
                  aria-label="Clear input"
                  className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-600 transition-all hover:bg-amber-50 hover:border-amber-300 hover:text-amber-600"
                  title="Clear input"
                >
                  <Eraser size={16} />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Skills List */}
      <div className="space-y-2.5 max-h-96 overflow-y-auto">
        {skills.map((skill, idx) => (
          <div
            key={idx}
            className="rounded-lg border border-slate-200 bg-white p-3 shadow-sm transition-colors hover:border-slate-300"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-100">
                  <Sparkles size={12} className="text-slate-600" />
                </div>
                <h4 className="text-sm font-semibold text-slate-900">{skill.name}</h4>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-700">
                  {skill.weight}/10
                </span>
                <button
                  type="button"
                  onClick={() => removeSkill(idx)}
                  className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-rose-200 bg-white text-rose-600 transition-all hover:bg-rose-50 hover:border-rose-300"
                  title={`Remove ${skill.name}`}
                >
                  <Trash2 size={12} />
                </button>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <label className="text-xs font-medium text-slate-700 min-w-fit">Importance:</label>
              <div className="flex items-center gap-1.5 flex-1">
                <button
                  type="button"
                  onClick={() => updateSkillWeight(idx, Math.max(1, skill.weight - 1))}
                  disabled={skill.weight <= 1}
                  className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded border border-slate-200 text-slate-600 transition-all hover:border-orange-400 hover:bg-orange-50 hover:text-orange-600 disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:border-slate-200 disabled:hover:bg-transparent disabled:hover:text-slate-600"
                  title="Decrease"
                >
                  <Minus size={12} />
                </button>
                <input
                  type="number"
                  min={1}
                  max={10}
                  step={1}
                  value={skill.weight}
                  onChange={(e) => {
                    const val = parseInt(e.target.value, 10);
                    if (!isNaN(val) && val >= 1 && val <= 10) {
                      updateSkillWeight(idx, val);
                    }
                  }}
                  className="h-7 w-14 rounded border border-slate-200 px-2 text-center text-sm font-semibold text-slate-900 outline-none transition-all focus:border-purple-500 focus:ring-2 focus:ring-purple-100"
                />
                <button
                  type="button"
                  onClick={() => updateSkillWeight(idx, Math.min(10, skill.weight + 1))}
                  disabled={skill.weight >= 10}
                  className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded border border-slate-200 text-slate-600 transition-all hover:border-green-400 hover:bg-green-50 hover:text-green-600 disabled:cursor-not-allowed disabled:opacity-30 disabled:hover:border-slate-200 disabled:hover:bg-transparent disabled:hover:text-slate-600"
                  title="Increase"
                >
                  <Plus size={12} />
                </button>
              </div>
              <span className="text-[10px] text-slate-400 min-w-fit">1 - 10</span>
            </div>
          </div>
        ))}

        {skills.length === 0 && (
          <div className="flex flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed border-slate-200 bg-white py-12 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-slate-100">
              <Sparkles size={24} className="text-slate-600" />
            </div>
            <div>
              <p className="mb-1 text-sm font-semibold text-slate-700">No skills added yet</p>
              <p className="text-xs text-slate-500">Start by adding the key skills required for this position</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SkillList;