"use client";

import { cn } from "@/lib/utils";
import { useAdminSummary } from "@/hooks/use-admin-summary";
import { NavLinks } from "@/components/layout/nav-links";

export function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { data } = useAdminSummary();
  const retrievalBackend = data?.ok ? data.data.retrieval_backend : null;

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 items-center gap-2 px-5">
        <span className="block h-6 w-2 rounded-sm bg-gradient-to-b from-primary to-cyan-400" />
        <span className="text-h4 font-semibold text-sidebar-foreground">Nexus</span>
      </div>

      <NavLinks onNavigate={onNavigate} />

      <div className="border-t border-sidebar-border px-5 py-4">
        <div className="flex items-center gap-2 text-label uppercase tracking-wide text-muted-foreground">
          <span
            className={cn(
              "size-1.5 rounded-full",
              retrievalBackend ? "bg-success" : "bg-muted-foreground",
            )}
          />
          Retrieval: {retrievalBackend ?? "unknown"}
        </div>
      </div>
    </div>
  );
}
