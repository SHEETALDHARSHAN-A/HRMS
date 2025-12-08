// import { Settings } from "lucide-react";
// import type { FC } from "react";

// interface ScoringConfigProps {
//   roleFit: number;
//   setRoleFit: (value: number) => void;
//   potential: number;
//   setPotential: (value: number) => void;
//   jobLocationScore: number;
//   setJobLocationScore: (value: number) => void;
//   shortlisted: number; // This is now the "Shortlist Threshold"
//   setShortlisted: (value: number) => void;
//   rejectThreshold: number; // 💡 NEW: This is the "Reject Threshold"
//   setRejectThreshold: (value: number) => void; // 💡 NEW: Setter for the reject threshold
// }

// const ScoringConfig: FC<ScoringConfigProps> = ({
//   roleFit,
//   setRoleFit,
//   potential,
//   setPotential,
//   jobLocationScore,
//   setJobLocationScore,
//   shortlisted,
//   setShortlisted,
//   rejectThreshold, // 💡 NEW
//   setRejectThreshold, // 💡 NEW
// }) => {
//   const scoreFields = [
//     { label: "Role Fit", value: roleFit, set: setRoleFit },
//     { label: "Potential", value: potential, set: setPotential },
//     { label: "Job Location", value: jobLocationScore, set: setJobLocationScore },
//   ];

//   const totalScore = scoreFields.reduce((sum, field) => sum + field.value, 0);
//   const isValidTotal = totalScore <= 100;

//   const handleUpdateScore = (currentValue: number, newValue: number, setter: (value: number) => void) => {
//     const newTotal = totalScore - currentValue + newValue;
//     if (newTotal <= 100) {
//       setter(newValue);
//     }
//   };

//   // 💡 UPDATED: Shortlist slider is now independent
//   const handleUpdateShortlist = (e: React.ChangeEvent<HTMLInputElement>) => {
//     const value = Math.min(Number(e.target.value), 100);
//     setShortlisted(value);
//   };
  
//   // 💡 NEW: Reject slider is independent
//   const handleUpdateRejectThreshold = (e: React.ChangeEvent<HTMLInputElement>) => {
//     const value = Math.min(Number(e.target.value), 100);
//     setRejectThreshold(value);
//   };
  
//   const handleResetScores = () => {
//     setRoleFit(45);
//     setPotential(45);
//     setJobLocationScore(10);
//     setShortlisted(75); // 💡 Sensible default
//     setRejectThreshold(50); // 💡 Sensible default
//   }
  
//   // 💡 Validation message for threshold logic
//   const thresholdError = rejectThreshold > shortlisted ? "Reject threshold cannot be higher than Shortlist threshold." : null;

//   return (
//     <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200">
//       {/* Header */}
//       <div className="flex items-center gap-3 mb-4">
//         <Settings size={20} className="text-[var(--color-primary-500)]" />
//         <h3 className="text-lg font-bold text-gray-900">Configuration & Scoring</h3>
//       </div>

//       <hr className="mb-5 border-gray-200" />

//       {/* Scoring section */}
//       <div className="flex flex-col space-y-6">
//         <div className="flex items-center justify-between">
//           <span className="font-semibold text-sm text-gray-800">Score Distribution</span>
//           <span 
//             className={`rounded-full px-3 py-1 text-xs font-bold shadow-md ${isValidTotal ? 'bg-[var(--color-primary-500)] text-white' : 'bg-red-500 text-white'}`}
//             title="Total score of Role Fit, Potential, and Job Location"
//           >
//             Total: {Math.min(totalScore, 100)}%
//           </span>
//         </div>

//         {scoreFields.map(({ label, value, set }) => (
//           <div className="flex flex-col" key={label}>
//             <div className="flex items-center justify-between mb-2">
//               <span className="text-sm text-gray-700 font-medium">{label}</span>
//               <span className="text-xs text-gray-600 font-semibold w-8 text-right">{value}%</span>
//             </div>
//             <input
//               type="range"
//               min={0}
//               max={100}
//               step={1}
//               value={value}
//               onChange={(e) => handleUpdateScore(value, Number(e.target.value), set)}
//               className="w-full accent-[var(--color-primary-500)] h-2 rounded-lg cursor-pointer"
//             />
//           </div>
//         ))}
//       </div>

//       {/* Shortlisting criteria */}
//       <div className="mt-8 pt-6 border-t border-gray-200">
//         <span className="font-semibold text-sm block mb-4 text-gray-800">Shortlisting Criteria</span>
        
//         {/* 💡 Threshold Error Message */}
//         {thresholdError && (
//             <div className="text-xs text-red-700 bg-red-50 p-3 rounded-lg border border-red-200 mb-4 font-medium">
//                 {thresholdError}
//             </div>
//         )}

//         <div className="flex flex-col space-y-6">
//           {/* 💡 UPDATED: Shortlist Threshold Slider */}
//           <div>
//             <div className="flex items-center justify-between mb-2">
//               <span className="text-sm text-gray-700 font-medium">Shortlist Threshold</span>
//               <span className="text-xs font-bold text-white px-3 py-1 rounded-full bg-green-500 shadow-md w-12 text-center"> {shortlisted}% </span>
//             </div>
//             <input
//               type="range"
//               min={0}
//               max={100}
//               step={1}
//               value={shortlisted}
//               onChange={handleUpdateShortlist}
//               className="w-full accent-green-500 h-2 rounded-lg cursor-pointer"
//             />
//             <p className="text-xs text-gray-500 mt-1">
//               Candidates scoring <span className="font-bold">{shortlisted}% or higher</span> will be Shortlisted.
//             </p>
//           </div>
          
//           {/* 💡 NEW: Reject Threshold Slider */}
//           <div>
//             <div className="flex items-center justify-between mb-2">
//               <span className="text-sm text-gray-700 font-medium">Reject Threshold</span>
//               <span className="text-xs font-bold text-white px-3 py-1 rounded-full bg-red-500 shadow-md w-12 text-center">{rejectThreshold}%</span>
//             </div>
//             <input
//               type="range"
//               min={0}
//               max={100}
//               step={1}
//               value={rejectThreshold}
//               onChange={handleUpdateRejectThreshold}
//               className="w-full accent-red-500 h-2 rounded-lg cursor-pointer"
//             />
//             <p className="text-xs text-gray-500 mt-1">
//               Candidates scoring <span className="font-bold">{rejectThreshold}% or lower</span> will be Rejected.
//             </p>
//           </div>

//           {/* 💡 NEW: Under Review Info */}
//           <div className="text-center p-3 bg-gray-50 rounded-lg border border-gray-200">
//             <span className="text-sm font-medium text-gray-800">
//               Under Review
//             </span>
//             <p className="text-xs text-gray-600 mt-1">
//               Candidates scoring between <span className="font-bold">{rejectThreshold + 1}%</span> and <span className="font-bold">{shortlisted - 1}%</span> will be marked for "Under Review".
//             </p>
//           </div>
//         </div>
//       </div>

//       {/* Action buttons */}
//       <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-200">
//         <div className="flex justify-center w-full">
//           <button
//             onClick={handleResetScores}
//             className="px-4 py-2 rounded-md text-sm font-medium border border-gray-300 text-gray-700 bg-gray-100 hover:bg-gray-200 transition-colors"
//           >
//             Reset Scores
//           </button>
//         </div>
//       </div>
//     </div>
//   );
// };

// export default ScoringConfig;

// src/components/common/ScoringConfig.tsx
import { Settings } from "lucide-react";
import type { FC } from "react";

interface ScoringConfigProps {
  roleFit: number;
  setRoleFit: (value: number) => void;
  potential: number;
  setPotential: (value: number) => void;
  jobLocationScore: number;
  setJobLocationScore: (value: number) => void;
  // 💡 REMOVED: Shortlisted/Reject props
}

const ScoringConfig: FC<ScoringConfigProps> = ({
  roleFit,
  setRoleFit,
  potential,
  setPotential,
  jobLocationScore,
  setJobLocationScore,
  // 💡 REMOVED: Shortlisted/Reject props
}) => {
  const scoreFields = [
    { label: "Role Fit", value: roleFit, set: setRoleFit },
    { label: "Potential", value: potential, set: setPotential },
    { label: "Job Location", value: jobLocationScore, set: setJobLocationScore },
  ];

  const totalScore = scoreFields.reduce((sum, field) => sum + field.value, 0);
  const isValidTotal = totalScore <= 100;

  const handleUpdateScore = (currentValue: number, newValue: number, setter: (value: number) => void) => {
    const newTotal = totalScore - currentValue + newValue;
    if (newTotal <= 100) {
      setter(newValue);
    }
  };

  const handleResetScores = () => {
    setRoleFit(45);
    setPotential(45);
    setJobLocationScore(10);
    // 💡 REMOVED: Shortlisted/Reject setters
  }
  
  return (
    <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <Settings size={20} className="text-[var(--color-primary-500)]" />
        <h3 className="text-lg font-bold text-gray-900">Configuration & Scoring</h3>
      </div>

      <hr className="mb-5 border-gray-200" />

      {/* Scoring section */}
      <div className="flex flex-col space-y-6">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-sm text-gray-800">Score Distribution</span>
          <span 
            className={`rounded-full px-3 py-1 text-xs font-bold shadow-md ${isValidTotal ? 'bg-[var(--color-primary-500)] text-white' : 'bg-red-500 text-white'}`}
            title="Total score of Role Fit, Potential, and Job Location"
          >
            Total: {Math.min(totalScore, 100)}%
          </span>
        </div>

        {scoreFields.map(({ label, value, set }) => (
          <div className="flex flex-col" key={label}>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-700 font-medium">{label}</span>
              <span className="text-xs text-gray-600 font-semibold w-8 text-right">{value}%</span>
            </div>
            <input
              type="range"
              min={0}
              max={100}
              step={1}
              value={value}
              onChange={(e) => handleUpdateScore(value, Number(e.target.value), set)}
              className="w-full accent-[var(--color-primary-500)] h-2 rounded-lg cursor-pointer"
            />
          </div>
        ))}
      </div>

      {/* 💡 REMOVED: Entire Shortlisting Criteria section */}
      
      {/* Action buttons */}
      <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-200">
        <div className="flex justify-center w-full">
          <button
            onClick={handleResetScores}
            className="px-4 py-2 rounded-md text-sm font-medium border border-gray-300 text-gray-700 bg-gray-100 hover:bg-gray-200 transition-colors"
          >
            Reset Scores
          </button>
        </div>
      </div>
    </div>
  );
};

export default ScoringConfig;