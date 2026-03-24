"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Plus, Tag as TagIcon, Pencil, Trash2 } from "lucide-react";
import { listTags, createTag, updateTag, deleteTag } from "@/lib/api";
import type { Tag } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

const PRESET_COLORS = [
  "#ef4444",
  "#f97316",
  "#eab308",
  "#22c55e",
  "#06b6d4",
  "#3b82f6",
  "#8b5cf6",
  "#ec4899",
  "#6b7280",
  "#78716c",
];

// ── Color Picker ────────────────────────────────────────────────────────

function ColorPicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (color: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {PRESET_COLORS.map((color) => (
        <button
          key={color}
          type="button"
          onClick={() => onChange(color)}
          className="size-6 rounded-full border-2 transition-transform hover:scale-110"
          style={{
            backgroundColor: color,
            borderColor: value === color ? "var(--foreground)" : "transparent",
          }}
          aria-label={`Select color ${color}`}
        />
      ))}
    </div>
  );
}

// ── Tag Row ─────────────────────────────────────────────────────────────

function TagRow({
  tag,
  onUpdate,
  onDelete,
}: {
  tag: Tag;
  onUpdate: (id: string, body: { name?: string; color?: string }) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState(tag.name);
  const [editColor, setEditColor] = useState(tag.color);
  const [showColorPicker, setShowColorPicker] = useState(false);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const handleSave = useCallback(async () => {
    const trimmed = editName.trim();
    if (!trimmed) {
      setEditName(tag.name);
      setEditColor(tag.color);
      setEditing(false);
      setShowColorPicker(false);
      return;
    }

    if (trimmed === tag.name && editColor === tag.color) {
      setEditing(false);
      setShowColorPicker(false);
      return;
    }

    setSaving(true);
    try {
      const body: { name?: string; color?: string } = {};
      if (trimmed !== tag.name) body.name = trimmed;
      if (editColor !== tag.color) body.color = editColor;
      await onUpdate(tag.id, body);
      setEditing(false);
      setShowColorPicker(false);
    } catch {
      // keep editing on error
    } finally {
      setSaving(false);
    }
  }, [editName, editColor, tag, onUpdate]);

  const handleColorChange = useCallback(
    async (color: string) => {
      setEditColor(color);
      // If we're not in name-editing mode, save immediately
      if (!editing) {
        setSaving(true);
        try {
          await onUpdate(tag.id, { color });
          setShowColorPicker(false);
        } catch {
          setEditColor(tag.color);
        } finally {
          setSaving(false);
        }
      }
    },
    [editing, tag, onUpdate],
  );

  const handleDelete = useCallback(async () => {
    if (!window.confirm(`Delete tag "${tag.name}"? This cannot be undone.`)) {
      return;
    }
    await onDelete(tag.id);
  }, [tag, onDelete]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleSave();
      } else if (e.key === "Escape") {
        setEditName(tag.name);
        setEditColor(tag.color);
        setEditing(false);
        setShowColorPicker(false);
      }
    },
    [handleSave, tag],
  );

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 rounded-lg border p-3">
        {/* Color swatch */}
        <button
          type="button"
          onClick={() => setShowColorPicker(!showColorPicker)}
          className="size-5 shrink-0 rounded-full border border-border transition-transform hover:scale-110"
          style={{ backgroundColor: editColor }}
          aria-label="Change tag color"
        />

        {/* Name */}
        <div className="min-w-0 flex-1">
          {editing ? (
            <Input
              ref={inputRef}
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onBlur={handleSave}
              onKeyDown={handleKeyDown}
              maxLength={50}
              disabled={saving}
              className="h-7 text-sm"
            />
          ) : (
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="truncate text-sm font-medium hover:underline"
            >
              {tag.name}
            </button>
          )}
        </div>

        {/* Session count */}
        <span className="shrink-0 text-xs text-muted-foreground">
          {tag.session_count} session{tag.session_count !== 1 ? "s" : ""}
        </span>

        {/* Actions */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={() => {
              setEditing(true);
            }}
            aria-label="Edit tag"
          >
            <Pencil className="size-3" />
          </Button>
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={handleDelete}
            aria-label="Delete tag"
          >
            <Trash2 className="size-3 text-destructive" />
          </Button>
        </div>
      </div>

      {/* Inline color picker — below the tag row */}
      {showColorPicker && (
        <div className="pl-8">
          <ColorPicker value={editColor} onChange={handleColorChange} />
        </div>
      )}
    </div>
  );
}

// ── Tags Page ───────────────────────────────────────────────────────────

export default function TagsPage() {
  const [tags, setTags] = useState<Tag[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create form state
  const [newName, setNewName] = useState("");
  const [newColor, setNewColor] = useState(PRESET_COLORS[5]); // default blue
  const [creating, setCreating] = useState(false);

  const fetchTags = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listTags();
      setTags(data.sort((a, b) => a.name.localeCompare(b.name)));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load tags");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTags();
  }, [fetchTags]);

  const handleCreate = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const trimmed = newName.trim();
      if (!trimmed) return;

      setCreating(true);
      try {
        const tag = await createTag({ name: trimmed, color: newColor });
        setTags((prev) =>
          [...prev, tag].sort((a, b) => a.name.localeCompare(b.name)),
        );
        setNewName("");
        setNewColor(PRESET_COLORS[5]);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to create tag");
      } finally {
        setCreating(false);
      }
    },
    [newName, newColor],
  );

  const handleUpdate = useCallback(
    async (id: string, body: { name?: string; color?: string }) => {
      const updated = await updateTag(id, body);
      setTags((prev) =>
        prev
          .map((t) => (t.id === id ? { ...t, ...updated } : t))
          .sort((a, b) => a.name.localeCompare(b.name)),
      );
    },
    [],
  );

  const handleDelete = useCallback(async (id: string) => {
    await deleteTag(id);
    setTags((prev) => prev.filter((t) => t.id !== id));
  }, []);

  if (error && !loading && tags.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <p className="text-muted-foreground">Failed to load tags</p>
        <p className="text-sm text-destructive mt-1">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">Manage tags for your sessions</p>
      </div>

      {/* Create tag form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TagIcon className="size-4" />
            Create Tag
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="space-y-3">
            <div className="flex items-center gap-2">
              <div
                className="size-5 shrink-0 rounded-full border border-border"
                style={{ backgroundColor: newColor }}
              />
              <Input
                placeholder="Tag name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                maxLength={50}
                disabled={creating}
                className="flex-1"
              />
              <Button type="submit" size="sm" disabled={creating || !newName.trim()}>
                <Plus className="size-3.5" />
                Create
              </Button>
            </div>
            <ColorPicker value={newColor} onChange={setNewColor} />
          </form>
        </CardContent>
      </Card>

      <Separator />

      {/* Tag list */}
      <div>
        <h2 className="mb-3 text-lg font-medium">Your Tags</h2>

        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-[52px] rounded-lg" />
            ))}
          </div>
        ) : tags.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <TagIcon className="size-8 text-muted-foreground/50 mb-2" />
              <p className="text-muted-foreground">
                No tags yet. Create one to organize your sessions.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-2">
            {tags.map((tag) => (
              <TagRow
                key={tag.id}
                tag={tag}
                onUpdate={handleUpdate}
                onDelete={handleDelete}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
