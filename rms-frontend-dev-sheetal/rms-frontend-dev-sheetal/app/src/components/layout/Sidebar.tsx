// import { Briefcase, LayoutDashboard, FileText, BarChart, MessageCircle, Users, Headset, UploadCloud, Settings, X } from "lucide-react";
// import { NavLink } from "react-router-dom";
// import logo from "../../assets/logo.svg";
// import { useUser } from "../../context/UserContext";
// import type { UserRole } from "../router/ProtectedRoute"; 

// const ALL_ADMIN_ROLES: UserRole[] = ["ADMIN", "SUPER_ADMIN"];
// const ALL_ROLES: UserRole[] = [...ALL_ADMIN_ROLES, "CANDIDATE"];
// const navItems = [
// 	{ label: "Dashboard", icon: LayoutDashboard, path: "/dashboard", roles: ALL_ADMIN_ROLES },
// 	{ label: "Job Posts", icon: Briefcase, path: "/jobs", roles: ALL_ADMIN_ROLES },

// 	{ label: "Career Page", icon: FileText, path: "/career-page", roles: ALL_ROLES },

//     // Other Admin/SuperAdmin Pages
// 	{ label: "Control Hub", icon: UploadCloud, path: "/control-hub", roles: ALL_ADMIN_ROLES },
// 	{ label: "Job Recruitment", icon: BarChart, path: "/job-recruitment", roles: ALL_ADMIN_ROLES },
// 	{ label: "Interview Results", icon: MessageCircle, path: "/interview-results", roles: ALL_ADMIN_ROLES },
// 	{ label: "Onboarding", icon: Users, path: "/onboarding", roles: ALL_ADMIN_ROLES },
// 	{ label: "Interview Agent", icon: Headset, path: "/interview-agent", roles: ALL_ADMIN_ROLES },
// 	{ label: "Settings", icon: Settings, path: "/settings", roles: ALL_ADMIN_ROLES }, 
// ];

// export default function Sidebar({ isOpen, onClose }: { isOpen?: boolean; onClose?: () => void }) {
//     const { user } = useUser();
//     const userRole = user?.roles;

//     const filteredNavItems = navItems.filter(item => {
//         if (!userRole) return false;

//         const rolesToCheck = Array.isArray(userRole) ? userRole : [userRole];

//         // Super Admin sees every link defined above
//         if (rolesToCheck.includes("SUPER_ADMIN")) return true;

//         // Check if the user's role is specifically included in the item's allowed roles
//         return rolesToCheck.some(role => item.roles.includes(role));
//     });

//     // Separate the "Settings" tab
//     const settingsTab = navItems.find(item => item.label === "Settings");

//     return (
//         <>
//         {/* Desktop / large screens */}
//         <aside
//             className="hidden lg:flex flex-col bg-white border-r border-gray-100 shadow-xl shadow-gray-50/10 z-20"
//             style={{
//                 width: "var(--sidebar-width)",
//                 minWidth: "var(--sidebar-width)",
//                 height: "100vh",
//                 position: "sticky",
//                 top: 0,
//             }}
//         >
//             {/* Sidebar Header */}
//             <div className="p-6 pb-8 h-16 flex items-center">
//                 <img src={logo} alt="PRAYAG.AI Logo" className="w-full max-w-[200px] h-auto object-contain" />
//             </div>

//             {/* Sidebar Navigation */}
//             <nav className="flex-1 flex flex-col gap-2 px-4 pt-4">
//                 {/* Render all navigation items except "Settings" */}
//                 {filteredNavItems
//                     .filter(item => item.label !== "Settings")
//                     .map(({ label, icon: Icon, path }) => (
//                         <NavLink
//                             key={label}
//                             to={path}
//                             className={({ isActive }) => {
//                                 let navLinkClasses = "flex items-center gap-3 w-full px-4 py-3 rounded-md font-medium";
//                                 if (isActive) {
//                                     navLinkClasses += " bg-[var(--color-primary-500)] text-white shadow-md";
//                                 } else {
//                                     navLinkClasses += " text-gray-700 hover:bg-gray-100";
//                                 }
//                                 return navLinkClasses;
//                             }}
//                             style={({ isActive }) => ({
//                                 color: isActive ? 'white' : 'var(--color-primary-500)',
//                             })}
//                         >
//                             <Icon size={16} />
//                             {label}
//                         </NavLink>
//                     ))}
//             </nav>

//             {/* Render the "Settings" tab at the bottom */}
//             {settingsTab && (
//                 <div className="px-4 pb-4">
//                     <NavLink
//                         to={settingsTab.path}
//                         className={({ isActive }) => {
//                             let navLinkClasses = "flex items-center gap-3 w-full px-4 py-3 rounded-md font-medium";
//                             if (isActive) {
//                                 navLinkClasses += " bg-[var(--color-primary-500)] text-white shadow-md";
//                             } else {
//                                 navLinkClasses += " text-gray-700 hover:bg-gray-100";
//                             }
//                             return navLinkClasses;
//                         }}
//                         style={({ isActive }) => ({
//                             color: isActive ? 'white' : 'var(--color-primary-500)',
//                         })}
//                     >
//                         <settingsTab.icon size={16} />
//                         {settingsTab.label}
//                     </NavLink>
//                 </div>
//             )}
//         </aside>

//         {/* Mobile slide-over */}
//         <div className={`fixed inset-0 z-40 lg:hidden ${isOpen ? '' : 'pointer-events-none'}`} aria-hidden={!isOpen}>
//           {/* Backdrop */}
//           <div
//             className={`absolute inset-0 bg-black/40 transition-opacity ${isOpen ? 'opacity-100' : 'opacity-0'}`}
//             onClick={() => onClose && onClose()}
//           />

//           <div className={`absolute left-0 top-0 bottom-0 w-64 bg-white shadow-xl transform transition-transform ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
//             <div className="p-4 flex items-center justify-between">
//               <img src={logo} alt="PRAYAG.AI Logo" className="w-36 h-auto object-contain" />
//               <button onClick={() => onClose && onClose()} aria-label="Close menu" className="p-2 rounded-md hover:bg-gray-100">
//                 <X size={18} />
//               </button>
//             </div>

//             <nav className="flex-1 flex flex-col gap-2 px-4 pt-2">
//                 {filteredNavItems
//                     .filter(item => item.label !== "Settings")
//                     .map(({ label, icon: Icon, path }) => (
//                         <NavLink
//                             key={label}
//                             to={path}
//                             onClick={() => onClose && onClose()}
//                             className={({ isActive }) => {
//                                 let navLinkClasses = "flex items-center gap-3 w-full px-4 py-3 rounded-md font-medium";
//                                 if (isActive) {
//                                     navLinkClasses += " bg-[var(--color-primary-500)] text-white shadow-md";
//                                 } else {
//                                     navLinkClasses += " text-gray-700 hover:bg-gray-100";
//                                 }
//                                 return navLinkClasses;
//                             }}
//                             style={({ isActive }) => ({
//                                 color: isActive ? 'white' : 'var(--color-primary-500)',
//                             })}
//                         >
//                             <Icon size={16} />
//                             {label}
//                         </NavLink>
//                     ))}
//             </nav>

//             {settingsTab && (
//               <div className="px-4 pb-4">
//                 <NavLink
//                     to={settingsTab.path}
//                     onClick={() => onClose && onClose()}
//                     className={({ isActive }) => {
//                         let navLinkClasses = "flex items-center gap-3 w-full px-4 py-3 rounded-md font-medium";
//                         if (isActive) {
//                             navLinkClasses += " bg-[var(--color-primary-500)] text-white shadow-md";
//                         } else {
//                             navLinkClasses += " text-gray-700 hover:bg-gray-100";
//                         }
//                         return navLinkClasses;
//                     }}
//                     style={({ isActive }) => ({
//                         color: isActive ? 'white' : 'var(--color-primary-500)',
//                     })}
//                 >
//                     <settingsTab.icon size={16} />
//                     {settingsTab.label}
//                 </NavLink>
//               </div>
//             )}

//           </div>
//         </div>
//         </>
//     );
// }


import React from 'react';
import { Briefcase, LayoutDashboard, FileText, BarChart, MessageCircle, Users, Headset, UploadCloud, Settings, X } from "lucide-react";
import { NavLink } from "react-router-dom";
import logo from "../../assets/logo.svg";
import { useUser } from "../../context/UserContext";
import type { UserRole } from "../router/ProtectedRoute"; 

// Include HR as an admin-level role so HR users see admin sidebar items
const ALL_ADMIN_ROLES: UserRole[] = ["ADMIN", "SUPER_ADMIN", "HR"];
const ALL_ROLES: UserRole[] = [...ALL_ADMIN_ROLES, "CANDIDATE"];
const navItems = [
	{ label: "Dashboard", icon: LayoutDashboard, path: "/dashboard", roles: ALL_ADMIN_ROLES },
	{ label: "My Job Posts", icon: Briefcase, path: "/jobs/my-jobs", roles: ALL_ADMIN_ROLES },
	{ label: "All Job Posts", icon: Users, path: "/jobs/all-jobs", roles: ALL_ADMIN_ROLES },
	{ label: "Career Page", icon: FileText, path: "/career-page", roles: ALL_ROLES },

    // Other Admin/SuperAdmin Pages
	{ label: "Control Hub", icon: UploadCloud, path: "/control-hub", roles: ALL_ADMIN_ROLES },
	{ label: "Job Recruitment", icon: BarChart, path: "/job-recruitment", roles: ALL_ADMIN_ROLES },
	{ label: "Interview Results", icon: MessageCircle, path: "/interview-results", roles: ALL_ADMIN_ROLES },
	{ label: "Onboarding", icon: Users, path: "/onboarding", roles: ALL_ADMIN_ROLES },
	{ label: "Interview Agent", icon: Headset, path: "/interview-agent", roles: ALL_ADMIN_ROLES },
	{ label: "Settings", icon: Settings, path: "/settings", roles: ALL_ADMIN_ROLES }, 
];

export default function Sidebar({ isOpen, onClose }: { isOpen?: boolean; onClose?: () => void }) {
        const { user } = useUser();
        const mobileWrapperRef = React.useRef<HTMLDivElement | null>(null);

        // Accessibility: when the mobile sidebar is closed, ensure no focusable element
        // inside it remains focused while the container is aria-hidden. This prevents
        // the browser warning about aria-hidden on an ancestor of a focused element.
        React.useEffect(() => {
            if (isOpen) return; // only act when closing
            try {
                const wrapper = mobileWrapperRef.current;
                if (!wrapper) return;
                const active = document.activeElement as HTMLElement | null;
                if (active && wrapper.contains(active)) {
                    // Move focus away: blur the focused element to avoid hidden-focus issue.
                    active.blur();
                    // Optionally, move focus to the document body so assistive tech has a valid target
                    (document.body as HTMLElement).focus?.();
                }
            } catch (e) {
                // Non-fatal — keep app working
                // eslint-disable-next-line no-console
                console.warn('Sidebar accessibility focus handler failed', e);
            }
        }, [isOpen]);
    const userRole = user?.role;

    const filteredNavItems = navItems.filter(item => {
        if (!userRole) return false;

        const rolesToCheck = Array.isArray(userRole) ? userRole : [userRole];

        // Super Admin sees every link defined above
        if (rolesToCheck.includes("SUPER_ADMIN")) return true;

        // Check if the user's role is specifically included in the item's allowed roles
        return rolesToCheck.some(role => item.roles.includes(role));
    });

    // Separate the "Settings" tab - only show if user has the right role
    const settingsTab = navItems.find(item => item.label === "Settings");
    // For debugging: always show settings if user has any admin role
    // Allow HR to access Settings as well
    const shouldShowSettings = settingsTab && userRole && (
        userRole === "SUPER_ADMIN" || 
        userRole === "ADMIN" ||
        userRole === "HR" || 
        (Array.isArray(userRole) && (userRole.includes("SUPER_ADMIN") || userRole.includes("ADMIN") || userRole.includes("HR")))
    );

    return (
        <>
        {/* Desktop / large screens */}
        <aside
            className="hidden lg:flex flex-col bg-white border-r border-gray-100 shadow-xl shadow-gray-50/10 z-20"
            style={{
                width: "var(--sidebar-width)",
                minWidth: "var(--sidebar-width)",
                height: "100vh",
                position: "sticky",
                top: 0,
                paddingBottom: 'calc(env(safe-area-inset-bottom, 0px) + 4rem)'
            }}
        >
            {/* Sidebar Header */}
            <div className="p-6 pb-8 h-16 flex items-center">
                <img src={logo} alt="PRAYAG.AI Logo" className="w-full max-w-[200px] h-auto object-contain" />
            </div>

            {/* Sidebar Navigation */}
            <nav className="flex-1 flex flex-col gap-2 px-4 pt-4">
                {/* Render all navigation items except "Settings" */}
                {filteredNavItems
                    .filter(item => item.label !== "Settings")
                    .map(({ label, icon: Icon, path }) => (
                        <NavLink
                            key={label}
                            to={path}
                            className={({ isActive }) => {
                                let navLinkClasses = "flex items-center gap-3 w-full px-3 py-2 rounded-md font-medium";
                                if (isActive) {
                                    navLinkClasses += " bg-[var(--color-primary-500)] text-white shadow-md";
                                } else {
                                    navLinkClasses += " text-gray-700 hover:bg-gray-100";
                                }
                                return navLinkClasses;
                            }}
                            style={({ isActive }) => ({
                                color: isActive ? 'white' : 'var(--color-primary-500)',
                            })}
                        >
                            <Icon size={16} />
                            {label}
                        </NavLink>
                    ))}
            </nav>

            {/* Render the "Settings" tab at the bottom */}
            {shouldShowSettings && settingsTab && (
                <div className="px-4 mt-auto" style={{ paddingBottom: 'calc(4rem + env(safe-area-inset-bottom, 0px))' }}>
                    <NavLink
                        to={settingsTab.path}
                        className={({ isActive }) => {
                            let navLinkClasses = "flex items-center gap-3 w-full px-3 py-2 rounded-md font-medium";
                            if (isActive) {
                                navLinkClasses += " bg-[var(--color-primary-500)] text-white shadow-md";
                            } else {
                                navLinkClasses += " text-gray-700 hover:bg-gray-100";
                            }
                            return navLinkClasses;
                        }}
                        style={({ isActive }) => ({
                            color: isActive ? 'white' : 'var(--color-primary-500)',
                        })}
                    >
                        <settingsTab.icon size={16} />
                        {settingsTab.label}
                    </NavLink>
                </div>
            )}
        </aside>

        {/* Mobile slide-over */}
    <div ref={mobileWrapperRef} className={`fixed inset-0 z-40 lg:hidden ${isOpen ? '' : 'pointer-events-none'}`} aria-hidden={!isOpen}>
          {/* Backdrop */}
          <div
            className={`absolute inset-0 bg-black/40 transition-opacity ${isOpen ? 'opacity-100' : 'opacity-0'}`}
            onClick={() => onClose && onClose()}
          />

          <div className={`absolute left-0 top-0 bottom-0 w-64 bg-white shadow-xl transform transition-transform ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
            <div className="p-4 flex items-center justify-between">
              <img src={logo} alt="PRAYAG.AI Logo" className="w-36 h-auto object-contain" />
              <button onClick={() => onClose && onClose()} aria-label="Close menu" className="p-2 rounded-md hover:bg-gray-100">
                <X size={18} />
              </button>
            </div>

            <nav className="flex-1 flex flex-col gap-2 px-4 pt-2">
                {filteredNavItems
                    .filter(item => item.label !== "Settings")
                    .map(({ label, icon: Icon, path }) => (
                        <NavLink
                            key={label}
                            to={path}
                            onClick={() => onClose && onClose()}
                            className={({ isActive }) => {
                                let navLinkClasses = "flex items-center gap-3 w-full px-3 py-2 rounded-md font-medium";
                                if (isActive) {
                                    navLinkClasses += " bg-[var(--color-primary-500)] text-white shadow-md";
                                } else {
                                    navLinkClasses += " text-gray-700 hover:bg-gray-100";
                                }
                                return navLinkClasses;
                            }}
                            style={({ isActive }) => ({
                                color: isActive ? 'white' : 'var(--color-primary-500)',
                            })}
                        >
                            <Icon size={16} />
                            {label}
                        </NavLink>
                    ))}
            </nav>

            {shouldShowSettings && settingsTab && (
              <div className="px-4" style={{ paddingBottom: 'calc(4rem + env(safe-area-inset-bottom, 0px))' }}>
                <NavLink
                    to={settingsTab.path}
                    onClick={() => onClose && onClose()}
                    className={({ isActive }) => {
                        let navLinkClasses = "flex items-center gap-3 w-full px-3 py-2 rounded-md font-medium";
                        if (isActive) {
                            navLinkClasses += " bg-[var(--color-primary-500)] text-white shadow-md";
                        } else {
                            navLinkClasses += " text-gray-700 hover:bg-gray-100";
                        }
                        return navLinkClasses;
                    }}
                    style={({ isActive }) => ({
                        color: isActive ? 'white' : 'var(--color-primary-500)',
                    })}
                >
                    <settingsTab.icon size={16} />
                    {settingsTab.label}
                </NavLink>
              </div>
            )}

          </div>
        </div>
        </>
    );
}