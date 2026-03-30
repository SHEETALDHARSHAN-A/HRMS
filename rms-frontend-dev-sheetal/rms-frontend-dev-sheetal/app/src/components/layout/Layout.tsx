// // src/components/layout/Layout.tsx

// import Sidebar from "./Sidebar";
// import Header from "./Header";
// import TopBanner from "../common/TopBanner";

// interface LayoutProps {
//   children: React.ReactNode;
//   searchPlaceholder: string;
//   bannerTitle?: string;
//   bannerSubtitle?: string;
//   bannerActionButton?: React.ReactNode;
//   showBackButton?: boolean;
//   onBackClick?: () => void;
// }

// export default function Layout({
//   children,
//   searchPlaceholder,
//   bannerTitle,
//   bannerSubtitle,
//   bannerActionButton,
//   showBackButton,
//   onBackClick,
// }: LayoutProps) {
//   return (
//     <div className="flex w-full min-h-screen items-stretch">
//       <Sidebar />
//       <div className="flex flex-col flex-1 min-h-screen">
//         <Header searchPlaceholder={searchPlaceholder} />
        
//         {/* Optional Top Banner, placed below Header */}
//         {(bannerTitle && bannerSubtitle) && (
//             <TopBanner 
//                 title={bannerTitle}
//                 subtitle={bannerSubtitle}
//                 actionButton={bannerActionButton}
//                 showBackButton={showBackButton}
//                 onBackClick={onBackClick}
//             />
//         )}
        
//         <main
//           className="flex-1 overflow-y-auto layout-bg"
//           style={{
//             padding: "var(--page-padding-y) var(--page-padding-x)", 
//             paddingTop: "var(--page-padding-y)",
//           }}
//         >
//           {children}
//         </main>
//       </div>
//     </div>
//   );
// }


import { useState, type CSSProperties } from 'react';
import { Menu, X } from 'lucide-react';
import { Outlet } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import Sidebar from "./Sidebar";
import TopBanner from "../common/TopBanner";

interface LayoutProps {
  children?: React.ReactNode;
  searchPlaceholder: string;
  bannerTitle?: string;
  bannerSubtitle?: string;
  bannerActionButton?: React.ReactNode;
  showBackButton?: boolean;
  onBackClick?: () => void;
  bannerTabs?: { id: string; label: string }[];
  activeTab?: string;
  onTabChange?: (tabId: string) => void;
}

export default function Layout({
  children,
  searchPlaceholder: _searchPlaceholder,
  bannerTitle,
  bannerSubtitle,
  bannerActionButton,
  showBackButton,
  onBackClick,
  bannerTabs,
  activeTab,
  onTabChange,
}: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div
      className="flex min-h-svh w-full bg-background text-foreground"
      style={
        {
          "--sidebar-width": "16rem",
          "--header-height": "3rem",
        } as CSSProperties
      }
    >
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex min-h-svh flex-1 flex-col">
        <div className="flex h-12 items-center border-b bg-background px-3 lg:hidden">
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            onClick={() => setSidebarOpen((prev) => !prev)}
            aria-label={sidebarOpen ? 'Close menu' : 'Open menu'}
          >
            {sidebarOpen ? <X className="size-4" /> : <Menu className="size-4" />}
          </Button>
        </div>
        
        {(bannerTitle && bannerSubtitle) && (
            <TopBanner 
                title={bannerTitle}
                subtitle={bannerSubtitle}
                actionButton={bannerActionButton}
                showBackButton={showBackButton}
                onBackClick={onBackClick}
                tabs={bannerTabs}
                activeTab={activeTab}
                onTabChange={onTabChange}
            />
        )}
        
        <main
          className="flex-1 overflow-y-auto bg-muted/30"
          style={{
            padding: "var(--page-padding-y) var(--page-padding-x)", 
            paddingTop: "var(--page-padding-y)",
          }}
        >
          {children ?? <Outlet />}
        </main>
      </div>
    </div>
  );
}
