// ats-frontend-dev-sheetal/app/src/hooks/useTaskStatus.ts (CRITICAL FIX APPLIED)

import { useEffect, useState, useRef, useCallback } from 'react';

// Define the structure of the status message from your Redis channel
interface TaskStatusMessage {
  task: string; // Use 'task' key from worker output
  job_id: string;
  profile_id: string;
  file_name: string; // <-- New field for file-specific updates
  status: string; // 'Starting job processing', 'Processed Resume_1.pdf', 'Job completed successfully'
  stage: string;
  processing_percentage: number;
}


// Get the base URL from the environment config
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

// Construct the WebSocket base URL (mirror HTTP base, but ws/wss)
const WEBSOCKET_BASE = BACKEND_URL.replace(/^http/, 'ws');

// Helper function to decode JWT payload (for expiration check)
const decodeJwt = (token: string): { exp: number } | null => {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    // Use the global 'atob' to decode Base64
    const payload = JSON.parse(atob(parts[1]));
    return payload;
  } catch {
    return null;
  }
};


export const useTaskStatus = (taskId: string | null) => {
  const [latestMessage, setLatestMessage] = useState<TaskStatusMessage | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const websocketRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (!taskId || websocketRef.current) return;

    const token = localStorage.getItem("authToken");
    if (!token) {
        console.error("WS Error: No auth token found. Cannot connect.");
        setIsConnected(false);
        return;
    }
    
  const decodedToken = decodeJwt(token);
  // Use 60 seconds of buffer for expiration: treat token as expired if it will
  // expire within the next 60 seconds to avoid mid-connection expiry.
  if (decodedToken && decodedToken.exp * 1000 < Date.now() + 60000) {
    console.error("WS Auth: Token is expired or will expire within 60s. Please log in again.");
    setIsConnected(false);
    return;
  }

  // 💡 CRITICAL FIX: Ensure the WS path correctly includes /api/v1 prefix
  const wsPath = `/api/v1/ws/task-status/${taskId}?token=${encodeURIComponent(token)}`;
  const wsUrl = `${WEBSOCKET_BASE}${wsPath}`;

    
    console.log(`WS Attempting to connect to: ${wsUrl}`);
    
    const ws = new WebSocket(wsUrl);
    websocketRef.current = ws;

    ws.onopen = () => {
      console.log(`WS CONNECTED for task: ${taskId}`);
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const messageData = JSON.parse(event.data);
        // The message structure from the worker is now consistent
        setLatestMessage(messageData as TaskStatusMessage); 
      } catch (error) {
        console.error('WS Failed to parse message:', event.data, error);
      }
    };

    ws.onclose = (event) => {
      console.log(`WS DISCONNECTED for task: ${taskId}. Code: ${event.code}, Reason: ${event.reason}`);
      setIsConnected(false);
      websocketRef.current = null;
    };

    ws.onerror = (error) => {
      console.error(`WS ERROR for task ${taskId}:`, error);
      setIsConnected(false);
    };

  }, [taskId]);

  useEffect(() => {
    // Only connect if the taskId changes or if the component mounted and taskId is present
    if (taskId) {
      connect();
    }

    return () => {
      if (websocketRef.current) {
        websocketRef.current.close();
        websocketRef.current = null;
      }
    };
  }, [taskId, connect]);

  return { latestMessage, isConnected };
};