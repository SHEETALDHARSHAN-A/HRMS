// rms-frontend-dev-sheetal/app/src/components/auth/SignInForm.tsx
import { useState, useEffect, useCallback, useRef } from 'react';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { useAuthContext } from '../../context/AuthContext';
import { AUTH_CONFIG } from '../../constants/auth';
import { authService } from '../../services/authService';

// Debounce hook (assuming it exists as provided)
const useDebounce = (callback: (...args: any[]) => void, delay: number) => {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const debouncedCallback = useCallback((...args: any[]) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(() => {
      callback(...args);
    }, delay);
  }, [callback, delay]);

  useEffect(() => () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
  }, []);

  return debouncedCallback;
};


const SignInForm: React.FC = () => {
  // 💡 MODIFICATION: Removed switchToSignUp
  const { loading, error, signIn, userEmail } = useAuthContext();

  const [formData, setFormData] = useState(() => ({
    email: userEmail || '',
    rememberMe: localStorage.getItem('rememberMe') === 'true'
  }));
  const previousUserEmailRef = useRef<string | null>(userEmail || null);

  const [emailStatus, setEmailStatus] = useState<'idle' | 'checking' | 'available' | 'exists' | 'invalid' | 'not_registered'>('idle');
  const [emailCheckMessage, setEmailCheckMessage] = useState<string | null>(null);

  // checkEmailExistence and debounce logic remains the same
  const checkEmailExistence = useCallback(async (email: string) => {
    if (!email) {
      setEmailStatus('idle');
      setEmailCheckMessage(null);
      return;
    }

    setEmailStatus('checking');
    setEmailCheckMessage(null);

    try {
      const result = await authService.checkEmailStatus(email);
      const apiStatus = result.data?.user_status;

      if (apiStatus === 'EXIST') {
        // This is an Admin, this is a good state (allow sign-in)
        setEmailStatus('exists');
      } else if (apiStatus === 'NOT_EXIST') {
        // This email is not registered as an Admin -> disallow sign-in
        setEmailStatus('not_registered');
        setEmailCheckMessage('This email is not registered as an administrator.');
      } else if (apiStatus === 'INVALID_FORMAT') {
        setEmailStatus('invalid');
        setEmailCheckMessage(result.error || result.message || 'Please enter a valid email address.');
      } else if (!result.success) {
        // If the backend returned an error status (e.g., 403), treat NOT_EXIST specially
        const statusFromData = result.data?.user_status;
        if (statusFromData === 'NOT_EXIST') {
          setEmailStatus('not_registered');
          setEmailCheckMessage(result.message || 'This email is not registered as an administrator.');
        } else {
          setEmailStatus('invalid');
          setEmailCheckMessage(result.error || result.message || 'Error checking email status.');
        }
      } else {
        setEmailStatus('idle');
        setEmailCheckMessage(null);
      }
    } catch (err: any) {
      setEmailStatus('invalid');
      setEmailCheckMessage((err && err.message) ? err.message : 'Error checking email status.');
    }
  }, []);

  const debouncedCheck = useDebounce(checkEmailExistence, 500);

   // (useEffect hooks remain the same)
   useEffect(() => {
    if (!emailCheckMessage) return;
    const t = setTimeout(() => setEmailCheckMessage(null), 7000);
    return () => clearTimeout(t);
  }, [emailCheckMessage]);

  useEffect(() => {
    if (userEmail && userEmail !== previousUserEmailRef.current) {
      previousUserEmailRef.current = userEmail;
      setFormData(prev => ({ ...prev, email: userEmail }));
      if (userEmail.length > 5 && userEmail.includes('@') && userEmail.includes('.')) {
        checkEmailExistence(userEmail);
      }
    }
  }, [userEmail, checkEmailExistence]);


  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;

    if (name === 'email') {
      setFormData(prev => ({ ...prev, [name]: value }));
      if (value.length > 5 && value.includes('@') && value.includes('.')) {
        debouncedCheck(value);
      } else {
        setEmailStatus('idle');
        setEmailCheckMessage(null);
      }
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: type === 'checkbox' ? checked : value
      }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // More lenient validation - allow submission with basic email format validation
    if (!formData.email || loading || emailStatus === 'checking' || emailStatus === 'invalid') {
      return;
    }

    // Block sign-in for unregistered emails
    if (emailStatus === 'not_registered') {
      setEmailCheckMessage('This email is not registered as an administrator. Sign-in is not allowed.');
      return;
    }
    
    setEmailCheckMessage(null);
    
    if (signIn) {
      await signIn(formData.email, formData.rememberMe);
    }
  };

  // (renderStatusIcon, getInputBorderClass, inputClass remain the same)
  const inputClass = `
    w-full h-12 sm:h-[57px] px-4 sm:px-6 py-3 border rounded-[9px]
    font-normal text-sm sm:text-base text-gray-700 placeholder-gray-400 bg-white
    focus:outline-none focus:ring-2 transition-shadow
  `;

  const renderStatusIcon = () => {
    const iconClass = "absolute right-3 sm:right-4 top-1/2 transform -translate-y-1/2";
    switch (emailStatus) {
      case 'checking':
        return <Loader2 size={18} className={`text-blue-500 animate-spin ${iconClass}`} />;
      case 'exists':
        return <CheckCircle className={`text-green-500 ${iconClass} w-5 h-5 sm:w-6 sm:h-6`} />;
      case 'available':
      case 'invalid':
      case 'not_registered':
        return <XCircle size={18} className={`text-red-500 ${iconClass}`} />;
      default:
        return null;
    }
  };

  const getInputBorderClass = () => {
    switch (emailStatus) {
        case 'exists':
            return 'border-green-500 focus:ring-green-500';
        case 'available':
        case 'invalid':
        case 'not_registered':
            return 'border-red-500 focus:ring-red-500';
        default:
            return 'border-[#4285F4] focus:ring-[#4285F4]';
    }
  }

  // 💡 MODIFICATION: More lenient button enabling for better edit experience
  // Allow submission if email format is valid, even if status check hasn't completed or shows 'idle'
  const isValidEmailFormat = formData.email.includes('@') && formData.email.includes('.') && formData.email.length > 5;
  // Disable button when email is not registered (not_allowed to sign in)
  const isButtonDisabled = loading || !formData.email || !isValidEmailFormat || emailStatus === 'checking' || emailStatus === 'invalid' || emailStatus === 'not_registered';

  return (
    <div className="w-full max-w-md mx-auto space-y-4 sm:space-y-5">

      <h2 className="text-xl sm:text-2xl font-semibold text-gray-700" style={{ fontFamily: 'Poppins' }}>
        {AUTH_CONFIG.CONTENT.signInTitle}
      </h2>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="space-y-2">
          <label className="block text-sm sm:text-base font-medium text-gray-900" style={{ fontFamily: 'Poppins' }}>
            Administrator Email
          </label>
          <div className="relative">
            <input
              type="email"
              name="email"
              placeholder={AUTH_CONFIG.CONTENT.emailPlaceholder}
              value={formData.email}
              onChange={handleInputChange}
              required
              className={`${inputClass} ${getInputBorderClass()} ${emailStatus !== 'idle' ? 'pr-10 sm:pr-12' : 'pr-4 sm:pr-6'}`}
              autoComplete="email"
            />
            {renderStatusIcon()}
          </div>
        </div>
        
        {/* ... Remember Me Checkbox ... (no change) */}
        <div className="flex items-center justify-between text-xs text-black h-5">
          <label htmlFor="rememberMe" className="flex items-center cursor-pointer gap-2">
             <span className="relative flex items-center">
               <input
                 type="checkbox"
                 name="rememberMe"
                 id="rememberMe"
                 checked={formData.rememberMe}
                 onChange={handleInputChange}
                 className="appearance-none h-4 w-4 border border-gray-500 rounded-sm bg-white checked:bg-[var(--color-primary-500)] checked:border-transparent focus:ring-1 focus:ring-offset-1 focus:ring-blue-500 transition-colors"
               />
               {formData.rememberMe && (
                 <svg
                   className="absolute left-0 top-0 w-4 h-4 pointer-events-none text-white"
                   viewBox="0 0 16 16"
                   fill="none"
                   stroke="currentColor"
                   strokeWidth="3"
                   strokeLinecap="round"
                   strokeLinejoin="round"
                 >
                   <path d="M4 8l3 3 5-5" />
                 </svg>
               )}
             </span>
             <span className="font-normal text-sm" style={{ fontFamily: 'Poppins' }}>
               {AUTH_CONFIG.CONTENT.rememberMe}
             </span>
          </label>
        </div>


        {(emailCheckMessage || error) && (
          <div
            className={`text-xs sm:text-sm p-3 rounded-lg border font-medium ${emailStatus === 'exists' ? 'text-green-600 bg-green-50 border-green-200' : 'text-red-600 bg-red-50 border-red-200'}`}
            role="alert"
          >
            {error || emailCheckMessage}
          </div>
        )}

        <div className="pt-4 sm:pt-6">
          <button
            type="submit"
            disabled={isButtonDisabled}
            className={`
              w-full h-12 sm:h-14 rounded-xl text-white font-semibold text-base sm:text-lg tracking-wider
              shadow-lg hover:bg-[var(--color-primary-600)] transition-colors duration-200
              disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center
            `}
            style={{
              fontFamily: 'Poppins',
              backgroundColor: 'var(--color-primary-500)',
              boxShadow: '0px 4px 19px rgba(1,107,174,0.3)',
            }}
          >
            {loading ? (
              <div className="flex items-center justify-center space-x-2">
                <Loader2 size={18} className="animate-spin sm:w-5 sm:h-5" />
                <span>Generating OTP...</span>
              </div>
            ) : (
              AUTH_CONFIG.CONTENT.signInButton
            )}
          </button>
        </div>

        {/* 💡 MODIFICATION: Removed the "Register here" link */}
        <div className="text-center pt-2 sm:pt-4">
          <p className="text-xs sm:text-sm text-gray-700" style={{ fontFamily: 'Poppins' }}>
            This login is for authorized administrators only.
          </p>
        </div>

      </form>
    </div>
  );
};

export default SignInForm;