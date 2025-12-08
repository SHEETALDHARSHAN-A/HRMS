// rms-frontend-dev-sheetal/app/src/components/common/JobCard.tsx
import React from 'react';
import { Briefcase, MapPin, Send, Zap, Clock } from 'lucide-react';
import type { PublicJob } from '../../pages/Career/CareerPage'; // We will export this type from CareerPage
import Button from './Button';
import { useNavigate } from 'react-router-dom';

interface JobCardProps {
  job: PublicJob;
  style?: React.CSSProperties; // For animation delay
  className?: string; // For additional CSS classes
  onCardClick?: () => void; // For opening modal
}

/**
 * A modern, redesigned job card for the public career page.
 * Features a clean layout, icon-based metadata, and a "Top Skills" summary.
 */
const JobCard: React.FC<JobCardProps> = ({ job, style, className = "", onCardClick }) => {
  const navigate = useNavigate();
  
  const handleApply = () => {
    navigate(`/apply/${job.job_id}`);
  };

  const handleCardClick = () => {
    if (onCardClick) {
      onCardClick();
    } else {
      // Fallback to navigation if no modal handler provided
      navigate(`/apply/${job.job_id}`);
    }
  };

  // Show the top 3-4 skills prominently
  const topSkills = job.skills.slice(0, 3);
  const remainingSkills = job.skills.length - topSkills.length;

  return (
    <div
      className={`group bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700
                 grid grid-cols-1 lg:grid-cols-[1fr_auto] gap-6 items-start
                 transition-all duration-300 ease-out
                 hover:shadow-md hover:border-blue-200 dark:hover:border-blue-700
                 cursor-pointer relative ${className}`}
      style={style} // Apply animation delay
      onClick={handleCardClick}
    >
      {/* Subtle hover overlay */}
      <div className="absolute inset-0 bg-blue-50/0 dark:bg-blue-900/0 group-hover:bg-blue-50/30 dark:group-hover:bg-blue-900/10 transition-colors duration-300 pointer-events-none rounded-xl" />
      
      {/* Content wrapper */}
  <div className="relative z-10 flex items-start w-full">
        {/* === Main Info Block === */}
        <div className="flex-1 min-w-0">
          {/* Job Title */}
          <div className="flex items-start justify-between mb-3">
            <h3 className="text-xl font-bold text-gray-900 leading-tight group-hover:text-blue-600 transition-colors duration-200" title={job.job_title}>
              {job.job_title}
            </h3>
            {/* Bookmark icon */}
            <button 
              className="p-1 rounded-full text-gray-400 hover:text-yellow-500 hover:bg-yellow-50 transition-all duration-200"
              onClick={(e) => {
                e.stopPropagation();
                // Add bookmark functionality
              }}
            >
              <Zap size={18} />
            </button>
          </div>
          
          {/* Metadata (Location, Experience, Type) */}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-gray-600 mb-4">
            <div className="flex items-center gap-1.5" title="Location">
              <MapPin size={16} className="text-gray-400 group-hover:text-blue-500 transition-colors duration-200" />
              <span className="font-medium">{job.work_from_home ? "Remote" : job.job_location}</span>
            </div>
            <div className="flex items-center gap-1.5" title="Experience">
              <Briefcase size={16} className="text-gray-400 group-hover:text-blue-500 transition-colors duration-200" />
              <span className="font-medium">{job.min_experience}-{job.max_experience} years</span>
            </div>
            <div className="flex items-center gap-1.5" title="Work Type">
              <Clock size={16} className="text-gray-400 group-hover:text-blue-500 transition-colors duration-200" />
              <span className="font-medium">Full-time</span>
            </div>
          </div>
          
          {/* Short Description */}
          <p className="text-sm text-gray-500 line-clamp-3 mb-4 leading-relaxed">
            {job.short_description}
          </p>

        </div>

  {/* === Professional Skills & CTA Block === */}
  <div className="flex-shrink-0 flex flex-col justify-between items-start lg:items-end w-full lg:w-56 space-y-4">
          
          {/* Skills Section */}
          <div className="flex flex-wrap gap-2 lg:justify-end">
            {topSkills.map((skill) => (
              <span 
                key={skill} 
                className="px-3 py-1 text-xs bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full font-medium border border-blue-200 dark:border-blue-700"
              >
                {skill}
              </span>
            ))}
            {remainingSkills > 0 && (
              <span 
                className="px-3 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full font-medium border border-gray-200 dark:border-gray-600"
                title={job.skills.slice(3).join(', ')}
              >
                +{remainingSkills} more
              </span>
            )}
          </div>
          
          {/* Apply Button */}
          <Button
            onClick={(e) => {
              e.stopPropagation();
              handleApply();
            }}
            variant="primary"
            className="w-full lg:w-auto py-2 px-6 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors duration-200"
          >
            <Send size={16} />
            Apply Now
          </Button>
        </div>
      </div>
    </div>
  );
};

export default JobCard;