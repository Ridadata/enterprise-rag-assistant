import { StatusBadge, type StatusLevel } from "@/components/shared/status-badge";
import type { IngestionStatusCount } from "@/lib/types";

const STATUS_LEVEL: Record<string, StatusLevel> = {
  ingested: "high",
  pending: "neutral",
  failed: "low",
};

export function IngestionStatusChips({
  counts,
  mostRecentAt,
}: {
  counts: IngestionStatusCount[];
  mostRecentAt: string | null;
}) {
  if (counts.length === 0) {
    return <p className="text-body text-muted-foreground">No documents ingested yet.</p>;
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {counts.map((item) => (
          <StatusBadge key={item.status} level={STATUS_LEVEL[item.status] ?? "neutral"}>
            {item.count} {item.status}
          </StatusBadge>
        ))}
      </div>
      {mostRecentAt ? (
        <p className="text-body-s text-muted-foreground">
          Last ingested: {new Date(mostRecentAt).toLocaleString()}
        </p>
      ) : null}
    </div>
  );
}
