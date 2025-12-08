// import React, { useState, useEffect, useCallback } from 'react';
// import { Linkedin, Briefcase, Key, Trash2, Plus, Loader2, Clipboard, Check } from 'lucide-react';
// import { useToast } from '../../context/ModalContext';
// import { addSourcingPlatform, getSourcingPlatforms, deleteSourcingPlatform } from '../../api/sourcingApi';
// import type { SourcingPlatform } from '../../api/sourcingApi';
// import Button from '../../components/common/Button';

// const platformIcons: { [key: string]: React.ReactNode } = {
//     linkedin: <Linkedin size={24} className="text-blue-700" />,
//     naukri: <Briefcase size={24} className="text-orange-500" />,
// };

// const ExternalSourcing: React.FC = () => {
//     const [platforms, setPlatforms] = useState<SourcingPlatform[]>([]);
//     const [isLoading, setIsLoading] = useState(true);
//     const [isSubmitting, setIsSubmitting] = useState(false);
//     const [newPlatform, setNewPlatform] = useState({ platform_name: 'linkedin', api_key: '', client_secret: '' });
//     const { showToast } = useToast();
//     const [copiedUrl, setCopiedUrl] = useState<string | null>(null);

//     const fetchPlatforms = useCallback(async () => {
//         setIsLoading(true);
//         const result = await getSourcingPlatforms();
//         if (result.success) {
//             setPlatforms(result.data.data);
//         } else {
//             showToast(result.error || 'Failed to fetch sourcing platforms.', 'error');
//         }
//         setIsLoading(false);
//     }, [showToast]);

//     useEffect(() => {
//         fetchPlatforms();
//     }, [fetchPlatforms]);
    
//     const handleCopy = (url: string) => {
//         navigator.clipboard.writeText(url);
//         setCopiedUrl(url);
//         showToast("Webhook URL copied to clipboard!", "success");
//         setTimeout(() => setCopiedUrl(null), 2000);
//     };


//     const handleAddPlatform = async (e: React.FormEvent) => {
//         e.preventDefault();
//         setIsSubmitting(true);
        
//         const platformData: SourcingPlatform = {
//             platform_name: newPlatform.platform_name,
//             api_key: newPlatform.api_key,
//             client_secret: newPlatform.client_secret,
//         };

//         const result = await addSourcingPlatform(platformData);
//         if (result.success) {
//             showToast('Sourcing platform added successfully!', 'success');
//             fetchPlatforms(); // Refresh the list
//             setNewPlatform({ platform_name: 'linkedin', api_key: '', client_secret: '' });
//         } else {
//             showToast(result.error || 'Failed to add platform.', 'error');
//         }
//         setIsSubmitting(false);
//     };
    
//     const handleDeletePlatform = async (platform: SourcingPlatform) => {
//         if (!platform.id) return;
        
//         const confirmDelete = window.confirm(`Are you sure you want to remove the integration for ${platform.platform_name}?`);
//         if (!confirmDelete) return;

//         const result = await deleteSourcingPlatform(platform.id);
//         if (result.success) {
//             showToast('Platform integration removed.', 'success');
//             fetchPlatforms();
//         } else {
//             showToast(result.error || 'Failed to remove integration.', 'error');
//         }
//     };


//     const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
//         const { name, value } = e.target;
//         setNewPlatform(prev => ({ ...prev, [name]: value }));
//     };

//     return (
//         <div className="grid grid-cols-1 md:grid-cols-3 gap-8 p-4">
//             {/* Left Column: Add New Integration */}
//             <div className="md:col-span-1 bg-white p-6 rounded-xl shadow-lg border border-gray-200">
//                 <h3 className="text-xl font-bold text-gray-800 mb-4">Add New Integration</h3>
//                 <form onSubmit={handleAddPlatform} className="space-y-4">
//                     <div>
//                         <label className="block text-sm font-medium text-gray-700 mb-1">Platform</label>
//                         <select
//                             name="platform_name"
//                             value={newPlatform.platform_name}
//                             onChange={handleInputChange}
//                             className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[var(--color-primary-500)]"
//                         >
//                             <option value="linkedin">LinkedIn</option>
//                             <option value="naukri">Naukri</option>
//                         </select>
//                     </div>
//                     <div>
//                         <label className="block text-sm font-medium text-gray-700 mb-1">API Key / Client ID</label>
//                         <input
//                             type="password"
//                             name="api_key"
//                             value={newPlatform.api_key}
//                             onChange={handleInputChange}
//                             placeholder="Enter API Key or Client ID"
//                             className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[var(--color-primary-500)]"
//                             required
//                         />
//                     </div>
//                      <div>
//                         <label className="block text-sm font-medium text-gray-700 mb-1">Client Secret (if applicable)</label>
//                         <input
//                             type="password"
//                             name="client_secret"
//                             value={newPlatform.client_secret || ''}
//                             onChange={handleInputChange}
//                             placeholder="Enter Client Secret"
//                             className="w-full bg-gray-50 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-[var(--color-primary-500)]"
//                         />
//                     </div>
//                     <div className="pt-2">
//                         <Button type="submit" disabled={isSubmitting} className="w-full py-2.5">
//                             {isSubmitting ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
//                             {isSubmitting ? 'Adding...' : 'Add Integration'}
//                         </Button>
//                     </div>
//                 </form>
//             </div>

//             {/* Right Column: Existing Integrations */}
//             <div className="md:col-span-2 bg-white p-6 rounded-xl shadow-lg border border-gray-200">
//                 <h3 className="text-xl font-bold text-gray-800 mb-4">Active Integrations</h3>
//                 {isLoading ? (
//                     <div className="flex justify-center items-center h-40">
//                         <Loader2 size={32} className="animate-spin text-[var(--color-primary-500)]" />
//                     </div>
//                 ) : platforms.length === 0 ? (
//                     <p className="text-center text-gray-500 py-10">No external sourcing platforms configured yet.</p>
//                 ) : (
//                     <div className="space-y-4">
//                         {platforms.map(platform => (
//                             <div key={platform.id} className="p-4 rounded-lg border border-gray-200 bg-gray-50 flex items-start justify-between">
//                                 <div className="flex items-start gap-4">
//                                     <div className="flex-shrink-0 w-10 h-10 bg-white rounded-lg flex items-center justify-center border">
//                                         {platformIcons[platform.platform_name.toLowerCase()] || <Key size={24} className="text-gray-500" />}
//                                     </div>
//                                     <div>
//                                         <h4 className="font-bold text-gray-800 capitalize">{platform.platform_name}</h4>
//                                         <p className="text-xs text-gray-500 mt-1">API Key: ••••••••{platform.api_key.slice(-4)}</p>
//                                         {platform.webhook_url && (
//                                             <div className="mt-2 flex items-center gap-2">
//                                                 <input type="text" readOnly value={platform.webhook_url} className="text-xs bg-white border border-gray-300 rounded-md px-2 py-1 w-full sm:w-80" />
//                                                 <Button variant="ghost" size="sm" onClick={() => handleCopy(platform.webhook_url!)} className="p-2 h-auto">
//                                                     {copiedUrl === platform.webhook_url ? <Check size={16} className="text-green-500" /> : <Clipboard size={16} />}
//                                                 </Button>
//                                             </div>
//                                         )}
//                                     </div>
//                                 </div>
//                                 <Button variant="ghost" size="sm" className="p-2 text-red-500 hover:bg-red-50 h-auto" onClick={() => handleDeletePlatform(platform)}>
//                                     <Trash2 size={16} />
//                                 </Button>
//                             </div>
//                         ))}
//                     </div>
//                 )}
//             </div>
//         </div>
//     );
// };

// export default ExternalSourcing;



import React, { useState, useEffect, useCallback } from 'react';
import { Linkedin, Briefcase, Key, Trash2, Plus, Loader2, Clipboard, Check, Settings } from 'lucide-react';
import { useToast } from '../../context/ModalContext';
import { getSourcingPlatforms, deleteSourcingPlatform } from '../../api/sourcingApi';
import type { SourcingPlatform } from '../../api/sourcingApi';
import Button from '../../components/common/Button';
import SourcingIntegrationModal from '../../components/common/SourcingIntegrationModal';

const platformIcons: { [key: string]: React.ReactNode } = {
    linkedin: <Linkedin size={24} className="text-blue-700" />,
    naukri: <Briefcase size={24} className="text-orange-500" />,
};

const ExternalSourcing: React.FC = () => {
    const [platforms, setPlatforms] = useState<SourcingPlatform[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const { showToast } = useToast();
    const [copiedUrl, setCopiedUrl] = useState<string | null>(null);

    const fetchPlatforms = useCallback(async () => {
        setIsLoading(true);
        const result = await getSourcingPlatforms();
        if (result.success) {
            setPlatforms(result.data.data);
        } else {
            showToast(result.error || 'Failed to fetch sourcing platforms.', 'error');
        }
        setIsLoading(false);
    }, [showToast]);

    useEffect(() => {
        fetchPlatforms();
    }, [fetchPlatforms]);
    
    const handleCopy = (url: string) => {
        navigator.clipboard.writeText(url);
        setCopiedUrl(url);
        showToast("Webhook URL copied to clipboard!", "success");
        setTimeout(() => setCopiedUrl(null), 2000);
    };

    const handleDeletePlatform = async (platform: SourcingPlatform) => {
        if (!platform.id) return;
        
        const confirmDelete = window.confirm(`Are you sure you want to remove the integration for ${platform.platform_name}?`);
        if (!confirmDelete) return;

        const result = await deleteSourcingPlatform(platform.id);
        if (result.success) {
            showToast('Platform integration removed.', 'success');
            fetchPlatforms();
        } else {
            showToast(result.error || 'Failed to remove integration.', 'error');
        }
    };

    const handleSavePlatform = () => {
        fetchPlatforms();
        setIsModalOpen(false);
    }

    return (
        <div className="p-4 sm:p-6">
             {isModalOpen && (
                <SourcingIntegrationModal
                    isOpen={isModalOpen}
                    onClose={() => setIsModalOpen(false)}
                    onSave={handleSavePlatform}
                />
            )}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-2xl font-bold text-gray-800">Sourcing Integrations</h2>
                    <p className="text-sm text-gray-500 mt-1">Connect and manage your external candidate sources.</p>
                </div>
                <Button onClick={() => setIsModalOpen(true)}>
                    <Plus size={16} />
                    Add Integration
                </Button>
            </div>
            
            {isLoading ? (
                <div className="flex justify-center items-center h-64">
                    <Loader2 size={32} className="animate-spin text-[var(--color-primary-500)]" />
                </div>
            ) : platforms.length === 0 ? (
                 <div className="text-center py-20 border-2 border-dashed border-gray-300 rounded-xl bg-gray-50">
                    <Settings size={48} className="mx-auto text-gray-400" />
                    <h3 className="mt-4 text-lg font-semibold text-gray-700">No Integrations Configured</h3>
                    <p className="mt-1 text-sm text-gray-500">Click "Add Integration" to connect your first platform.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {platforms.map(platform => (
                        <div key={platform.id} className="p-5 rounded-xl border border-gray-200 bg-white shadow-sm flex flex-col justify-between">
                            <div>
                                <div className="flex items-center justify-between mb-4">
                                     <div className="flex items-center gap-3">
                                        <div className="flex-shrink-0 w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center border">
                                            {platformIcons[platform.platform_name.toLowerCase()] || <Key size={24} className="text-gray-500" />}
                                        </div>
                                        <h4 className="font-bold text-lg text-gray-800 capitalize">{platform.platform_name}</h4>
                                    </div>
                                    <Button variant="ghost" className="p-2 text-red-500 hover:bg-red-50 h-auto" onClick={() => handleDeletePlatform(platform)}>
                                        <Trash2 size={16} />
                                    </Button>
                                </div>
                               
                                <p className="text-xs text-gray-500 mt-1">API Key: ••••••••{platform.api_key.slice(-4)}</p>
                                
                                {platform.webhook_url && (
                                    <div className="mt-4">
                                        <label className="text-xs font-semibold text-gray-600 mb-1 block">Webhook URL</label>
                                        <div className="flex items-center gap-2">
                                            <input type="text" readOnly value={platform.webhook_url} className="text-xs bg-gray-100 border border-gray-300 rounded-md px-2 py-1.5 w-full" />
                                            <Button variant="ghost" onClick={() => handleCopy(platform.webhook_url!)} className="p-2 h-auto">
                                                {copiedUrl === platform.webhook_url ? <Check size={16} className="text-green-500" /> : <Clipboard size={16} />}
                                            </Button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default ExternalSourcing;

