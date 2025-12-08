
// // src/pages/ControlHub/index.tsx
// import { useState } from "react";
// import Layout from "../../components/layout/Layout";
// import ControlHub from "./ControlHub";

// interface JobPost {
//   job_id: string;
//   job_title: string;
// }

// export default function ControlHubPage() {
//   const [selectedJob, setSelectedJob] = useState<JobPost | null>(null);

//   // This function will be called by the "Back to Jobs" button
//   const handleCompletion = () => {
//     setSelectedJob(null);
//   };

//   const isJobSelected = !!selectedJob;

//   return (
//     <Layout
//       bannerTitle={isJobSelected ? `Bulk Upload for: ${selectedJob.job_title}` : "Control Hub"}
//       bannerSubtitle={isJobSelected ? "Upload multiple resumes for this role" : "Select a job post to begin bulk uploading resumes"}
//       searchPlaceholder="Search in Control Hub..."
//       showBackButton={isJobSelected}
//       onBackClick={handleCompletion} // The back button also uses the same logic
//     >
//       <ControlHub 
//         selectedJob={selectedJob}
//         onJobSelect={setSelectedJob}
//         onUploadComplete={handleCompletion} // Pass the handler down
//       />
//     </Layout>
//   );
// }

import { useState } from "react";
import Layout from "../../components/layout/Layout";
import ControlHub from "./ControlHub";

interface JobPost {
  job_id: string;
  job_title: string;
}

export default function ControlHubPage() {
  const [selectedJob, setSelectedJob] = useState<JobPost | null>(null);
  const [activeTab, setActiveTab] = useState<'bulk-upload' | 'external-sourcing'>('bulk-upload');

  const handleCompletion = () => {
    setSelectedJob(null);
  };

  const isJobSelected = !!selectedJob;
  const showBackButton = isJobSelected && activeTab === 'bulk-upload';

  const bannerTitle = () => {
    if (activeTab === 'external-sourcing') return "External Sourcing";
    if (isJobSelected) return `Bulk Upload for: ${selectedJob.job_title}`;
    return "Control Hub";
  };

  const bannerSubtitle = () => {
    if (activeTab === 'external-sourcing') return "Manage integrations with LinkedIn, Naukri, and more";
    if (isJobSelected) return "Upload multiple resumes for this role";
    return "Select a job post for bulk upload or manage external sourcing";
  };
  
  // Define tabs for the TopBanner
  const bannerTabs = [
      { id: 'bulk-upload', label: 'Bulk Resume Upload' },
      { id: 'external-sourcing', label: 'External Sourcing' }
  ];

  return (
    <Layout
      bannerTitle={bannerTitle()}
      bannerSubtitle={bannerSubtitle()}
      searchPlaceholder="Search in Control Hub..."
      showBackButton={showBackButton}
      onBackClick={handleCompletion}
      bannerTabs={bannerTabs} // Pass tabs to layout
      activeTab={activeTab} // Pass active tab
      onTabChange={(tabId) => setActiveTab(tabId as any)} // Handle tab changes
    >
      <ControlHub 
        selectedJob={selectedJob}
        onJobSelect={setSelectedJob}
        onUploadComplete={handleCompletion}
        activeTab={activeTab}
      />
    </Layout>
  );
}
