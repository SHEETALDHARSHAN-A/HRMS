import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

const Input: React.FC<InputProps> = ({ 
  label,
  className = "",
  ...props 
}) => {
  return (
    <div>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-2 pointer-events-none">
          {label}
        </label>
      )}
      <input
        className={`
          w-full px-4 py-3 border border-gray-300 rounded-lg 
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
          placeholder-gray-400 text-gray-700 bg-gray-50
          pointer-events-auto cursor-text z-10 relative
          ${className}
        `}
        {...props}
      />
    </div>
  );
};

export default Input;
// Also provide a named export for compatibility with named imports
// (some files or legacy imports may use `import { Input } from ...`).
export { Input };