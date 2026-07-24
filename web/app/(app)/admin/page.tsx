"use client";

import { motion } from "framer-motion";
import { Activity, Clock, HelpCircle, Coins, DollarSign, FileX } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCard } from "@/components/shared/stat-card";
import { StatCardSkeleton } from "@/components/shared/stat-card-skeleton";
import { ErrorState } from "@/components/shared/error-state";
import { ConfidenceChart } from "@/components/admin/confidence-chart";
import { QueriesOverTimeChart } from "@/components/admin/queries-over-time-chart";
import { IngestionStatusChips } from "@/components/admin/ingestion-status-chips";
import { MostCitedTable } from "@/components/admin/most-cited-table";
import { useAdminSummary } from "@/hooks/use-admin-summary";

export default function AdminPage() {
  const { data, isPending } = useAdminSummary();

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-6">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
      >
        <h2 className="text-h2 text-foreground">Admin Analytics</h2>
        <p className="mt-1 text-body text-muted-foreground">
          Usage and quality metrics computed from logged queries and answers. Feedback and
          faithfulness/hallucination scoring aren&apos;t wired up yet, so those sections are
          intentionally omitted rather than shown empty.
        </p>
      </motion.div>

      {isPending ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <StatCardSkeleton key={i} />
          ))}
        </div>
      ) : data && !data.ok ? (
        <ErrorState result={data} />
      ) : data ? (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="space-y-6"
        >
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <StatCard label="Total Queries" value={data.data.total_queries} icon={Activity} />
            <StatCard
              label="Mean Latency"
              value={data.data.mean_latency_ms ? `${Math.round(data.data.mean_latency_ms)}ms` : "-"}
              icon={Clock}
            />
            <StatCard
              label="p95 Latency"
              value={data.data.p95_latency_ms ? `${Math.round(data.data.p95_latency_ms)}ms` : "-"}
              icon={Clock}
            />
            <StatCard
              label="IDK Rate"
              value={`${(data.data.idk_rate * 100).toFixed(1)}%`}
              icon={HelpCircle}
            />
            <StatCard
              label="Tokens In/Out"
              value={`${data.data.total_tokens_in}/${data.data.total_tokens_out}`}
              icon={Coins}
            />
            <StatCard
              label="Est. Cost"
              value={`$${data.data.total_cost_estimate.toFixed(4)}`}
              icon={DollarSign}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Confidence distribution</CardTitle>
              </CardHeader>
              <CardContent>
                <ConfidenceChart counts={data.data.confidence_counts} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Queries over time</CardTitle>
              </CardHeader>
              <CardContent>
                <QueriesOverTimeChart points={data.data.queries_by_day} />
              </CardContent>
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Ingestion status</CardTitle>
              </CardHeader>
              <CardContent>
                <IngestionStatusChips
                  counts={data.data.ingestion_status_counts}
                  mostRecentAt={data.data.most_recent_ingestion_at}
                />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileX className="size-4 text-muted-foreground" />
                  Documents never retrieved
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="font-mono text-h1 tabular-nums text-foreground">
                  {data.data.never_retrieved_document_count}
                </div>
                <p className="mt-1 text-body-s text-muted-foreground">
                  Documents in the corpus that have never appeared in a retrieval result.
                </p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Most cited documents</CardTitle>
            </CardHeader>
            <CardContent>
              <MostCitedTable documents={data.data.most_cited_documents} />
            </CardContent>
          </Card>
        </motion.div>
      ) : null}
    </div>
  );
}
