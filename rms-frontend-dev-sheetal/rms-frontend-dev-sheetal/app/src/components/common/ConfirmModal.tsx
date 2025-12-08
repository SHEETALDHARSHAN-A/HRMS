import React from 'react';
import { AlertTriangle, X, Loader2 } from 'lucide-react';
import Button from './Button';
import clsx from 'clsx';

interface ConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  isDestructive?: boolean;
  isProcessing?: boolean;
}

const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  isDestructive = false,
  isProcessing = false,
}) => {
  if (!isOpen) return null;

  const handleConfirm = () => {
    if (!isProcessing) {
      onConfirm();
    }
  };
  
  const destructiveConfirmClass = 'bg-red-600 hover:bg-red-700 text-white';
  const defaultConfirmClass = 'bg-[var(--color-primary-500)] hover:bg-[var(--color-primary-600)] text-white';
  
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-transparent bg-opacity-50 backdrop-blur-sm transition-opacity overflow-y-auto" aria-modal="true" role="dialog" style={{ paddingTop: '2rem', paddingBottom: '6rem' }}>
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 my-4 transform transition-all animate-in zoom-in-95 ease-out duration-300" style={{ maxHeight: 'calc(100vh - 12rem)', overflowY: 'auto' }}>
        
        {/* Header */}
        <div className="p-6 border-b border-gray-100 flex justify-between items-center">
          <div className={clsx("flex items-center gap-3", isDestructive ? 'text-red-600' : 'text-yellow-600')}>
            <AlertTriangle size={24} />
            <h3 className="text-xl font-bold text-gray-900">{title}</h3>
          </div>
          <button onClick={onClose} className="p-2 rounded-full text-gray-400 hover:bg-gray-100 transition-colors">
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="p-6">
          <p className="text-sm text-gray-600">{message}</p>
        </div>

        {/* Actions */}
        <div className="p-6 pt-0 flex justify-end gap-3">
          <Button
            onClick={onClose}
            variant="secondary"
            className="px-5 py-2"
            disabled={isProcessing}
          >
            {cancelText}
          </Button>
          <Button
            onClick={handleConfirm}
            className={clsx("px-5 py-2", isDestructive ? destructiveConfirmClass : defaultConfirmClass)}
            disabled={isProcessing}
          >
            {isProcessing ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              confirmText
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};

const LogoutModal: React.FC<{ isOpen: boolean; onClose: () => void; onConfirm: () => void }> = ({
  isOpen,
  onClose,
  onConfirm,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black bg-opacity-30 backdrop-blur-md overflow-y-auto" style={{ paddingTop: '2rem', paddingBottom: '6rem' }}>
      <div className="bg-white rounded-xl shadow-md w-72 p-5" style={{ margin: '1rem', maxHeight: 'calc(100vh - 12rem)', overflowY: 'auto' }}>
        <h3 className="text-lg font-semibold text-gray-800">Confirm Logout</h3>
        <p className="text-sm text-gray-500 mt-2">Are you sure you want to log out?</p>
        <div className="flex justify-end gap-3 mt-4">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-gray-600 bg-gray-200 rounded-md hover:bg-gray-300"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 text-sm text-white bg-red-500 rounded-md hover:bg-red-600"
          >
            Logout
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmModal;
export { LogoutModal };