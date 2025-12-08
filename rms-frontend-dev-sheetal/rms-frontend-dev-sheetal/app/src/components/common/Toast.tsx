import type { FC } from "react";
import clsx from "clsx";

interface ToastProps {
  message: string;
  type: 'success' | 'error' | 'info';
}

const Toast: FC<ToastProps> = ({ message, type }) => {
  const baseStyles = "px-4 py-2 rounded-md shadow-lg text-sm font-medium text-white flex items-center gap-2 transition-transform duration-300 transform translate-x-0";

  const variants = {
    success: "bg-green-600",
    error: "bg-red-600",
    info: "bg-blue-600",
  };

  const Icon = () => {
    switch (type) {
      case "success":
        return <span role="img" aria-label="success">✅</span>;
      case "error":
        return <span role="img" aria-label="error">❌</span>;
      case "info":
        return <span role="img" aria-label="info">ℹ️</span>;
      default:
        return null;
    }
  };

  return (
    <div className={clsx(baseStyles, variants[type])}>
      <Icon />
      <span>{message}</span>
    </div>
  );
};

export default Toast;