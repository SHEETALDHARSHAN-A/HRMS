// // src/components/common/CandidateDetailModal.tsx
// import React from 'react';
// import { Zap, FileText, Mail, MapPin, User, Target, XCircle as CloseCircle } from 'lucide-react';
// import clsx from 'clsx';
// import type { Candidate } from '../../api/recruitmentApi';

// interface CandidateDetailModalProps {
//     candidate: Candidate;
//     onClose: () => void;
// }

// const CandidateDetailModal: React.FC<CandidateDetailModalProps> = ({ candidate, onClose }) => {
//     const { extracted_resume_content, score_breakdown, skill_explanation } = candidate;
//     const { 
//         summary, 
//         skills: extractedSkills, 
//         experience, 
//         education,
//         email, 
//         location 
//     } = extracted_resume_content;

//     const scoreFields = Object.keys(score_breakdown).map(key => ({
//         label: key,
//         value: (score_breakdown as any)[key],
//     }));

//     const sortedSkills = Object.keys(skill_explanation).map(key => ({
//         skill: key,
//         ...skill_explanation[key]
//     })).sort((a, b) => b.score - a.score);

//     const getStatusText = (score: number) => {
//         if (score >= 60) return "High Match";
//         if (score >= 30) return "Moderate Match";
//         return "Low/No Match";
//     };

//     return (
//         <div className="fixed inset-0 z-[9999] bg-black/40 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
//             <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
                
//                 {/* Header */}
//                 <div className="sticky top-0 bg-white border-b border-gray-200 p-6 flex justify-between items-center z-10">
//                     <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
//                         <User size={24} className="text-[var(--color-primary-500)]" />
//                         {candidate.candidate_name}
//                     </h2>
//                     <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-100 text-gray-500">
//                         <CloseCircle size={20} />
//                     </button>
//                 </div>

//                 <div className="p-6 space-y-8">
//                     {/* Section 1: Quick Score Summary */}
//                     <section>
//                         <h3 className="text-xl font-semibold text-gray-800 mb-4">Overall Score: <span className={clsx(
//                             'text-3xl font-bold',
//                             candidate.round_status === 'shortlisted' ? 'text-green-600' :
//                             candidate.round_status === 'rejected' ? 'text-red-600' : 'text-yellow-600'
//                         )}>{candidate.overall_score}%</span></h3>
//                         <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
//                             {scoreFields.map((field, index) => (
//                                 <div key={index} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
//                                     <div className="text-sm font-medium text-gray-600 truncate">{field.label}</div>
//                                     <div className="text-xl font-bold text-gray-900 mt-1">{field.value}%</div>
//                                 </div>
//                             ))}
//                         </div>
//                     </section>

//                     {/* Section 2: Skill Score Breakdown */}
//                     <section>
//                         <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
//                             <Zap size={20} className="text-amber-500" />
//                             Skill Match & Evidence
//                         </h3>
//                         <div className="space-y-3">
//                             {sortedSkills.map((skill, index) => (
//                                 <div key={index} className="p-4 border border-gray-100 rounded-lg shadow-sm bg-white hover:border-blue-200 transition-colors">
//                                     <div className="flex justify-between items-center mb-2">
//                                         <h4 className="font-semibold text-gray-900">{skill.skill}</h4>
//                                         <div className={clsx(
//                                             'px-3 py-1 text-xs font-bold rounded-full border',
//                                             skill.score >= 60 ? 'bg-green-50 text-green-700 border-green-200' :
//                                             skill.score >= 30 ? 'bg-yellow-50 text-yellow-700 border-yellow-200' : 'bg-red-50 text-red-700 border-red-200'
//                                         )}>
//                                             <Target size={12} className="inline mr-1"/>{skill.score}% - {getStatusText(skill.score)}
//                                         </div>
//                                     </div>
//                                     <div className="text-sm space-y-1.5">
//                                         <p className="text-gray-700">
//                                             <span className="font-medium text-blue-600">Explanation:</span> {skill.explanation}
//                                         </p>
//                                         <p className="text-gray-500 text-xs mt-1 border-t border-gray-100 pt-1">
//                                             <span className="font-medium text-gray-600">Evidence in Resume:</span> {skill.evidence}
//                                         </p>
//                                     </div>
//                                 </div>
//                             ))}
//                         </div>
//                     </section>

//                     {/* Section 3: Extracted Resume Content */}
//                     <section>
//                         <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
//                             <FileText size={20} className="text-blue-500" />
//                             Extracted Resume Summary
//                         </h3>
//                         <div className="bg-blue-50/50 border border-blue-200 rounded-lg p-4">
//                             <p className="text-sm text-gray-700 italic leading-relaxed">{extracted_resume_content.summary}</p>
//                             <div className="mt-4 pt-3 border-t border-blue-200">
//                                 <p className="text-xs text-gray-600">
//                                     <Mail size={12} className="inline mr-1" /> {extracted_resume_content.email}
//                                     <span className="mx-3 text-gray-400">|</span>
//                                     <MapPin size={12} className="inline mr-1" /> {extracted_resume_content.location}
//                                 </p>
//                             </div>
//                         </div>
//                     </section>

//                     {/* Section 4: Extracted Skills List */}
//                     {extractedSkills && extractedSkills.length > 0 && (
//                         <section>
//                             <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
//                                 <Code size={20} className="text-indigo-500" />
//                                 Extracted Skills ({extractedSkills.length})
//                             </h3>
//                             <div className="flex flex-wrap gap-2">
//                                 {extractedSkills.map((skill, index) => (
//                                     <span key={index} className="px-3 py-1 text-sm font-medium rounded-full bg-indigo-100 text-indigo-700 border border-indigo-200">
//                                         {skill}
//                                     </span>
//                                 ))}
//                             </div>
//                         </section>
//                     )}

//                     {/* Section 5: Experience */}
//                     {experience && experience.length > 0 && (
//                         <section>
//                             <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
//                                 <Briefcase size={20} className="text-green-500" />
//                                 Experience ({experience.length})
//                             </h3>
//                             <div className="space-y-4">
//                                 {experience.map((exp: any, index: number) => (
//                                     <div key={index} className="p-4 border border-gray-100 rounded-lg shadow-sm">
//                                         <div className="flex justify-between items-start">
//                                             <h4 className="text-lg font-bold text-gray-900">{exp.role} at {exp.company}</h4>
//                                             <span className="text-sm text-gray-500">{exp.duration}</span>
//                                         </div>
//                                         <p className="text-sm text-gray-600 mt-2 whitespace-pre-wrap">{exp.description}</p>
//                                     </div>
//                                 ))}
//                             </div>
//                         </section>
//                     )}

//                     {/* Section 6: Education */}
//                     {education && education.length > 0 && (
//                         <section>
//                             <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
//                                 <GraduationCap size={20} className="text-purple-500" />
//                                 Education ({education.length})
//                             </h3>
//                             <div className="space-y-4">
//                                 {education.map((edu: any, index: number) => (
//                                     <div key={index} className="p-4 border border-gray-100 rounded-lg shadow-sm bg-purple-50">
//                                         <h4 className="text-md font-bold text-gray-900">{edu.degree}</h4>
//                                         <p className="text-sm text-gray-700">{edu.institution}</p>
//                                         <p className="text-xs text-gray-500 mt-1">Graduation Year: {edu.year}</p>
//                                     </div>
//                                 ))}
//                             </div>
//                         </section>
//                     )};
//                 </div>
//             </div>
//         </div>
//     );
// };

// export default CandidateDetailModal;


// src/components/common/CandidateDetailModal.tsx
import React from 'react';
import { Zap, FileText, Mail, MapPin, User, Target, XCircle as CloseCircle, Code, Briefcase, GraduationCap } from 'lucide-react';
import clsx from 'clsx';
import type { Candidate } from '../../api/recruitmentApi';

interface CandidateDetailModalProps {
    candidate: Candidate;
    onClose: () => void;
}

const CandidateDetailModal: React.FC<CandidateDetailModalProps> = ({ candidate, onClose }) => {
    const { extracted_resume_content, score_breakdown, skill_explanation } = candidate;
    const { 
        summary, 
        skills: extractedSkills, 
        experience, 
        education,
        email, 
        location 
    } = extracted_resume_content;

    const scoreFields = Object.keys(score_breakdown).map(key => ({
        label: key,
        value: (score_breakdown as any)[key],
    }));

    // Sort skills by relevance score descending
    const sortedSkills = Object.keys(skill_explanation).map(key => ({
        skill: key,
        ...skill_explanation[key]
    })).sort((a, b) => b.score - a.score);

    const getStatusText = (score: number) => {
        if (score >= 60) return "High Match";
        if (score >= 30) return "Moderate Match";
        return "Low/No Match";
    };

    return (
        <div className="fixed inset-0 z-[9999] bg-black/40 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
                
                {/* Header */}
                <div className="sticky top-0 bg-white border-b border-gray-200 p-6 flex justify-between items-center z-10">
                    <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
                        <User size={24} className="text-[var(--color-primary-500)]" />
                        {candidate.candidate_name}
                    </h2>
                    <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-100 text-gray-500">
                        <CloseCircle size={20} />
                    </button>
                </div>

                <div className="p-6 space-y-8">
                    {/* Section 1: Quick Score Summary */}
                    <section>
                        <h3 className="text-xl font-semibold text-gray-800 mb-4">Overall Score: <span className={clsx(
                            'text-3xl font-bold',
                            candidate.round_status === 'shortlisted' ? 'text-green-600' :
                            candidate.round_status === 'rejected' ? 'text-red-600' : 'text-yellow-600'
                        )}>{candidate.overall_score}%</span></h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            {scoreFields.map((field, index) => (
                                <div key={index} className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                                    <div className="text-sm font-medium text-gray-600 truncate">{field.label}</div>
                                    <div className="text-xl font-bold text-gray-900 mt-1">{field.value}%</div>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* Section 2: Skill Score Breakdown (AI-Scored Skills) */}
                    <section>
                        <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
                            <Zap size={20} className="text-amber-500" />
                            Skill Match & Evidence (Scored)
                        </h3>
                        <div className="space-y-3">
                            {sortedSkills.map((skill, index) => (
                                <div key={index} className="p-4 border border-gray-100 rounded-lg shadow-sm bg-white hover:border-blue-200 transition-colors">
                                    <div className="flex justify-between items-center mb-2">
                                        <h4 className="font-semibold text-gray-900">{skill.skill}</h4>
                                        <div className={clsx(
                                            'px-3 py-1 text-xs font-bold rounded-full border',
                                            skill.score >= 60 ? 'bg-green-50 text-green-700 border-green-200' :
                                            skill.score >= 30 ? 'bg-yellow-50 text-yellow-700 border-yellow-200' : 'bg-red-50 text-red-700 border-red-200'
                                        )}>
                                            <Target size={12} className="inline mr-1"/>{skill.score}% - {getStatusText(skill.score)}
                                        </div>
                                    </div>
                                    <div className="text-sm space-y-1.5">
                                        <p className="text-gray-700">
                                            <span className="font-medium text-blue-600">Explanation:</span> {skill.explanation}
                                        </p>
                                        <p className="text-gray-500 text-xs mt-1 border-t border-gray-100 pt-1">
                                            <span className="font-medium text-gray-600">Evidence in Resume:</span> {skill.evidence}
                                        </p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* Section 3: Extracted Resume Content Summary */}
                    <section>
                        <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
                            <FileText size={20} className="text-blue-500" />
                            Extracted Resume Details
                        </h3>
                        <div className="bg-blue-50/50 border border-blue-200 rounded-lg p-4">
                            <h4 className="text-lg font-semibold text-gray-900 mb-3">Professional Summary</h4>
                            <p className="text-sm text-gray-700 italic leading-relaxed">
                                {summary || "Summary details not present in the resume."}
                            </p>
                            
                            <div className="mt-4 pt-3 border-t border-blue-200">
                                <p className="text-xs text-gray-600">
                                    <Mail size={12} className="inline mr-1" /> {email}
                                    <span className="mx-3 text-gray-400">|</span>
                                    <MapPin size={12} className="inline mr-1" /> {location || "Not provided"}
                                </p>
                            </div>
                        </div>
                    </section>

                    {/* Section 4: Extracted Skills List */}
                    {extractedSkills && extractedSkills.length > 0 && (
                        <section>
                            <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
                                <Code size={20} className="text-indigo-500" />
                                Extracted Skills ({extractedSkills.length})
                            </h3>
                            <div className="flex flex-wrap gap-2">
                                {extractedSkills.map((skill, index) => (
                                    <span key={index} className="px-3 py-1 text-sm font-medium rounded-full bg-indigo-100 text-indigo-700 border border-indigo-200">
                                        {skill}
                                    </span>
                                ))}
                            </div>
                        </section>
                    )}

                    {/* Section 5: Experience */}
                    {experience && experience.length > 0 && (
                        <section>
                            <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
                                <Briefcase size={20} className="text-green-500" />
                                Experience ({experience.length})
                            </h3>
                            <div className="space-y-4">
                                {experience.map((exp: any, index: number) => (
                                    <div key={index} className="p-4 border border-gray-100 rounded-lg shadow-sm">
                                        <div className="flex justify-between items-start">
                                            <h4 className="text-lg font-bold text-gray-900">{exp.role} at {exp.company}</h4>
                                            <span className="text-sm text-gray-500">{exp.duration}</span>
                                        </div>
                                        <p className="text-sm text-gray-600 mt-2 whitespace-pre-wrap">{exp.description}</p>
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}

                    {/* Section 6: Education */}
                    {education && education.length > 0 && (
                        <section>
                            <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
                                <GraduationCap size={20} className="text-purple-500" />
                                Education ({education.length})
                            </h3>
                            <div className="space-y-4">
                                {education.map((edu: any, index: number) => (
                                    <div key={index} className="p-4 border border-gray-100 rounded-lg shadow-sm bg-purple-50">
                                        <h4 className="text-md font-bold text-gray-900">{edu.degree}</h4>
                                        <p className="text-sm text-gray-700">{edu.institution}</p>
                                        <p className="text-xs text-gray-500 mt-1">Graduation Year: {edu.year}</p>
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}
                </div>
            </div>
        </div>
    );
};

export default CandidateDetailModal;