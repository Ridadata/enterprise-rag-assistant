"use client";

import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";
import type { QueryVolumePoint } from "@/lib/types";

const chartConfig = {
  query_count: {
    label: "Queries",
    color: "var(--primary)",
  },
} satisfies ChartConfig;

export function QueriesOverTimeChart({ points }: { points: QueryVolumePoint[] }) {
  return (
    <ChartContainer config={chartConfig} className="h-56 w-full">
      <LineChart data={points} margin={{ left: 8, right: 8 }}>
        <CartesianGrid vertical={false} stroke="var(--border)" />
        <XAxis dataKey="day" tickLine={false} axisLine={false} />
        <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={32} />
        <ChartTooltip content={<ChartTooltipContent />} />
        <Line
          type="monotone"
          dataKey="query_count"
          stroke="var(--color-query_count)"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ChartContainer>
  );
}
