// src/components/common/BulkUploaderForJob.tsx
import { useState, useCallback, useEffect, useMemo } from 'react';
import { Loader2, UploadCloud, CheckCircle } from 'lucide-react';
import { useToast } from '../../context/ModalContext';
import { BulkUpload } from '../../api/resumeApi';
import { useTaskStatus } from '../../hooks/useTaskStatus';
import Button from '../../components/common/Button';
import ResumeUploadZone from '../../components/common/ResumeUploadZone';
// import UploadQueue from '../../components/common/UploadQueue'; // REMOVED
// import FileStatusList from '../../components/common/FileStatusList'; // NOT RENDERED
import CircularProgress from './CircularProgress'; // 💡 Import new donut
import FileStatusList from './FileStatusList';

interface JobPost {
  job_id: string;
  job_title: string;
  is_active?: boolean;
}

interface BulkUploaderForJobProps {
  job: JobPost;
  onComplete: () => void; // Callback to go back to the job list
}

interface UploadedFile {
  file: File;
  status: 'pending' | 'queued' | 'processing' | 'initialization' | 'extraction' | 'completed' | 'failed';
  progress: number;
  error?: string;
  profileId?: string;
  stage?: string;
  currentFileNumber?: number;
  totalFiles?: number;
  statusMessage?: string;
}

interface TaskStatusMessage {
  task_id: string;
  job_id: string;
  profile_id?: string; 
  file_name?: string; 
  status: string; 
  stage: string; 
  processing_percentage: number;
}

const normalizeFileName = (name: string | undefined | null) => {
  if (!name) {
    return "";
  }
  return name
    .toLowerCase()
    .replace(/\.[^/.]+$/, "")
    .replace(/[^a-z0-9]/g, "");
};

const BulkUploaderForJob: React.FC<BulkUploaderForJobProps> = ({ job, onComplete }) => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [forceComplete, setForceComplete] = useState(false);
  const [jobProgress, setJobProgress] = useState<number>(0);
  const [jobStage, setJobStage] = useState<string>("");
  const [jobStatusText, setJobStatusText] = useState<string>("");
  const [jobCompleted, setJobCompleted] = useState<boolean>(false);
  const { showToast } = useToast();

  const { latestMessage, isConnected } = useTaskStatus(taskId);

  // Effect to update file status from WebSocket messages
  useEffect(() => {
    if (!latestMessage) {
      return;
    }

  const msg = latestMessage as unknown as TaskStatusMessage;
  // Debug incoming WS payload to help trace missing/incorrect fields
   
  console.debug('BulkUploaderForJob received WS message:', msg);
  const workerStage = (msg.stage || "").toLowerCase();
  const statusText = msg.status ?? "";
    const rawProgress = Number(msg.processing_percentage ?? 0);
    const normalizedProgress = Number.isFinite(rawProgress) ? Math.min(100, Math.max(0, rawProgress)) : 0;

    if (statusText) {
      setJobStatusText(statusText);
    }

    // Parse file numbers from the message text (e.g., "Starting extraction for file 3/4")
    const fileNumberMatch = statusText.match(/file (\d+)\/(\d+)/i);
    const currentFileNumber = fileNumberMatch ? parseInt(fileNumberMatch[1]) : undefined;
    const totalFiles = fileNumberMatch ? parseInt(fileNumberMatch[2]) : undefined;

    // Global job progress update
    if (!msg.file_name) {
      setJobStage(workerStage);
      const targetProgress = (workerStage === "completed" || workerStage === "failed") ? 100 : normalizedProgress;
      setJobProgress(prev => Math.max(prev, targetProgress));

      // Update all files that are in processing state with the current progress
      if (currentFileNumber && totalFiles) {
        setFiles(prevFiles => prevFiles.map(f => {
          if (f.status === 'processing' || f.status === 'initialization' || f.status === 'extraction') {
            return {
              ...f,
              progress: normalizedProgress,
              currentFileNumber,
              totalFiles,
              stage: workerStage,
              statusMessage: statusText
            };
          }
          return f;
        }));
      }
    } else if (normalizedProgress > 0) {
      // Cap at 99 so the final job-level message can clearly move it to 100
      setJobProgress(prev => Math.max(prev, Math.min(99, normalizedProgress)));
    }

    if (!msg.file_name && (workerStage === "completed" || workerStage === "failed")) {
      const messageTextLower = statusText.toLowerCase();
      const isDuplicateCompletion = messageTextLower.includes("duplicate") || messageTextLower.includes("already exists");
      
      // For duplicates, we'll mark as completed but with a note
      const targetStatus: UploadedFile['status'] = workerStage === "completed" ? "completed" : "failed";
      
      setJobCompleted(true);
      setJobProgress(100); // Ensure progress is 100% for duplicates

      if (isDuplicateCompletion) {
        showToast("Files were already processed previously.", "info");
      }

      setFiles(prevFiles => {
        const allFilesDone = prevFiles.map(f => {
          // For completed jobs
          if (targetStatus === 'completed') {
            if (isDuplicateCompletion) {
              return { 
                ...f, 
                status: 'completed' as const, 
                progress: 100, 
                error: isDuplicateCompletion ? 'File was previously processed' : undefined 
              };
            }
            if (f.status !== 'failed') {
              return { ...f, status: 'completed' as const, progress: 100, error: undefined };
            }
          } else {
            // For failed jobs
            if (f.status === 'queued' || f.status === 'processing' || f.status === 'pending') {
              return { ...f, status: 'failed' as const, progress: 100, error: statusText };
            }
          }
          return f;
        });
        return allFilesDone;
      });

      if (isDuplicateCompletion) {
        setForceComplete(true);
      }
      return;
    }

    if (msg.file_name) {
      let localStatus: UploadedFile['status'];
      let errorMessage: string | undefined = undefined;

      const statusTextLower = statusText.toLowerCase();
      const isDuplicate = statusTextLower.includes('duplicate') || statusTextLower.includes('already exists');

      // Parse file numbers from the message
      const fileNumberMatch = statusText.match(/file (\d+)\/(\d+)/i);
      const currentFileNumber = fileNumberMatch ? parseInt(fileNumberMatch[1]) : undefined;
      const totalFiles = fileNumberMatch ? parseInt(fileNumberMatch[2]) : undefined;

      if (workerStage.includes('failed')) {
        if (isDuplicate) {
          localStatus = 'completed';
          errorMessage = 'File was previously processed';
        } else {
          localStatus = 'failed';
          errorMessage = statusText.replace('File skipped/failed: ', '');
        }
      } else if (workerStage === 'curation_complete' || workerStage === 'processed' || workerStage === 'completed') {
        localStatus = 'completed';
      } else if (workerStage === 'initialization') {
        localStatus = 'initialization';
      } else if (workerStage === 'extraction' || workerStage.includes('extract')) {
        localStatus = 'extraction';
      } else if (workerStage === 'curation_in_progress' || workerStage === 'processing') {
        localStatus = 'processing';
      } else if (workerStage === 'queued') {
        localStatus = 'queued';
      } else {
        localStatus = 'processing';
      }

      // Calculate per-file progress based on stage
      let calculatedProgress = normalizedProgress;
      if (currentFileNumber && totalFiles) {
        // For multi-file processing, calculate progress based on current file number
        const baseProgress = ((currentFileNumber - 1) / totalFiles) * 100;
        const fileProgress = (normalizedProgress / totalFiles);
        calculatedProgress = Math.min(baseProgress + fileProgress, 100);
      }

      const derivedStage = isDuplicate ? 'duplicate' : workerStage;

      setFiles(prevFiles => {
        const incomingName = normalizeFileName(msg.file_name);
        const updated = prevFiles.map(f => {
          const matchesByProfile = msg.profile_id && f.profileId && f.profileId === msg.profile_id;
          const matchesByName = incomingName !== "" && normalizeFileName(f.file.name) === incomingName;

          if (matchesByProfile || matchesByName) {
            const finalProgress = localStatus === 'failed' ? 100 : calculatedProgress;
            return {
              ...f,
              profileId: msg.profile_id || f.profileId,
              status: localStatus,
              progress: finalProgress,
              error: errorMessage || f.error,
              stage: derivedStage,
              currentFileNumber,
              totalFiles,
              statusMessage: isDuplicate ? 'File was previously processed' : (statusText || undefined),
            };
          }
          return f;
        });

        return updated;
      });
    }
  }, [latestMessage]);

  // Reset job-level status when switching tasks
  useEffect(() => {
    if (!taskId) {
      setJobProgress(0);
      setJobStage("");
      setJobStatusText("");
      setJobCompleted(false);
      return;
    }

    setJobProgress(0);
    setJobStage("queued");
    setJobStatusText("Job queued. Awaiting worker start...");
    setJobCompleted(false);
  }, [taskId]);

  // Ensure that once we mark a run as duplicate complete, all files resolve to a terminal state
  useEffect(() => {
    if (!forceComplete) {
      return;
    }

    setFiles(prevFiles => {
      const needsUpdate = prevFiles.some(f => 
        f.status === 'pending' || f.status === 'processing' || f.status === 'queued'
      );
      
      if (!needsUpdate) {
        return prevFiles;
      }

      const updated = prevFiles.map(f => {
        if (f.status === 'pending' || f.status === 'processing' || f.status === 'queued') {
          return {
            ...f,
            status: 'completed' as const,  // Mark as completed for duplicates
            progress: 100,
            error: 'File was previously processed',  // More user-friendly message
            stage: 'duplicate',
            statusMessage: 'File was previously processed'
          };
        }
        return f;
      });
      
      return updated;
    });

    // Ensure job progress shows as complete for duplicates
    setJobProgress(100);
    setJobStatusText('All files were previously processed');
  }, [forceComplete]);

  const handleFileSelect = (selectedFiles: File[]) => {
    // If the job is inactive, prevent selecting files here
    if (job && job.is_active === false) {
      showToast('Cannot add files: this job is inactive. Activate on the Career Page to enable resume uploads.', 'warning');
      return;
    }
    const newFiles: UploadedFile[] = [];
    const duplicates: string[] = [];

    selectedFiles.forEach(selectedFile => {
      if (files.some(f => f.file.name === selectedFile.name)) {
        duplicates.push(selectedFile.name);
      } else {
        newFiles.push({ file: selectedFile, status: 'pending', progress: 0 });
      }
    });

    if (duplicates.length > 0) {
      if (duplicates.length === 1) {
        showToast(`File "${duplicates[0]}" already in the list.`, "info");
      } else {
        showToast(`${duplicates.length} files were already in the list.`, "info");
      }
    }

    if (newFiles.length > 0) {
      setFiles(prevFiles => [...prevFiles, ...newFiles]);
    }
  };

  const removeFile = (fileName: string) => {
    // Only remove if status is pending (i.e., not uploaded yet)
    setFiles(prevFiles => prevFiles.filter(f => !(f.file.name === fileName && f.status === 'pending')));
  };
  
  const resetUploader = () => {
    setFiles([]);
    setTaskId(null);
    setForceComplete(false);
    setJobCompleted(false);
  }

  const handleUpload = useCallback(async () => {
    // Guard: do not allow uploads for inactive jobs
    if (job && job.is_active === false) {
      showToast('Cannot upload resumes for an inactive job. Activate the job on the Career Page first.', 'error');
      return;
    }
    const pendingFiles = files.filter(f => f.status === 'pending').map(f => f.file);
    if (pendingFiles.length === 0) {
      showToast("No new files to upload.", "info");
      return;
    }

    setIsUploading(true);
  setForceComplete(false);
    showToast(`Uploading ${pendingFiles.length} file(s) for "${job.job_title}"...`, 'info');

    const result = await BulkUpload(job.job_id, pendingFiles);

    if (result.success && result.data?.task_id) {
      setTaskId(result.data.task_id);
      const savedFileNames = result.data.saved_files || []; 
      const uploadedFileNames = pendingFiles.map(f => f.name);

      setFiles(prevFiles =>
        prevFiles.map(pf => {
          const wasJustUploaded = uploadedFileNames.includes(pf.file.name) && pf.status === 'pending';
          if (wasJustUploaded && savedFileNames.includes(pf.file.name)) {
            return { ...pf, status: 'queued', error: undefined };
          }
          if (wasJustUploaded) {
             return { ...pf, status: 'failed', progress: 100, error: 'Upload rejected by server (e.g., unsupported format/server issue).' };
          }
          return pf;
        })
      );
      showToast("Upload initiated. Waiting for processing status...", 'success');
    } else {
      setFiles(prevFiles => prevFiles.map(pf => 
        pf.status === 'pending' ? { ...pf, status: 'failed', progress: 100, error: result.error || 'Bulk upload failed.' } : pf
      ));
      showToast(result.error || "Failed to start upload process.", 'error');
    }
    setIsUploading(false);
    }, [files, showToast, job.job_id, job.job_title]);

  // Memoized values to track overall progress and completion
  const { completedCount, failedCount, pendingCount, processingCount, overallProgress, isAllDone, totalFiles } = useMemo(() => {
    const total = files.length;
    if (total === 0) {
      return { completedCount: 0, failedCount: 0, pendingCount: 0, processingCount: 0, overallProgress: 0, isAllDone: false, totalFiles: 0 };
    }
    
    const completed = files.filter(f => f.status === 'completed').length;
    const failed = files.filter(f => f.status === 'failed').length;
    const pending = files.filter(f => f.status === 'pending').length;
    const processing = files.filter(f =>
      f.status === 'queued' ||
      f.status === 'processing' ||
      f.status === 'initialization' ||
      f.status === 'extraction'
    ).length;
    
    const doneCount = completed + failed;
    const progress = total > 0 ? (doneCount / total) * 100 : 0;
    
    // All done if no files are pending or processing
    const allDone = total > 0 && pending === 0 && processing === 0;

    let finalCompleted = completed;
    let finalFailed = failed;
    let finalPending = pending;
    let finalProcessing = processing;
    let finalProgress = progress;
    let finalAllDone = allDone;

    if (forceComplete && total > 0) {
      finalPending = 0;
      finalProcessing = 0;
      finalProgress = 100;
      finalAllDone = true;
      if (finalCompleted + finalFailed === 0) {
        finalFailed = total;
      }
    }

    return {
      completedCount: finalCompleted,
      failedCount: finalFailed,
      pendingCount: finalPending,
      processingCount: finalProcessing,
      overallProgress: finalProgress,
      isAllDone: finalAllDone,
      totalFiles: total
    };
  }, [files, forceComplete]);

  const effectiveProgress = Math.max(overallProgress, jobProgress);
  const processedCount = completedCount + failedCount;
  const estimatedProcessedCount = files.length > 0
    ? Math.min(files.length, Math.max(processedCount, Math.round((effectiveProgress / 100) * files.length)))
    : 0;
  const statusMessage = jobStatusText || `${processingCount} file(s) currently being analyzed. You can continue to add more resumes or monitor the status below.`;
  const stageLabel = jobStage ? jobStage.replace(/_/g, ' ') : '';
  const showSuccessState = totalFiles > 0 && isAllDone && (jobCompleted || forceComplete || effectiveProgress >= 100);
  
  useEffect(() => {
    if (isAllDone && taskId && jobCompleted) { // Only show once per task ID completion
      showToast(`Processing complete: ${completedCount} successful, ${failedCount} failed.`, 'success');
      setTaskId(null); // Clear task ID
      // Notify career page to refresh (cross-tab and same-tab)
      try {
        window.localStorage.setItem('career_jobs_refresh', String(Date.now()));
      } catch {
        // ignore
      }
      try {
        window.dispatchEvent(new CustomEvent('career_jobs_refresh'));
      } catch {
        // ignore
      }
    }
  }, [isAllDone, completedCount, failedCount, showToast, taskId, jobCompleted]);


  return (
    // 💡 Single card layout
    <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200 space-y-6">
      {/* If the job is inactive, show a friendly message and disable upload UI */}
      {job && job.is_active === false ? (
        <div className="flex flex-col items-center justify-center text-center min-h-[200px]">
          <div className="text-yellow-600 font-semibold">This job is currently inactive</div>
          <p className="text-sm text-gray-600 mt-2">Resume uploads are disabled for inactive job posts. Activate the job on the Career Page to enable uploading resumes.</p>
          <div className="mt-4 flex gap-2">
            <Button onClick={onComplete} variant="secondary">Back to Jobs</Button>
          </div>
        </div>
  ) : showSuccessState ? (
          // --- Finished State ---
          <div className="flex flex-col items-center justify-center text-center min-h-[300px]">
              <CheckCircle size={64} className="text-green-500 mb-4" />
              <h3 className="text-xl font-bold text-gray-800">Done Uploaded!</h3> {/* 💡 Simplified completion message */}
              <p className="text-gray-600 mt-2">
                  Processing finished for all {totalFiles} files.<br/>
                  Successful: <strong className="text-green-600">{completedCount}</strong>, Failed: <strong className="text-red-600">{failedCount}</strong>
              </p>
               <Button onClick={resetUploader} variant="outline" className="mt-6">
                  <UploadCloud size={16} className="mr-2" /> Start New Upload
              </Button>
          </div>
      ) : (
        
          <>
              {/* 1. Upload Zone */}
              <ResumeUploadZone onFileSelect={handleFileSelect} />
              
              {/* 2. Background job status */}
              {files.length > 0 && (
                <div className="p-4 rounded-lg bg-gray-50 border border-gray-200">
                    <p className="text-sm font-semibold text-gray-700 mb-2">Background Processing</p>
                    <p className="text-xs text-gray-600">{statusMessage}</p>
                    {stageLabel && (
                      <p className="text-[11px] text-gray-500 mt-1">Stage: {stageLabel}</p>
                    )}
                </div>
              )}

              {/* 3. Detailed per-file status list */}
              {files.length > 0 && (
                <FileStatusList 
                    files={files} 
                    isConnected={isConnected} 
                    onRemoveFile={removeFile} 
                />
              )}
          </>
      )}

      {/* --- Footer Actions --- */}
      <div className="flex flex-col sm:flex-row justify-between items-center pt-4 border-t border-gray-100 gap-4">
        {showSuccessState ? (
              // Footer when done
              <Button onClick={onComplete} variant="secondary" className="w-full sm:w-auto py-2.5">
                  Back to Jobs
              </Button>
          ) : (
              // Footer when uploading/pending
              <>
                  {/* 💡 Left Side: Donut Progress */}
                  <div className="flex items-center gap-3">
                      <CircularProgress percentage={effectiveProgress} />
                      <div>
                          <span className="text-sm font-semibold text-gray-700">Overall Progress</span>
                          <span className="text-xs text-gray-500 block">
                            {estimatedProcessedCount} / {files.length} files processed
                          </span>
                      </div>
                  </div>
                  
                  {/* Right Side: Upload Button */}
                  <Button 
                    onClick={handleUpload} 
                    disabled={pendingCount === 0 || isUploading || processingCount > 0 || (!!taskId && !isAllDone) || (job && job.is_active === false)} 
                    className="w-full sm:w-auto py-2.5"
                    title={job && job.is_active === false ? "This job is inactive - activate to enable uploads" : (pendingCount === 0 ? "Add files to upload" : (processingCount > 0 ? "Processing in progress..." : "Start upload"))}
                  >
                      {isUploading ? <><Loader2 size={16} className="animate-spin mr-2" /> <span>Initiating...</span></> 
                      : (processingCount > 0 ? 'Processing...' : `Start Upload (${pendingCount})`)}
                  </Button>
              </>
          )}
      </div>
    </div>
  );
};

export default BulkUploaderForJob;