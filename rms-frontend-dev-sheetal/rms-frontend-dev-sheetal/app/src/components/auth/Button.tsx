import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary';
}

const Button: React.FC<ButtonProps> = ({ 
  children,
  variant = 'primary',
  disabled = false,
  className = "",
  ...props 
}) => {
  const baseStyles = `
    w-full py-3 px-6 rounded-md font-semibold transition-colors duration-200 
    focus:outline-none focus:ring-2 focus:ring-offset-2
    pointer-events-auto cursor-pointer z-10 relative
  `;
  
  const variants = {
    primary: 'bg-blue-600 hover:bg-blue-700 text-white focus:ring-blue-500',
    secondary: 'bg-gray-200 hover:bg-gray-300 text-gray-800 focus:ring-gray-500'
  };

  const disabledStyles = disabled ? 'opacity-50 cursor-not-allowed' : '';

  return (
    <button
      disabled={disabled}
      className={`${baseStyles} ${variants[variant]} ${disabledStyles} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};

export default Button;