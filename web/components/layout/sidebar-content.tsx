"use client";

import Image from "next/image";
import { cn } from "@/lib/utils";
import { useAdminSummary } from "@/hooks/use-admin-summary";
import { NavLinks } from "@/components/layout/nav-links";

export function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { data } = useAdminSummary();
  const retrievalBackend = data?.ok ? data.data.retrieval_backend : null;

  return (
    <div className="flex h-full flex-col">
      <div className="relative flex h-14 items-center gap-2 px-5">
        <span className="pointer-events-none absolute -left-6 top-1/2 size-16 -translate-y-1/2 rounded-full bg-gradient-brand opacity-20 blur-2xl" />
        {/* Source asset is 202x235 (not square) -- height set to match that aspect ratio
            so Next/Image doesn't warn about (and silently stretch to fix) a mismatch. */}
        <Image src="/nexus-icon-v2.png" alt="" width={24} height={28} priority className="relative shrink-0" />
        <span className="relative text-h4 font-semibold text-sidebar-foreground">Nexus</span>
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
