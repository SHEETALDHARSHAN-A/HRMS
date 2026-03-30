// Enhanced Job Application Page with Modern Design
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  Loader2, FileText, Upload, Mail, CheckCircle, ArrowLeft, Phone, User, 
  MapPin, Clock, Star, Building2, Briefcase, DollarSign,
  Shield, Users, ChevronDown
} from 'lucide-react';
import { useToast } from '../../context/ModalContext';
import { getPublicJobById } from '../../api/jobApi';
import { sendApplicationOTP, verifyAndSubmitApplication } from '../../api/careerApi';
import PublicLayout from "../../components/layout/PublicLayout";
import OTPVerificationForm from '../../components/auth/OTPVerificationForm';
import { AuthProvider } from '../../context/AuthContext';
import type { AuthContextType, VerifyResult } from '../../context/AuthContext';
import { z, ZodError } from 'zod';

// Comprehensive Country codes data with flags
const COUNTRY_CODES = [
  // Most popular countries first
  { code: '+91', country: 'IN', flag: '🇮🇳', name: 'India' },
  { code: '+1', country: 'US', flag: '🇺🇸', name: 'United States' },
  { code: '+44', country: 'GB', flag: '🇬🇧', name: 'United Kingdom' },
  { code: '+1', country: 'CA', flag: '🇨🇦', name: 'Canada' },
  { code: '+61', country: 'AU', flag: '🇦🇺', name: 'Australia' },
  
  // Major European countries
  { code: '+49', country: 'DE', flag: '🇩🇪', name: 'Germany' },
  { code: '+33', country: 'FR', flag: '🇫🇷', name: 'France' },
  { code: '+39', country: 'IT', flag: '🇮🇹', name: 'Italy' },
  { code: '+34', country: 'ES', flag: '🇪🇸', name: 'Spain' },
  { code: '+31', country: 'NL', flag: '🇳🇱', name: 'Netherlands' },
  { code: '+41', country: 'CH', flag: '🇨🇭', name: 'Switzerland' },
  { code: '+43', country: 'AT', flag: '🇦🇹', name: 'Austria' },
  { code: '+32', country: 'BE', flag: '🇧🇪', name: 'Belgium' },
  { code: '+45', country: 'DK', flag: '🇩🇰', name: 'Denmark' },
  { code: '+46', country: 'SE', flag: '🇸🇪', name: 'Sweden' },
  { code: '+47', country: 'NO', flag: '🇳🇴', name: 'Norway' },
  { code: '+358', country: 'FI', flag: '🇫🇮', name: 'Finland' },
  { code: '+353', country: 'IE', flag: '🇮🇪', name: 'Ireland' },
  { code: '+48', country: 'PL', flag: '🇵🇱', name: 'Poland' },
  { code: '+351', country: 'PT', flag: '🇵🇹', name: 'Portugal' },
  { code: '+30', country: 'GR', flag: '🇬🇷', name: 'Greece' },
  { code: '+420', country: 'CZ', flag: '🇨🇿', name: 'Czech Republic' },
  { code: '+36', country: 'HU', flag: '🇭🇺', name: 'Hungary' },
  
  // Asia Pacific
  { code: '+86', country: 'CN', flag: '🇨🇳', name: 'China' },
  { code: '+81', country: 'JP', flag: '🇯🇵', name: 'Japan' },
  { code: '+82', country: 'KR', flag: '🇰🇷', name: 'South Korea' },
  { code: '+65', country: 'SG', flag: '🇸🇬', name: 'Singapore' },
  { code: '+60', country: 'MY', flag: '🇲🇾', name: 'Malaysia' },
  { code: '+66', country: 'TH', flag: '🇹🇭', name: 'Thailand' },
  { code: '+62', country: 'ID', flag: '🇮🇩', name: 'Indonesia' },
  { code: '+63', country: 'PH', flag: '🇵🇭', name: 'Philippines' },
  { code: '+84', country: 'VN', flag: '🇻🇳', name: 'Vietnam' },
  { code: '+886', country: 'TW', flag: '🇹🇼', name: 'Taiwan' },
  { code: '+852', country: 'HK', flag: '🇭🇰', name: 'Hong Kong' },
  { code: '+853', country: 'MO', flag: '🇲🇴', name: 'Macau' },
  { code: '+64', country: 'NZ', flag: '🇳🇿', name: 'New Zealand' },
  
  // Middle East & Africa
  { code: '+971', country: 'AE', flag: '🇦🇪', name: 'UAE' },
  { code: '+966', country: 'SA', flag: '🇸🇦', name: 'Saudi Arabia' },
  { code: '+974', country: 'QA', flag: '🇶🇦', name: 'Qatar' },
  { code: '+965', country: 'KW', flag: '🇰🇼', name: 'Kuwait' },
  { code: '+973', country: 'BH', flag: '🇧🇭', name: 'Bahrain' },
  { code: '+968', country: 'OM', flag: '🇴🇲', name: 'Oman' },
  { code: '+962', country: 'JO', flag: '🇯🇴', name: 'Jordan' },
  { code: '+961', country: 'LB', flag: '🇱🇧', name: 'Lebanon' },
  { code: '+972', country: 'IL', flag: '🇮🇱', name: 'Israel' },
  { code: '+90', country: 'TR', flag: '🇹🇷', name: 'Turkey' },
  { code: '+98', country: 'IR', flag: '🇮🇷', name: 'Iran' },
  { code: '+20', country: 'EG', flag: '🇪🇬', name: 'Egypt' },
  { code: '+27', country: 'ZA', flag: '🇿🇦', name: 'South Africa' },
  { code: '+234', country: 'NG', flag: '🇳🇬', name: 'Nigeria' },
  { code: '+254', country: 'KE', flag: '🇰🇪', name: 'Kenya' },
  
  // Americas
  { code: '+55', country: 'BR', flag: '🇧🇷', name: 'Brazil' },
  { code: '+52', country: 'MX', flag: '🇲🇽', name: 'Mexico' },
  { code: '+54', country: 'AR', flag: '🇦🇷', name: 'Argentina' },
  { code: '+56', country: 'CL', flag: '🇨🇱', name: 'Chile' },
  { code: '+57', country: 'CO', flag: '🇨🇴', name: 'Colombia' },
  { code: '+51', country: 'PE', flag: '🇵🇪', name: 'Peru' },
  { code: '+58', country: 'VE', flag: '🇻🇪', name: 'Venezuela' },
  { code: '+593', country: 'EC', flag: '🇪🇨', name: 'Ecuador' },
  { code: '+598', country: 'UY', flag: '🇺🇾', name: 'Uruguay' },
  
  // South Asia
  { code: '+92', country: 'PK', flag: '🇵🇰', name: 'Pakistan' },
  { code: '+880', country: 'BD', flag: '🇧🇩', name: 'Bangladesh' },
  { code: '+94', country: 'LK', flag: '🇱🇰', name: 'Sri Lanka' },
  { code: '+977', country: 'NP', flag: '🇳🇵', name: 'Nepal' },
  { code: '+975', country: 'BT', flag: '🇧🇹', name: 'Bhutan' },
  { code: '+960', country: 'MV', flag: '🇲🇻', name: 'Maldives' },
  { code: '+93', country: 'AF', flag: '🇦🇫', name: 'Afghanistan' },
  
  // Eastern Europe & Russia
  { code: '+7', country: 'RU', flag: '🇷🇺', name: 'Russia' },
  { code: '+380', country: 'UA', flag: '🇺🇦', name: 'Ukraine' },
  { code: '+375', country: 'BY', flag: '🇧�', name: 'Belarus' },
  { code: '+374', country: 'AM', flag: '🇦🇲', name: 'Armenia' },
  { code: '+995', country: 'GE', flag: '🇬🇪', name: 'Georgia' },
  { code: '+994', country: 'AZ', flag: '🇦🇿', name: 'Azerbaijan' },
  { code: '+7', country: 'KZ', flag: '🇰🇿', name: 'Kazakhstan' },
  { code: '+996', country: 'KG', flag: '🇰🇬', name: 'Kyrgyzstan' },
  { code: '+992', country: 'TJ', flag: '🇹🇯', name: 'Tajikistan' },
  { code: '+993', country: 'TM', flag: '🇹🇲', name: 'Turkmenistan' },
  { code: '+998', country: 'UZ', flag: '🇺🇿', name: 'Uzbekistan' },
  
  // Additional European countries
  { code: '+385', country: 'HR', flag: '🇭🇷', name: 'Croatia' },
  { code: '+386', country: 'SI', flag: '�🇮', name: 'Slovenia' },
  { code: '+387', country: 'BA', flag: '🇧🇦', name: 'Bosnia and Herzegovina' },
  { code: '+382', country: 'ME', flag: '🇲�🇪', name: 'Montenegro' },
  { code: '+381', country: 'RS', flag: '��🇸', name: 'Serbia' },
  { code: '+389', country: 'MK', flag: '🇲🇰', name: 'North Macedonia' },
  { code: '+355', country: 'AL', flag: '🇦🇱', name: 'Albania' },
  { code: '+359', country: 'BG', flag: '🇧🇬', name: 'Bulgaria' },
  { code: '+40', country: 'RO', flag: '🇷🇴', name: 'Romania' },
  { code: '+421', country: 'SK', flag: '🇸🇰', name: 'Slovakia' },
  { code: '+370', country: 'LT', flag: '�🇹', name: 'Lithuania' },
  { code: '+371', country: 'LV', flag: '🇱🇻', name: 'Latvia' },
  { code: '+372', country: 'EE', flag: '🇪🇪', name: 'Estonia' },
  { code: '+373', country: 'MD', flag: '🇲🇩', name: 'Moldova' },
  
  // Caribbean & Central America
  { code: '+1', country: 'JM', flag: '��', name: 'Jamaica' },
  { code: '+1', country: 'TT', flag: '🇹🇹', name: 'Trinidad and Tobago' },
  { code: '+1', country: 'BB', flag: '🇧🇧', name: 'Barbados' },
  { code: '+1', country: 'BS', flag: '🇧🇸', name: 'Bahamas' },
  { code: '+502', country: 'GT', flag: '🇬🇹', name: 'Guatemala' },
  { code: '+503', country: 'SV', flag: '🇸�', name: 'El Salvador' },
  { code: '+504', country: 'HN', flag: '🇭🇳', name: 'Honduras' },
  { code: '+505', country: 'NI', flag: '🇳🇮', name: 'Nicaragua' },
  { code: '+506', country: 'CR', flag: '�🇷', name: 'Costa Rica' },
  { code: '+507', country: 'PA', flag: '🇵🇦', name: 'Panama' },
];

// (Validation schema, FileUploadZone helper, and Input helper remain the same)
const applicationSchema = z.object({
  firstName: z.string().trim().min(2, { message: "First name is required." }),
  lastName: z.string().trim().min(1, { message: "Last name is required." }),
  email: z.string().email({ message: "A valid email is required." }),
  phone: z.string().trim().min(10, { message: "A valid phone number is required." }),
  resume: z.instanceof(File, { message: "A resume file is required." })
    .refine(file => file.size <= 5 * 1024 * 1024, `Resume must be 5MB or less.`)
    .refine(
      file => ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"].includes(file.type),
      "Must be a PDF or Word document."
    ),
});
type ApplicationFormData = z.infer<typeof applicationSchema>;
interface FileUploadZoneProps {
  file: File | null;
  onFileSelect: (file: File) => void;
  error?: string;
}
const FileUploadZone: React.FC<FileUploadZoneProps> = ({ file, onFileSelect, error }) => {
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      onFileSelect(selectedFile);
    }
  };
  
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };
  
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      onFileSelect(droppedFile);
    }
  };

  const baseClasses = "relative w-full p-8 border-2 border-dashed rounded-3xl transition-all duration-300 cursor-pointer flex flex-col items-center justify-center text-center group overflow-hidden";
  const stateClasses = error
    ? "border-red-400 bg-gradient-to-br from-red-50 to-red-100/50 dark:bg-red-900/20 text-red-700 dark:text-red-400"
    : file
    ? "border-green-500 bg-gradient-to-br from-green-50 to-emerald-100/50 dark:bg-green-900/20 text-green-700 dark:text-green-400"
    : isDragging
    ? "border-blue-500 bg-gradient-to-br from-blue-50 to-indigo-100/50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 scale-[1.02] shadow-xl"
    : "border-gray-300 dark:border-gray-600 bg-gradient-to-br from-gray-50 to-gray-100/50 dark:bg-gray-800/50 text-gray-600 dark:text-gray-400 hover:border-blue-400 hover:from-blue-50/50 hover:to-indigo-50/50 dark:hover:bg-blue-900/10 hover:scale-[1.01]";

  return (
    <div
      className={`${baseClasses} ${stateClasses}`}
      onClick={() => fileInputRef.current?.click()}
      onDragOver={handleDragOver}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
    >
      {/* Animated background pattern */}
      <div className="absolute inset-0 opacity-[0.03] dark:opacity-[0.05]">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,currentColor_2px,transparent_2px)] bg-[length:30px_30px] animate-pulse"></div>
      </div>
      
      {/* Floating particles effect */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-4 left-4 w-1 h-1 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
        <div className="absolute top-6 right-8 w-1 h-1 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: '1s' }}></div>
        <div className="absolute bottom-8 left-12 w-1 h-1 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '2s' }}></div>
      </div>
      
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.doc,.docx"
        className="hidden"
        onChange={handleFileChange}
      />
      
      {file ? (
        <div className="relative z-10 animate-fade-in">
          <div className="relative mb-6">
            <div className="w-20 h-20 mx-auto bg-gradient-to-br from-green-100 to-emerald-200 dark:from-green-900/30 dark:to-emerald-800/30 rounded-2xl flex items-center justify-center shadow-lg">
              <FileText size={32} className="text-green-600 dark:text-green-400" />
            </div>
          </div>
          <p className="font-bold text-green-800 dark:text-green-300 mb-2 text-lg">{file.name}</p>
          <p className="text-sm text-green-600 dark:text-green-400 font-medium">
            {(file.size / 1024 / 1024).toFixed(2)} MB • Ready to submit
          </p>
          <div className="mt-4 inline-flex items-center gap-2 text-xs text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30 px-3 py-1 rounded-full">
            <Shield size={12} />
            File uploaded securely
          </div>
        </div>
      ) : (
        <div className="relative z-10">
          <div className="relative mb-6 group-hover:scale-110 transition-transform duration-300">
            <div className="mx-auto flex items-center justify-center">
              <Upload size={32} className="text-gray-500 dark:text-gray-300 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors duration-300" />
            </div>
          </div>
          
          <div className="space-y-3">
            <p className="font-bold text-gray-800 dark:text-gray-200 text-lg group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors duration-300">
              {isDragging ? 'Drop your file here' : 'Drop your resume here or click to upload'}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">
              PDF or DOCX files only • Maximum 5MB
            </p>
            <div className="inline-flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500 bg-gray-100 dark:bg-gray-700 px-3 py-1 rounded-full">
              <Shield size={12} />
              Your file will be kept confidential
            </div>
          </div>
        </div>
      )}
      
      {error && (
        <div className="relative z-10 mt-4 p-3 bg-red-100 dark:bg-red-900/30 rounded-lg border border-red-300 dark:border-red-700">
          <p className="text-sm text-red-700 dark:text-red-400 font-medium flex items-center justify-center gap-2">
            <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
            {error}
          </p>
        </div>
      )}
    </div>
  );
};
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  name: string;
  error?: string;
  Icon: React.ElementType;
}
const Input: React.FC<InputProps> = ({ label, name, error, Icon, ...props }) => (
  <div className="w-full">
    <label htmlFor={name} className="block text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">
      {label}
    </label>
    <div className="relative group">
      {/* Icon */}
      <div className={`absolute inset-y-0 left-0 flex items-center pl-4 z-10 transition-all duration-200 ${
        error ? "text-red-500" : "text-gray-400 group-focus-within:text-blue-600 dark:group-focus-within:text-blue-400"
      }`}>
        <Icon size={20} />
      </div>
      
      {/* Input Field */}
      <input
        id={name}
        name={name}
        className={`relative w-full pl-14 pr-4 py-4 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 bg-white dark:bg-gray-800 border-2 rounded-2xl focus:outline-none transition-all duration-300 ${
          error 
            ? 'border-red-300 focus:border-red-500 focus:ring-4 focus:ring-red-100 dark:focus:ring-red-900/20 bg-red-50/50 dark:bg-red-900/10' 
            : 'border-gray-200 dark:border-gray-600 focus:border-blue-500 focus:ring-4 focus:ring-blue-100 dark:focus:ring-blue-900/20 hover:border-gray-300 dark:hover:border-gray-500'
          }`}
        {...props}
      />
      
      {/* Success indicator */}
      {props.value && !error && (
        <div className="absolute inset-y-0 right-0 flex items-center pr-4">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
        </div>
      )}
    </div>
    
    {error && (
      <div className="mt-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
        <p className="text-sm text-red-700 dark:text-red-400 font-medium flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-red-500 rounded-full"></span>
          {error}
        </p>
      </div>
    )}
  </div>
);

// Specialized Phone Input Component with Country Code Selector
interface PhoneInputProps {
  label: string;
  name: string;
  value: string;
  error?: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

const PhoneInput: React.FC<PhoneInputProps> = ({ label, name, value, error, onChange }) => {
  const [selectedCountry, setSelectedCountry] = useState(COUNTRY_CODES[0]); // Default to India
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const dropdownRef = React.useRef<HTMLDivElement>(null);
  const searchInputRef = React.useRef<HTMLInputElement>(null);

  // Filter countries based on search term
  const filteredCountries = COUNTRY_CODES.filter(country => 
    country.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    country.code.includes(searchTerm) ||
    country.country.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Reset highlighted index when search term changes
  useEffect(() => {
    setHighlightedIndex(-1);
  }, [searchTerm]);

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isDropdownOpen && searchInputRef.current) {
      setTimeout(() => searchInputRef.current?.focus(), 100);
    }
  }, [isDropdownOpen]);

  // Extract country code and phone number from the current value
  useEffect(() => {
    if (value) {
      const matchedCountry = COUNTRY_CODES.find(country => value.startsWith(country.code));
      if (matchedCountry) {
        setSelectedCountry(matchedCountry);
        setPhoneNumber(value.slice(matchedCountry.code.length));
      } else {
        setPhoneNumber(value);
      }
    }
  }, [value]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
        setSearchTerm(''); // Reset search when closing
      }
    };
    
    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isDropdownOpen]);

  const handleCountrySelect = (country: typeof COUNTRY_CODES[0]) => {
    setSelectedCountry(country);
    setIsDropdownOpen(false);
    // Update the full phone number
    const fullNumber = country.code + phoneNumber;
    const syntheticEvent = {
      target: { name, value: fullNumber }
    } as React.ChangeEvent<HTMLInputElement>;
    onChange(syntheticEvent);
  };

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const input = e.target.value;
    // Only allow digits - remove any non-numeric characters
    const numericValue = input.replace(/[^\d]/g, '');
    setPhoneNumber(numericValue);
    // Update the full phone number with country code
    const fullNumber = selectedCountry.code + numericValue;
    const syntheticEvent = {
      target: { name, value: fullNumber }
    } as React.ChangeEvent<HTMLInputElement>;
    onChange(syntheticEvent);
  };

  // Handle keyboard navigation in dropdown
  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (!isDropdownOpen) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex(prev => 
          prev < filteredCountries.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(prev => prev > 0 ? prev - 1 : filteredCountries.length - 1);
        break;
      case 'Enter':
        e.preventDefault();
        if (highlightedIndex >= 0 && filteredCountries[highlightedIndex]) {
          handleCountrySelect(filteredCountries[highlightedIndex]);
          setSearchTerm('');
        }
        break;
      case 'Escape':
        e.preventDefault();
        setIsDropdownOpen(false);
        setSearchTerm('');
        break;
    }
  };

  return (
    <div className="w-full">
      <label htmlFor={name} className="block text-sm font-semibold text-gray-800 dark:text-gray-200 mb-3">
        {label}
      </label>
      <div className="relative group">
        {/* Phone Icon */}
        <div className={`absolute inset-y-0 left-0 flex items-center pl-4 z-10 transition-all duration-200 ${
          error ? "text-red-500" : "text-gray-400 group-focus-within:text-blue-600 dark:group-focus-within:text-blue-400"
        }`}>
          <Phone size={20} />
        </div>
        
        {/* Country Code Dropdown */}
        <div className="absolute inset-y-0 left-14 flex items-center z-20">
          <div className="relative" ref={dropdownRef}>
            <button
              type="button"
              onClick={() => {
                setIsDropdownOpen(!isDropdownOpen);
                if (!isDropdownOpen) {
                  setSearchTerm(''); // Reset search when opening dropdown
                }
              }}
              className={`flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border-r transition-all duration-200 ${
                error 
                  ? 'text-red-600 border-red-300' 
                  : 'text-gray-700 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              <span className="text-base">{selectedCountry.flag}</span>
              <span className="font-mono text-sm">{selectedCountry.code}</span>
              <ChevronDown size={14} className={`transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} />
            </button>
            
            {/* Enhanced Dropdown Menu with Search */}
            {isDropdownOpen && (
              <div className="absolute top-full mt-1 left-0 w-80 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-xl z-50">
                {/* Search Header */}
                <div className="p-3 border-b border-gray-200 dark:border-gray-600">
                  <div className="relative">
                    <input
                      ref={searchInputRef}
                      type="text"
                      placeholder="Search countries..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      onKeyDown={handleSearchKeyDown}
                      className="w-full pl-8 pr-3 py-2 text-sm bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                    <svg className="absolute left-2.5 top-2.5 w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                  <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    {filteredCountries.length} countries found
                  </div>
                </div>
                
                {/* Countries List */}
                <div className="max-h-64 overflow-y-auto">
                  {filteredCountries.length > 0 ? (
                    filteredCountries.map((country, index) => (
                      <button
                        key={`${country.flag}-${country.code}-${country.country}`}
                        type="button"
                        onClick={() => {
                          handleCountrySelect(country);
                          setSearchTerm('');
                        }}
                        className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors ${
                          index === highlightedIndex && highlightedIndex >= 0
                            ? 'bg-blue-100 dark:bg-blue-900/30' 
                            : 'hover:bg-gray-50 dark:hover:bg-gray-700'
                        } ${
                          selectedCountry.flag === country.flag && selectedCountry.code === country.code
                            ? 'bg-blue-50 dark:bg-blue-900/20 border-r-2 border-blue-500' 
                            : ''
                        }`}
                      >
                        <span className="text-xl flex-shrink-0">{country.flag}</span>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-gray-900 dark:text-gray-100 truncate">
                            {country.name}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400 font-mono">
                            {country.code}
                          </div>
                        </div>
                        {selectedCountry.flag === country.flag && selectedCountry.code === country.code && (
                          <div className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0"></div>
                        )}
                      </button>
                    ))
                  ) : (
                    <div className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                      <svg className="w-8 h-8 mx-auto mb-2 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                      <p className="text-sm">No countries found</p>
                      <p className="text-xs mt-1">Try a different search term</p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
        
        {/* Phone Number Input */}
        <input
          id={name}
          name={name}
          type="tel"
          value={phoneNumber}
          onChange={handlePhoneChange}
          onKeyPress={(e) => {
            // Only allow digits, backspace, delete, arrow keys, and tab
            if (!/[0-9]/.test(e.key) && !['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Tab'].includes(e.key)) {
              e.preventDefault();
            }
          }}
          placeholder="Phone number"
          inputMode="numeric"
          pattern="[0-9]*"
          className={`relative w-full pl-44 pr-4 py-4 text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 bg-white dark:bg-gray-800 border-2 rounded-2xl focus:outline-none transition-all duration-300 ${
            error 
              ? 'border-red-300 focus:border-red-500 focus:ring-4 focus:ring-red-100 dark:focus:ring-red-900/20 bg-red-50/50 dark:bg-red-900/10' 
              : 'border-gray-200 dark:border-gray-600 focus:border-blue-500 focus:ring-4 focus:ring-blue-100 dark:focus:ring-blue-900/20 hover:border-gray-300 dark:hover:border-gray-500'
            }`}
        />
        
        {/* Success indicator */}
        {value && !error && (
          <div className="absolute inset-y-0 right-0 flex items-center pr-4">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          </div>
        )}
      </div>
      
      {error && (
        <div className="mt-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm text-red-700 dark:text-red-400 font-medium flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-red-500 rounded-full"></span>
            {error}
          </p>
        </div>
      )}
    </div>
  );
};

const JobApplicationPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [step, setStep] = useState<'details' | 'otp' | 'submitting' | 'success'>('details');
  const [jobDetails, setJobDetails] = useState<{ 
    title: string; 
    location: string; 
    wfh: boolean;
    skills?: string[];
    experience?: string;
    description?: string;
    salary?: string;
    employment_type?: string;
    department?: string;
  } | null>(null);
  const [isLoadingJob, setIsLoadingJob] = useState(true);

  // (Form state and fetch logic remain the same)
  const [formData, setFormData] = useState<Partial<ApplicationFormData>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSendingOTP, setIsSendingOTP] = useState(false);
  // OTP lifecycle state  
  const [resendCooldown, setResendCooldown] = useState<number>(0); // seconds remaining before resend allowed

  useEffect(() => {
    if (!jobId) {
      showToast('No Job ID provided.', 'error');
      navigate('/career-page');
      return;
    }
    getPublicJobById(jobId)
      .then(res => {
        if (res.success && res.data) {
          console.log('Job API Response:', res.data); // Debug log
          setJobDetails({
            title: res.data.title || 'Job Title',
            location: res.data.location || 'Location',
            wfh: res.data.wfh || false,
            skills: res.data.skills || [],
            experience: res.data.min_experience && res.data.max_experience 
              ? `${res.data.min_experience}-${res.data.max_experience} years`
              : 'Experience not specified',
            description: res.data.job_description || '',
            salary: res.data.salary,
            employment_type: res.data.employment_type,
            department: res.data.department,
          });
          setIsLoadingJob(false);
        } else {
          showToast('Could not find job.', 'error');
          navigate('/career-page');
        }
      })
      .catch(err => {
        showToast(err.message, 'error');
        navigate('/career-page');
      });
  }, [jobId, navigate, showToast]);

  // (All handler functions remain the same)
  const handleDetailsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };
  const handleFileSelect = (file: File) => {
    setFormData(prev => ({ ...prev, resume: file }));
    if (errors.resume) {
      setErrors(prev => ({ ...prev, resume: '' }));
    }
  };
  const handleSendOTP = async () => {
    try {
      const validatedData = applicationSchema.parse(formData);
      setErrors({});
      setIsSendingOTP(true);
      const result = await sendApplicationOTP({
        jobId: jobId!,
        email: validatedData.email,
        firstName: validatedData.firstName,
        lastName: validatedData.lastName,
        phone: validatedData.phone,
      });
      if (result.success) {
        showToast('OTP sent to your email!', 'success');
        // Initialize resend cooldown
        setResendCooldown(30); // 30s cooldown before resend
        setStep('otp');
      } else {
        if (result.status === 409) {
          setErrors({ email: result.error || "You have already applied for this job." });
        } else {
          showToast(result.error || 'Failed to send OTP.', 'error');
        }
      }
    } catch (error) {
      if (error instanceof ZodError) {
        const fieldErrors: Record<string, string> = {};
        error.issues.forEach(issue => {
          fieldErrors[issue.path[0] as string] = issue.message;
        });
        setErrors(fieldErrors);
      } else {
        showToast((error as Error).message, 'error');
      }
    } finally {
      setIsSendingOTP(false);
    }
  };
  // (All step render functions remain the same)
  // OTP resend cooldown timer
  useEffect(() => {
    if (step !== 'otp') return;
    const t = setInterval(() => {
      setResendCooldown(prev => Math.max(prev - 1, 0));
    }, 1000);
    return () => clearInterval(t);
  }, [step]);

  // Resend wrapper that respects cooldown
  const handleResendOTP = async () => {
    if (resendCooldown > 0) return;
    // reuse existing send flow but indicate it's a resend
    try {
      setIsSendingOTP(true);
      const validatedData = applicationSchema.parse(formData);
      const result = await sendApplicationOTP({
        jobId: jobId!,
        email: validatedData.email,
        firstName: validatedData.firstName,
        lastName: validatedData.lastName,
        phone: validatedData.phone,
      });
      if (result.success) {
        showToast('New OTP sent to your email!', 'success');
        setResendCooldown(30);
      } else {
        showToast(result.error || 'Failed to resend OTP.', 'error');
      }
    } catch (err) {
      if (err instanceof ZodError) {
        showToast('Please fill details correctly before resending.', 'error');
      } else {
        showToast((err as Error).message, 'error');
      }
    } finally {
      setIsSendingOTP(false);
    }
  };

  // Wrapper functions for AuthContext integration
  const verifyOTPForContext = async (otpParam: string): Promise<VerifyResult> => {
    // Basic validation
    if (!formData.resume) {
      return { success: false, message: 'Please attach a resume before verifying.' };
    }

    const submissionData = new FormData();
    submissionData.append('jobId', jobId!);
    submissionData.append('email', formData.email!);
    submissionData.append('otp', otpParam);
    submissionData.append('firstName', formData.firstName!);
    submissionData.append('lastName', formData.lastName!);
    submissionData.append('phone', formData.phone!);
    submissionData.append('resume', formData.resume!);

    try {
      setStep('submitting');
      const result = await verifyAndSubmitApplication(submissionData);
      if (result.success) {
        setStep('success');
      } else {
        // OTP verification failed
        setStep('otp');
      }
      return result;
    } catch (err) {
      setStep('otp');
      return { success: false, message: (err as Error).message };
    }
  };

  const resendOTPForContext = async (): Promise<VerifyResult> => {
    if (resendCooldown > 0) {
      return { success: false, message: `Please wait ${resendCooldown} seconds before resending.` };
    }

    try {
      await handleResendOTP();
      return { success: true, message: 'Code sent successfully!' };
    } catch (error) {
      return { success: false, message: (error as Error).message || 'Failed to resend code' };
    }
  };
  const renderDetailsStep = () => (
    <div className="space-y-10">
      {/* Personal Information Section */}
      <div className="relative">
        {/* Section Header */}
        <div className="flex items-center gap-4 mb-8">
          <div className="flex items-center justify-center w-12 h-12 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-2xl shadow-lg">
            <User size={24} className="text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Personal Information</h2>
            <p className="text-gray-600 dark:text-gray-400">Tell us about yourself</p>
          </div>
        </div>
        
        {/* Form Fields with Enhanced Layout */}
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="group">
              <Input 
                name="firstName" 
                label="First Name" 
                value={formData.firstName || ''} 
                error={errors.firstName} 
                onChange={handleDetailsChange} 
                Icon={User} 
              />
            </div>
            <div className="group">
              <Input 
                name="lastName" 
                label="Last Name" 
                value={formData.lastName || ''} 
                error={errors.lastName} 
                onChange={handleDetailsChange} 
                Icon={User} 
              />
            </div>
          </div>
          
          <div className="group">
            <Input 
              name="email" 
              type="email" 
              label="Email Address" 
              value={formData.email || ''} 
              error={errors.email} 
              onChange={handleDetailsChange} 
              Icon={Mail} 
            />
          </div>
          
          <div className="group">
            <PhoneInput 
              name="phone" 
              label="Phone Number" 
              value={formData.phone || ''} 
              error={errors.phone} 
              onChange={handleDetailsChange} 
            />
          </div>
        </div>
      </div>

      {/* Divider */}
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-200 dark:border-gray-700"></div>
        </div>
        <div className="relative flex justify-center">
          <div className="bg-white dark:bg-gray-800 px-4">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
          </div>
        </div>
      </div>

      {/* Resume Upload Section */}
      <div className="relative">
        {/* Section Header */}
        <div className="flex items-center gap-4 mb-8">
          <div className="flex items-center justify-center w-12 h-12 bg-gradient-to-r from-emerald-500 to-green-600 rounded-2xl shadow-lg">
            <FileText size={24} className="text-white" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Resume Upload</h2>
            <p className="text-gray-600 dark:text-gray-400">Share your professional experience</p>
          </div>
        </div>
        
        <FileUploadZone file={formData.resume || null} onFileSelect={handleFileSelect} error={errors.resume} />
      </div>

      {/* Enhanced Submit Button */}
      <div className="pt-6">
        <div className="relative">
          {/* Progress indicator */}
          <div className="mb-4 text-center">
            <div className="inline-flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></div>
              Step 1 of 3: Personal Details
            </div>
          </div>
          
          <button
            type="button" 
            onClick={handleSendOTP} 
            disabled={isSendingOTP}
            className="group relative w-full py-4 px-6 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed overflow-hidden"
          >
            {/* Button background effect */}
            <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/10 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
            
            {isSendingOTP ? (
              <>
                <Loader2 className="animate-spin" size={20} />
                <span>Sending verification code...</span>
              </>
            ) : (
              <>
                <Mail size={20} />
                <span>Continue to Verification</span>
                <div className="ml-2 w-6 h-6 bg-white/20 rounded-full flex items-center justify-center group-hover:translate-x-1 transition-transform duration-200">
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path d="M4 2L8 6L4 10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
  const renderOTPStep = () => {
    // Create AuthContext value for OTPVerificationForm
    const authContextValue: AuthContextType = {
      verifyOTP: verifyOTPForContext,
      resendOTP: resendOTPForContext,
      userEmail: formData.email,
      loading: step === 'submitting' || isSendingOTP,
      error: errors.otp || null,
      goBackToForm: () => setStep('details')
    };

    return (
      <div className="w-full max-w-md mx-auto">
        <div className="bg-white dark:bg-gray-800 p-6 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm">

          <div className="mt-4">
            <AuthProvider value={authContextValue}>
              <OTPVerificationForm />
            </AuthProvider>
          </div>

          <div className="mt-4 flex items-center justify-start">
            <button
              type="button"
              onClick={() => setStep('details')}
              className="text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 transition-colors"
            >
              <ArrowLeft size={14} className="inline-block mr-2" /> Edit details
            </button>
          </div>
        </div>
      </div>
    );
  };
  const renderSubmittingStep = () => (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-col items-center justify-center min-h-[20rem] text-center space-y-6 px-6"
    >
      <div className="flex items-center gap-6">
        <div className="flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-br from-white/30 to-white/10 border border-gray-100 dark:border-gray-700 shadow-lg">
          <div className="w-12 h-12 rounded-full flex items-center justify-center bg-blue-50 dark:bg-blue-900">
            <Loader2 size={28} className="animate-spin text-blue-600 dark:text-blue-300" />
          </div>
        </div>

        <div className="text-left">
          <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">Processing your application</h2>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400 max-w-xl">
            We're securely uploading and analysing your resume. This usually takes a few seconds — please keep this page open.
          </p>
        </div>
      </div>

      {/* subtle progress bar */}
      <div className="w-full max-w-2xl">
        <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
          <div className="h-3 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full animate-[progress_2.5s_linear_infinite]" style={{ width: '60%' }}></div>
        </div>
        <div className="flex items-center justify-between mt-3 text-xs text-gray-500 dark:text-gray-400">
          <span>Uploading resume</span>
          <span>Encrypting & analysing</span>
        </div>
      </div>

      {/* what happens next */}
      <div className="w-full max-w-2xl bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-lg p-4 text-left shadow-sm">
        <p className="text-sm text-gray-700 dark:text-gray-300 mb-2 font-medium">What happens next</p>
        <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-2">
          <li className="flex items-start gap-3">
            <span className="w-3 h-3 mt-1 rounded-full bg-blue-600/80" />
            We validate your submission and run an initial screening.
          </li>
          <li className="flex items-start gap-3">
            <span className="w-3 h-3 mt-1 rounded-full bg-blue-600/80" />
            If shortlisted, our team will contact you for the next steps.
          </li>
          <li className="flex items-start gap-3">
            <span className="w-3 h-3 mt-1 rounded-full bg-blue-600/80" />
            You'll also receive an email confirmation shortly.
          </li>
        </ul>

        <div className="mt-4 text-xs text-gray-500 dark:text-gray-400">Need help? <a href="mailto:hr@prayag.ai" className="text-blue-600 hover:underline">Contact support</a></div>
      </div>
    </div>
  );

  const renderSuccessStep = () => (
    <div className="flex flex-col items-center justify-center min-h-[28rem] text-center space-y-8 py-12 px-4">
      <div className="flex items-center justify-center w-28 h-28 rounded-full bg-green-50 dark:bg-green-900/20 border border-green-100 dark:border-green-800 shadow-sm">
        <CheckCircle size={56} className="text-green-600" />
      </div>

      <div className="max-w-3xl">
        <h2 className="text-3xl font-semibold text-gray-900 dark:text-gray-100">Application submitted</h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
          Thank you for applying to Our company. Your application is received and under review. We will contact you within <strong>2-3 business days</strong> if your profile matches the role.
        </p>
      </div>

      <div className="w-full max-w-3xl grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-lg text-left shadow-sm">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">Confirmation</h4>
          <p className="text-sm text-gray-600 dark:text-gray-400">A confirmation email has been sent to <strong className="text-gray-800 dark:text-gray-200">{formData.email}</strong>. Check your inbox for details.</p>
        </div>

        <div className="p-4 bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-lg text-left shadow-sm">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-1">Next steps</h4>
          <p className="text-sm text-gray-600 dark:text-gray-400">If shortlisted, our recruitment team will reach out via email or phone to schedule interviews.</p>
        </div>
      </div>

      <div className="flex items-center gap-3 mt-4">
        <Link to="/career-page" className="inline-block">
          <button className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium shadow flex items-center">
            <Briefcase size={16} className="mr-2" />
            Explore other roles
          </button>
        </Link>
      </div>
    </div>
  );

  // --- Main Render ---
  if (isLoadingJob || !jobDetails) {
    return (
      <PublicLayout
        bannerTitle="Loading Job..."
        bannerSubtitle="Please wait while we retrieve the details"
        showHeroContent={true} // Show hero text while loading
      >
        <div className="flex items-center justify-center h-96">
          <Loader2 size={32} className="animate-spin text-blue-600" />
        </div>
      </PublicLayout>
    );
  }

  const subtitle = jobDetails.wfh ? 'Remote Work' : jobDetails.location;

  return (
    <PublicLayout
        bannerTitle={jobDetails.title}
        bannerSubtitle={subtitle}
        showHeroContent={false} // Clean layout for application form
    >
      <style>{`
        @keyframes slideIn { 
          from { opacity: 0; transform: translateX(20px); } 
          to { opacity: 1; transform: translateX(0); } 
        }
        @keyframes fadeIn { 
          from { opacity: 0; transform: translateY(10px); } 
          to { opacity: 1; transform: translateY(0); } 
        }
        .animate-slide-in { 
          animation: slideIn 0.6s ease-out forwards; 
        }
        .animate-fade-in { 
          animation: fadeIn 0.5s ease-out forwards; 
        }
      `}</style>
      <div className="w-full max-w-6xl mx-auto px-4">
        <div className="flex flex-col lg:flex-row gap-8">
          
          {/* Job Information Sidebar */}
          <div className={step === 'otp' ? 'hidden' : 'lg:w-2/5'}>
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg border border-gray-200 dark:border-gray-700 p-6 sticky top-24 animate-slide-in">
              
              {/* Header with Back Button */}
              <div className="flex items-center justify-between mb-6">
                <button
                  type="button"
                  onClick={() => {
                    if (step === 'otp') setStep('details');
                    else navigate('/career-page');
                  }}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 rounded-lg transition-colors duration-200"
                >
                  <ArrowLeft size={16} />
                  Back
                </button>
                
                <div className="text-xs font-semibold text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 px-3 py-1 rounded-full">
                  OUR COMPANY
                </div>
              </div>

              {/* Job Title Section */}
              <div className="mb-6">
                <div className="flex items-center gap-2 mb-3">
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400">
                    <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-2"></span>
                    Open Position
                  </span>
                  <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400">
                    <Users size={10} className="mr-1" />
                    Hiring
                  </span>
                </div>
                
                <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100 mb-2 leading-tight">
                  {jobDetails.title}
                </h2>
                
                <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 mb-4">
                  <Building2 size={14} className="text-gray-400" />
                  <span></span>
                </div>
            
              </div>
              
              {/* Job Details */}
              <div className="space-y-4 mb-6">
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center">
                      <MapPin size={18} className="text-blue-600 dark:text-blue-400" />
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-gray-900 dark:text-gray-100">{jobDetails.wfh ? 'Remote Work' : jobDetails.location}</p>
                      <p className="text-sm text-gray-600 dark:text-gray-400">Work Location</p>
                    </div>
                  </div>
                </div>
                
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                      <Clock size={18} className="text-purple-600 dark:text-purple-400" />
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-gray-900 dark:text-gray-100">{jobDetails.experience || 'Open to all levels'}</p>
                      <p className="text-sm text-gray-600 dark:text-gray-400">Experience Required</p>
                    </div>
                  </div>
                </div>
                
                <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center">
                      <Briefcase size={18} className="text-green-600 dark:text-green-400" />
                    </div>
                    <div className="flex-1">
                      <p className="font-semibold text-gray-900 dark:text-gray-100">{jobDetails.employment_type || 'Full-time'}</p>
                      <p className="text-sm text-gray-600 dark:text-gray-400">Employment Type</p>
                    </div>
                  </div>
                </div>
                
                {jobDetails.salary && (
                  <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-orange-100 dark:bg-orange-900/30 rounded-lg flex items-center justify-center">
                        <DollarSign size={18} className="text-orange-600 dark:text-orange-400" />
                      </div>
                      <div className="flex-1">
                        <p className="font-semibold text-gray-900 dark:text-gray-100">{jobDetails.salary}</p>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Salary Package</p>
                      </div>
                    </div>
                  </div>
                )}
                
                {jobDetails.department && (
                  <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-indigo-100 dark:bg-indigo-900/30 rounded-lg flex items-center justify-center">
                        <Building2 size={18} className="text-indigo-600 dark:text-indigo-400" />
                      </div>
                      <div className="flex-1">
                        <p className="font-semibold text-gray-900 dark:text-gray-100">{jobDetails.department}</p>
                        <p className="text-sm text-gray-600 dark:text-gray-400">Department</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Required Skills (show top 3) */}
              {jobDetails.skills && jobDetails.skills.length > 0 && (
                <div className="mb-6">
                  <div className="flex items-center gap-2 mb-4">
                    <Star size={16} className="text-amber-500" />
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                      Required Skills
                    </h3>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {jobDetails.skills.slice(0, 3).map((skill, index) => (
                      <span
                        key={index}
                        className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200 border border-blue-100 dark:border-blue-700"
                      >
                        {skill}
                      </span>
                    ))}

                    {jobDetails.skills.length > 3 && (
                      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600">
                        +{jobDetails.skills.length - 3} more
                      </span>
                    )}
                  </div>
                </div>
              )}

              {jobDetails.description && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <FileText size={16} className="text-gray-600 dark:text-gray-400" />
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                      About this role
                    </h3>
                  </div>
                  <div className="p-4 bg-gray-50 dark:bg-gray-700/30 rounded-lg border border-gray-200 dark:border-gray-600">
                    <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                      {jobDetails.description}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Application Form */}
          <div className={step === 'otp' ? 'w-full max-w-3xl mx-auto' : 'lg:w-3/5'}>
            <div className="bg-gradient-to-br from-white to-blue-50/20 dark:from-gray-800 dark:to-gray-900/50 rounded-3xl shadow-2xl overflow-hidden border border-blue-100 dark:border-gray-700 animate-fade-in backdrop-blur-sm">
              
              {/* Professional Progress Indicator */}
              <div className="px-6 py-6 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Apply for this position</h1>
                    <p className="text-gray-600 dark:text-gray-400 text-sm">Complete the steps below... </p>
                  </div>
                  
                  {/* Professional Step Indicator */}
                  <div className="flex items-center">
                    {/* Step 1 */}
                    <div className="flex flex-col items-center">
                      <div className={`relative w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300 ${
                        step === 'details' 
                          ? 'bg-blue-600 text-white ring-4 ring-blue-200 dark:ring-blue-800' 
                          : (step === 'otp' || step === 'submitting' || step === 'success')
                            ? 'bg-green-600 text-white'
                            : 'bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300'
                      }`}>
                        {(step === 'otp' || step === 'submitting' || step === 'success') ? (
                          <CheckCircle size={16} />
                        ) : (
                          '1'
                        )}
                      </div>
                      <span className="text-xs font-medium text-gray-600 dark:text-gray-400 mt-1">Details</span>
                    </div>
                    
                    {/* Connector Line 1 */}
                    <div className={`w-16 h-0.5 mx-2 transition-colors duration-500 ${
                      (step === 'otp' || step === 'submitting' || step === 'success') 
                        ? 'bg-green-600' 
                        : 'bg-gray-300 dark:bg-gray-600'
                    }`}></div>
                    
                    {/* Step 2 */}
                    <div className="flex flex-col items-center">
                      <div className={`relative w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300 ${
                        step === 'otp' 
                          ? 'bg-blue-600 text-white ring-4 ring-blue-200 dark:ring-blue-800' 
                          : (step === 'submitting' || step === 'success')
                            ? 'bg-green-600 text-white'
                            : 'bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300'
                      }`}>
                        {(step === 'submitting' || step === 'success') ? (
                          <CheckCircle size={16} />
                        ) : (
                          '2'
                        )}
                      </div>
                      <span className="text-xs font-medium text-gray-600 dark:text-gray-400 mt-1">Verify</span>
                    </div>
                    
                    {/* Connector Line 2 */}
                    <div className={`w-16 h-0.5 mx-2 transition-colors duration-500 ${
                      (step === 'submitting' || step === 'success') 
                        ? 'bg-green-600' 
                        : 'bg-gray-300 dark:bg-gray-600'
                    }`}></div>
                    
                    {/* Step 3 */}
                    <div className="flex flex-col items-center">
                      <div className={`relative w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300 ${
                        step === 'success'
                          ? 'bg-green-600 text-white ring-4 ring-green-200 dark:ring-green-800'
                          : 'bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300'
                      }`}>
                        {step === 'success' ? (
                          <CheckCircle size={16} />
                        ) : (
                          '3'
                        )}
                      </div>
                      <span className="text-xs font-medium text-gray-600 dark:text-gray-400 mt-1">Complete</span>
                    </div>
                  </div>
                </div>
                
                {/* Current Step Description */}
                <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                  <div className={`w-2 h-2 rounded-full ${
                    step === 'details' ? 'bg-blue-600 animate-pulse' : 
                    step === 'otp' ? 'bg-blue-600 animate-pulse' : 
                    step === 'submitting' ? 'bg-orange-500 animate-pulse' : 
                    'bg-green-600'
                  }`}></div>
                  <span className="font-medium">
                    {step === 'details' && 'Fill in your information and upload your resume'}
                    {step === 'otp' && 'Check your email and enter the verification code'}
                    {step === 'submitting' && 'Processing your application...'}
                    {step === 'success' && 'Application submitted successfully!'}
                  </span>
                </div>
              </div>

              <div className="p-10 md:p-12 space-y-10">
                {step === 'details' && renderDetailsStep()}
                {step === 'otp' && renderOTPStep()}
                {step === 'submitting' && renderSubmittingStep()}
                {step === 'success' && renderSuccessStep()}
              </div>
            </div>
          </div>
        </div>
      </div>
    </PublicLayout>
  );
};

export default JobApplicationPage;