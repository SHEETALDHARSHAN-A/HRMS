// src/pages/Configuration/EmailTemplateManagementTab.tsx

import React, { useState, useEffect } from 'react';
import { useToast, useModal } from '../../context/ModalContext';
import { getTemplate, previewTemplate, updateTemplate, resetTemplate } from '../../api/configApi';
import type { 
    EmailTemplateResponseData, 
    EmailTemplatePreviewRequest, 
    EmailTemplateUpdateRequest
} from '../../types/config';
import { 
    DEFAULT_EMAIL_TEMPLATES, 
    TEMPLATE_PLACEHOLDERS, 
    CONFIGURABLE_TEMPLATES 
} from '../../utils/emailDefaultTemplates'; 
import { Loader2, Mail, Check, Eye, Save, Code, Info, ChevronLeft } from 'lucide-react';
import clsx from 'clsx';
import Button from '../../components/common/Button';

// Props interface to accept the onBack function
interface EmailTemplateManagementTabProps {
  onBack: () => void;
}

const EmailTemplateManagementTab: React.FC<EmailTemplateManagementTabProps> = ({ onBack }) => {
    const { showToast } = useToast();
    const { showConfirm, setModalProcessing } = useModal();

    // UI State
    const [activeTemplateKey, setActiveTemplateKey] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [isPreviewing, setIsPreviewing] = useState(false);
    const [activeEditorView, setActiveEditorView] = useState<'edit' | 'preview'>('edit');

    // Data State
    const [subject, setSubject] = useState('');
    const [body, setBody] = useState('');
    const [previewHtml, setPreviewHtml] = useState('');
    const [previewSubject, setPreviewSubject] = useState('');
    const [placeholders, setPlaceholders] = useState<{ key: string, description: string }[]>([]);
    
    // Reset state when active key is cleared
    useEffect(() => {
        if (!activeTemplateKey) {
            setSubject('');
            setBody('');
            setPreviewHtml('');
            setPreviewSubject('');
            setActiveEditorView('edit');
            setPlaceholders([]);
        }
    }, [activeTemplateKey]);

    // API Handlers

    const handleSelectTemplate = async (key: string) => {
        if (key === activeTemplateKey && !isLoading) return; // Don't re-fetch

        setIsLoading(true);
        setActiveTemplateKey(key);
        setPreviewHtml('');
        setActiveEditorView('edit');
        setPlaceholders(TEMPLATE_PLACEHOLDERS.get(key) || []);
        
        try {
            // 1. Try to get the template saved in the DB
            const data: EmailTemplateResponseData = await getTemplate(key);
            setSubject(data.subject_template);
            setBody(data.body_template_html);
            showToast(`Loaded saved template: ${key}`, 'success');

        } catch (error: any) {
            // 2. If it fails (e.g., 404), load the hardcoded default
            const fallback = DEFAULT_EMAIL_TEMPLATES.get(key);
            if (fallback) {
                setSubject(fallback.subject);
                setBody(fallback.body);
                showToast(`No custom template found. Loaded default for: ${key}`, 'info');
            } else {
                showToast(`Error: No default template found for key: ${key}`, 'error');
                setActiveTemplateKey(null);
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleSaveTemplate = async () => {
        if (!activeTemplateKey) return;

        setIsSaving(true);
        try {
            const payload: EmailTemplateUpdateRequest = {
                template_key: activeTemplateKey,
                subject_template: subject,
                body_template_html: body,
            };
            await updateTemplate(payload);
            showToast('Template saved successfully!', 'success');
        } catch (error: any) {
            console.error('Failed to save template:', error);
            showToast(`Error saving template: ${error.message || 'Server error'}`, 'error');
        } finally {
            setIsSaving(false);
        }
    };

    const handleResetTemplate = async () => {
        if (!activeTemplateKey) return;

        const confirmed = await showConfirm({
            title: `Reset template '${activeTemplateKey}' to default?`,
            message: 'This action will overwrite the current saved template with the server-side default. This cannot be undone.',
            confirmText: 'Reset',
            cancelText: 'Cancel',
            isDestructive: true,
        });
        if (!confirmed) return;

        setModalProcessing(true);
        setIsSaving(true);
        try {
            await resetTemplate(activeTemplateKey);
            // Refresh the currently selected template from backend
            await handleSelectTemplate(activeTemplateKey);
            showToast('Template reset to server default.', 'success');
        } catch (error: any) {
            console.error('Failed to reset template:', error);
            showToast(`Error resetting template: ${error.message || 'Server error'}`, 'error');
        } finally {
            setIsSaving(false);
            setModalProcessing(false);
        }
    };

    const handlePreviewTemplate = async () => {
        if (!activeTemplateKey) return;

        setIsPreviewing(true);
    setPreviewSubject('');
        // Client-side quick sanity check: detect mismatched handlebars-style braces
        const countOccurrences = (s: string, sub: string) => (s.match(new RegExp(sub.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&'), 'g')) || []).length;
        const openBraces = countOccurrences(body, '{{');
        const closeBraces = countOccurrences(body, '}}');
        if (openBraces !== closeBraces) {
            // Show the same styled error used for backend empty responses
            setPreviewHtml("<div style='font-family: Arial, sans-serif; padding: 20px; color: #dc2626; background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px;'><strong>Preview Error:</strong><p>The backend returned an empty response. This often means there is a syntax error in your template (like a mismatched `{{` or `}}`) that the server could not render.</p><p>Please check your template and try again.</p></div>");
            setActiveEditorView('preview');
            setIsPreviewing(false);
            return;
        }
        try {
            const payload: EmailTemplatePreviewRequest = {
                template_subject: subject,
                template_body: body,
                // Send mock data for placeholders
                sample_context: Object.fromEntries(
                    (TEMPLATE_PLACEHOLDERS.get(activeTemplateKey) || []).map(p => {
                        // key is the placeholder key (e.g., "ADMIN_NAME")
                        return [p.key, `[Sample ${p.key}]`]; // e.g., { "ADMIN_NAME": "[Sample ADMIN_NAME]" }
                    })
                ), 
            };
            
            // --- FIX for preview error ---
                const data: any = await previewTemplate(payload);
            
                // If previewTemplate returned a backend error wrapper, show it.
                if (data && typeof data === 'object' && data.__error) {
                    setPreviewHtml(`<div style='font-family: Arial, sans-serif; padding: 20px; color: #dc2626; background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px;'><strong>Preview Error:</strong><p>${data.__error}</p></div>`);
                } else if (data && data.rendered_html_body) {
                    // SUCCESS: We have HTML, show it.
                    setPreviewHtml(data.rendered_html_body);
                    // If backend provided a rendered subject, show it as well
                    if (data.rendered_subject) setPreviewSubject(data.rendered_subject);
                } else {
                    // FAILURE: Data is null or missing HTML. Show a helpful error in the preview pane.
                    setPreviewHtml("<div style='font-family: Arial, sans-serif; padding: 20px; color: #dc2626; background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px;'><strong>Preview Error:</strong><p>The backend returned an empty response. This often means there is a syntax error in your template (like a mismatched `{{` or `}}`) that the server could not render.</p><p>Please check your template and try again.</p></div>");
                }
            // --- END FIX ---

            setActiveEditorView('preview'); // Switch to preview tab
        } catch (error: any) {
            console.error('Failed to render preview:', error);
            // Catch any other network-level errors
            setPreviewHtml(`<div style='font-family: Arial, sans-serif; padding: 20px; color: #dc2626; background-color: #fef2f2; border: 1px solid #fecaca; border-radius: 8px;'><strong>Preview Error:</strong><p>${error.message || 'An unknown error occurred.'}</p></div>`);
            setActiveEditorView('preview'); // Still switch to preview to show the error
            showToast(`Error rendering preview: ${error.message || 'Server error'}`, 'error');
        } finally {
            setIsPreviewing(false);
        }
    };

    /**
     * Renders the main content area (placeholder, loader, or editor)
     */
    const renderContent = () => {
        if (isLoading) {
            return (
                <div className="flex items-center justify-center h-96">
                    <Loader2 size={32} className="animate-spin text-indigo-600" />
                    <span className="ml-3 text-gray-600">Loading Template...</span>
                </div>
            );
        }

        if (!activeTemplateKey) {
            return (
                <div className="flex items-center justify-center h-96 border-2 border-dashed border-gray-300 rounded-xl bg-gray-50">
                    <div className="text-center">
                        <Mail size={40} className="mx-auto text-gray-400 mb-3" />
                        <p className="text-gray-600 font-medium">Select a template from the list</p>
                        <p className="text-sm text-gray-500">Choose an email to view, edit, and preview its content.</p>
                    </div>
                </div>
            );
        }
        
        // --- This is the main Editor/Preview component ---
        return (
            <div className="border border-gray-200 rounded-xl shadow-md bg-white">
                {/* Header with Edit/Preview Tabs and Actions */}
                <div className="p-4 border-b border-gray-200 bg-gray-50/70 rounded-t-xl flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                    {/* Tabs */}
                    <div className="flex w-full sm:w-auto rounded-lg border-2 p-1 bg-gray-200 border-gray-300">
                        <button
                            type="button"
                            onClick={() => setActiveEditorView('edit')}
                            className={clsx(
                                "flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium transition-all duration-200",
                                activeEditorView === 'edit'
                                    ? 'bg-white text-indigo-700 shadow-sm ring-1 ring-indigo-100'
                                    : 'text-gray-600 hover:text-gray-900'
                            )}
                        >
                            <Code size={16} /> Edit
                        </button>
                        <button
                            type="button"
                            onClick={handlePreviewTemplate}
                            disabled={isPreviewing}
                            className={clsx(
                                "flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-md text-sm font-medium transition-all duration-200",
                                activeEditorView === 'preview'
                                    ? 'bg-white text-indigo-700 shadow-sm ring-1 ring-indigo-100'
                                    : 'text-gray-600 hover:text-gray-900'
                            )}
                        >
                            {isPreviewing ? <Loader2 size={16} className="animate-spin" /> : <Eye size={16} />}
                            Preview
                        </button>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex-shrink-0 flex gap-2 w-full sm:w-auto">
                        <Button 
                            variant="primary" 
                            className="w-full sm:w-auto"
                            onClick={handleSaveTemplate} 
                            disabled={isSaving || isPreviewing || activeEditorView === 'preview'}
                        >
                            {isSaving ? <Loader2 size={16} className="animate-spin mr-2" /> : <Save size={16} className="mr-2" />}
                            Save Template
                        </Button>
                        <Button 
                            variant="outline"
                            className="w-full sm:w-auto"
                            onClick={handleResetTemplate}
                            disabled={!activeTemplateKey || isSaving}
                        >
                            Reset to Default
                        </Button>
                    </div>
                </div>

                {/* Content Area (Edit or Preview) */}
                <div className="p-4 sm:p-6">
                    {activeEditorView === 'edit' ? (
                        <div className="space-y-6">
                            {/* Editor Form */}
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-bold text-gray-700 mb-2">Subject *</label>
                                    <input
                                        type="text"
                                        value={subject}
                                        onChange={(e) => setSubject(e.target.value)}
                                        placeholder="Enter email subject"
                                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:ring-indigo-500 focus:border-indigo-500 transition-shadow"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-gray-700 mb-2">Body (HTML) *</label>
                                    <textarea
                                        rows={18}
                                        value={body}
                                        onChange={(e) => setBody(e.target.value)}
                                        placeholder="Enter email body (HTML is supported)"
                                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-base focus:ring-indigo-500 focus:border-indigo-500 transition-shadow resize-y font-mono text-sm"
                                    />
                                </div>
                            </div>

                            {/* Placeholders Info */}
                            <div className="p-4 bg-indigo-50 rounded-lg border border-indigo-200">
                                <p className="text-sm font-semibold text-indigo-800 mb-3 flex items-center gap-2">
                                    <Info size={16} /> Available Placeholders:
                                </p>
                                <div className="space-y-2">
                                    {placeholders.length > 0 ? (
                                        placeholders.map(p => (
                                            <div key={p.key} className="flex items-center gap-2">
                                                <code className="bg-indigo-100 text-indigo-700 p-1 px-2 rounded text-xs font-medium">{`{{${p.key}}}`}</code>
                                                <span className="text-xs text-gray-600">- {p.description}</span>
                                            </div>
                                        ))
                                    ) : (
                                        <span className="text-xs text-indigo-700">No placeholders defined for this template.</span>
                                    )}
                                </div>
                            </div>
                        </div>
                    ) : (
                        // --- Preview Pane ---
                        <div className="space-y-4">
                            <h3 className="text-lg font-semibold text-gray-800">Rendered Subject:</h3>
                            <p className="p-3 bg-gray-100 border border-gray-200 rounded-md text-gray-900">
                                {isPreviewing ? "Loading subject..." : (previewSubject || "Subject preview not available. It will be rendered live by the backend.")}
                            </p>
                            
                            <h3 className="text-lg font-semibold text-gray-800">Rendered Body Preview:</h3>
                            <div 
                                className="w-full border border-gray-300 rounded-lg overflow-hidden"
                                style={{ minHeight: '500px' }}
                            >
                                <iframe
                                    srcDoc={previewHtml || "<p style='padding: 20px; color: #666;'>Click 'Preview' to render the email content.</p>"}
                                    title="Email Preview"
                                    className="w-full h-full border-0"
                                    style={{ minHeight: '500px' }}
                                    sandbox="allow-same-origin" // Security sandbox
                                />
                            </div>
                        </div>
                    )}
                </div>
            </div>
        );
    };

    return (
        // Wrapper div with Back button for full-screen layout
        <div>
            <div className="flex items-center justify-between mb-6 border-b pb-4">
                <h1 className="text-2xl font-bold text-gray-900">
                    Email Template Configuration
                </h1>
                <Button variant="outline" onClick={onBack} className="flex-shrink-0">
                    <ChevronLeft size={16} className="mr-1" />
                    Back to Settings
                </Button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Column 1: Template Card List */}
                <div className="lg:col-span-1 space-y-3 self-start">
                    <h2 className="text-lg font-semibold text-gray-800 border-b pb-2 mb-4">Template List</h2>
                    {CONFIGURABLE_TEMPLATES.map((template) => (
                        <button
                            key={template.key}
                            onClick={() => handleSelectTemplate(template.key)}
                            className={clsx(
                                "w-full p-4 rounded-xl border-2 text-left transition-all duration-200 group shadow-sm",
                                activeTemplateKey === template.key
                                    ? "bg-white border-indigo-500 shadow-indigo-100 ring-2 ring-indigo-300"
                                    : "bg-white border-gray-200 hover:bg-gray-50 hover:border-indigo-400"
                            )}
                        >
                            <div className="flex items-center justify-between">
                                <span className="font-semibold text-gray-900 flex items-center gap-3">
                                    <span className={clsx(
                                        "p-2 rounded-full",
                                        activeTemplateKey === template.key ? "bg-indigo-100 text-indigo-600" : "bg-gray-100 text-gray-500 group-hover:text-indigo-500"
                                    )}>
                                        <Mail size={16} />
                                    </span>
                                    {template.name}
                                </span>
                                {activeTemplateKey === template.key && (
                                    <Check size={20} className="text-green-600 flex-shrink-0" />
                                )}
                            </div>
                            <p className="text-xs text-gray-600 mt-2 pl-11">
                                {template.description}
                            </p>
                        </button>
                    ))}
                </div>

                {/* Column 2: Editor & Preview Area */}
                <div className="lg:col-span-2">
                    {renderContent()}
                </div>
            </div>
        </div>
    );
};

export default EmailTemplateManagementTab;