import React from 'react';
import { X, MapPin, Clock, DollarSign, Users, Briefcase, Home } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface JobDetailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  job: {
    job_id: string;
    job_title: string;
    job_location: string;
    work_from_home: boolean;
    // 💡 Allow for simple string[] or object[]
    skills_required: Array<{ skill_name: string; skill_level: string } | string>;
    minimum_experience: number;
    maximum_experience: number;
    job_description: string;
    short_description: string;
    salary?: string;
    employment_type?: string;
    department?: string;
    posted_date: string;
  } | null;
}

/**
 * A centered, responsive modal with a scrolling content area and
 * fixed header/footer.
 */
const JobDetailsModal: React.FC<JobDetailsModalProps> = ({ isOpen, onClose, job }) => {
  const navigate = useNavigate();

  if (!isOpen || !job) return null;

  const handleApplyClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('Apply button clicked, navigating to:', `/apply/${job.job_id}`);
    onClose(); // Close the modal first
    navigate(`/apply/${job.job_id}`);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  return (
    // 💡 FIX 1: The Overlay
    // - Use `items-center` to center vertically.
    // - Remove inline styles and `overflow-y-auto`.
    // - Add padding `p-4` or `p-6` for screen gutters.
    <div 
      className="fixed inset-0 bg-black/20 backdrop-blur-sm flex items-center justify-center z-[9999] p-4 sm:p-6"
      onClick={onClose} // Allow closing by clicking overlay
    >
      {/* 💡 FIX 2: The Modal Panel
          - Use `flex flex-col` and `max-h-[90vh]` to constrain the height.
          - Remove all inline styles (maxHeight) and margins (my-4).
          - `w-full` and `max-w-4xl` make it responsive.
      */}
      <div 
        className="bg-white rounded-lg max-w-4xl w-full shadow-2xl flex flex-col max-h-[90vh]"
        onClick={(e) => e.stopPropagation()} // Stop overlay click from closing
      >
        {/* Header (This is now a non-sticky flex item) */}
        <div className="border-b border-gray-200 p-6 flex justify-between items-start rounded-t-lg">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">{job.job_title}</h2>
            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
              <div className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                <span>{job.job_location}</span>
              </div>
              {job.work_from_home && (
                <div className="flex items-center gap-1">
                  <Home className="w-4 h-4" />
                  <span>Work from Home</span>
                </div>
              )}
              <div className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                <span>{job.minimum_experience}-{job.maximum_experience} years</span>
              </div>
              {job.employment_type && (
                <div className="flex items-center gap-1">
                  <Briefcase className="w-4 h-4" />
                  <span>{job.employment_type}</span>
                </div>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="ml-4 p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* 💡 FIX 3: The Content Area
            - This div now wraps all the scrollable content.
            - `overflow-y-auto` makes *this* section scroll,
              while the header and footer remain fixed.
        */}
        <div className="p-6 space-y-6 overflow-y-auto">
          {/* Quick Info Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {job.salary && (
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <DollarSign className="w-5 h-5 text-green-600" />
                  <span className="font-medium text-gray-900">Salary</span>
                </div>
                <p className="text-gray-700">{job.salary}</p>
              </div>
            )}
            
            {job.department && (
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Users className="w-5 h-5 text-blue-600" />
                  <span className="font-medium text-gray-900">Department</span>
                </div>
                <p className="text-gray-700">{job.department}</p>
              </div>
            )}

            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="w-5 h-5 text-orange-600" />
                <span className="font-medium text-gray-900">Posted</span>
              </div>
              <p className="text-gray-700">{formatDate(job.posted_date)}</p>
            </div>
          </div>

          {/* Skills Required */}
          {job.skills_required && job.skills_required.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Skills Required</h3>
              <div className="flex flex-wrap gap-2">
                {job.skills_required.map((skill, index) => {
                  // Handle both string and object skill formats
                  const skillName = typeof skill === 'object' && skill !== null 
                    ? skill.skill_name
                    : String(skill);
                  const skillLevel = typeof skill === 'object' && skill !== null 
                    ? skill.skill_level
                    : '';
                  
                  return (
                    <span
                      key={index}
                      className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 text-blue-800"
                    >
                {skillName}
                      {skillLevel && <span className="ml-1 text-xs text-blue-600">({skillLevel})</span>}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {/* Job Description */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-3">Job Description</h3>
            <div className="prose max-w-none">
              {job.short_description && (
                <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-4">
                  <p className="text-blue-800 font-medium">{job.short_description}</p>
                </div>
              )}
              <div className="text-gray-700 whitespace-pre-wrap leading-relaxed">
                {job.job_description || 'No detailed description available.'}
            </div>
            </div>
          </div>
        </div>

        {/* Footer (This is now a non-sticky flex item) */}
        {/* 💡 FIX 4: Removed sticky and inline style. Added `rounded-b-lg` */}
        <div className="border-t border-gray-200 p-6 flex justify-between items-center rounded-b-lg">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
          >
            Close
          </button>
          <button
            type="button"
            onClick={handleApplyClick}
            className="bg-blue-600 hover:bg-blue-700 text-white px-8 py-2 rounded-lg font-medium transition-colors flex items-center gap-2 cursor-pointer"
          >
            Apply Now
          </button>
        </div>
      </div>
    </div>
  );
};

export default JobDetailsModal;