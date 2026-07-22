"use client";

import { Bar, BarChart, CartesianGrid, Cell, XAxis, YAxis } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";

const LEVEL_COLOR: Record<string, string> = {
  high: "var(--success)",
  medium: "var(--warning)",
  low: "var(--destructive)",
};

const chartConfig = {
  count: { label: "Answers" },
} satisfies ChartConfig;

export function ConfidenceChart({ counts }: { counts: Record<string, number> }) {
  const order = ["high", "medium", "low"];
  const data = [
    ...order.filter((level) => level in counts).map((level) => [level, counts[level]] as const),
    ...Object.entries(counts).filter(([level]) => !order.includes(level)),
  ].map(([level, count]) => ({ level, count }));

  return (
    <ChartContainer config={chartConfig} className="h-56 w-full">
      <BarChart data={data} layout="vertical" margin={{ left: 8 }}>
        <CartesianGrid horizontal={false} stroke="var(--border)" />
        <XAxis type="number" allowDecimals={false} tickLine={false} axisLine={false} />
        <YAxis type="category" dataKey="level" tickLine={false} axisLine={false} width={70} />
        <ChartTooltip content={<ChartTooltipContent />} />
        <Bar dataKey="count" radius={4}>
          {data.map((entry) => (
            <Cell key={entry.level} fill={LEVEL_COLOR[entry.level] ?? "var(--muted-foreground)"} />
          ))}
        </Bar>
      </BarChart>
    </ChartContainer>
  );
}
