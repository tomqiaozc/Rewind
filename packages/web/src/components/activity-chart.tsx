"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DayCount } from "@/lib/types";

interface ActivityChartProps {
  data: DayCount[];
}

function fillDays(data: DayCount[], days: number) {
  const map = new Map(data.map((d) => [d.date, d.count]));
  const result: { date: string; sessions: number }[] = [];
  const today = new Date();
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    result.push({ date: key.slice(5), sessions: map.get(key) || 0 });
  }
  return result;
}

export function ActivityChart({ data }: ActivityChartProps) {
  const chartData = fillDays(data, 30);

  const hasActivity = chartData.some((d) => d.sessions > 0);

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Daily Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {!hasActivity ? (
          <div className="flex h-[260px] items-center justify-center text-muted-foreground">
            No activity data yet
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData} barCategoryGap="20%">
              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
                className="stroke-border"
              />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                interval={Math.floor(chartData.length / 7)}
                className="fill-muted-foreground"
              />
              <YAxis
                tick={{ fontSize: 11 }}
                tickLine={false}
                axisLine={false}
                width={32}
                className="fill-muted-foreground"
                allowDecimals={false}
              />
              <Tooltip
                cursor={{ fill: "hsl(var(--muted))", opacity: 0.5 }}
                contentStyle={{
                  backgroundColor: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                  fontSize: "12px",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.1)",
                }}
              />
              <Bar
                dataKey="sessions"
                fill="hsl(142 71% 45%)"
                radius={[3, 3, 0, 0]}
                maxBarSize={24}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
