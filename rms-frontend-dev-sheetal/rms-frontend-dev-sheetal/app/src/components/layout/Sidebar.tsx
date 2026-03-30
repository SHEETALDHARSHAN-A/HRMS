import {
  BarChart3,
  BadgeCheck,
  Bell,
  Briefcase,
  ChevronsUpDown,
  CreditCard,
  FileText,
  Headset,
  LayoutDashboard,
  LogOut,
  MessageCircle,
  Search,
  Settings,
  UploadCloud,
  Users,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import logo from '@/assets/rms-mark.svg';
import { useUser } from '../../context/UserContext';
import type { UserRole } from '../router/ProtectedRoute';
import { cn } from '@/lib/utils';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Separator } from '@/components/ui/separator';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

interface SidebarNavItem {
  label: string;
  icon: LucideIcon;
  path: string;
  roles: UserRole[];
  section: 'main' | 'documents' | 'secondary';
}

const ALL_ADMIN_ROLES: UserRole[] = ['ADMIN', 'SUPER_ADMIN', 'HR'];
const ALL_ROLES: UserRole[] = [...ALL_ADMIN_ROLES, 'CANDIDATE'];

const navItems: SidebarNavItem[] = [
  { label: 'Dashboard', icon: LayoutDashboard, path: '/dashboard', roles: ALL_ADMIN_ROLES, section: 'main' },
  { label: 'My Job Posts', icon: Briefcase, path: '/jobs/my-jobs', roles: ALL_ADMIN_ROLES, section: 'main' },
  { label: 'Job Posts by others', icon: Users, path: '/jobs/all-jobs', roles: ALL_ADMIN_ROLES, section: 'main' },
  { label: 'Job Recruitment', icon: BarChart3, path: '/job-recruitment', roles: ALL_ADMIN_ROLES, section: 'main' },
  { label: 'Interview Results', icon: MessageCircle, path: '/interview-results', roles: ALL_ADMIN_ROLES, section: 'main' },
  { label: 'Interview Agent', icon: Headset, path: '/interview-agent', roles: ALL_ADMIN_ROLES, section: 'main' },
  { label: 'Onboarding', icon: Users, path: '/onboarding', roles: ALL_ADMIN_ROLES, section: 'main' },
  { label: 'Career Page', icon: FileText, path: '/career-page', roles: ALL_ROLES, section: 'documents' },
  { label: 'Control Hub', icon: UploadCloud, path: '/control-hub', roles: ALL_ADMIN_ROLES, section: 'documents' },
  { label: 'Settings', icon: Settings, path: '/settings', roles: ALL_ADMIN_ROLES, section: 'secondary' },
  { label: 'Search Jobs', icon: Search, path: '/jobs/all-jobs', roles: ALL_ADMIN_ROLES, section: 'secondary' },
];

const toRoleArray = (roleValue: unknown): UserRole[] => {
  if (!roleValue) {
    return [];
  }

  if (Array.isArray(roleValue)) {
    return roleValue.filter((role): role is UserRole => typeof role === 'string') as UserRole[];
  }

  if (typeof roleValue === 'string') {
    return [roleValue as UserRole];
  }

  return [];
};

const getVisibleItems = (roleValue: unknown) => {
  const rolesToCheck = toRoleArray(roleValue);

  if (rolesToCheck.length === 0) {
    return [] as SidebarNavItem[];
  }

  if (rolesToCheck.includes('SUPER_ADMIN')) {
    return navItems;
  }

  return navItems.filter((item) => rolesToCheck.some((role) => item.roles.includes(role)));
};

const formatRoleLabel = (roleValue: unknown) => {
  const firstRole = toRoleArray(roleValue)[0];
  if (!firstRole) {
    return 'Admin';
  }

  return firstRole
    .toLowerCase()
    .split('_')
    .map((token) => token.charAt(0).toUpperCase() + token.slice(1))
    .join(' ');
};

const NavItems = ({
  items,
  closeSidebar,
}: {
  items: SidebarNavItem[];
  closeSidebar?: () => void;
}) => {
  return (
    <div className="space-y-1">
      {items.map(({ label, icon: Icon, path }) => (
        <NavLink
          key={label}
          to={path}
          onClick={closeSidebar}
          className={({ isActive }) =>
            cn(
              'group flex h-10 w-full items-center gap-2.5 rounded-md px-3 text-sm transition-colors',
              isActive
                ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                : 'text-sidebar-foreground/80 hover:bg-sidebar-accent/70 hover:text-sidebar-foreground'
            )
          }
        >
          <Icon className="size-4" />
          <span className="truncate">{label}</span>
        </NavLink>
      ))}
    </div>
  );
};

const SidebarBody = ({
  items,
  userName,
  userEmail,
  roleLabel,
  onLogout,
  closeSidebar,
}: {
  items: SidebarNavItem[];
  userName: string;
  userEmail: string;
  roleLabel: string;
  onLogout: () => Promise<void>;
  closeSidebar?: () => void;
}) => {
  const mainItems = items.filter((item) => item.section === 'main');
  const documentItems = items.filter((item) => item.section === 'documents');
  const secondaryItems = items.filter((item) => item.section === 'secondary');

  const initials = userName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((token) => token.charAt(0))
    .join('')
    .toUpperCase() || 'US';

  const handleLogout = async () => {
    await onLogout();
    closeSidebar?.();
  };

  return (
    <div className="flex h-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="shrink-0 px-3 py-3">
        <img src={logo} alt="RMS" className="h-8 w-8 object-contain" />
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-2 pt-4">

        <NavItems items={mainItems} closeSidebar={closeSidebar} />

        {documentItems.length > 0 && (
          <div className="mt-6">
            <p className="mb-1 px-2 text-xs text-sidebar-foreground/60">Documents</p>
            <NavItems items={documentItems} closeSidebar={closeSidebar} />
          </div>
        )}

        {secondaryItems.length > 0 && (
          <div className="mt-6">
            <NavItems items={secondaryItems} closeSidebar={closeSidebar} />
          </div>
        )}
      </div>

      <Separator className="my-2" />

      <div className="p-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="group flex h-8 w-full items-center gap-2 rounded-md px-2 text-sm transition-colors hover:bg-sidebar-accent/70 hover:text-sidebar-foreground data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
            >
              <Avatar className="h-8 w-8 rounded-lg">
                <AvatarFallback className="rounded-lg bg-[#016BAE] text-white">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <div className="grid min-w-0 flex-1 text-left text-sm leading-tight">
                <span className="truncate font-semibold">{userName}</span>
                <span className="truncate text-xs">{userEmail || roleLabel}</span>
              </div>
              <ChevronsUpDown className="ml-auto size-4" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
            side={closeSidebar ? 'bottom' : 'right'}
            align="end"
            sideOffset={4}
          >
            <DropdownMenuLabel className="p-0 font-normal">
              <div className="flex items-center gap-2 px-1 py-1.5 text-left text-sm">
                <Avatar className="h-8 w-8 rounded-lg">
                  <AvatarFallback className="rounded-lg bg-[#016BAE] text-white">
                    {initials}
                  </AvatarFallback>
                </Avatar>
                <div className="grid min-w-0 flex-1 text-left text-sm leading-tight">
                  <span className="truncate font-semibold">{userName}</span>
                  <span className="truncate text-xs">{userEmail || roleLabel}</span>
                </div>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem>
                <BadgeCheck className="mr-2 size-4" />
                Account
              </DropdownMenuItem>
              <DropdownMenuItem>
                <CreditCard className="mr-2 size-4" />
                Billing
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Bell className="mr-2 size-4" />
                Notifications
              </DropdownMenuItem>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout}>
              <LogOut className="mr-2 size-4" />
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
};

export default function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const { user, logout } = useUser();
  const visibleItems = getVisibleItems(user?.role);
  const roleLabel = formatRoleLabel(user?.role);
  const userName = user ? `${user.first_name} ${user.last_name}`.trim() : 'User';
  const userEmail = user?.email ?? '';

  return (
    <>
      <aside
        className="hidden h-svh w-[var(--sidebar-width)] shrink-0 flex-col border-r bg-sidebar text-sidebar-foreground lg:flex"
        style={{ position: 'sticky', top: 0 }}
      >
        <SidebarBody
          items={visibleItems}
          userName={userName}
          userEmail={userEmail}
          roleLabel={roleLabel}
          onLogout={logout}
        />
      </aside>

      <Sheet
        open={isOpen}
        onOpenChange={(open) => {
          if (!open) {
            onClose?.();
          }
        }}
      >
        <SheetContent
          side="left"
          className="w-[var(--sidebar-width)] border-r bg-sidebar p-0 text-sidebar-foreground sm:max-w-[var(--sidebar-width)]"
          showCloseButton
        >
          <SheetHeader className="sr-only">
            <SheetTitle>Navigation</SheetTitle>
          </SheetHeader>
          <SidebarBody
            items={visibleItems}
            userName={userName}
            userEmail={userEmail}
            roleLabel={roleLabel}
            onLogout={logout}
            closeSidebar={onClose}
          />
        </SheetContent>
      </Sheet>
    </>
  );
}
