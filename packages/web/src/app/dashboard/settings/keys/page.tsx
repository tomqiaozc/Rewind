"use client";

import { useCallback, useEffect, useState } from "react";
import { Copy, Check, Key, Plus, Trash2 } from "lucide-react";
import { listApiKeys, createApiKey, deleteApiKey } from "@/lib/api";
import type { ApiKey } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

// ── Newly Created Key Banner ──────────────────────────────────────────

function NewKeyBanner({
  plaintext,
  onDismiss,
}: {
  plaintext: string;
  onDismiss: () => void;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(plaintext);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [plaintext]);

  return (
    <Card className="border-green-500/50 bg-green-500/5">
      <CardContent className="py-4">
        <div className="space-y-2">
          <p className="text-sm font-medium text-green-700 dark:text-green-400">
            API key created! Copy it now — you won&apos;t be able to see it again.
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 rounded bg-muted px-3 py-2 text-sm font-mono break-all">
              {plaintext}
            </code>
            <Button variant="outline" size="sm" onClick={handleCopy}>
              {copied ? (
                <Check className="size-3.5 text-green-600" />
              ) : (
                <Copy className="size-3.5" />
              )}
              {copied ? "Copied" : "Copy"}
            </Button>
          </div>
          <Button variant="ghost" size="sm" onClick={onDismiss} className="mt-1">
            Dismiss
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ── Key Row ──────────────────────────────────────────────────────────

function KeyRow({
  apiKey,
  onDelete,
}: {
  apiKey: ApiKey;
  onDelete: (id: string) => Promise<void>;
}) {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = useCallback(async () => {
    const name = apiKey.device_name || "this API key";
    if (!window.confirm(`Revoke ${name}? This cannot be undone.`)) {
      return;
    }
    setDeleting(true);
    try {
      await onDelete(apiKey.id);
    } finally {
      setDeleting(false);
    }
  }, [apiKey, onDelete]);

  const createdAt = new Date(apiKey.created_at).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });

  const lastUsed = apiKey.last_used_at
    ? new Date(apiKey.last_used_at).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "Never";

  return (
    <div className="flex items-center gap-3 rounded-lg border p-3">
      <Key className="size-4 shrink-0 text-muted-foreground" />

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-medium">
            {apiKey.device_name || "Unnamed key"}
          </span>
          {apiKey.key_prefix && (
            <code className="shrink-0 rounded bg-muted px-1.5 py-0.5 text-xs font-mono text-muted-foreground">
              {apiKey.key_prefix}...
            </code>
          )}
        </div>
        <div className="flex gap-4 text-xs text-muted-foreground mt-0.5">
          <span>Created {createdAt}</span>
          <span>Last used: {lastUsed}</span>
        </div>
      </div>

      <Button
        variant="ghost"
        size="icon-xs"
        onClick={handleDelete}
        disabled={deleting}
        aria-label="Revoke key"
      >
        <Trash2 className="size-3 text-destructive" />
      </Button>
    </div>
  );
}

// ── Keys Page ─────────────────────────────────────────────────────────

export default function KeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create form state
  const [deviceName, setDeviceName] = useState("");
  const [creating, setCreating] = useState(false);
  const [newPlaintext, setNewPlaintext] = useState<string | null>(null);

  const fetchKeys = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listApiKeys();
      setKeys(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load API keys");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchKeys();
  }, [fetchKeys]);

  const handleCreate = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setCreating(true);
      setError(null);
      try {
        const result = await createApiKey(deviceName.trim() || undefined);
        setNewPlaintext(result.key);
        setDeviceName("");
        // Re-fetch the full list
        const data = await listApiKeys();
        setKeys(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to create API key");
      } finally {
        setCreating(false);
      }
    },
    [deviceName],
  );

  const handleDelete = useCallback(async (id: string) => {
    await deleteApiKey(id);
    setKeys((prev) => prev.filter((k) => k.id !== id));
  }, []);

  if (error && !loading && keys.length === 0 && !newPlaintext) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <p className="text-muted-foreground">Failed to load API keys</p>
        <p className="text-sm text-destructive mt-1">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">API Keys</h1>
        <p className="text-muted-foreground">
          Manage API keys for CLI authentication
        </p>
      </div>

      {/* New key banner */}
      {newPlaintext && (
        <NewKeyBanner
          plaintext={newPlaintext}
          onDismiss={() => setNewPlaintext(null)}
        />
      )}

      {/* Create key form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="size-4" />
            Create API Key
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="flex items-center gap-2">
            <Input
              placeholder="Device name (optional)"
              value={deviceName}
              onChange={(e) => setDeviceName(e.target.value)}
              maxLength={100}
              disabled={creating}
              className="flex-1"
            />
            <Button type="submit" size="sm" disabled={creating}>
              <Plus className="size-3.5" />
              {creating ? "Creating..." : "Create Key"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Separator />

      {/* Key list */}
      <div>
        <h2 className="mb-3 text-lg font-medium">Your API Keys</h2>

        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-[68px] rounded-lg" />
            ))}
          </div>
        ) : keys.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Key className="size-8 text-muted-foreground/50 mb-2" />
              <p className="text-muted-foreground">
                No API keys yet. Create one to connect the Rewind CLI.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {keys.map((k) => (
              <KeyRow key={k.id} apiKey={k} onDelete={handleDelete} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
