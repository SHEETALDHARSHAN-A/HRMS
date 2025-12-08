import React, { useRef, useMemo, useEffect } from 'react';

interface OTPInputProps {
  length: number;
  value: string;
  onChange: (value: string) => void;
  disabled: boolean; 
}

const OTPInput: React.FC<OTPInputProps> = ({ length, value, onChange, disabled }) => {
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Calculate the current values for each input box
  const valueItems = useMemo(() => {
    // Defensive: `value` may be undefined during initial renders — coerce to empty string
    const valueArray = (value ?? '').split('');
    const items: Array<string> = [];

    for (let i = 0; i < length; i++) {
      items.push(valueArray[i] || '');
    }
    return items;
  }, [value, length]);

  // Debug: log value changes and internal items to help trace issues where digits
  // don't appear in the UI (useful during development). Remove in production.
  useEffect(() => {
    // eslint-disable-next-line no-console
    console.debug('OTPInput value changed:', { value, valueItems });
  }, [value, valueItems]);

  const focusInput = (index: number) => {
    // Make sure index is within bounds
    const targetIndex = Math.max(0, Math.min(index, length - 1));
    if (inputRefs.current[targetIndex]) {
      inputRefs.current[targetIndex]?.focus();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>, index: number) => {
    const target = e.target;
    let targetValue = target.value;
    
    // Only allow digits
    if (!/^\d*$/.test(targetValue)) {
      return;
    }
    
    // For multi-digit input, distribute across fields
    if (targetValue.length > 1) {
      // Create a new array with all digits
      const digits = targetValue.split('');
      let newValue = [...valueItems];
      
      // Fill in as many fields as we can, starting at the current index
      for (let i = 0; i < digits.length && index + i < length; i++) {
        newValue[index + i] = digits[i];
      }
      
      onChange(newValue.join(''));
      
      // Focus the last field that was filled or the last field if we filled them all
      const lastIndex = Math.min(index + targetValue.length - 1, length - 1);
      focusInput(lastIndex);
      return;
    }
    
    // Single digit case
    const newValue = [...valueItems];
    newValue[index] = targetValue;
    onChange(newValue.join(''));
    
    // Move focus forward if we entered a digit
    if (targetValue && index < length - 1) {
      focusInput(index + 1);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, index: number) => {
    const target = e.target as HTMLInputElement;

    // Prevent paste via keyboard shortcuts (Ctrl+V / Cmd+V)
    if ((e.ctrlKey || e.metaKey) && (e.key === 'v' || e.key === 'V')) {
      e.preventDefault();
      return;
    }
    
    // Handle backspace
    if (e.key === 'Backspace') {
      if (target.value === '' && index > 0) {
        e.preventDefault();
        focusInput(index - 1);
        // Update the value to remove the previous digit
        const newValue = [...valueItems];
        newValue[index - 1] = '';
        onChange(newValue.join(''));
      }
      // If current field has content, let default behavior happen (clear it)
    } 
    // Handle arrow navigation
    else if (e.key === 'ArrowRight' && index < length - 1) {
      e.preventDefault();
      focusInput(index + 1);
    } else if (e.key === 'ArrowLeft' && index > 0) {
      e.preventDefault();
      focusInput(index - 1);
    }
    // Handle Delete key
    else if (e.key === 'Delete') {
      if (target.value !== '') {
        // Clear the current field
        const newValue = [...valueItems];
        newValue[index] = '';
        onChange(newValue.join(''));
      } else if (index < length - 1) {
        // If current field is empty and not the last one, clear the next field
        const newValue = [...valueItems];
        newValue[index + 1] = '';
        onChange(newValue.join(''));
      }
    }
  };
  
  const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
    // Select the content when focused
    e.target.select();
  };
  
  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    // Disallow paste into OTP inputs
    e.preventDefault();
    return;
  };
  
  return (
    <div className="flex justify-between space-x-2 md:space-x-3">
      {valueItems.map((digit, index) => (
        <input
          key={index}
          type="text"
          value={digit}
          onChange={(e) => handleChange(e, index)}
          onKeyDown={(e) => handleKeyDown(e, index)}
          onFocus={handleFocus}
          onPaste={(e) => handlePaste(e)}
          ref={(el) => { inputRefs.current[index] = el; }}
          disabled={disabled}
          maxLength={1}
          inputMode="numeric"
          autoComplete="off"
          className={`
            w-1/6 aspect-square text-center text-2xl font-bold 
            border-2 rounded-lg transition-all duration-150 outline-none
            ${disabled 
              ? 'bg-gray-100 border-gray-300 text-gray-500 cursor-not-allowed' 
              : 'bg-white border-[#4285F4] focus:border-[#4285F4] focus:ring-2 focus:ring-[#4285F4] focus:outline-none'}
          `}
          style={!disabled ? { 
            borderColor: '#4285F4',
            // Ensure the focus outline color matches the border color
            ['--tw-ring-color' as any]: '#4285F4'
          } as React.CSSProperties : {}}
        />
      ))}
    </div>
  );
};

export default OTPInput;