---
type: internal-doc
tags: [docs-internal, web-ui, components]
date_updated: 2026-06-10
---

# Sidebar

**File:** `ui/components/sidebar/Sidebar.tsx`

## Purpose

Left navigation panel for session and project management. Collapsible between 240px and 48px.

## Structure

- **Header**: "aede" title + collapse toggle
- **New Session**: Button to start a fresh session
- **Project List**: Collapsible accordions grouping sessions by project directory. Each project shows its sessions via `SessionSearch` component. "Add project" button at the bottom.
- **Chats Section**: Sessions without a project directory, grouped under "Chats" accordion.
- **Footer**: Profile and Settings icon buttons.

## Project Management

Integrated with `FolderPicker` for adding projects and `RemoveProjectDialog` for project removal actions (remove from list, delete folder, remove .git).

## Session Navigation

`SessionSearch` inside each project section provides search/filter over sessions. Props: `sessions`, `activeSessionId`, `onSelectSession` callbacks.
