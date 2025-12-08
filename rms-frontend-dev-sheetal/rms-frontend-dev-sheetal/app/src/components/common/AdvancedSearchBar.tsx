// src/components/common/AdvancedSearchBar.tsx

import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search, Briefcase, MapPin, Code, X, ChevronDown } from 'lucide-react';
import { getSearchSuggestions } from '../../api/jobApi';
import type { SearchSuggestions } from '../../api/jobApi';

interface AdvancedSearchBarProps {
  onSearchSubmit?: (params: { role: string; location: string; skills: string }) => void;
  onCollapse?: () => void;
  className?: string;
}

const AdvancedSearchBar: React.FC<AdvancedSearchBarProps> = ({ 
  onSearchSubmit,
  onCollapse,
  className = ""
}) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  // Search field states
  const [role, setRole] = useState(searchParams.get('role') || '');
  const [location, setLocation] = useState(searchParams.get('locations') || '');
  const [skills, setSkills] = useState(searchParams.get('skills') || '');
  
  // Dropdown states
  const [showRoleSuggestions, setShowRoleSuggestions] = useState(false);
  const [showLocationSuggestions, setShowLocationSuggestions] = useState(false);
  const [showSkillsSuggestions, setShowSkillsSuggestions] = useState(false);
  
  // Keyboard navigation states
  const [selectedRoleIndex, setSelectedRoleIndex] = useState(-1);
  const [selectedLocationIndex, setSelectedLocationIndex] = useState(-1);
  const [selectedSkillsIndex, setSelectedSkillsIndex] = useState(-1);
  
  // Suggestions from API
  const [suggestions, setSuggestions] = useState<SearchSuggestions | null>(null);
  const [recentSearches, setRecentSearches] = useState<string[]>([]);
  
  // Selected items as arrays for chip display (except roles which use text)
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [selectedLocations, setSelectedLocations] = useState<string[]>([]);
  
  // Refs for dropdown positioning
  const roleRef = useRef<HTMLDivElement>(null);
  const locationRef = useRef<HTMLDivElement>(null);
  const skillsRef = useRef<HTMLDivElement>(null);
  // Styles for portal dropdown positioning
  const [dropdownStyle, setDropdownStyle] = useState<React.CSSProperties | null>(null);
  const [activeDropdown, setActiveDropdown] = useState<'role' | 'location' | 'skills' | null>(null);
  
  // Load suggestions from backend
  useEffect(() => {
    const loadSuggestions = async () => {
      try {
        const result = await getSearchSuggestions();
        if (result.success) {
          setSuggestions(result.data);
        }
      } catch (error) {
        console.error('Failed to load search suggestions:', error);
      }
    };
    
    loadSuggestions();
    
    // Load recent searches from localStorage
    const saved = localStorage.getItem('recentJobSearches');
    if (saved) {
      try {
        setRecentSearches(JSON.parse(saved));
      } catch (e) {
        console.error('Failed to parse recent searches:', e);
      }
    }
    
    // Initialize selected arrays from string values (role stays as text)
    if (skills) {
      setSelectedSkills(skills.split(',').map(s => s.trim()).filter(Boolean));
      setSkills(''); // Clear text input after loading into chips
    }
    if (location) {
      setSelectedLocations(location.split(',').map(s => s.trim()).filter(Boolean));
      setLocation(''); // Clear text input after loading into chips
    }
  }, []);

  // Don't update string values when arrays change - keep inputs clear for chip-only display
  // This prevents showing both chips and text at the same time
  
  // Handle keyboard navigation
  const handleKeyDown = (
    e: React.KeyboardEvent, 
    type: 'role' | 'location' | 'skills',
    suggestions: string[],
    selectedIndex: number,
    setSelectedIndex: (index: number) => void
  ) => {
    if (!suggestions.length) return;
    
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(selectedIndex < suggestions.length - 1 ? selectedIndex + 1 : 0);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(selectedIndex > 0 ? selectedIndex - 1 : suggestions.length - 1);
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
          handleSuggestionClick(type, suggestions[selectedIndex]);
        }
        break;
      case 'Escape':
        if (type === 'role') setShowRoleSuggestions(false);
        if (type === 'location') setShowLocationSuggestions(false);
        if (type === 'skills') setShowSkillsSuggestions(false);
        setSelectedIndex(-1);
        break;
    }
  };

  // Handle input changes with live suggestions
  const handleRoleChange = (value: string) => {
    setRole(value);
    setSelectedRoleIndex(-1); // Reset selection when typing
    // Show suggestions when typing
    if (value.length > 0) {
      setShowRoleSuggestions(true);
    } else {
      setShowRoleSuggestions(false);
    }
  };

  const handleLocationChange = (value: string) => {
    setLocation(value);
    setSelectedLocationIndex(-1); // Reset selection when typing
    // Show suggestions when typing
    if (value.length > 0) {
      setShowLocationSuggestions(true);
    } else {
      setShowLocationSuggestions(false);
    }
  };

  const handleSkillsChange = (value: string) => {
    setSkills(value);
    setSelectedSkillsIndex(-1); // Reset selection when typing
    // Show suggestions when typing
    if (value.length > 0) {
      setShowSkillsSuggestions(true);
    } else {
      setShowSkillsSuggestions(false);
    }
  };

  // Handle form submission - use text inputs and chips
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Build search terms - use role text input directly, chips for others
    const roleTerms = role.trim();
    const skillTerms = selectedSkills.join(', ');
    const locationTerms = selectedLocations.join(', ');
    
    // Save to recent searches if any field has content
    if (roleTerms || skillTerms || locationTerms) {
      const searchQuery = `${roleTerms} | ${skillTerms} | ${locationTerms}`.replace(/\|\s*\|/g, '|').replace(/^\||\|$/g, '');
      const newRecentSearches = [searchQuery, ...recentSearches.filter(s => s !== searchQuery)].slice(0, 5);
      setRecentSearches(newRecentSearches);
      localStorage.setItem('recentJobSearches', JSON.stringify(newRecentSearches));
    }
    
    if (onSearchSubmit) {
      onSearchSubmit({ role: roleTerms, location: locationTerms, skills: skillTerms });
    } else {
      // Navigate to career page with search params
      const params = new URLSearchParams();
      if (roleTerms) params.set('role', roleTerms);
      if (locationTerms) params.set('locations', locationTerms);
      if (skillTerms) params.set('skills', skillTerms);
      
      navigate({
        pathname: '/career-page',
        search: params.toString()
      });
    }
    
    // Close all dropdowns
    setShowRoleSuggestions(false);
    setShowLocationSuggestions(false);
    setShowSkillsSuggestions(false);
  };
  
  // Handle suggestion clicks - set text for role, chips for others
  const handleSuggestionClick = (type: 'role' | 'location' | 'skills', value: string) => {
    if (type === 'role') {
      setRole(value); // Set the text input directly
      setShowRoleSuggestions(false);
      setSelectedRoleIndex(-1);
    } else if (type === 'location') {
      if (!selectedLocations.some(l => l.toLowerCase() === value.toLowerCase())) {
        setSelectedLocations(prev => [...prev, value]);
      }
      setLocation(''); // Clear input after selection
      setShowLocationSuggestions(false);
      setSelectedLocationIndex(-1);
    } else if (type === 'skills') {
      if (!selectedSkills.some(s => s.toLowerCase() === value.toLowerCase())) {
        setSelectedSkills(prev => [...prev, value]);
      }
      setSkills(''); // Clear input after selection
      setShowSkillsSuggestions(false);
      setSelectedSkillsIndex(-1);
    }
    setActiveDropdown(null);
  };
  
  // Clear individual sections  
  const clearSkills = () => {
    setSelectedSkills([]);
    setSkills('');
    setShowSkillsSuggestions(false);
  };

  const clearLocations = () => {
    setSelectedLocations([]);
    setLocation('');
    setShowLocationSuggestions(false);
  };

  // Remove individual chips
  const removeSkill = (skillToRemove: string) => {
    setSelectedSkills(prev => prev.filter(s => s !== skillToRemove));
  };

  const removeLocation = (locationToRemove: string) => {
    setSelectedLocations(prev => prev.filter(l => l !== locationToRemove));
  };
  
  // Filter suggestions based on input - simplified for text input
  const getFilteredRoleSuggestions = () => {
    if (!suggestions?.job_titles) return [];
    if (!role) return suggestions.job_titles.slice(0, 8); // Show top 8 suggestions when empty
    return suggestions.job_titles.filter(suggestion => 
      suggestion.toLowerCase().includes(role.toLowerCase())
    ).slice(0, 8);
  };

  const getFilteredLocationSuggestions = () => {
    if (!suggestions?.locations) return [];
    if (!location) return suggestions.locations.filter(loc => !selectedLocations.includes(loc));
    return suggestions.locations.filter(suggestion => 
      suggestion.toLowerCase().includes(location.toLowerCase()) && !selectedLocations.includes(suggestion)
    );
  };

  const getFilteredSkillsSuggestions = () => {
    if (!suggestions?.skills) return [];
    if (!skills) return suggestions.skills.filter(skill => !selectedSkills.includes(skill));
    return suggestions.skills.filter(suggestion => 
      suggestion.toLowerCase().includes(skills.toLowerCase()) && !selectedSkills.includes(suggestion)
    );
  };

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        roleRef.current && !roleRef.current.contains(event.target as Node) &&
        locationRef.current && !locationRef.current.contains(event.target as Node) &&
        skillsRef.current && !skillsRef.current.contains(event.target as Node)
      ) {
        setShowRoleSuggestions(false);
        setShowLocationSuggestions(false);
        setShowSkillsSuggestions(false);
        setActiveDropdown(null);
      }
    };
    
    // Use 'click' so portal suggestion clicks fire before this handler hides dropdowns
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);

  // Keep dropdown positioned when role suggestions open
  useEffect(() => {
    if (showRoleSuggestions) {
      setActiveDropdown('role');
      updateDropdownPosition(roleRef);
    } else if (activeDropdown === 'role') {
      setActiveDropdown(null);
      setDropdownStyle(null);
    }
  }, [showRoleSuggestions]);

  // Keep dropdown positioned when location suggestions open
  useEffect(() => {
    if (showLocationSuggestions) {
      setActiveDropdown('location');
      updateDropdownPosition(locationRef);
    } else if (activeDropdown === 'location') {
      setActiveDropdown(null);
      setDropdownStyle(null);
    }
  }, [showLocationSuggestions]);

  // Keep dropdown positioned when skills suggestions open
  useEffect(() => {
    if (showSkillsSuggestions) {
      setActiveDropdown('skills');
      updateDropdownPosition(skillsRef);
    } else if (activeDropdown === 'skills') {
      setActiveDropdown(null);
      setDropdownStyle(null);
    }
  }, [showSkillsSuggestions]);

  // Compute and set dropdown position for a given ref
  const updateDropdownPosition = (ref: React.RefObject<any> | null) => {
    const el = ref?.current;
    if (!el) return setDropdownStyle(null);
    const rect = el.getBoundingClientRect();
    setDropdownStyle({
      position: 'absolute',
      left: `${rect.left + window.pageXOffset}px`,
      top: `${rect.bottom + window.pageYOffset + 6}px`, // small gap
      width: `${rect.width}px`,
      zIndex: 99999,
    });
  };

  // Update position on scroll/resize when any dropdown is open
  useEffect(() => {
    const handler = () => {
      if (activeDropdown === 'role') updateDropdownPosition(roleRef);
      if (activeDropdown === 'location') updateDropdownPosition(locationRef);
      if (activeDropdown === 'skills') updateDropdownPosition(skillsRef);
    };
    window.addEventListener('resize', handler);
    window.addEventListener('scroll', handler, true);
    return () => {
      window.removeEventListener('resize', handler);
      window.removeEventListener('scroll', handler, true);
    };
  }, [activeDropdown]);
  
  const renderSuggestionDropdown = (
    suggestions: string[],
    onSelect: (value: string) => void,
    recentItems?: string[],
    selectedIndex?: number
  ) => (
    <div style={dropdownStyle || undefined} className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-xl max-h-64 overflow-y-auto animate-in slide-in-from-top-2 duration-200 z-[9999]">
      {recentItems && recentItems.length > 0 && (
        <div className="p-3 border-b border-gray-100 dark:border-gray-700">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">Recent</p>
          {recentItems.slice(0, 3).map((item, index) => (
            <button
              key={`recent-${index}`}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onSelect(item);
              }}
              className="block w-full text-left px-3 py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 rounded transition-colors cursor-pointer"
            >
              {item}
            </button>
          ))}
        </div>
      )}
      {suggestions.length > 0 ? (
        <div className="p-3">
          <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-2">Popular</p>
          <div className="space-y-1">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onSelect(suggestion);
                }}
                className={`block w-full text-left px-3 py-2 text-sm rounded transition-colors cursor-pointer ${
                  selectedIndex === index 
                    ? 'bg-blue-100 dark:bg-blue-800 text-blue-900 dark:text-blue-100' 
                    : 'text-gray-700 dark:text-gray-200 hover:bg-blue-50 dark:hover:bg-blue-900 hover:text-blue-700 dark:hover:text-blue-300'
                }`}
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      ) : (
        (!recentItems || recentItems.length === 0) && (
          <div className="p-3 text-center">
            <p className="text-sm text-gray-500 dark:text-gray-400">No suggestions found</p>
          </div>
        )
      )}
    </div>
  );
  
  return (
    <div className={`w-full ${className}`}>
      <form onSubmit={handleSubmit} className="w-full">
        <div className="flex flex-col md:flex-row gap-2 p-6 bg-transparent rounded-xl relative">
          
          {/* Collapse Button */}
          {onCollapse && (
            <button
              type="button"
              onClick={onCollapse}
              className="absolute -top-5 right-2 p-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white rounded-full transition-all z-10"
              title="Close search"
            >
              <X size={18} />
            </button>
          )}
          
          {/* Role Search - Simple Text Input */}
          <div ref={roleRef} className="relative flex-1">
            <div className="relative">
              <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 dark:text-gray-500 z-10" size={20} />
              <div className="relative">
                <input
                  type="text"
                  placeholder="Job title, role, or keywords..."
                  value={role}
                  onChange={(e) => handleRoleChange(e.target.value)}
                  onFocus={() => setShowRoleSuggestions(true)}
                  onKeyDown={(e) => handleKeyDown(e, 'role', getFilteredRoleSuggestions(), selectedRoleIndex, setSelectedRoleIndex)}
                  className="w-full h-14 pl-12 pr-12 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-full focus:ring-2 focus:ring-blue-500 focus:border-blue-500 focus:outline-none transition-all text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 text-sm"
                />
              </div>
              {role && (
                <button
                  type="button"
                  onClick={() => setRole('')}
                  className="absolute right-8 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-red-500 transition-colors"
                  title="Clear input"
                >
                  <X size={14} />
                </button>
              )}
              <button
                type="button"
                onClick={() => setShowRoleSuggestions(!showRoleSuggestions)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 dark:text-gray-500"
              >
                <ChevronDown size={16} />
              </button>
            </div>
            {showRoleSuggestions && suggestions && (
              createPortal(
                renderSuggestionDropdown(
                  getFilteredRoleSuggestions(),
                  (value) => handleSuggestionClick('role', value),
                  [], // Remove recent searches from role dropdown
                  selectedRoleIndex
                ),
                document.body
              )
            )}
          </div>
          
          {/* Location Search */}
          <div ref={locationRef} className="relative flex-1">
            <div className="relative">
              <MapPin className="absolute left-3 top-4 text-gray-400 dark:text-gray-500 z-10" size={20} />
              <div className="relative min-h-[3.5rem] border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 rounded-full focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition-all">
                <div className="flex flex-wrap gap-1 p-2 pl-12 pr-16">
                  {selectedLocations.map((locationItem, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center gap-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 text-sm px-2 py-1 rounded-full"
                    >
                      {locationItem}
                      <button
                        type="button"
                        onClick={() => removeLocation(locationItem)}
                        className="hover:text-purple-600 dark:hover:text-purple-300"
                      >
                        <X size={12} />
                      </button>
                    </span>
                  ))}
                  <input
                    type="text"
                    placeholder={selectedLocations.length === 0 ? "City, state, or remote..." : "Add more..."}
                    value={location}
                    onChange={(e) => handleLocationChange(e.target.value)}
                    onFocus={() => setShowLocationSuggestions(true)}
                    onKeyDown={(e) => handleKeyDown(e, 'location', getFilteredLocationSuggestions(), selectedLocationIndex, setSelectedLocationIndex)}
                    className="flex-1 min-w-0 bg-transparent border-none outline-none text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 py-2"
                  />
                </div>
              </div>
              {selectedLocations.length > 0 && (
                <button
                  type="button"
                  onClick={clearLocations}
                  className="absolute right-8 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-red-500 transition-colors"
                  title="Clear all locations"
                >
                  <X size={14} />
                </button>
              )}
              <button
                type="button"
                onClick={() => setShowLocationSuggestions(!showLocationSuggestions)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 dark:text-gray-500"
              >
                <ChevronDown size={16} />
              </button>
            </div>
            {showLocationSuggestions && suggestions && (
              createPortal(
                renderSuggestionDropdown(
                  getFilteredLocationSuggestions(),
                  (value) => handleSuggestionClick('location', value),
                  [], // Remove recent searches from location dropdown
                  selectedLocationIndex
                ),
                document.body
              )
            )}
          </div>
          
          {/* Skills Search */}
          <div ref={skillsRef} className="relative flex-1">
            <div className="relative">
              <Code className="absolute left-3 top-4 text-gray-400 dark:text-gray-500 z-10" size={20} />
              <div className="relative min-h-[3.5rem] border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 rounded-full focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition-all">
                <div className="flex flex-wrap gap-1 p-2 pl-12 pr-16">
                  {selectedSkills.map((skillItem, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center gap-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 text-sm px-2 py-1 rounded-full"
                    >
                      {skillItem}
                      <button
                        type="button"
                        onClick={() => removeSkill(skillItem)}
                        className="hover:text-green-600 dark:hover:text-green-300"
                      >
                        <X size={12} />
                      </button>
                    </span>
                  ))}
                  <input
                    type="text"
                    placeholder={selectedSkills.length === 0 ? "Skills (e.g., React, Python)..." : "Add more..."}
                    value={skills}
                    onChange={(e) => handleSkillsChange(e.target.value)}
                    onFocus={() => setShowSkillsSuggestions(true)}
                    onKeyDown={(e) => handleKeyDown(e, 'skills', getFilteredSkillsSuggestions(), selectedSkillsIndex, setSelectedSkillsIndex)}
                    className="flex-1 min-w-0 bg-transparent border-none outline-none text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 py-2"
                  />
                </div>
              </div>
              {selectedSkills.length > 0 && (
                <button
                  type="button"
                  onClick={clearSkills}
                  className="absolute right-8 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-red-500 transition-colors"
                  title="Clear all skills"
                >
                  <X size={14} />
                </button>
              )}
              <button
                type="button"
                onClick={() => setShowSkillsSuggestions(!showSkillsSuggestions)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 dark:text-gray-500"
              >
                <ChevronDown size={16} />
              </button>
            </div>
            {showSkillsSuggestions && suggestions && (
              createPortal(
                renderSuggestionDropdown(
                  getFilteredSkillsSuggestions(),
                  (value) => handleSuggestionClick('skills', value),
                  [], // Remove recent searches from skills dropdown
                  selectedSkillsIndex
                ),
                document.body
              )
            )}
          </div>
          
          {/* Search Button */}
          <div className="flex justify-center md:w-auto">
            <button
                type="submit"
                className="flex items-center justify-center w-12 h-12 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-full hover:from-blue-700 hover:to-blue-800 focus:outline-none focus:ring-4 focus:ring-blue-500/30 transition-transform duration-200 shadow-lg hover:shadow-xl transform hover:scale-105"
                aria-label="Search"
            >
                <Search size={20} />
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};

export default AdvancedSearchBar;