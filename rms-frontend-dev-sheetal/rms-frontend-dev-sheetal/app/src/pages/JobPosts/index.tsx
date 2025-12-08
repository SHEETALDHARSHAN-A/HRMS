// src/pages/JobPosts/index.tsx

import { useState, useMemo } from "react";
import Layout from "../../components/layout/Layout";
import { useLocation } from "react-router-dom";
import JobPostsForm from "./JobPostsForm";
import JobPostsList from "./JobPostsList";
import Button from "../../components/common/Button";
import { Plus } from "lucide-react";

type ViewMode = 'list' | 'create' | 'edit'; // Ensure 'edit' is supported

// 💡 DEFINE TAB IDS
type JobTab = 'my_jobs' | 'all_jobs';

export default function JobPostsPage() {
  const location = useLocation();
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [editingJobId, setEditingJobId] = useState<string | undefined>(undefined); 
 
  const activeTab: JobTab = useMemo(() => {
    if (viewMode !== 'list') return 'my_jobs'; // Default to my_jobs when in form view
    if (location.pathname.includes('/jobs/all-jobs')) return 'all_jobs';
    return 'my_jobs'; // Default for /jobs/my-jobs
  }, [location.pathname, viewMode]);

  const handleCreateNew = () => {
    setEditingJobId(undefined); // Clear ID for creation
    setViewMode("create");
  }
  
  const handleEditJob = (jobId: string) => {
    setEditingJobId(jobId);
    setViewMode("edit");
  }

  const handleCancel = () => {
    setEditingJobId(undefined);
    setViewMode("list");
  }

  const bannerButton = (
    <Button
      onClick={handleCreateNew}
      variant="ghost"
      className="rounded-full px-3 py-2 ml-2 flex items-center gap-1 bg-white text-[#0b2447]"
    >
      <Plus size={15} /> Add New Job Post
    </Button>
  );

  const isFormView = viewMode === 'create' || viewMode === 'edit';

  // Update banner title based on the list view
  const listTitle = activeTab === 'my_jobs' ? "My Job Posts" : "All Job Posts";

 

  return (
    <Layout
      bannerTitle={viewMode === 'list' ? "Job Posts Management" : viewMode === 'create' ? "Job Post Creating Form" : "Job Post Editing Form"}
      bannerSubtitle={viewMode === 'list' ? "Manage your job postings and track candidate applications" : "Configure and refine your job post with AI powered insights"}
      searchPlaceholder="Search jobs..."
      bannerActionButton={viewMode === 'list' ? bannerButton : undefined}
      showBackButton={isFormView}
      onBackClick={handleCancel}
    >
      {viewMode === "list" ? (
        <JobPostsList 
          onAddNewJob={handleCreateNew} 
          onEditJob={handleEditJob} // PASSING EDIT HANDLER
          activeTab={activeTab} // 💡 PASS ACTIVE TAB
          key={activeTab} // 💡 Use activeTab as key to force re-render on tab change
        />
      ) : (
        <JobPostsForm 
          onCancel={handleCancel} 
          jobId={editingJobId} 
          key={editingJobId || 'create'}
        />
      )}
    </Layout>
  );
}