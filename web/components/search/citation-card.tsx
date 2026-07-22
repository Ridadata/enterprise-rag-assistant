import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge, scoreLevel } from "@/components/shared/status-badge";
import type { SourceCitation } from "@/lib/types";

export function CitationCard({ source }: { source: SourceCitation }) {
  return (
    <Card>
      <CardContent className="space-y-2">
        <div className="flex items-start justify-between gap-2">
          <span className="text-body font-medium text-foreground">{source.title}</span>
          <StatusBadge level={scoreLevel(source.score)} className="shrink-0">
            {Math.round(source.score * 100)}% match
          </StatusBadge>
        </div>
        <p className="line-clamp-3 text-body-s text-muted-foreground">{source.excerpt}</p>
        <p className="font-mono text-mono-caption text-muted-foreground/70">{source.chunk_id}</p>
      </CardContent>
    </Card>
  );
}
