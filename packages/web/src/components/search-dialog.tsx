"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowDown,
  ArrowUp,
  CornerDownLeft,
  Loader2,
  Search,
} from "lucide-react";
import { searchSessions } from "@/lib/api";
import type { SearchResult } from "@/lib/types";
import { SOURCE_LABELS } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

export function SearchDialog() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const resultRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const router = useRouter();

  // ── Global keyboard shortcut: Cmd+K / Ctrl+K ───────────────────────
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // ── Auto-focus input when dialog opens ──────────────────────────────
  useEffect(() => {
    if (open) {
      // Small delay so the DOM is ready
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  // ── Close helper ────────────────────────────────────────────────────
  const closeDialog = useCallback(() => {
    setOpen(false);
    setQuery("");
    setResults([]);
    setSearched(false);
    setSelectedIndex(0);
  }, []);

  // ── Search with debounce ────────────────────────────────────────────
  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) {
      setResults([]);
      setSearched(false);
      setLoading(false);
      return;
    }
    setLoading(true);
    setSearched(true);
    try {
      const data = await searchSessions({ q: q.trim(), limit: 10 });
      setResults(data.results);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!open) return;
    debounceRef.current = setTimeout(() => doSearch(query), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, doSearch, open]);

  // ── Reset selection when results change ─────────────────────────────
  useEffect(() => {
    setSelectedIndex(0);
  }, [results]);

  // ── Navigate to a result ────────────────────────────────────────────
  const navigateToResult = useCallback(
    (result: SearchResult) => {
      router.push(`/dashboard/sessions/${result.session_id}`);
      closeDialog();
    },
    [router, closeDialog],
  );

  // ── Input keyboard handling ─────────────────────────────────────────
  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      e.preventDefault();
      closeDialog();
      return;
    }

    if (results.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => {
        const next = prev < results.length - 1 ? prev + 1 : 0;
        resultRefs.current[next]?.scrollIntoView({ block: "nearest" });
        return next;
      });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => {
        const next = prev > 0 ? prev - 1 : results.length - 1;
        resultRefs.current[next]?.scrollIntoView({ block: "nearest" });
        return next;
      });
    } else if (e.key === "Enter") {
      e.preventDefault();
      const selected = results[selectedIndex];
      if (selected) navigateToResult(selected);
    }
  }

  if (!open) return null;

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm"
        onClick={closeDialog}
        aria-hidden="true"
      />

      {/* Dialog content */}
      <div className="fixed left-1/2 top-1/2 z-50 w-full max-w-lg -translate-x-1/2 -translate-y-1/2">
        <div className="rounded-xl border bg-background shadow-2xl">
          {/* Search input */}
          <div className="flex items-center border-b px-3">
            <Search className="mr-2 size-4 shrink-0 text-muted-foreground" />
            <input
              ref={inputRef}
              type="text"
              placeholder="Search sessions..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground"
            />
            {loading && (
              <Loader2 className="ml-2 size-4 shrink-0 animate-spin text-muted-foreground" />
            )}
          </div>

          {/* Results area */}
          <div className="max-h-[300px] overflow-y-auto p-2">
            {!searched && !loading && (
              <p className="py-6 text-center text-sm text-muted-foreground">
                Search sessions...
              </p>
            )}

            {searched && !loading && results.length === 0 && (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No results found
              </p>
            )}

            {results.length > 0 && (
              <div className="space-y-1">
                {results.map((result, i) => (
                  <button
                    key={`${result.session_id}-${result.message_id}-${i}`}
                    ref={(el) => {
                      resultRefs.current[i] = el;
                    }}
                    type="button"
                    onClick={() => navigateToResult(result)}
                    onMouseEnter={() => setSelectedIndex(i)}
                    className={`w-full cursor-pointer rounded-lg px-3 py-2 text-left transition-colors ${
                      i === selectedIndex
                        ? "bg-accent text-accent-foreground"
                        : "hover:bg-muted/50"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="text-xs">
                        {SOURCE_LABELS[result.source] || result.source}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        {result.role}
                      </Badge>
                      <span className="truncate text-sm font-medium">
                        {result.session_title || "Untitled session"}
                      </span>
                    </div>
                    <p
                      className="mt-1 text-xs text-muted-foreground line-clamp-2 [&_mark]:bg-yellow-200 [&_mark]:text-foreground dark:[&_mark]:bg-yellow-500/30"
                      dangerouslySetInnerHTML={{ __html: result.snippet }}
                    />
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Footer hints */}
          <div className="flex items-center gap-4 border-t px-3 py-2 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <ArrowUp className="size-3" />
              <ArrowDown className="size-3" />
              navigate
            </span>
            <span className="inline-flex items-center gap-1">
              <CornerDownLeft className="size-3" />
              open
            </span>
            <span className="ml-auto">
              <kbd className="rounded border bg-muted px-1.5 py-0.5 font-mono text-[10px]">
                esc
              </kbd>{" "}
              close
            </span>
          </div>
        </div>
      </div>
    </>
  );
}
