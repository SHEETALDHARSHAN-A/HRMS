// rms-frontend-dev-sheetal/app/src/components/common/TopBanner.tsx
import type { FC, ReactNode } from "react";
import { ArrowLeft } from "lucide-react";
import Button from "./Button";
import clsx from 'clsx';

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
    <section className="relative isolate overflow-hidden bg-gradient-to-br from-[#0a1734] via-[#0b2447] to-[#040a1e] text-white">
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute left-1/2 top-[-110px] h-64 w-64 -translate-x-1/2 rounded-full bg-blue-500/20 blur-3xl" />
        <div className="absolute bottom-[-140px] left-[-120px] h-64 w-64 rounded-full bg-sky-500/18 blur-3xl" />
        <div className="absolute right-[-120px] top-[-50px] h-72 w-72 rounded-full bg-indigo-500/18 blur-3xl" />
        <div className="absolute inset-0">
          <svg className="h-full w-full" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <pattern id="topBannerGrid" width="120" height="120" patternUnits="userSpaceOnUse">
                <path d="M 120 0 L 0 0 0 120" fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="1" />
              </pattern>
            </defs>
            <rect fill="url(#topBannerGrid)" height="100%" width="100%" />
          </svg>
        </div>
      </div>

      <div className="relative mx-auto max-w-7xl px-4 pb-3 pt-4 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-col gap-3">
            <div className="space-y-2.5">
              <h1 className="text-[26px] font-semibold leading-tight text-white sm:text-[30px]">
                {title}
              </h1>
              <p className="max-w-3xl text-[13px] text-blue-100/85 sm:text-sm">
                {subtitle}
              </p>
            </div>
          </div>
          {(showBackButton || actionButton) && (
            <div className="flex items-center gap-2">
              {actionButton && actionButton}
              {showBackButton && (
                <Button
                  type="button"
                  onClick={onBackClick}
                  variant="ghost"
                  className="inline-flex items-center gap-2 rounded-full border border-white/25 bg-white/10 px-3.5 py-1.5 text-[11px] font-medium text-blue-50 backdrop-blur transition hover:border-white/40 hover:bg-white/20 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/50"
                >
                  <ArrowLeft size={16} />
                  <span>Back</span>
                </Button>
              )}
            </div>
          )}
        </div>

        {hasTabs && (
          <div className="mt-5 flex w-full justify-start">
            <div className="inline-flex flex-wrap gap-1.5 rounded-full border border-white/15 bg-white/10 p-1.5 backdrop-blur">
              {tabItems.map((tab) => {
                const isActive = tab.id === activeTab;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => onTabChange?.(tab.id)}
                    className={clsx(
                      "relative overflow-hidden rounded-full px-3.5 py-1.5 text-[13px] font-semibold transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60",
                      isActive
                        ? "bg-white text-[#081b3b] shadow-[0_12px_30px_rgba(29,78,216,0.35)]"
                        : "text-blue-100 hover:bg-white/10 hover:text-white"
                    )}
                    aria-pressed={isActive}
                  >
                    {isActive && (
                      <span className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-r from-white via-white to-blue-100 opacity-95" />
                    )}
                    {tab.label}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </section>
  );
};

export default TopBanner;