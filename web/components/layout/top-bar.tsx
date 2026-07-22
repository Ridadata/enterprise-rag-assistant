"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { Menu, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { VisuallyHidden } from "@/components/ui/visually-hidden";
import { SidebarContent } from "@/components/layout/sidebar-content";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { NAV_ITEMS } from "@/components/layout/command-palette";

export function TopBar({ onOpenPalette }: { onOpenPalette: () => void }) {
  const pathname = usePathname();
  const current = NAV_ITEMS.find((item) => item.href === pathname);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // navigator isn't available during SSR -- resolve the shortcut label after mount only,
  // to avoid a server/client render mismatch (defaults to the non-Mac label until then).
  const [shortcutLabel, setShortcutLabel] = useState("Ctrl K");
  useEffect(() => {
    if (navigator.platform.toLowerCase().includes("mac")) {
      setShortcutLabel("⌘K");
    }
  }, []);

  return (
    <header className="flex h-14 items-center justify-between gap-4 border-b border-border px-4 sm:px-6">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          aria-label="Open navigation"
          onClick={() => setMobileNavOpen(true)}
        >
          <Menu className="size-4.5" />
        </Button>
        <h1 className="text-h4 text-foreground">{current?.label ?? "Nexus"}</h1>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          className="hidden gap-2 text-body-s text-muted-foreground sm:flex"
          onClick={onOpenPalette}
        >
          <Search className="size-3.5" />
          Search
          <kbd className="ml-2 rounded border border-border bg-muted px-1.5 py-0.5 font-mono text-[11px]">
            {shortcutLabel}
          </kbd>
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="sm:hidden"
          aria-label="Search"
          onClick={onOpenPalette}
        >
          <Search className="size-4.5" />
        </Button>
        <ThemeToggle />
      </div>

      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-64 bg-sidebar p-0">
          <VisuallyHidden>
            <SheetTitle>Navigation</SheetTitle>
          </VisuallyHidden>
          <SidebarContent onNavigate={() => setMobileNavOpen(false)} />
        </SheetContent>
      </Sheet>
    </header>
  );
}
