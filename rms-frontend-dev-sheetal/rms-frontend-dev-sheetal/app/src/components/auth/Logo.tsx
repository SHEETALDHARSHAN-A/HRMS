// rms-frontend-dev-sheetal/app/src/components/auth/Logo.tsx
import React from 'react';

interface LogoProps {
  className?: string;
  size?: 'small' | 'medium' | 'large';
}

const Logo: React.FC<LogoProps> = ({ className = '', size = 'medium' }) => {
  const sizeClasses = {
    small: 'h-10 w-auto',
    medium: 'h-14 w-auto', 
    large: 'h-[60.52px] w-[198.53px]' 
  };

  return (
    <div className={`flex items-center relative ${className}`}> 
      <img 
        src="/logo.svg" 
        alt="PRAYAG.AI" 
        className={`${sizeClasses[size]} object-contain`}
      />
    </div>
  );
};

export default Logo;