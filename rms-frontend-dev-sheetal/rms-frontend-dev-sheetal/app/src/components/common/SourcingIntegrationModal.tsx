import React, { useState } from 'react';
import { X, Plus, Loader2, Linkedin, Briefcase } from 'lucide-react';
import { useToast } from '../../context/ModalContext';
import { addSourcingPlatform } from '../../api/sourcingApi';
import type { SourcingPlatform } from '../../api/sourcingApi';
import Button from './Button';

interface SourcingIntegrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: () => void;
}

const SourcingIntegrationModal: React.FC<SourcingIntegrationModalProps> = ({ isOpen, onClose, onSave }) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [newPlatform, setNewPlatform] = useState({ platform_name: 'linkedin', api_key: '', client_secret: '' });
  const { showToast } = useToast();

  const handleAddPlatform = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    const platformData: SourcingPlatform = {
        platform_name: newPlatform.platform_name,
        api_key: newPlatform.api_key,
        client_secret: newPlatform.client_secret,
    };

    const result = await addSourcingPlatform(platformData);
    if (result.success) {
        showToast('Sourcing platform added successfully!', 'success');
        onSave();
    } else {
        showToast(result.error || 'Failed to add platform.', 'error');
    }
    setIsSubmitting(false);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setNewPlatform(prev => ({ ...prev, [name]: value }));
  };

  if (!isOpen) return null;

  return (
    <div 
        className="fixed inset-0 z-50 flex items-start justify-center bg-black bg-opacity-40 backdrop-blur-sm transition-opacity overflow-y-auto" 
        aria-modal="true" 
        role="dialog"
        onClick={onClose}
        style={{ paddingTop: '2rem', paddingBottom: '6rem' }}
    >
        <div 
            className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 my-4 transform transition-all animate-in zoom-in-95 ease-out duration-300"
            onClick={e => e.stopPropagation()}
            style={{ maxHeight: 'calc(100vh - 12rem)', overflowY: 'auto' }}
        >
            <div className="p-6 border-b border-gray-200 flex justify-between items-center">
                <h3 className="text-xl font-bold text-gray-800">Add New Integration</h3>
                <button onClick={onClose} className="p-2 rounded-full text-gray-400 hover:bg-gray-100 transition-colors">
                    <X size={20} />
                </button>
            </div>
            <form onSubmit={handleAddPlatform} className="p-6 space-y-4">
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Platform</label>
                    <div className="relative">
                        <select
                            name="platform_name"
                            value={newPlatform.platform_name}
                            onChange={handleInputChange}
                            className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[var(--color-primary-500)] appearance-none pl-10"
                        >
                            <option value="linkedin">LinkedIn</option>
                            <option value="naukri">Naukri</option>
                        </select>
                        <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
                            {newPlatform.platform_name === 'linkedin' 
                                ? <Linkedin size={18} className="text-blue-700" />
                                : <Briefcase size={18} className="text-orange-500" />
                            }
                        </div>
                    </div>
                </div>
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">API Key / Client ID</label>
                    <input
                        type="password"
                        name="api_key"
                        value={newPlatform.api_key}
                        onChange={handleInputChange}
                        placeholder="Enter API Key or Client ID"
                        className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[var(--color-primary-500)]"
                        required
                    />
                </div>
                 <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Client Secret (if applicable)</label>
                    <input
                        type="password"
                        name="client_secret"
                        value={newPlatform.client_secret || ''}
                        onChange={handleInputChange}
                        placeholder="Enter Client Secret"
                        className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[var(--color-primary-500)]"
                    />
                </div>
                <div className="pt-4 flex justify-end gap-3">
                    <Button type="button" variant="secondary" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button type="submit" disabled={isSubmitting}>
                        {isSubmitting ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
                        {isSubmitting ? 'Adding...' : 'Add Integration'}
                    </Button>
                </div>
            </form>
        </div>
    </div>
  );
};

export default SourcingIntegrationModal;
