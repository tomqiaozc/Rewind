"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SOURCE_LABELS, SOURCE_COLORS } from "@/lib/types";

interface SourceBreakdownProps {
  data: Record<string, number>;
}

export function SourceBreakdown({ data }: SourceBreakdownProps) {
  const entries = Object.entries(data).sort(([, a], [, b]) => b - a);
  const total = entries.reduce((sum, [, count]) => sum + count, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Sessions by Source</CardTitle>
      </CardHeader>
      <CardContent>
        {entries.length === 0 ? (
          <p className="text-muted-foreground text-sm">No data yet</p>
        ) : (
          <div className="space-y-3">
            {entries.map(([source, count]) => {
              const pct = total > 0 ? (count / total) * 100 : 0;
              return (
                <div key={source} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span>{SOURCE_LABELS[source] || source}</span>
                    <span className="text-muted-foreground">{count}</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-muted">
                    <div
                      className="h-2 rounded-full transition-all"
                      style={{
                        width: `${pct}%`,
                        backgroundColor:
                          SOURCE_COLORS[source] || "hsl(var(--primary))",
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
