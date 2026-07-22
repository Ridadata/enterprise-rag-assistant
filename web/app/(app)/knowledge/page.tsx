"use client";

import { FileText, Layers, Tags } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/shared/stat-card";
import { StatCardSkeleton } from "@/components/shared/stat-card-skeleton";
import { ErrorState } from "@/components/shared/error-state";
import { SourceTypeChart } from "@/components/knowledge/source-type-chart";
import { useCorpusSummary } from "@/hooks/use-corpus-summary";

export default function KnowledgePage() {
  const { data, isPending } = useCorpusSummary();

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6">
      <div>
        <h2 className="text-h2 text-foreground">Knowledge Base</h2>
        <p className="mt-1 text-body text-muted-foreground">
          A live snapshot of the corpus currently indexed for retrieval.
        </p>
      </div>

      {isPending ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCardSkeleton />
          <StatCardSkeleton />
          <StatCardSkeleton />
        </div>
      ) : data && !data.ok ? (
        <ErrorState result={data} />
      ) : data ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <StatCard label="Documents" value={data.data.document_count} icon={FileText} />
            <StatCard label="Chunks" value={data.data.chunk_count} icon={Layers} />
            <StatCard
              label="Source Types"
              value={Object.keys(data.data.source_types).length}
              icon={Tags}
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Documents by source type</CardTitle>
            </CardHeader>
            <CardContent>
              <SourceTypeChart sourceTypes={data.data.source_types} />
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
