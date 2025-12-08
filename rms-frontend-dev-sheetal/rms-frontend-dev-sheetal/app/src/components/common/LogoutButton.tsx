import React from 'react';
import { LogOut } from 'lucide-react';
import useLogout from '../../hooks/useLogout';
import clsx from "clsx"; 

interface LogoutButtonProps {
  variant?: 'primary' | 'secondary' | 'icon';
  className?: string;
}

const LogoutButton: React.FC<LogoutButtonProps> = ({ 
  variant = 'secondary', 
  className = '' 
}) => {
  const { logout, loading } = useLogout();

  const handleLogout = async () => {
    if (window.confirm('Are you sure you want to logout?')) {
      await logout();
    }
  };

  const baseClasses = "flex items-center gap-2 px-4 py-2 rounded-md font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
  
  const variantClasses = {
    primary: "bg-red-600 text-white hover:bg-red-700 justify-center",
    secondary: "bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300 justify-center",
    icon: "p-2 bg-gray-100 text-gray-700 hover:bg-gray-200 rounded-full w-fit h-fit"
  };

  return (
    <button
      onClick={handleLogout}
      disabled={loading}
      className={clsx(baseClasses, variantClasses[variant], className)}
      aria-label={variant === 'icon' ? 'Logout' : undefined}
    >
      <LogOut size={variant === 'icon' ? 18 : 16} />
      {variant !== 'icon' && (
        <span>{loading ? 'Logging out...' : 'Logout'}</span>
      )}
    </button>
  );
};

export default LogoutButton;