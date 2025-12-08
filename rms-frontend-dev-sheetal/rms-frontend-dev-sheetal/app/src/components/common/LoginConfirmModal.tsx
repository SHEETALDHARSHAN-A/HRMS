import React from 'react';
import { X, AlertTriangle, Loader2 } from 'lucide-react';
import Button from './Button';
import clsx from 'clsx';

interface LoginConfirmModalProps {
  isOpen: boolean;
  message?: string;
  onClose: () => void;
  onConfirm: () => void;
  isProcessing?: boolean;
}

const LoginConfirmModal: React.FC<LoginConfirmModalProps> = ({
  isOpen,
  message = 'Your session is no longer valid. For your security, please sign in again.',
  onClose,
  onConfirm,
  isProcessing = false,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-xl" aria-modal="true" role="dialog">
      <div className="absolute inset-0 bg-gradient-to-b from-black/30 to-black/40 pointer-events-none" />

      <div className="relative w-full max-w-lg mx-4">
        <div className="bg-white/6 backdrop-blur-lg border border-white/10 rounded-2xl shadow-2xl overflow-hidden transform transition-all duration-300 scale-100">
          <div className="flex items-center gap-4 p-6 border-b border-white/8">
            <div className="flex items-center justify-center h-12 w-12 rounded-lg bg-yellow-600/10 text-yellow-500">
              <AlertTriangle size={22} />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-white">Session expired</h3>
              <p className="text-sm text-white/80 mt-1">{message}</p>
            </div>
            <button onClick={onClose} className="ml-3 inline-flex items-center justify-center h-9 w-9 rounded-full bg-white/6 text-white/70 hover:bg-white/12 transition">
              <X size={18} />
            </button>
          </div>

          <div className="p-6">
            <p className="text-sm text-white/80">For your security, please sign in again to continue using the application. You will be redirected to the login page.</p>
          </div>

          <div className="p-6 pt-0 flex flex-col sm:flex-row-reverse gap-3">
            <Button onClick={onConfirm} className={clsx('w-full sm:w-auto px-5 py-3 bg-[var(--color-primary-500)] hover:bg-[var(--color-primary-600)] text-white rounded-lg shadow-md')} disabled={isProcessing}>
              {isProcessing ? <Loader2 size={16} className="animate-spin" /> : 'Sign in again'}
            </Button>
            <Button onClick={onClose} variant="secondary" className="w-full sm:w-auto px-5 py-3 bg-white/6 text-white/80 border border-white/8 rounded-lg" disabled={isProcessing}>
              Dismiss
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginConfirmModal;
