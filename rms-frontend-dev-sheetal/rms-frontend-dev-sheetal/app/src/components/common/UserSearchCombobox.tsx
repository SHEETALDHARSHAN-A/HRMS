import React, { useState, useEffect, useRef } from 'react';
import { searchUsers, getAdminById } from '../../api/adminApi.ts';
import type { User } from '../../types/auth';
import { Loader2, Search, User as UserIcon, X } from 'lucide-react';
import { useToast } from '../../context/ModalContext';

interface UserSearchComboboxProps {
  value: string | null; // The selected User ID
  onChange: (userId: string | null) => void;
}

// Debounce hook
const useDebounce = (value: string, delay: number) => {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  return debouncedValue;
};

const UserSearchCombobox: React.FC<UserSearchComboboxProps> = ({ value, onChange }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [results, setResults] = useState<User[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [initialNameLoaded, setInitialNameLoaded] = useState(false);
  
  const debouncedSearchTerm = useDebounce(searchTerm, 300);
  const { showToast } = useToast();
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Effect to load the user's name on initial component load if a value (ID) is provided
  useEffect(() => {
    if (value && !initialNameLoaded) {
      setIsLoading(true);
      getAdminById(value)
        .then(res => {
          if (res.success && res.data) {
            setSearchTerm(`${res.data.first_name} ${res.data.last_name}`.trim() || res.data.email);
            setInitialNameLoaded(true);
          } else {
            showToast(`Could not load user ${value}`, 'error');
            setSearchTerm(value); // Fallback to showing the ID
          }
        })
        .finally(() => setIsLoading(false));
    }
  }, [value, initialNameLoaded, showToast]);

  // Effect to search when the debounced search term changes
  useEffect(() => {
    if (debouncedSearchTerm.length < 2 || (value && initialNameLoaded)) {
      setResults([]);
      setIsDropdownOpen(false);
      return;
    }

    setIsLoading(true);
    setIsDropdownOpen(true);
    searchUsers(debouncedSearchTerm)
      .then(res => {
        if (res.success && res.data) {
          setResults(res.data);
        } else {
          setResults([]);
        }
      })
      .finally(() => setIsLoading(false));
  }, [debouncedSearchTerm, value, initialNameLoaded]);

  // Handle clicking outside the dropdown to close it
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleSelectUser = (user: User) => {
    onChange(user.user_id);
    setSearchTerm(`${user.first_name} ${user.last_name}`.trim() || user.email);
    setInitialNameLoaded(true); // Mark as "loaded"
    setIsDropdownOpen(false);
    setResults([]);
  };

  const handleClear = () => {
    setSearchTerm('');
    onChange(null);
    setInitialNameLoaded(true); // Mark as "loaded" since it's now empty
    setIsDropdownOpen(false);
    setResults([]);
  };
  
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTerm = e.target.value;
    setSearchTerm(newTerm);
    setInitialNameLoaded(true); // Any user typing invalidates the pre-loaded name
    if (newTerm === '') {
      handleClear();
    } else {
      setIsDropdownOpen(true);
    }
  };

  return (
    <div className="relative w-full" ref={dropdownRef}>
      <div className="relative">
        <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none">
          <Search size={18} className="text-gray-400" />
        </div>
        <input
          type="text"
          value={searchTerm}
          onChange={handleInputChange}
          onFocus={() => { if (searchTerm.length > 1) setIsDropdownOpen(true); }}
          placeholder="Search interviewer by name, email, or ID..."
          className="w-full bg-white border-2 rounded-xl px-12 py-3 text-base placeholder-gray-400 focus:outline-none focus:ring-0 focus:border-blue-500 shadow-sm transition-all duration-200 border-gray-200 hover:border-gray-300"
        />
        <div className="absolute inset-y-0 right-0 flex items-center pr-3">
          {isLoading ? (
            <Loader2 size={18} className="text-gray-400 animate-spin" />
          ) : (
            value && <button type="button" onClick={handleClear} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
          )}
        </div>
      </div>
      
      {isDropdownOpen && (isLoading || results.length > 0 || debouncedSearchTerm.length > 1) && (
        <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {isLoading && results.length === 0 ? (
            <div className="p-3 text-center text-gray-500">Loading...</div>
          ) : (
            <ul>
              {results.map(user => (
                <li key={user.user_id}>
                  <button
                    type="button"
                    onClick={() => handleSelectUser(user)}
                    className="w-full flex items-center gap-3 p-3 text-left hover:bg-gray-50 transition-colors"
                  >
                    <UserIcon size={16} className="text-gray-500" />
                    <div className="flex-1">
                      <p className="font-medium text-gray-800">{ `${user.first_name} ${user.last_name}`.trim()}</p>
                      <p className="text-sm text-gray-500">{user.email}</p>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {results.length === 0 && !isLoading && debouncedSearchTerm.length > 1 && (
             <div className="p-3 text-center text-gray-500">No users found.</div>
          )}
        </div>
      )}
    </div>
  );
};

export default UserSearchCombobox;