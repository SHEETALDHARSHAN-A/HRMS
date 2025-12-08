// src/components/common/ProcessingStatusDisplay.tsx (CRITICAL FIX APPLIED)
import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Loader2,AlertTriangle, CheckCircle, Clock } from 'lucide-react';

interface ProcessingStatusDisplayProps {
  jobId: string;
}

// IMPORTANT: Use consistent WebSocket URL pattern that matches useTaskStatus.ts
// Base URL from environment 
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000"; 
// 💡 FIX 1: Construct the base WebSocket URL correctly (ws://host:port)
const WEBSOCKET_BASE_URL = BACKEND_URL.replace(/^http/, 'ws');

// Define expected message structure from the Redis Publisher (Worker)
interface StatusMessage {
  task?: string;             // Task ID from worker
  job_id?: string;           // Job ID from worker
  profile_id?: string;       // Profile ID for the resume
  file_name?: string;        // File name being processed
  status?: string;            // Status message (e.g., " Starting job processing\, \Job completed successfully\)
 message?: string; // New field for human-readable message            // Status message (e.g., "Starting job processing", "Job completed successfully")
  stage?: string;            // Processing stage
  processing_percentage?: number; // Progress percentage
  updated_at?: string;       // ISO timestamp
}

// Force the component to refresh after a fixed interval, to help with debugging issues where a websocket message
// might not be triggering a render correctly. During normal operation this should be removed.
const USE_REFRESH_TIMER = true; // Set to false to remove the timer-based refresh

const ProcessingStatusDisplay: React.FC<ProcessingStatusDisplayProps> = ({ jobId }) => {
  const [connectionMessage, setConnectionMessage] = useState("Connecting...");
  const [latestMessage, setLatestMessage] = useState<StatusMessage | null>(null);
  const [isWsOnline, setIsWsOnline] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const [lastRefreshTime, setLastRefreshTime] = useState<number>(Date.now());
  // Local animated progress so bar fills smoothly to the worker-reported percent
  const [localProgress, setLocalProgress] = useState<number>(0);
  // When true, UI will show the final completed state (green) — set after bar hits 100%
  const [showComplete, setShowComplete] = useState<boolean>(false);
  const progressAnimationRef = useRef<number | null>(null);  // 💡 FIX: Destructure the latest status message for clean use in the JSX
  const { status, message, processing_percentage, stage } = latestMessage || { 
    status: 'QUEUED', 
    message: 'Waiting for worker...',
    stage: 'queued',
    processing_percentage: 0 
  };
  
  // Prefer message field first (from worker's publish_progress), then status, then connection state
  const currentMessageText = message || status || connectionMessage;


  const getStatusClasses = (statusValue: string) => {
    if (statusValue.toLowerCase().includes('queued') || statusValue.toLowerCase().includes('initialization')) return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    if (statusValue.toLowerCase().includes('processing')) return 'bg-blue-100 text-blue-800 border-blue-300';
    if (statusValue.toLowerCase().includes('complet') || statusValue.toLowerCase().includes('final status')) return 'bg-green-100 text-green-800 border-green-300';
    if (statusValue.toLowerCase().includes('fail') || statusValue.toLowerCase().includes('error')) return 'bg-red-100 text-red-800 border-red-300';
    return 'bg-gray-100 text-gray-600 border-gray-300';
  };

  const getIcon = (statusValue: string) => {
    if (statusValue.toLowerCase().includes('queued') || statusValue.toLowerCase().includes('initialization')) return <Clock size={18} />;
    if (statusValue.toLowerCase().includes('processing')) return <Loader2 size={18} className="animate-spin" />;
    if (statusValue.toLowerCase().includes('complet') || statusValue.toLowerCase().includes('final status')) return <CheckCircle size={18} />;
    if (statusValue.toLowerCase().includes('fail') || statusValue.toLowerCase().includes('error')) return <AlertTriangle size={18} />;
    return null;
  }

  const connectWebSocket = useCallback(() => {
    // CRITICAL: Close any existing connection before trying to establish a new one
    if (wsRef.current) {
        wsRef.current.close(1000, "Initiating Reconnect");
        wsRef.current = null;
    }

    const token = localStorage.getItem('authToken');
    if (!token) {
      setConnectionMessage('No auth token available. Real-time status disabled.');
      setIsWsOnline(false);
      return;
    }
    
    const wsPath = `/api/v1/ws/task-status/${jobId}?token=${encodeURIComponent(token)}`;
    const wsUrl = `${WEBSOCKET_BASE_URL}${wsPath}`;

    console.log(`ProcessingStatusDisplay: Attempting to connect to WebSocket: ${wsUrl}`);
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsWsOnline(true);
      setConnectionMessage("Connected. Waiting for file processing status...");
      console.log("WebSocket connection established.");
    };

    ws.onmessage = (event) => {
      try {
        // Always log every incoming message with task/job_id details
        const rawData = event.data;
        console.log(`[WS][${new Date().toLocaleTimeString()}] RAW MSG:`, rawData);
        
        const data = JSON.parse(event.data);
        const message: StatusMessage = data as StatusMessage;
        console.log(`[WS] Message task=${message.task}, job_id=${message.job_id}, stage=${message.stage}, progress=${message.processing_percentage}`);
        
        // Try to match messages by task id (task), job_id, or id in the message
        const matchesJob = (message.task && message.task === jobId) || (message.job_id && message.job_id === jobId);
        if (matchesJob) {
          setLatestMessage(message);
          console.log(`[WS] ✓ MATCHED jobId=${jobId}:`, message);
          // Force state refresh as a last resort
          setLastRefreshTime(Date.now());
        } else {
          console.log(`[WS] ✗ NO MATCH (component jobId=${jobId}, but message has task=${message.task}, job_id=${message.job_id})`);
        }
      } catch (e) {
        console.error("Error parsing WebSocket message:", e);
      }
    };

    ws.onclose = (event) => {
      setIsWsOnline(false);
      const reason = event?.reason || 'Connection closed';
      const wasClean = (event as any)?.wasClean !== undefined ? (event as any).wasClean : 'unknown';
      console.warn(`ProcessingStatusDisplay: WebSocket closed. code=${event.code}, wasClean=${wasClean}, reason=${reason}`);
      setConnectionMessage(`Disconnected: ${reason}`);

      setTimeout(() => {
        console.log('ProcessingStatusDisplay: Attempting one reconnect after close...');
        // Only try reconnect if component still mounted and no active ws
        if (!wsRef.current) connectWebSocket();
      }, 1200);
    };

    ws.onerror = (event) => {
      console.error('ProcessingStatusDisplay: WebSocket encountered error event:', event);
      setConnectionMessage('Connection failed. Status monitor offline. Check browser console.');
      setIsWsOnline(false);
    }
  }, [jobId]);

  useEffect(() => {
    connectWebSocket();
    
    // Set up periodic refresh if enabled (DEBUGGING ONLY)
    let refreshTimer: number | null = null;
    if (USE_REFRESH_TIMER) {
      refreshTimer = window.setInterval(() => {
        setLastRefreshTime(Date.now());
      }, 3000);
    }
    
    return () => {
      // Clean up the WebSocket connection on unmount
      if (wsRef.current) wsRef.current.close(1000, "Component Unmounted");
      if (refreshTimer) window.clearInterval(refreshTimer);
    };
  }, [connectWebSocket, jobId]);  // Determine if the job is truly finished (based on the final worker message: "Job completed successfully")
  // The worker indicates completion (candidate) when stage==='completed' or progress>=100
  const completionCandidate = (
    stage === 'completed' ||
    (message && (
      message.toLowerCase().includes('completed') || 
      message.toLowerCase().includes('duplicates') ||
      message.toLowerCase().includes('final status')
    )) ||
    (status && (
      status.toLowerCase().includes('completed') || 
      status.toLowerCase().includes('duplicates') ||
      status.toLowerCase().includes('final status')
    )) ||
    (typeof processing_percentage === 'number' && processing_percentage >= 100)
  );

  // Final display decision: showComplete is set after the progress bar animation reaches 100%
  const isComplete = showComplete || (completionCandidate && localProgress >= 100);
  
  // Determine the primary status message for display
  const primaryStatus = isComplete ? "Processing Complete" : "Real-time File Status";

  // Use processing_percentage directly from the worker's message, defaulting to 0
  const progress = processing_percentage !== undefined ? processing_percentage : 0;

  // Animate the displayed (local) progress towards the incoming progress value
  useEffect(() => {
    // Reset completion when a new non-final progress appears
    if (progress < 100) {
      setShowComplete(false);
    }

    // Clear any existing animation
    if (progressAnimationRef.current) {
      window.clearInterval(progressAnimationRef.current);
      progressAnimationRef.current = null;
    }

    // Smoothly increment localProgress towards the target 'progress'
    const stepMs = 30; // ms per step
    progressAnimationRef.current = window.setInterval(() => {
      setLocalProgress((cur) => {
        const delta = Math.max(1, Math.round((progress - cur) * 0.25));
        const next = Math.min(100, cur + Math.max(1, delta));
        // If we've reached or passed target, stop interval
        if (next >= progress) {
          if (progressAnimationRef.current) {
            window.clearInterval(progressAnimationRef.current);
            progressAnimationRef.current = null;
          }
        }
        return next;
      });
    }, stepMs);

    return () => {
      if (progressAnimationRef.current) {
        window.clearInterval(progressAnimationRef.current);
        progressAnimationRef.current = null;
      }
    };
  }, [progress]);

  // When localProgress reaches 100, give a short pause then show the completed state
  useEffect(() => {
    if (localProgress >= 100) {
      const t = window.setTimeout(() => {
        setShowComplete(true);
      }, 550); // pause so the user sees the bar reach 100%
      return () => clearTimeout(t);
    }
    return;
  }, [localProgress]);
  
  // --- Conditional Rendering Logic ---

  // Display initial connection status
  if (!isWsOnline && !isComplete) {
      return (
        <div className="w-full p-3 rounded-lg border text-sm font-medium bg-red-50 border-red-300 text-red-700 flex items-center gap-2">
            <AlertTriangle size={16} />
            <span>{currentMessageText} (WS required for real-time file status).</span>
        </div>
      );
  }

  // This block handles the Connected state, the Initial message state, and the Finalized state
  return (
    <div 
        // The status variable here is the worker's status message, e.g., "Starting job processing"
        className={`w-full p-3 rounded-lg border shadow-sm text-sm font-medium transition-colors duration-300 ${getStatusClasses(currentMessageText)}`}
    >
        <div className="flex items-center gap-2 justify-between">
            <div className="flex items-center gap-2">
                {getIcon(currentMessageText)}
                <span className="font-bold">{primaryStatus}</span>
            </div>      {!isComplete && (
        <span className="font-semibold text-xs">{Math.min(100, Math.round(localProgress))}%</span>
      )}
            
      {isComplete && (
        <span className="font-semibold text-xs">Final Score Ready</span>
      )}
        </div>
        
        <p className="text-xs mt-1">{currentMessageText}</p>

        {/* DEBUG INFO: Visible helper to diagnose ID matching issues */}
        <div className="mt-2 text-xs text-gray-500 bg-gray-50 p-2 rounded">
          <div><strong>Debug:</strong> component id = <code>{jobId}</code></div>
          <div>latest task id = <code>{latestMessage?.task || '—'}</code></div>
          <div>latest job id = <code>{latestMessage?.job_id || '—'}</code></div>
          <div className="mt-1">raw message: <code>{JSON.stringify(latestMessage || {}, null, 2)}</code></div>
          <div className="mt-1">ws connected: <code>{isWsOnline ? '✅ yes' : '❌ no'}</code></div>
          <div className="mt-1">is complete: <code>{isComplete ? '✅ yes' : '❌ no'}</code></div>
          <div className="mt-1">completion candidate: <code>{completionCandidate ? '✅ yes' : '❌ no'}</code></div>
          <div className="mt-1">local progress: <code>{localProgress}%</code></div>
          <div className="mt-1">show complete: <code>{showComplete ? '✅ yes' : '❌ no'}</code></div>
          <div className="mt-1">last refresh: <code>{new Date(lastRefreshTime).toLocaleTimeString()}</code></div>
        </div>

        {!isComplete && (
            <div className="w-full bg-gray-300 rounded-full h-1 mt-2">
              <div 
                className={`h-1 rounded-full bg-blue-600 transition-all duration-300`} 
                style={{ width: `${Math.min(100, localProgress)}%` }}
              ></div>
            </div>
        )}
    </div>
  );
};

export default ProcessingStatusDisplay;
