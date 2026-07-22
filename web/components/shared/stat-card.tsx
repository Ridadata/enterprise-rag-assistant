import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: React.ReactNode;
  icon?: LucideIcon;
  className?: string;
}

export function StatCard({ label, value, icon: Icon, className }: StatCardProps) {
  return (
    <Card className={className}>
      <CardContent>
        <div className="flex items-center justify-between">
          <span className="text-label uppercase tracking-wide text-muted-foreground">
            {label}
          </span>
          {Icon ? <Icon className="size-4 text-muted-foreground" /> : null}
        </div>
        <div className="mt-1 font-mono text-h2 tabular-nums text-foreground">{value}</div>
      </CardContent>
    </Card>
  );
}
