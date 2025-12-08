// app/src/components/common/ResumeUploadZone.tsx
import { useState } from 'react';
import { FileUp, CheckCircle, UploadCloud } from 'lucide-react';
import FileUpload from './FileUpload'; // This is your existing logic wrapper
import clsx from 'clsx';

interface ResumeUploadZoneProps {
  onFileSelect: (files: File[]) => void;
}

const ResumeUploadZone: React.FC<ResumeUploadZoneProps> = ({ onFileSelect }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [justDropped, setJustDropped] = useState(false);

  const handleFileDrop = (files: File[]) => {
    // We only accept arrays from FileUpload, but logic expects array
    const fileList = Array.isArray(files) ? files : [files];
    
    if (fileList.length > 0) {
      onFileSelect(fileList);
      setJustDropped(true);
      setTimeout(() => setJustDropped(false), 2000); // Reset after 2s
    }
    setIsDragging(false);
  };

  return (
    <div className="relative group">
      {/* Animated Gradient Border - visible on hover/drag */}
      <div className={clsx(
        "absolute -inset-0.5 rounded-2xl bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 opacity-0 transition-all duration-300 blur",
        "group-hover:opacity-60",
        isDragging && "opacity-100 animate-pulse"
      )} />
      
      <FileUpload
        onFileSelect={(files) => handleFileDrop(files as File[])}
        className={clsx(
          "relative w-full min-h-[200px] rounded-xl transition-all duration-300 ease-out",
          isDragging
            ? 'scale-[1.03] shadow-inner'
            : 'shadow-sm'
        )}
        // Pass drag events to FileUpload's wrapper
        onDragOver={() => setIsDragging(true)}
        onDragLeave={() => setIsDragging(false)}
      >
        <div className={clsx(
          "relative w-full h-full min-h-[200px] flex flex-col items-center justify-center p-8 text-center rounded-xl transition-colors duration-300",
          isDragging ? 'bg-blue-50' : 'bg-gray-50'
        )}>
          
          {/* State: Dropped */}
          <div className={clsx(
            "absolute inset-0 flex flex-col items-center justify-center bg-green-50 transition-opacity duration-300 z-20 rounded-xl",
            justDropped ? 'opacity-100' : 'opacity-0'
          )}>
            <CheckCircle size={40} className="text-green-500 mb-3" />
            <p className="text-lg font-semibold text-green-700">
              Files Added!
            </p>
            <p className="text-sm text-green-600">
              Added to the queue
            </p>
          </div>
          
          {/* State: Default / Dragging */}
          <div className={clsx(
            "flex flex-col items-center justify-center transition-opacity duration-300 z-10",
            justDropped ? 'opacity-0' : 'opacity-100'
          )}>
            <div className={clsx(
              "flex items-center justify-center w-16 h-16 rounded-2xl bg-white border border-gray-200 shadow-sm mb-4 transition-all duration-300 transform-gpu",
              isDragging ? 'scale-110' : 'scale-100'
            )}>
              <UploadCloud
                size={32}
                className={clsx(
                  "transition-colors duration-300",
                  isDragging ? 'text-blue-500' : 'text-gray-500'
                )}
              />
            </div>
            
            <p className={clsx(
              "text-lg font-semibold transition-colors duration-300",
              isDragging ? 'text-blue-600' : 'text-gray-700'
            )}>
              {isDragging ? 'Drop files to upload' : 'Drag & Drop files here'}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              or click to browse
            </p>
            <p className="text-xs text-gray-400 mt-4">
              (PDF, DOCX, CSV supported)
            </p>
          </div>
        </div>
      </FileUpload>
    </div>
  );
};

export default ResumeUploadZone;