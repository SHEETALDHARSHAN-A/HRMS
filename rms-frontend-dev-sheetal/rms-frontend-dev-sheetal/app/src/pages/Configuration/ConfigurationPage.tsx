import React, { useState, useCallback } from 'react';
import Layout from '../../components/layout/Layout';
import AdminManagementTab from './AdminManagementTab'; 
import EmailTemplateManagementTab from './EmailTemplateManagementTab'; // <--- 1. IMPORT NEW COMPONENT
import { Settings, UserCog, Briefcase, Mail } from 'lucide-react'; // <--- 2. IMPORT 'Mail' ICON
import { useUser } from '../../context/UserContext';
import type { UserRole } from '../../components/router/ProtectedRoute';

// Define the tabs for the Configuration Page
const ALL_ADMIN_ROLES: UserRole[] = ["ADMIN", "SUPER_ADMIN", "HR"]; 

const tabs: { 
    id: 'admin' | 'job-config' | 'email-templates'; // <--- 3. ADD NEW ID TYPE
    label: string; 
    Icon: React.FC<any>; 
    roles: UserRole[]; 
}[] = [
  { 
    id: 'admin', 
    label: 'Admin Management', 
    Icon: UserCog, 
    roles: ALL_ADMIN_ROLES
  },
  // --- 4. ADD NEW TAB DEFINITION (placed before Job Config) ---
  {
    id: 'email-templates',
    label: 'Email Templates',
    Icon: Mail,
    roles: ["SUPER_ADMIN"] // Restricted to Super Admin
  },
  // --- END NEW TAB ---
  { 
    id: 'job-config', 
    label: 'Job Post Config', 
    Icon: Briefcase, 
    roles: ["SUPER_ADMIN"] 
  },
];

const ConfigurationPage: React.FC = () => {
  const { user } = useUser();
  const userRole = user?.role;

  // Function to determine if a role array contains the user's role(s)
  const isAuthorized = useCallback((roles: UserRole[]): boolean => {
    if (!userRole) return false;
    const rolesArray = Array.isArray(userRole) ? userRole : [userRole];
    return rolesArray.some(role => roles.includes(role as UserRole));
  }, [userRole]);

  // Filter tabs based on user role 
  const availableTabs = tabs.filter(tab => isAuthorized(tab.roles));

  // Determine initial active tab
  const initialTab = availableTabs.length > 0 ? availableTabs[0].id : '';
  const [activeTab, setActiveTab] = useState<'admin' | 'job-config' | 'email-templates' | string>(initialTab); // <--- 5. ADD NEW ID TYPE
  // When opening a full-screen tab (like email-templates) we'll allow returning to a sensible tab
  const backTab = availableTabs.find(t => t.id !== 'email-templates')?.id ?? initialTab;
  
  const renderContent = () => {
    switch (activeTab) {
      case 'admin':
        return <AdminManagementTab />;
      case 'job-config':
        return <div className="p-4 text-gray-600">Job Post Configuration Coming Soon... (Super Admin Only)</div>;
      case 'email-templates':
        // handled as full-screen view in the return below
        return null;
      default:
        if (availableTabs.length === 0) {
          return <div className="p-4 text-gray-600">You do not have permission to view any configuration sections.</div>;
        }
        return <div className="p-4 text-gray-600">Please select a configuration tab.</div>;
    }
  };

  return (
    <Layout
      bannerTitle="Settings & Configuration"
      bannerSubtitle="Manage platform-wide configurations and user roles"
      searchPlaceholder="Search settings..."
    >
      {/* If Email Templates is active, show it full-screen and hide the left sidebar */}
      {activeTab === 'email-templates' ? (
        <div className="p-6">
          <EmailTemplateManagementTab onBack={() => setActiveTab(backTab)} />
        </div>
      ) : (
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Left Sidebar for Tabs */}
          <div className="w-full lg:w-72 xl:w-80 bg-white rounded-xl shadow-lg border border-gray-100 p-4 flex-shrink-0 self-start">
            <div className="flex items-center gap-2 mb-4 pb-2 border-b border-gray-100">
               <Settings size={20} className="text-[var(--color-primary-500)]" />
               <h2 className="text-lg font-semibold text-gray-800">Configuration Sections</h2>
            </div>
            <nav className="space-y-1">
              {availableTabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-3 w-full px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === tab.id
                      ? 'bg-[var(--color-primary-500)] text-white shadow-md'
                      : 'text-gray-700 hover:bg-gray-100 hover:text-gray-900'
                  }`}
                >
                  <tab.Icon size={18} className={activeTab === tab.id ? 'text-white' : 'text-[var(--color-primary-500)]'} />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Main Content Area */}
          <div className="flex-1 bg-white rounded-xl shadow-lg border border-gray-100 min-h-[600px] overflow-auto">
            {/* Header is now inside the content area for better context */}
            <div className="p-6">
              <h1 className="text-2xl font-bold text-gray-900 mb-6 border-b pb-4">
                {availableTabs.find(t => t.id === activeTab)?.label ?? 'Configuration'}
              </h1>
              {renderContent()}
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
};

export default ConfigurationPage;