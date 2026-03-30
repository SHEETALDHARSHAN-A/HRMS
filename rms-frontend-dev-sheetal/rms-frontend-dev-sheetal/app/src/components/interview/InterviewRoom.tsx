import {
  LiveKitRoom,
  VideoConference,
  ControlBar,
  RoomAudioRenderer,
} from "@livekit/components-react";
import "@livekit/components-styles";
import { Code2, Loader2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import ErrorBoundary from "../common/ErrorBoundary";

interface InterviewRoomProps {
  token: string;
  serverUrl: string;
  interviewToken?: string;
  candidateEmail?: string;
}

export const InterviewRoom: React.FC<InterviewRoomProps> = ({
  token,
  serverUrl,
  interviewToken,
  candidateEmail,
}) => {
  const [isConnected, setIsConnected] = useState(false);
  const navigate = useNavigate();

  const openCodingWorkspace = () => {
    if (!interviewToken || !candidateEmail) return;
    const target = `/interview/coding?token=${encodeURIComponent(interviewToken)}&email=${encodeURIComponent(candidateEmail)}`;
    window.open(target, "_blank", "noopener,noreferrer");
  };

  return (
    <div style={{ height: "100vh", width: "100vw", backgroundColor: "#111", position: "relative" }}>
  {interviewToken && candidateEmail && (
        <button
          type="button"
          onClick={openCodingWorkspace}
          className="absolute right-4 top-4 z-[70] inline-flex items-center gap-2 rounded-md border border-blue-200 bg-white px-3 py-2 text-sm font-medium text-blue-700 shadow-sm hover:bg-blue-50"
        >
          <Code2 className="h-4 w-4" />
          Open Assessment
        </button>
      )}
  <ErrorBoundary>
  <LiveKitRoom
        video={true}
        audio={true}
        token={token}
        serverUrl={serverUrl}
        connectOptions={{ autoSubscribe: true }}
        data-lk-theme="default"
        onConnected={() => setIsConnected(true)}
        onDisconnected={() => {
          // When disconnected (for example via the Leave control), navigate
          // to a friendly thank-you screen.
          try {
            navigate('/interview/thank-you')
          } catch (err) {
            console.warn('Navigation to thank-you failed', err)
          }
        }}
      >
        {/* The VideoConference component handles all participant tiles */}
        <VideoConference />
        
        {/* Custom Controls */}
        <ControlBar 
          controls={{ 
            microphone: true, 
            camera: true, 
            screenShare: true, 
            leave: true,
            chat: false, // Disable chat to avoid ChatToggle/layout-context errors
          }} 
        />
        
        {/* Handles all remote audio tracks */}
        <RoomAudioRenderer />

        {/* Loading overlay */}
        {!isConnected && (
          <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-black bg-opacity-75 text-white">
            <Loader2 className="h-12 w-12 animate-spin mb-4" />
            <p className="text-lg font-semibold">Connecting to interview room...</p>
          </div>
        )}
      </LiveKitRoom>
      </ErrorBoundary>
    </div>
  );
};