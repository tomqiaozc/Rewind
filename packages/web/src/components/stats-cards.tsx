"use client";

import { Clock, MessageSquare, Zap, Hash } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardStats } from "@/lib/types";
import { formatNumber, formatTokens } from "@/lib/format";

interface StatsCardsProps {
  stats: DashboardStats;
}

const cards = [
  {
    title: "Total Sessions",
    icon: Hash,
    getValue: (s: DashboardStats) => formatNumber(s.total_sessions),
  },
  {
    title: "Total Messages",
    icon: MessageSquare,
    getValue: (s: DashboardStats) => formatNumber(s.total_messages),
  },
  {
    title: "Input Tokens",
    icon: Zap,
    getValue: (s: DashboardStats) => formatTokens(s.total_input_tokens),
  },
  {
    title: "Output Tokens",
    icon: Clock,
    getValue: (s: DashboardStats) => formatTokens(s.total_output_tokens),
  },
];

export function StatsCards({ stats }: StatsCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.title}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{card.title}</CardTitle>
            <card.icon className="size-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{card.getValue(stats)}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
