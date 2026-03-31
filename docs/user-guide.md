# Rewind User Guide

A complete walkthrough for experiencing all features of the Rewind platform — from first login to advanced search and organization.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Web Dashboard — Getting Started](#2-web-dashboard--getting-started)
3. [Creating an API Key](#3-creating-an-api-key)
4. [CLI Installation & Login](#4-cli-installation--login)
5. [Syncing Your AI Sessions](#5-syncing-your-ai-sessions)
6. [Dashboard Overview](#6-dashboard-overview)
7. [Browsing Sessions](#7-browsing-sessions)
8. [Session Detail & Replay](#8-session-detail--replay)
9. [Full-Text Search](#9-full-text-search)
10. [Projects](#10-projects)
11. [Tags](#11-tags)
12. [Star & Trash](#12-star--trash)
13. [Keyboard Shortcuts](#13-keyboard-shortcuts)
14. [CLI Reference](#14-cli-reference)
15. [Troubleshooting](#15-troubleshooting)

---

## 1. Overview

Rewind is an AI coding session intelligence platform. It captures conversations from your local AI coding assistants (Claude Code, OpenCode, Gemini CLI), uploads them to a cloud backend, and provides a web dashboard for search, replay, and organization.

**Supported AI tools:**
| Tool | Parser | Session Location |
|------|--------|-----------------|
| Claude Code | `claude` | `~/.claude/projects/**/*.jsonl` |
| OpenCode | `opencode` | `~/.local/share/opencode/opencode.db` |
| Gemini CLI | `gemini` | `~/.gemini/tmp/**/chats/session-*.json` |

**Architecture:**
```
CLI (rewind sync) ──> Backend API ──> PostgreSQL + Azure Blob
Browser ──> Next.js Dashboard ──> BFF Proxy ──> Backend API
```

---

## 2. Web Dashboard — Getting Started

### Open the Dashboard

Navigate to your Rewind frontend URL in a browser:

```
https://app-frontend-rwnd-prod.azurewebsites.net
```

### Sign In with Google

1. Click **Sign in with Google** on the login page
2. Select your Google account and authorize
3. You'll be redirected to the Dashboard

> Only Google OAuth is supported for web login. The backend does not handle OAuth directly — NextAuth v5 manages the entire session lifecycle.

---

## 3. Creating an API Key

Before the CLI can sync sessions, you need an API key.

1. In the sidebar, go to **Settings > API Keys**
2. Optionally enter a **device name** (e.g., "MacBook Pro", "Work Laptop")
3. Click **Create Key**
4. A green banner appears with your key: `rw_a1b2c3d4...`

> **Copy the key immediately** — it is shown only once. If you lose it, delete the key and create a new one.

The key list shows each key's prefix, device name, creation date, and last used date. You can revoke any key by clicking its delete button.

---

## 4. CLI Installation & Login

### Install the CLI

From the repository root:

```bash
cd cli
pip install -e .
```

This installs the `rewind` command globally.

Verify the installation:

```bash
rewind --version
# rewind-cli 0.1.0
```

### Log In

```bash
rewind login --api-url https://app-backend-rwnd-prod.azurewebsites.net
```

When prompted, paste the API key you copied from the dashboard (`rw_...`).

The CLI saves your credentials to `~/.config/rewind/config.json`. You only need to do this once per machine.

### Check Status

```bash
rewind status
```

This displays:
- Authentication status (authenticated / not authenticated)
- API URL
- Device ID (auto-generated UUID for this machine)
- Config directory path
- Tracked sources and their sync cursors (after first sync)

---

## 5. Syncing Your AI Sessions

### Sync All Sources

```bash
rewind sync
```

The CLI discovers sessions from all supported AI tools installed on your machine, parses them into a canonical format, and uploads them to the backend.

### Sync a Specific Source

```bash
rewind sync --source claude      # Only Claude Code sessions
rewind sync --source opencode    # Only OpenCode sessions
rewind sync --source gemini      # Only Gemini CLI sessions
```

### Dry Run

Preview what would be synced without uploading:

```bash
rewind sync --dry-run
```

### Incremental Sync

Subsequent runs of `rewind sync` are incremental — the CLI tracks cursors to avoid re-uploading sessions it has already sent. Cursors are stored alongside your config in `~/.config/rewind/`.

### What Gets Uploaded

For each session:
- **Metadata**: title, source tool, model, project name, timestamps
- **Messages**: each user/assistant message with role, content, timestamps, token counts
- **Raw content**: the original session file, stored in Azure Blob Storage

The backend uses a 4-field idempotency check (`content_hash`, `raw_hash`, `parser_revision`, `schema_version`) to avoid duplicates.

---

## 6. Dashboard Overview

After syncing, return to the web dashboard. The **Dashboard** page shows:

### Stats Cards
- **Total Sessions** — number of synced sessions
- **Total Messages** — aggregate message count
- **Input Tokens** / **Output Tokens** — token usage across all sessions

### Activity Chart
A bar chart showing sessions per day over the last 90 days. Hover over any bar to see the exact count.

### Source Breakdown
A visual breakdown of sessions by source tool (Claude Code, OpenCode, Gemini CLI).

### Recent Sessions
A quick list of your most recent sessions with links to their detail pages.

---

## 7. Browsing Sessions

Navigate to **Sessions** in the sidebar.

### Session List

Each row shows:
- **Star** toggle (click to star/unstar)
- **Title** (click to open the session detail)
- **Source badge** (Claude Code / OpenCode / Gemini CLI)
- **Tags** as colored pills
- **Project name**
- **Model** used (e.g., claude-sonnet-4-20250514)
- **Message count** and **token count**
- **Duration**
- **Relative time** (e.g., "2 hours ago")

### Filtering

Use the dropdowns at the top to filter by:
- **Source** — show only sessions from a specific AI tool
- **Project** — show only sessions from a specific project

### Pagination

Sessions are displayed 20 per page. Use the **Previous** / **Next** buttons at the bottom to navigate.

---

## 8. Session Detail & Replay

Click any session title to open its detail page.

### Session Header
- **Title** with star toggle
- **Source badge** and **tags**
- **Project name** and **model**
- **Stats cards**: message count, duration, input tokens, output tokens
- **Timestamps**: started at, last message at

### Message Replay

Scroll through the full conversation. Each message shows:
- **Role** (user / assistant)
- **Content** — full text including tool use summaries
- **Timestamp**

### Keyboard Navigation

Press **j** to jump to the next message and **k** to go to the previous message.

### Trash a Session

Click the **Trash** button in the session header to soft-delete the session. You'll be redirected to the sessions list. The session can be restored from the Trash page.

---

## 9. Full-Text Search

Rewind provides powerful full-text search across all your synced messages.

### Search Page

Navigate to **Search** in the sidebar, or click the search bar.

- Type your query — results appear after a 300ms debounce
- Results show: source badge, session title, relative time, role badge, and a **highlighted snippet** with matching terms in yellow
- Click any result to jump to the session detail

Search supports natural language queries — PostgreSQL handles stemming and stop words automatically.

### Quick Search (Cmd+K)

Press **Cmd+K** (Mac) or **Ctrl+K** (Windows/Linux) from any dashboard page to open the search dialog.

- Type your query — top 10 results appear instantly
- Navigate with **Arrow Up** / **Arrow Down**
- Press **Enter** to open the selected result
- Press **Escape** to close

---

## 10. Projects

Navigate to **Projects** in the sidebar.

Projects are automatically derived from the `project_name` field in your sessions (typically the working directory). No manual setup is needed.

### Projects Overview

- **Top Projects bar chart** — horizontal bar chart of the top 10 projects by session count
- **Project cards** — each card shows:
  - Session count, message count, total tokens, duration
  - Source badges (which AI tools were used in this project)
  - Last activity timestamp

### Drill Down

Click any project card to view its sessions — this takes you to the Sessions page filtered by that project.

---

## 11. Tags

Navigate to **Settings > Tags** in the sidebar.

Tags let you categorize sessions with colored labels.

### Create a Tag

1. Enter a tag name (max 50 characters)
2. Pick a color from the 10-color palette
3. Click **Create**

### Manage Tags

The tag list shows each tag with its color, name, and session count.

- **Edit name**: click to edit inline
- **Change color**: click the color swatch to pick a new color
- **Delete**: click the delete button (confirms before deleting)

### Apply Tags to Sessions

Tags are applied to individual sessions via the backend API. On the session detail page, tags appear as colored pills next to the title.

---

## 12. Star & Trash

### Starring Sessions

Click the **star icon** on any session row or session detail page to mark it as a favorite. Starred sessions show a filled yellow star. Click again to unstar.

### Trashing Sessions

From a session's detail page, click **Trash** to soft-delete it. Trashed sessions are removed from the main sessions list and search results.

### Restoring Sessions

Navigate to **Trash** in the sidebar.

- Click **Restore** on any individual session to bring it back
- Click **Restore All** to restore all trashed sessions at once

---

## 13. Keyboard Shortcuts

| Shortcut | Where | Action |
|----------|-------|--------|
| `Cmd+K` / `Ctrl+K` | Any dashboard page | Open quick search dialog |
| `Escape` | Search dialog | Close the dialog |
| `Arrow Up` / `Arrow Down` | Search dialog | Navigate results |
| `Enter` | Search dialog | Open selected result |
| `j` | Session detail | Next message |
| `k` | Session detail | Previous message |

---

## 14. CLI Reference

```
Usage: rewind [OPTIONS] COMMAND [ARGS]

Commands:
  login    Authenticate with the Rewind API
  sync     Discover and upload AI coding sessions
  status   Show current sync state

Options:
  -v, --version  Show version and exit
  --help         Show help and exit
```

### rewind login

```
Usage: rewind login [OPTIONS]

Options:
  --api-url TEXT  Rewind API base URL [default: http://localhost:8000]
  --help          Show help
```

### rewind sync

```
Usage: rewind sync [OPTIONS]

Options:
  -s, --source TEXT  Filter by source (claude, opencode, gemini)
  --dry-run          Preview without uploading
  --help             Show help
```

### rewind status

```
Usage: rewind status [OPTIONS]

Options:
  --help  Show help
```

---

## 15. Troubleshooting

### CLI: "Not authenticated"

Run `rewind login` and paste a valid API key from the dashboard.

### CLI: Connection refused

Make sure `--api-url` points to the correct backend URL. For production:
```bash
rewind login --api-url https://app-backend-rwnd-prod.azurewebsites.net
```

### CLI: No sessions found

Check that the AI tool's session files exist at the expected paths:
- Claude Code: `~/.claude/projects/`
- OpenCode: `~/.local/share/opencode/`
- Gemini CLI: `~/.gemini/tmp/`

Use `--source` to narrow down which parser to test.

### Web: Google login fails

Ensure the `AUTH_URL` environment variable is set to the correct frontend URL. The Google OAuth callback must match what's configured in the Google Cloud Console.

### Web: "Configuration" error after login

This usually means `AUTH_URL` is misconfigured. It should be set to:
```
https://app-frontend-rwnd-prod.azurewebsites.net
```

### Search returns no results

Sessions must be synced and their messages chunked before search works. Run `rewind sync` from the CLI, then try searching again.

### Dashboard shows zero stats

Make sure sessions have been synced. Check `rewind status` to see tracked sources and cursor state.
