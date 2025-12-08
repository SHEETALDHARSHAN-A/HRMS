// src/components/common/SearchModal.tsx

import { Fragment, useState, useEffect } from 'react';
import type { FormEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Dialog, Transition } from '@headlessui/react';
import { Search, X, Clock, TrendingUp, MapPin, Code } from 'lucide-react';

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * This modal now contains a 3-field search (Role, Skills, Location)
 * and navigates to the career page with URL parameters on submit.
 * It has a z-index of 50 to appear above all content.
 */
const SearchModal: React.FC<SearchModalProps> = ({ isOpen, onClose }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Three state variables for the three inputs
  // Initialized from the URL params to "remember" the last search
  const [role, setRole] = useState(searchParams.get('role') || '');
  const [skills, setSkills] = useState(searchParams.get('skills') || '');
  const [locations, setLocations] = useState(searchParams.get('locations') || '');
  
  // Recent searches and suggestions
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(true);

  // Popular suggestions
  const popularRoles = ['Full Stack Developer', 'Frontend Engineer', 'Backend Developer', 'DevOps Engineer', 'Data Scientist'];
  const popularSkills = ['React', 'Python', 'Node.js', 'TypeScript', 'AWS', 'Docker', 'PostgreSQL'];
  const popularLocations = ['Remote', 'Mumbai', 'Bangalore', 'Chennai', 'Delhi', 'Hyderabad'];

  // This ensures that if the URL changes, the modal state updates
  useEffect(() => {
    if (isOpen) {
      setRole(searchParams.get('role') || '');
      setSkills(searchParams.get('skills') || '');
      setLocations(searchParams.get('locations') || '');
      
      // Load recent searches from localStorage
      const saved = localStorage.getItem('recentJobSearches');
      if (saved) {
        setRecentSearches(JSON.parse(saved));
      }
    }
  }, [isOpen, searchParams]);

  /**
   * Handles the form submission.
   * Creates a new URL search query with the three fields and navigates.
   */
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    
    const params = new URLSearchParams();
    
    // Only add parameters if they have a value
    if (role.trim()) {
      params.set("role", role.trim());
    }
    if (skills.trim()) {
      params.set("skills", skills.trim());
    }
    if (locations.trim()) {
      params.set("locations", locations.trim());
    }

    // Save to recent searches
    if (role.trim() || skills.trim() || locations.trim()) {
      const searchQuery = `${role.trim()} ${skills.trim()} ${locations.trim()}`.trim();
      const newRecentSearches = [searchQuery, ...recentSearches.filter(s => s !== searchQuery)].slice(0, 5);
      setRecentSearches(newRecentSearches);
      localStorage.setItem('recentJobSearches', JSON.stringify(newRecentSearches));
    }

    // Navigate to the career page with the new search parameters
    navigate({
      pathname: '/career-page',
      search: params.toString()
    });
    
    onClose(); // Close the modal
  };

  /**
   * Clears all inputs and the URL search params.
   */
  const handleClear = () => {
    setRole('');
    setSkills('');
    setLocations('');
    // Navigate to the career page with no search parameters
    navigate({
      pathname: '/career-page',
      search: ''
    });
    onClose(); // Close the modal
  };

  return (
    <Transition show={isOpen} as={Fragment}>
      {/* This z-50 is the highest layer, ensuring it's on top */}
      <Dialog as="div" className="fixed inset-0 z-50" onClose={onClose}>
        
        {/* Backdrop */}
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-900/60 backdrop-blur-sm" aria-hidden="true" />
        </Transition.Child>

        {/* Modal Panel */}
        <div className="fixed inset-0 flex items-start justify-center overflow-y-auto" style={{ paddingTop: '2rem', paddingBottom: '6rem' }}>
          <Transition.Child
            as={Fragment}
            enter="ease-out duration-300"
            enterFrom="opacity-0 scale-95 -translate-y-10"
            enterTo="opacity-100 scale-100 translate-y-0"
            leave="ease-in duration-200"
            leaveFrom="opacity-100 scale-100 translate-y-0"
            leaveTo="opacity-0 scale-95 -translate-y-10"
          >
            <Dialog.Panel as="form" onSubmit={handleSubmit} className="relative w-full max-w-2xl bg-white rounded-xl shadow-2xl mx-4 my-4" style={{ maxHeight: 'calc(100vh - 12rem)', overflowY: 'auto' }}>              {/* Header */}
              <div className="px-6 py-4 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">Find Your Perfect Role</h2>
                    <p className="text-sm text-gray-500">Search by role, skills, or location</p>
                  </div>
                  <button
                    type="button"
                    onClick={onClose}
                    className="rounded-md p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                  >
                    <X size={20} />
                  </button>
                </div>
              </div>

              {/* --- REFACTORED: 3-Input Form --- */}
              <div className="p-6 space-y-4">
                {/* 1. Role Input */}
                <div>
                  <label 
                    htmlFor="role-search"
                    className="block text-sm font-medium leading-6 text-gray-900"
                  >
                    Role / Title
                  </label>
                  <input
                    type="text"
                    id="role-search"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    placeholder="e.g., Software Engineer"
                    className="mt-2 w-full rounded-md border-0 bg-white py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-[var(--color-primary-500)] sm:text-sm sm:leading-6"
                  />
                </div>

                {/* 2. Skills Input */}
                <div>
                  <label 
                    htmlFor="skills-search"
                    className="block text-sm font-medium leading-6 text-gray-900"
                  >
                    Skills
                  </label>
                  <input
                    type="text"
                    id="skills-search"
                    value={skills}
                    onChange={(e) => setSkills(e.target.value)}
                    placeholder="e.g., React, Python, ..."
                    className="mt-2 w-full rounded-md border-0 bg-white py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-[var(--color-primary-500)] sm:text-sm sm:leading-6"
                  />
                  <p className="mt-1 text-xs text-gray-500">Separate multiple skills with a comma.</p>
                </div>
                
                {/* 3. Location Input */}
                <div>
                  <label 
                    htmlFor="locations-search"
                    className="block text-sm font-medium leading-6 text-gray-900"
                  >
                    Location
                  </label>
                  <input
                    type="text"
                    id="locations-search"
                    value={locations}
                    onChange={(e) => setLocations(e.target.value)}
                    placeholder="e.g., London, Remote, ..."
                    className="mt-2 w-full rounded-md border-0 bg-white py-2 px-3 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-[var(--color-primary-500)] sm:text-sm sm:leading-6"
                  />
                  <p className="mt-1 text-xs text-gray-500">Separate multiple locations with a comma.</p>
                </div>
              </div>

              {/* Suggestions Section */}
              {showSuggestions && (
                <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
                  {/* Recent Searches */}
                  {recentSearches.length > 0 && (
                    <div className="mb-6">
                      <div className="flex items-center gap-2 mb-3">
                        <Clock size={16} className="text-gray-500" />
                        <h3 className="text-sm font-semibold text-gray-700">Recent Searches</h3>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {recentSearches.map((search, index) => (
                          <button
                            key={index}
                            type="button"
                            onClick={() => {
                              const parts = search.split(' ');
                              setRole(parts[0] || '');
                              setSkills(parts.slice(1).join(' ') || '');
                            }}
                            className="inline-flex items-center px-3 py-1 rounded-full text-xs bg-white text-gray-700 border border-gray-200 hover:bg-gray-100"
                          >
                            {search}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Popular Suggestions */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Popular Roles */}
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <TrendingUp size={14} className="text-blue-500" />
                        <h4 className="text-xs font-semibold text-gray-700">Popular Roles</h4>
                      </div>
                      <div className="space-y-1">
                        {popularRoles.slice(0, 4).map((roleOption) => (
                          <button
                            key={roleOption}
                            type="button"
                            onClick={() => setRole(roleOption)}
                            className="block w-full text-left px-2 py-1 text-xs text-gray-600 hover:text-blue-600 hover:bg-white rounded"
                          >
                            {roleOption}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Popular Skills */}
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <Code size={14} className="text-green-500" />
                        <h4 className="text-xs font-semibold text-gray-700">Popular Skills</h4>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {popularSkills.slice(0, 6).map((skill) => (
                          <button
                            key={skill}
                            type="button"
                            onClick={() => setSkills(prev => prev ? `${prev}, ${skill}` : skill)}
                            className="inline-block px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200"
                          >
                            {skill}
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Popular Locations */}
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <MapPin size={14} className="text-purple-500" />
                        <h4 className="text-xs font-semibold text-gray-700">Popular Locations</h4>
                      </div>
                      <div className="space-y-1">
                        {popularLocations.slice(0, 4).map((location) => (
                          <button
                            key={location}
                            type="button"
                            onClick={() => setLocations(location)}
                            className="block w-full text-left px-2 py-1 text-xs text-gray-600 hover:text-purple-600 hover:bg-white rounded"
                          >
                            {location}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-gray-300">
                    <button
                      type="button"
                      onClick={() => setShowSuggestions(false)}
                      className="text-xs text-gray-500 hover:text-gray-700"
                    >
                      Hide suggestions
                    </button>
                  </div>
                </div>
              )}

              {/* Form Actions (Search / Clear) */}
              <div className="px-6 py-4 bg-gray-50 flex justify-end items-center gap-3">
                {/* Show "Clear" button only if there is text */}
                {(role || skills || locations) && (
                  <button
                    type="button"
                    onClick={handleClear}
                    className="inline-flex items-center justify-center gap-x-2 rounded-md bg-white px-3.5 py-2.5 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
                  >
                    <X className="h-5 w-5" />
                    Clear
                  </button>
                )}
                <button
                  type="submit"
                  className="inline-flex items-center justify-center gap-x-2 rounded-md bg-[var(--color-primary-500)] px-3.5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-[var(--color-primary-600)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-500)]"
                >
                  <Search className="h-5 w-5" />
                  Search
                </button>
              </div>
            </Dialog.Panel>
          </Transition.Child>
        </div>
      </Dialog>
    </Transition>
  );
};

export default SearchModal;