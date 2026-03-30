import type { FC, ReactNode } from "react";
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
interface TopBannerProps {
  title: string;
  subtitle: string | ReactNode;
  actionButton?: ReactNode;
  showBackButton?: boolean;
  onBackClick?: () => void;
  tabs?: { id: string; label: string }[];
  activeTab?: string;
  onTabChange?: (tabId: string) => void;
}
const TopBanner: FC<TopBannerProps> = ({
  title,
  subtitle,
  actionButton,
  showBackButton,
  onBackClick,
  tabs,
  activeTab,
  onTabChange,
}) => {
  const tabItems = tabs ?? [];
  const hasTabs = Boolean(tabItems.length && onTabChange);
  return (
    <section className="relative bg-background border-b border-border text-foreground px-6 py-6" style={{ backgroundColor: 'var(--background)' }}>
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-col gap-1.5">
            <h1 className="text-2xl font-semibold tracking-tight">
              {title}
            </h1>
            <p className="text-sm text-muted-foreground">
              {subtitle as ReactNode}
            </p>
          </div>
          {(showBackButton || actionButton) && (
            <div className="flex items-center gap-3">
              {showBackButton && (
                <Button
                  type="button"
                  onClick={onBackClick}
                  variant="outline"
                  size="sm"
                  className="gap-2"
                >
                  <ArrowLeft size={16} />
                  <span>Back</span>
                </Button>
              )}
              {actionButton}
            </div>
          )}
        </div>
        {hasTabs && (
          <div className="mt-8 flex items-center gap-6">
            {tabItems.map((tab) => {
              const isActive = tab.id === activeTab;
              return (
                <button
                  key={tab.id}
                  onClick={() => onTabChange?.(tab.id)}
                  className={cn(
                    "pb-3 text-sm font-medium transition-colors hover:text-primary relative",
                    isActive
                      ? "text-primary"
                      : "text-muted-foreground"
                  )}
                  aria-pressed={isActive}
                >
                  {tab.label}
                  {isActive && (
                    <div className="absolute bottom-[-1px] left-0 right-0 h-[2px] bg-primary" style={{ backgroundColor: 'hsl(var(--primary))' }} />
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
};
export default TopBanner;
