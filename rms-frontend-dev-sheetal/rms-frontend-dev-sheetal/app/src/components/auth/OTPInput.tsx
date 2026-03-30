import React, { useRef, useMemo } from 'react';

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
            aspect-square w-1/6 rounded-md border text-center text-lg font-semibold shadow-xs
            transition-all duration-150 outline-none
            ${disabled 
              ? 'cursor-not-allowed border-input bg-muted text-muted-foreground'
              : 'border-input bg-background focus:border-ring focus:ring-3 focus:ring-ring/30'}
          `}
        />
      ))}
    </div>
  );
};

export default OTPInput;