import { NavMain, type NavMainItem } from '@/components/nav-main';
import { SidebarGroup, SidebarGroupContent } from '@/components/ui/sidebar';

export function NavSecondary({ items }: { items: NavMainItem[] }) {
  if (items.length === 0) {
    return null;
  }

  return (
    <SidebarGroup className="mt-6">
      <SidebarGroupContent>
        <NavMain items={items} />
      </SidebarGroupContent>
    </SidebarGroup>
  );
}
