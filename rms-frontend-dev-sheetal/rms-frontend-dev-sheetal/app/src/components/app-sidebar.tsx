import {
  BarChart3,
  Briefcase,
  FileText,
  Headset,
  LayoutDashboard,
  MessageCircle,
  Search,
  Settings,
  UploadCloud,
  Users,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import logo from '@/assets/rms-mark.svg';
import { NavDocuments } from '@/components/nav-documents';
import { NavMain } from '@/components/nav-main';
import { NavSecondary } from '@/components/nav-secondary';
import { NavUser } from '@/components/nav-user';
import { Separator } from '@/components/ui/separator';
import { Sidebar, SidebarContent, SidebarFooter, SidebarHeader } from '@/components/ui/sidebar';
import { useUser } from '@/context/UserContext';
import type { UserRole } from '@/components/router/ProtectedRoute';
interface AppSidebarProps {
  variant?: 'sidebar' | 'floating' | 'inset';
}
interface AppNavItem {
  title: string;
  url: string;
  icon: LucideIcon;
  roles: UserRole[];
  section: 'main' | 'documents' | 'secondary';
}
const ALL_ADMIN_ROLES: UserRole[] = ['ADMIN', 'SUPER_ADMIN', 'HR'];
const ALL_ROLES: UserRole[] = [...ALL_ADMIN_ROLES, 'CANDIDATE'];
const KNOWN_ROLES: UserRole[] = ['ADMIN', 'SUPER_ADMIN', 'HR', 'CANDIDATE'];
const navItems: AppNavItem[] = [
  { title: 'Dashboard', icon: LayoutDashboard, url: '/dashboard', roles: ALL_ADMIN_ROLES, section: 'main' },
  { title: 'My Job Posts', icon: Briefcase, url: '/jobs/my-jobs', roles: ALL_ADMIN_ROLES, section: 'main' },
  { title: 'All Job Posts', icon: Users, url: '/jobs/all-jobs', roles: ALL_ADMIN_ROLES, section: 'main' },
  { title: 'Job Recruitment', icon: BarChart3, url: '/job-recruitment', roles: ALL_ADMIN_ROLES, section: 'main' },
  { title: 'Interview Results', icon: MessageCircle, url: '/interview-results', roles: ALL_ADMIN_ROLES, section: 'main' },
  { title: 'Interview Agent', icon: Headset, url: '/interview-agent', roles: ALL_ADMIN_ROLES, section: 'main' },
  { title: 'Onboarding', icon: Users, url: '/onboarding', roles: ALL_ADMIN_ROLES, section: 'main' },
  { title: 'Career Page', icon: FileText, url: '/career-page', roles: ALL_ROLES, section: 'documents' },
  { title: 'Control Hub', icon: UploadCloud, url: '/control-hub', roles: ALL_ADMIN_ROLES, section: 'documents' },
  { title: 'Settings', icon: Settings, url: '/settings', roles: ALL_ADMIN_ROLES, section: 'secondary' },
  { title: 'Search Jobs', icon: Search, url: '/jobs/all-jobs', roles: ALL_ADMIN_ROLES, section: 'secondary' },
];
const toRoleArray = (roleValue: unknown): UserRole[] => {
  const normalizeRole = (role: string): UserRole | null => {
    const normalized = role.trim().toUpperCase().replace(/[\s-]+/g, '_');
    return KNOWN_ROLES.includes(normalized as UserRole) ? (normalized as UserRole) : null;
  };

  if (!roleValue) return [];
  if (Array.isArray(roleValue)) {
    return roleValue
      .filter((role): role is string => typeof role === 'string')
      .map((role) => normalizeRole(role))
      .filter((role): role is UserRole => role !== null);
  }
  if (typeof roleValue === 'string') {
    const normalized = normalizeRole(roleValue);
    return normalized ? [normalized] : [];
  }
  return [];
};
const getVisibleItems = (roleValue: unknown): AppNavItem[] => {
  const rolesToCheck = toRoleArray(roleValue);
  if (rolesToCheck.length === 0) return [];
  if (rolesToCheck.includes('SUPER_ADMIN')) return navItems;
  return navItems.filter((item) => rolesToCheck.some((role) => item.roles.includes(role)));
};
export function AppSidebar({ variant = 'inset' }: AppSidebarProps) {
  const { user } = useUser();
  const visibleItems = getVisibleItems(user?.role);
  const mainItems = visibleItems
    .filter((item) => item.section === 'main')
    .map(({ title, url, icon }) => ({ title, url, icon }));
  const documentItems = visibleItems
    .filter((item) => item.section === 'documents')
    .map(({ title, url, icon }) => ({ title, url, icon }));
  const secondaryItems = visibleItems
    .filter((item) => item.section === 'secondary')
    .map(({ title, url, icon }) => ({ title, url, icon }));
  return (
    <Sidebar variant={variant}>
      <SidebarHeader className="h-[var(--header-height)] px-3">
        <div className="flex h-full items-center">
          <img src={logo} alt="RMS" className="h-8 w-8 object-contain" />
        </div>
      </SidebarHeader>
      <SidebarContent className="pt-4">
        <NavMain items={mainItems} />
        <NavDocuments items={documentItems} />
        <NavSecondary items={secondaryItems} />
      </SidebarContent>
      <Separator className="my-2" />
      <SidebarFooter>
        <NavUser />
      </SidebarFooter>
    </Sidebar>
  );
}
