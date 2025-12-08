import React, { createContext, useContext, useState, useCallback} from 'react';
import type { ReactNode } from 'react';
import Toast from "../components/common/Toast";

interface ToastContextType {
  showToast: (message: string, type: 'success' | 'error' | 'info') => void;
  // Backwards-compatible alias used by some components
  addToast?: (message: string, type?: 'success' | 'error' | 'info') => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

interface ToastMessage {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
}

export const ToastProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const showToast = useCallback((message: string, type: 'success' | 'error' | 'info') => {
    const id = Date.now().toString();
    setToasts((prevToasts) => [...prevToasts, { id, message, type }]);
    setTimeout(() => {
      setToasts((prevToasts) => prevToasts.filter((toast) => toast.id !== id));
    }, 5000);
  }, []);

  // expose both `showToast` and an `addToast` alias for backwards compatibility
  const providerValue: ToastContextType = {
    showToast,
    addToast: (message: string, type: 'success' | 'error' | 'info' = 'info') => showToast(message, type),
  };

  return (
    <ToastContext.Provider value={providerValue}>
      {children}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map((toast) => (
          <Toast key={toast.id} message={toast.message} type={toast.type} />
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
};