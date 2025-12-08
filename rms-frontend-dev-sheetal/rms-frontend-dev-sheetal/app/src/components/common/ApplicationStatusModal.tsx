// src/components/common/ApplicationStatusModal.tsx
import React, { useEffect } from 'react';
import { CheckCircle, X } from 'lucide-react';
import Button from './Button';
import ProcessingStatusDisplay from './ProcessingStatusDisplay'; // Import the new status component

interface ApplicationStatusModalProps {
  isOpen: boolean;
  onClose: () => void;
  jobId: string;
  jobTitle: string;
}

const ApplicationStatusModal: React.FC<ApplicationStatusModalProps> = ({
  isOpen,
  onClose,
  jobId,
  jobTitle,
}) => {
  // Prevent body scrolling when the modal is open
  useEffect(() => {
    document.body.style.overflow = isOpen ? 'hidden' : 'auto';
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-start justify-center bg-black bg-opacity-40 backdrop-blur-sm transition-opacity overflow-y-auto" 
      aria-modal="true" 
      role="dialog"
      style={{ paddingTop: '2rem', paddingBottom: '6rem' }}
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 my-4 transform transition-all animate-in zoom-in-95 ease-out duration-300" style={{ maxHeight: 'calc(100vh - 12rem)', overflowY: 'auto' }}>
        
        {/* Header/Close Button */}
        <div className="p-4 flex justify-end">
          <button 
            onClick={onClose} 
            className="p-1 rounded-full text-gray-400 hover:bg-gray-100 transition-colors"
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body Content */}
        <div className="flex flex-col items-center justify-center p-8 pt-0 text-center">
          
          {/* Green Check Mark Icon */}
          <CheckCircle size={80} className="text-green-600 mb-4" />
          
          {/* Main Title */}
          <h3 className="text-2xl font-bold text-gray-900 mb-2">THANK YOU FOR APPLYING!</h3>
          
          {/* Job Title Context */}
          <p className="text-sm font-semibold text-gray-600 mb-4">
            Position: {jobTitle}
          </p>

          {/* Submission Message */}
          <p className="text-gray-700 text-sm max-w-xs mb-6">
            Your application has been successfully submitted. Our Recruitment Team will review your profile and contact you if your qualifications match the role.
          </p>

          {/* Real-time Status Area */}
          <div className="w-full max-w-md my-4">
             <ProcessingStatusDisplay jobId={jobId} />
          </div>

          {/* Close Button */}
          <Button
            onClick={onClose}
            variant="primary"
            className="w-40 py-2 mt-4 bg-gray-500 hover:bg-gray-600 text-white"
          >
            Close
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ApplicationStatusModal;
