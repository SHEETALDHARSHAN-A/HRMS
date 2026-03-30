import React, { createContext, useContext, useState, useCallback, useMemo } from 'react';
import type { ReactNode } from 'react';
import Toast from "../components/common/Toast";
import ConfirmModal from '../components/common/ConfirmModal';

// --- Toast Types ---
type ToastType = 'success' | 'error' | 'info' | 'warning';
interface ToastMessage {
  id: string;
  message: string;
  type: ToastType;
}

// --- Modal Types ---
interface ConfirmOptions {
    title: string;
    message: string;
    confirmText?: string;
    cancelText?: string;
    isDestructive?: boolean;
    isProcessing?: boolean;
}

interface ModalContextType {
  showToast: (message: string, type: ToastType) => void;
  showConfirm: (options: ConfirmOptions) => Promise<boolean>;
  setModalProcessing: (isProcessing: boolean) => void;
}

const ModalContext = createContext<ModalContextType | undefined>(undefined);

export const ModalProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [modalState, setModalState] = useState<{
    isOpen: boolean;
    options: ConfirmOptions | null;
    resolver: ((value: boolean) => void) | null;
    isProcessing: boolean;
  }>({
    isOpen: false,
    options: null,
    resolver: null,
    isProcessing: false,
  });

  // --- Toast Logic ---
  const showToast = useCallback((message: string, type: ToastType) => {
    const id = Date.now().toString();
    setToasts((prevToasts) => [...prevToasts, { id, message, type }]);
    setTimeout(() => {
      setToasts((prevToasts) => prevToasts.filter((toast) => toast.id !== id));
    }, 5000);
  }, []);

  // --- Modal Logic ---
  const showConfirm = useCallback((options: ConfirmOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      setModalState({
        isOpen: true,
        options,
        resolver: resolve,
        isProcessing: false,
      });
    });
  }, []);
  
  const closeModal = useCallback((confirmed: boolean) => {
    if (modalState.resolver) {
      modalState.resolver(confirmed);
    }
    setModalState(prev => ({
      ...prev,
      isOpen: false,
      options: null,
      resolver: null,
      isProcessing: false,
    }));
  }, [modalState.resolver]);

  const setModalProcessing = useCallback((isProcessing: boolean) => {
    setModalState(prev => ({ ...prev, isProcessing }));
  }, []);

  const contextValue = useMemo(() => ({
    showToast,
    showConfirm,
    setModalProcessing,
  }), [showToast, showConfirm, setModalProcessing]);

  return (
    <ModalContext.Provider value={contextValue}>
      {children}
      
      {/* Toast Render Area */}
      <div className="fixed top-4 right-4 z-50 space-y-2">
        {toasts.map((toast) => (
          <Toast key={toast.id} message={toast.message} type={toast.type} />
        ))}
      </div>

      {/* Confirm Modal Render Area */}
      {modalState.options && (
        <ConfirmModal
          isOpen={modalState.isOpen}
          onClose={() => closeModal(false)}
          onConfirm={() => closeModal(true)}
          title={modalState.options.title}
          message={modalState.options.message}
          confirmText={modalState.options.confirmText}
          cancelText={modalState.options.cancelText}
          isDestructive={modalState.options.isDestructive}
          isProcessing={modalState.isProcessing}
        />
      )}
    </ModalContext.Provider>
  );
};

export const useModal = () => {
  const context = useContext(ModalContext);
  if (!context) {
    throw new Error('useModal must be used within a ModalProvider');
  }
  return context;
};

// For compatibility, keep useToast hook referencing useModal
export const useToast = () => {
    const { showToast } = useModal();
    return { showToast };
}