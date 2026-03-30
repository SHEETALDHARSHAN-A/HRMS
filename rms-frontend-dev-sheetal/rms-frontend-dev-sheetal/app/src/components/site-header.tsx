import Header from '@/components/layout/Header';
import { useSidebar } from '@/components/ui/sidebar';

export function SiteHeader() {
  const { mobileOpen, toggleMobile } = useSidebar();

  return (
    <Header
      onToggleSidebar={toggleMobile}
      sidebarOpen={mobileOpen}
    />
  );
}
