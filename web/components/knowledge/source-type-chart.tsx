"use client";

import { useState } from "react";
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { Table2, BarChart3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";

const chartConfig = {
  count: {
    label: "Documents",
    color: "var(--primary)",
  },
} satisfies ChartConfig;

export function SourceTypeChart({ sourceTypes }: { sourceTypes: Record<string, number> }) {
  const [view, setView] = useState<"chart" | "table">("chart");
  const data = Object.entries(sourceTypes)
    .map(([source_type, count]) => ({ source_type, count }))
    .sort((a, b) => b.count - a.count);

  return (
    <div>
      <div className="mb-3 flex items-center justify-end gap-1">
        <Button
          variant={view === "chart" ? "secondary" : "ghost"}
          size="icon-sm"
          aria-label="Chart view"
          onClick={() => setView("chart")}
        >
          <BarChart3 />
        </Button>
        <Button
          variant={view === "table" ? "secondary" : "ghost"}
          size="icon-sm"
          aria-label="Table view"
          onClick={() => setView("table")}
        >
          <Table2 />
        </Button>
      </div>

      {view === "chart" ? (
        <ChartContainer config={chartConfig} className="h-64 w-full">
          <BarChart data={data} layout="vertical" margin={{ left: 8 }}>
            <CartesianGrid horizontal={false} stroke="var(--border)" />
            <XAxis type="number" allowDecimals={false} tickLine={false} axisLine={false} />
            <YAxis
              type="category"
              dataKey="source_type"
              tickLine={false}
              axisLine={false}
              width={110}
            />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Bar dataKey="count" fill="var(--color-count)" radius={4} />
          </BarChart>
        </ChartContainer>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Source type</TableHead>
              <TableHead className="text-right">Documents</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((row) => (
              <TableRow key={row.source_type}>
                <TableCell className="font-medium">{row.source_type}</TableCell>
                <TableCell className="text-right font-mono tabular-nums">{row.count}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
