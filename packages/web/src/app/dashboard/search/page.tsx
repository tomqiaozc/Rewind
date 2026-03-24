"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import { searchSessions } from "@/lib/api";
import type { SearchResult } from "@/lib/types";
import { SOURCE_LABELS } from "@/lib/types";
import { formatRelativeTime } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      setTotal(0);
      setSearched(false);
      return;
    }
    setLoading(true);
    setSearched(true);
    try {
      const data = await searchSessions({ q: q.trim(), limit: 50 });
      setResults(data.results);
      setTotal(data.total);
    } catch {
      setResults([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(query), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, doSearch]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Search</h1>
        <p className="text-muted-foreground">
          Full-text search across all your sessions
        </p>
      </div>

      {/* Search input */}
      <div className="relative max-w-2xl">
        <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          type="text"
          placeholder="Search sessions..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-10"
          autoFocus
        />
      </div>

      {/* Results */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
      ) : searched ? (
        results.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Search className="mb-2 size-8 text-muted-foreground" />
              <p className="text-muted-foreground">
                No results found for &ldquo;{query}&rdquo;
              </p>
            </CardContent>
          </Card>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">
              {total} result{total !== 1 ? "s" : ""} for &ldquo;{query}&rdquo;
            </p>
            <div className="space-y-3">
              {results.map((result, i) => (
                <Link
                  key={`${result.session_id}-${result.message_id}-${i}`}
                  href={`/dashboard/sessions/${result.session_id}`}
                  className="block rounded-lg border p-4 transition-colors hover:bg-muted/50"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-xs">
                        {SOURCE_LABELS[result.source] || result.source}
                      </Badge>
                      <span className="text-sm font-medium">
                        {result.session_title || "Untitled session"}
                      </span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {formatRelativeTime(result.started_at)}
                    </span>
                  </div>
                  <div className="mt-2 flex items-start gap-2">
                    <Badge
                      variant="outline"
                      className="mt-0.5 shrink-0 text-xs"
                    >
                      {result.role}
                    </Badge>
                    <p
                      className="text-sm text-muted-foreground line-clamp-3 [&_mark]:bg-yellow-200 [&_mark]:text-foreground dark:[&_mark]:bg-yellow-500/30"
                      dangerouslySetInnerHTML={{ __html: result.snippet }}
                    />
                  </div>
                </Link>
              ))}
            </div>
          </>
        )
      ) : (
        <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
          <Search className="mb-2 size-8" />
          <p>Start typing to search your sessions</p>
          <p className="text-sm mt-1">
            Search across all message content with full-text search
          </p>
        </div>
      )}
    </div>
  );
}
