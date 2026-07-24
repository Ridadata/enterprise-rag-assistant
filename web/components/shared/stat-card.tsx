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
    <Card
      className={cn(
        "relative transition-all duration-200 hover:-translate-y-0.5 hover:shadow-glow",
        className,
      )}
    >
      <span className="absolute inset-x-0 top-0 h-0.5 bg-gradient-brand opacity-70" />
      <CardContent>
        <div className="flex items-center justify-between">
          <span className="text-label uppercase tracking-wide text-muted-foreground">
            {label}
          </span>
          {Icon ? (
            <span className="flex size-6 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Icon className="size-3.5" />
            </span>
          ) : null}
        </div>
        <div className="mt-1.5 break-all font-mono text-h2 tabular-nums text-foreground">{value}</div>
      </CardContent>
    </Card>
  );
}
