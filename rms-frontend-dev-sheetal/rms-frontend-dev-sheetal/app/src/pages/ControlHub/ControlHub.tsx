// // src/pages/ControlHub/ControlHub.tsx
// import {useState} from 'react';
// import JobListForHub from '../../components/common/JobListForHub';
// import BulkUploaderForJob from '../../components/common/BulkUploaderForJob';
// import ExternalSourcing from './ExternalSourcing'; // New import


// interface JobPost {
//   job_id: string;
//   job_title: string;
// }

// interface ControlHubProps {
//   selectedJob: JobPost | null;
//   onJobSelect: (job: JobPost) => void;
//   onUploadComplete: () => void;
//   activeTab: 'bulk-upload' | 'external-sourcing';
// }

// const ControlHub: React.FC<ControlHubProps> = ({ selectedJob, onJobSelect, onUploadComplete, activeTab }) => {
//  if (activeTab === 'external-sourcing') {
//     return <ExternalSourcing />;
//   }

//   // Bulk Upload Flow
//   if (selectedJob) {
//     return <BulkUploaderForJob job={selectedJob} onComplete={onUploadComplete} />;
//   }
  
//   return <JobListForHub onJobSelect={onJobSelect} />;
// };

// export default ControlHub;


// src/pages/ControlHub/ControlHub.tsx
import JobListForHub from '../../components/common/JobListForHub';
import BulkUploaderForJob from '../../components/common/BulkUploaderForJob';
import ExternalSourcing from './ExternalSourcing'; // New import

interface JobPost {
  job_id: string;
  job_title: string;
}

interface ControlHubProps {
  selectedJob: JobPost | null;
  onJobSelect: (job: JobPost) => void;
  onUploadComplete: () => void;
  activeTab: 'bulk-upload' | 'external-sourcing';
}

const ControlHub: React.FC<ControlHubProps> = ({ selectedJob, onJobSelect, onUploadComplete, activeTab }) => {
  
  if (activeTab === 'external-sourcing') {
    return <ExternalSourcing />;
  }

  // Bulk Upload Flow
  if (selectedJob) {
    return <BulkUploaderForJob job={selectedJob} onComplete={onUploadComplete} />;
  }
  
  return <JobListForHub onJobSelect={onJobSelect} />;
};

export default ControlHub;
