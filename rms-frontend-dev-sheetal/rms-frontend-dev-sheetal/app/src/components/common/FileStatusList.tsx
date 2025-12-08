// // src/pages/ControlHub/components/FileStatusList.tsx
// import { Loader2, CheckCircle, AlertTriangle, Database, Wifi, WifiOff, Clock } from 'lucide-react';

// interface UploadedFile {
//   file: File;
//   // Use a simplified status for UI mapping
//   status: 'pending' | 'queued' | 'processing' | 'completed' | 'failed'; 
//   progress: number;
//   error?: string;
//   parsedData?: Record<string, string>;
//   profileId?: string;
// }

// interface FileStatusListProps {
//   files: UploadedFile[];
//   isConnected: boolean; 
// }

// const statusStyles = {
//   pending: {
//     icon: <Loader2 size={16} className="text-gray-400" />,
//     text: 'text-gray-500',
//     bg: 'bg-white',
//     border: 'border-gray-200',
//     progressBg: 'bg-gray-400',
//     statusText: 'Pending Upload',
//   },
//   queued: {
//     icon: <Clock size={16} className="text-yellow-500" />,
//     text: 'text-yellow-600',
//     bg: 'bg-yellow-50',
//     border: 'border-yellow-300',
//     progressBg: 'bg-yellow-500',
//     statusText: 'Queued for Worker',
//   },
//   // Maps to 'processing' and 'curation_in_progress' stages from worker
//   processing: {
//     icon: <Loader2 size={16} className="animate-spin text-blue-500" />,
//     text: 'text-blue-600',
//     bg: 'bg-blue-50',
//     border: 'border-blue-300',
//     progressBg: 'bg-blue-500',
//     statusText: 'Processing',
//   },
//   completed: {
//     icon: <CheckCircle size={16} className="text-green-500" />,
//     text: 'text-green-600',
//     bg: 'bg-green-50',
//     border: 'border-green-300',
//     progressBg: 'bg-green-500',
//     statusText: 'Complete',
//   },
//   // Maps to 'failed_extraction', 'failed_curation', 'failed' from worker, plus frontend skips
//   failed: {
//     icon: <AlertTriangle size={16} className="text-red-500" />,
//     text: 'text-red-600',
//     bg: 'bg-red-50',
//     border: 'border-red-300',
//     progressBg: 'bg-red-500',
//     statusText: 'Failed/Skipped',
//   },
// };

// const FileStatusList: React.FC<FileStatusListProps> = ({ files, isConnected }) => {
//   // Check if all queued/processing files are now in a final state (completed or failed)
//   const isJobFinished = files.length > 0 && files.every(f => 
//     f.status === 'completed' || f.status === 'failed' || f.status === 'pending'
//   );
  
//   let globalStatus: 'live' | 'finished' | 'disconnected' = 'disconnected';
//   if (isConnected) {
//     globalStatus = 'live';
//   } else if (isJobFinished) {
//     globalStatus = 'finished';
//   }
  
//   const statusBadge = {
//       live: { text: 'Live', class: 'bg-green-100 text-green-700', Icon: Wifi },
//       finished: { text: 'Finished', class: 'bg-gray-100 text-gray-700', Icon: CheckCircle },
//       disconnected: { text: 'Disconnected', class: 'bg-red-100 text-red-700', Icon: WifiOff },
//   }[globalStatus];

//   // Sort files: Processing first, then Queued, then Completed/Failed
//   const sortedFiles = [...files].sort((a, b) => {
//     const statusOrder = { pending: 4, queued: 1, processing: 0, completed: 2, failed: 3 };
//     return statusOrder[a.status] - statusOrder[b.status];
//   }).filter(f => f.status !== 'pending'); // Filter out only 'pending' files from this list

//   return (
//     <div>
//       <div className="flex justify-between items-center mb-4">
//         <h3 className="text-lg font-bold text-gray-800">Processing & Validation</h3>
//         <div className={`flex items-center gap-2 text-xs font-semibold px-3 py-1 rounded-full ${statusBadge.class}`}>
//           <statusBadge.Icon size={14} />
//           <span>{statusBadge.text}</span>
//         </div>
//       </div>
//       <div className="space-y-4 max-h-[440px] overflow-y-auto pr-2">
//         {sortedFiles.map(file => {
//           const uiStatus = file.status; 
//           const style = statusStyles[uiStatus] || statusStyles.queued;
          
//           const isTerminalStatus = uiStatus === 'completed' || uiStatus === 'failed';
//           // Use the progress from the message directly, forcing 100% on terminal states
//           const displayProgress = isTerminalStatus ? 100 : file.progress;

//           // Determine if the file has fully completed the overall process (i.e., not a failed step within a batch)
//           const isFinalSuccess = uiStatus === 'completed' && file.profileId;

//           return (
//             <div key={file.file.name} className={`p-4 rounded-lg border-l-4 ${style.bg} ${style.border}`}>
//               <div className="flex justify-between items-start">
//                   <div>
//                       <p className="text-sm font-semibold text-gray-900 truncate">{file.file.name}</p>
//                       <div className={`flex items-center text-xs font-semibold mt-1 gap-1.5 ${style.text}`}>
//                           {style.icon}
//                           <span className="capitalize">{style.statusText}</span>
//                       </div>
//                   </div>
//                   {/* Show Profile ID for successfully completed files */}
//                   {isFinalSuccess && (
//                     <div className="flex items-center gap-1.5 text-xs font-medium text-green-700 bg-green-200 px-2 py-1 rounded-full">
//                         <Database size={12}/>
//                         Ready (Profile ID: {file.profileId?.substring(0, 4) || 'N/A'}...)
//                     </div>
//                   )}
//                   {/* Show specific status details for FAILED files at the end of the line */}
//                   {uiStatus === 'failed' && (
//                     <div className="flex items-center gap-1.5 text-xs font-medium text-red-700 bg-red-200 px-2 py-1 rounded-full">
//                         <AlertTriangle size={12}/>
//                         Skipped/Failed
//                     </div>
//                   )}
//               </div>
              
//               {/* Show progress bar for all states that use progress */}
//               {['queued', 'processing', 'completed', 'failed'].includes(uiStatus) && (
//                 <div className="relative pt-2">
//                   <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
//                     <div
//                       className={`h-1.5 rounded-full transition-all duration-300 ${style.progressBg}`}
//                       style={{ width: `${displayProgress}%` }}
//                     ></div>
//                   </div>
//                 </div>
//               )}

//               {/* CRITICAL: Display detailed error message below the progress bar/icon */}
//               {uiStatus === 'failed' && file.error && <p className="text-xs text-red-700 mt-2 font-medium">Reason: {file.error}</p>}
//             </div>
//           );
//         })}
//         {files.length === 0 && (
//             <div className="text-center py-10 border-2 border-dashed border-gray-300 rounded-lg">
//                 <p className="text-sm text-gray-500">Upload files to see their status.</p>
//             </div>
//         )}
//       </div>
//     </div>
//   );
// };

// export default FileStatusList;

// src/components/common/FileStatusList.tsx
import { Loader2, CheckCircle, AlertTriangle, Database, Wifi, WifiOff, Clock, FileText, X } from 'lucide-react';

interface UploadedFile {
  file: File;
  status: 'pending' | 'queued' | 'processing' | 'extraction' | 'initialization' | 'completed' | 'failed'; 
  progress: number;
  currentFileNumber?: number;
  totalFiles?: number;
  error?: string;
  profileId?: string;
  stage?: string;
  statusMessage?: string;
}

interface FileStatusListProps {
  files: UploadedFile[];
  isConnected: boolean; 
  onRemoveFile?: (fileName: string) => void; // 💡 Make remove optional
}

const statusStyles = {
  pending: {
    icon: <FileText size={16} className="text-gray-500" />,
    text: 'text-gray-600',
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    progressBg: 'bg-gradient-to-r from-gray-300 to-gray-400',
    statusText: 'Ready to Upload',
  },
  initialization: {
    icon: <Loader2 size={16} className="animate-spin text-purple-500" />,
    text: 'text-purple-600',
    bg: 'bg-purple-50',
    border: 'border-purple-300',
    progressBg: 'bg-gradient-to-r from-purple-400 to-purple-600',
    statusText: 'Initializing',
  },
  extraction: {
    icon: <Loader2 size={16} className="animate-spin text-indigo-500" />,
    text: 'text-indigo-600',
    bg: 'bg-indigo-50',
    border: 'border-indigo-300',
    progressBg: 'bg-gradient-to-r from-indigo-400 to-indigo-600',
    statusText: 'Extracting Content',
  },
  queued: {
    icon: <Clock size={16} className="text-yellow-500" />,
    text: 'text-yellow-600',
    bg: 'bg-yellow-50',
    border: 'border-yellow-300',
    progressBg: 'bg-gradient-to-r from-yellow-400 to-yellow-500',
    statusText: 'Queued for Processing',
  },
  processing: {
    icon: <Loader2 size={16} className="animate-spin text-blue-500" />,
    text: 'text-blue-600',
    bg: 'bg-blue-50',
    border: 'border-blue-300',
    progressBg: 'bg-gradient-to-r from-blue-400 to-blue-600',
    statusText: 'Processing File',
  },
  completed: {
    icon: <CheckCircle size={16} className="text-green-500" />,
    text: 'text-green-600',
    bg: 'bg-green-50',
    border: 'border-green-300',
    progressBg: 'bg-gradient-to-r from-green-400 to-green-500',
    statusText: 'Successfully Processed',
  },
  failed: {
    icon: <AlertTriangle size={16} className="text-red-500" />,
    text: 'text-red-600',
    bg: 'bg-red-50',
    border: 'border-red-300',
    progressBg: 'bg-gradient-to-r from-red-400 to-red-500',
    statusText: 'Failed/Skipped',
  },
};

const FileStatusList: React.FC<FileStatusListProps> = ({ files, isConnected, onRemoveFile }) => {
  const stageLabelMap: Record<string, string> = {
    duplicate: 'previously processed',
  };
  const isJobFinished = files.length > 0 && files.every(f => 
    f.status === 'completed' || f.status === 'failed'
  );
  
  let globalStatus: 'live' | 'finished' | 'disconnected' | 'idle' = 'disconnected';
  if (files.length === 0) {
      globalStatus = 'idle';
  } else if (isConnected) {
    globalStatus = 'live';
  } else if (isJobFinished) {
    globalStatus = 'finished';
  }
  
  const statusBadge = {
      idle: { text: 'Idle', class: 'bg-gray-100 text-gray-700', Icon: WifiOff },
      live: { text: 'Live', class: 'bg-green-100 text-green-700', Icon: Wifi },
      finished: { text: 'Finished', class: 'bg-gray-100 text-gray-700', Icon: CheckCircle },
      disconnected: { text: 'Disconnected', class: 'bg-red-100 text-red-700', Icon: WifiOff },
  }[globalStatus];

  // 💡 Sort files: Pending first, then Processing/Queued, then Completed/Failed
  const sortedFiles = [...files].sort((a, b) => {
    const statusOrder = { 
      pending: 0, 
      initialization: 1,
      extraction: 2,
      queued: 3, 
      processing: 4, 
      completed: 5, 
      failed: 6 
    };
    return (statusOrder[a.status as keyof typeof statusOrder] || 0) - (statusOrder[b.status as keyof typeof statusOrder] || 0);
  });

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-bold text-gray-800">File Queue & Status</h3>
        <div className={`flex items-center gap-2 text-xs font-semibold px-3 py-1 rounded-full ${statusBadge.class}`}>
          <statusBadge.Icon size={14} />
          <span>{statusBadge.text}</span>
        </div>
      </div>
      <div className="space-y-3 max-h-[440px] overflow-y-auto pr-2">
        {sortedFiles.map(file => {
          const uiStatus = file.status; 
          const style = statusStyles[uiStatus] || statusStyles.queued;
          const isTerminalStatus = uiStatus === 'completed' || uiStatus === 'failed';
          const displayProgress = isTerminalStatus ? 100 : file.progress;
          const isFinalSuccess = uiStatus === 'completed' && file.profileId;
          const friendlyStage = file.stage ? (stageLabelMap[file.stage] || file.stage.replace(/_/g, ' ')) : undefined;

          return (
            <div key={file.file.name} className={`p-4 rounded-lg border-l-4 ${style.bg} ${style.border}`}>
              <div className="flex justify-between items-start">
                  <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-900 truncate">{file.file.name}</p>
                      <div className={`flex items-center text-xs font-semibold mt-1 gap-1.5 ${style.text}`}>
                          {style.icon}
                          <span className="capitalize">{style.statusText}</span>
                          {uiStatus === 'pending' && (
                              <span className="text-gray-500 font-normal"> - {(file.file.size / 1024).toFixed(1)} KB</span>
                          )}
                      </div>
                  </div>

                  {/* 💡 Show Remove button only for 'pending' state */}
                  {uiStatus === 'pending' && onRemoveFile && (
                    <button onClick={() => onRemoveFile(file.file.name)} className="ml-4 p-1 text-gray-400 hover:text-red-500 rounded-full transition-colors flex-shrink-0">
                      <X size={16} />
                    </button>
                  )}

                  {isFinalSuccess && (
                    <div className="flex items-center gap-1.5 text-xs font-medium text-green-700 bg-green-200 px-2 py-1 rounded-full flex-shrink-0">
                        <Database size={12}/>
                        Ready
                    </div>
                  )}
                  {uiStatus === 'failed' && (
                    <div className="flex items-center gap-1.5 text-xs font-medium text-red-700 bg-red-200 px-2 py-1 rounded-full flex-shrink-0">
                        <AlertTriangle size={12}/>
                        Skipped/Failed
                    </div>
                  )}
              </div>
              
              <div className="relative pt-2">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>
                    {style.statusText}
                    {(file.currentFileNumber && file.totalFiles) && (
                      <span className="ml-1 text-gray-400">
                        (File {file.currentFileNumber}/{file.totalFiles})
                      </span>
                    )}
                    {file.stage && (
                      <span className="ml-1 text-gray-400">
                        - {friendlyStage}
                      </span>
                    )}
                  </span>
                  <span>{displayProgress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full transition-all duration-300 ${style.progressBg}`}
                    style={{ 
                      width: `${displayProgress}%`,
                      boxShadow: (uiStatus === 'processing' || uiStatus === 'extraction' || uiStatus === 'initialization') 
                        ? '0 0 8px rgba(59, 130, 246, 0.5)' 
                        : 'none'
                    }}
                  ></div>
                </div>
                {file.statusMessage && (
                  <p className="text-[11px] text-gray-500 mt-2 leading-snug">
                    {file.statusMessage}
                  </p>
                )}
              </div>

              {uiStatus === 'failed' && file.error && <p className="text-xs text-red-700 mt-2 font-medium">Reason: {file.error}</p>}
            </div>
          );
        })}
        {files.length === 0 && (
            <div className="text-center py-10 border-2 border-dashed border-gray-300 rounded-lg">
                <p className="text-sm text-gray-500">Upload files to see their status.</p>
            </div>
        )}
      </div>
    </div>
  );
};

export default FileStatusList;