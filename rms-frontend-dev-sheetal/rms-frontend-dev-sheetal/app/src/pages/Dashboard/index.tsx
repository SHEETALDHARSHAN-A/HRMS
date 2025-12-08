import { useState, useCallback } from "react";
import { BarChart2 } from "lucide-react";
import Layout from "../../components/layout/Layout";
import Dashboard from "./Dashboard";
import Button from "../../components/common/Button";
/**
 * This component acts as the page wrapper for the Dashboard feature,
 * applying the main application layout (Sidebar, Header, etc.).
 */
export default function DashboardPage() {
  const [showTotalsModal, setShowTotalsModal] = useState(false);

  const openTotals = useCallback(() => setShowTotalsModal(true), []);
  const closeTotals = useCallback(() => setShowTotalsModal(false), []);

  const bannerButton = (
    <Button
      onClick={openTotals}
      variant="ghost"
      className="rounded-full px-3 py-2 ml-2 flex items-center gap-1 bg-white/90 text-[#0b2447]"
    >
      <BarChart2 size={15} />
      Total Jobs Overview
    </Button>
  );

  return (
    <Layout
      bannerTitle="Dashboard"
      bannerSubtitle="Welcome to your dashboard"
      searchPlaceholder="Search dashboard..."
      bannerActionButton={bannerButton}
    >
      <Dashboard
        showTotalsModal={showTotalsModal}
        onOpenTotals={openTotals}
        onCloseTotals={closeTotals}
      />
    </Layout>
  );
}