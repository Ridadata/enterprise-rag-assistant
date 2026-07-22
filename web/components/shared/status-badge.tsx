import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type StatusLevel = "high" | "medium" | "low" | "neutral";

const LEVEL_CLASSES: Record<StatusLevel, string> = {
  high: "bg-success/15 text-success border-success/20",
  medium: "bg-warning/15 text-warning border-warning/20",
  low: "bg-destructive/15 text-destructive border-destructive/20",
  neutral: "bg-muted text-muted-foreground border-transparent",
};

/** Matches the confidence thresholds calibrated in generation/answer_generator.py's
 * _confidence_from_chunks, so a chip's color agrees with the backend's own semantics. */
export function scoreLevel(score: number): StatusLevel {
  if (score >= 0.6) return "high";
  if (score >= 0.5) return "medium";
  return "low";
}

export function StatusBadge({
  level,
  children,
  className,
}: {
  level: StatusLevel;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <Badge variant="outline" className={cn(LEVEL_CLASSES[level], className)}>
      {children}
    </Badge>
  );
}
