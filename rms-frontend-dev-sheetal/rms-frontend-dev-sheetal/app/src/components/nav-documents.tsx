import { NavMain, type NavMainItem } from '@/components/nav-main';
import { SidebarGroup, SidebarGroupContent, SidebarGroupLabel } from '@/components/ui/sidebar';

export function NavDocuments({ items }: { items: NavMainItem[] }) {
  if (items.length === 0) {
    return null;
  }

  return (
    <SidebarGroup className="mt-6">
      <SidebarGroupLabel>Documents</SidebarGroupLabel>
      <SidebarGroupContent>
        <NavMain items={items} />
      </SidebarGroupContent>
    </SidebarGroup>
  );
}
