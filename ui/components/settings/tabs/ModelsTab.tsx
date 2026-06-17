"use client";
import React, {
  useState,
  useCallback,
  useMemo,
  useEffect,
  useRef,
} from "react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useCredentials,
  useAddCredential,
  useDeleteCredential,
} from "@/hooks/useCredentials";
import {
  useStatus,
  useConnect,
  useDisconnect,
  useRegister,
  useConfigs,
  useDeleteAgent,
} from "@/hooks/useAcpAgents";
import {
  useModels,
  useAddModel,
  useDeleteModel,
  useUpdateModels,
  useResetModels,
} from "@/hooks/useModels";
import {
  DndContext,
  closestCenter,
  type DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  Plus,
  Trash2,
  Key,
  Wifi,
  WifiOff,
  GripVertical,
  RotateCcw,
  Settings2,
  X,
  Check,
  ChevronsUpDown,
  ExternalLink,
  Loader2,
} from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandGroup,
  CommandItem,
} from "@/components/ui/command";
import type { Model } from "@/hooks/useModels";
import { cn } from "@/lib/utils";
import { apiFetch } from "@/lib/api";

const ACP_AGENTS_META = [
  {
    name: "claude-code",
    label: "Claude Code",
    command: "npx",
    args: ["-y", "@agentclientprotocol/claude-agent-acp"],
    credentials_ref: "ANTHROPIC_API_KEY",
  },
  {
    name: "codex",
    label: "Codex",
    command: "npx",
    args: ["-y", "@agentclientprotocol/codex-acp"],
    credentials_ref: "OPENAI_API_KEY",
  },
  {
    name: "gemini",
    label: "Gemini",
    command: "gemini",
    args: ["--acp"],
    credentials_ref: "GEMINI_API_KEY",
  },
  { name: "agy", label: "Antigravity", command: "agy", args: ["--acp"] },
  { name: "cline", label: "Cline", command: "cline", args: ["--acp"] },
  {
    name: "cursor",
    label: "Cursor",
    command: "cursor-agent",
    args: ["--acp"],
    credentials_ref: "CURSOR_API_KEY",
  },
  { name: "goose", label: "Goose", command: "goose", args: ["acp"] },
];

const AUTH_CATEGORIES = [
  { value: "anthropic", label: "Anthropic" },
  { value: "openai", label: "OpenAI" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "openrouter", label: "OpenRouter" },
  { value: "google-ai", label: "Google AI" },
  { value: "claude-code", label: "Claude Code (ACP)" },
  { value: "gemini", label: "Gemini (ACP)" },
  { value: "agy", label: "Antigravity (ACP)" },
  { value: "codex", label: "Codex (ACP)" },
  { value: "cline", label: "Cline (ACP)" },
  { value: "cursor", label: "Cursor (ACP)" },
  { value: "goose", label: "Goose (ACP)" },
  { value: "opencode-zen", label: "OpenCode Zen" },
  { value: "opencode-go", label: "OpenCode Go" },
];

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  deepseek: "DeepSeek",
  openrouter: "OpenRouter",
  "google-ai": "Google AI",
  codex: "Codex (ACP)",
  "claude-code": "Claude Code (ACP)",
  gemini: "Gemini (ACP)",
  agy: "Antigravity (ACP)",
  cline: "Cline (ACP)",
  cursor: "Cursor (ACP)",
  goose: "Goose (ACP)",
  "opencode-zen": "OpenCode Zen",
  "opencode-go": "OpenCode Go",
};

const PROVIDER_BADGE_COLORS: Record<string, string> = {
  anthropic: "bg-amber-500/10 text-amber-600 dark:text-amber-400",
  openai: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400",
  deepseek: "bg-blue-500/10 text-blue-600 dark:text-blue-400",
  openrouter: "bg-violet-500/10 text-violet-600 dark:text-violet-400",
  "google-ai": "bg-sky-500/10 text-sky-600 dark:text-sky-400",
  codex: "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400",
  "claude-code": "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400",
  gemini: "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400",
  agy: "bg-sky-500/10 text-sky-600 dark:text-sky-400",
  cline: "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400",
  cursor: "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400",
  goose: "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400",
  "opencode-zen": "bg-purple-500/10 text-purple-600 dark:text-purple-400",
  "opencode-go": "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400",
};

interface ModelSuggestion {
  id: string;
  label: string;
  provider: string;
}

const MODEL_SUGGESTIONS: ModelSuggestion[] = [
  { label: "Claude Fable 5", id: "claude-fable-5", provider: "anthropic" },
  { label: "Claude Opus 4.8", id: "claude-opus-4-8", provider: "anthropic" },
  {
    label: "Claude Sonnet 4.6",
    id: "claude-sonnet-4-6",
    provider: "anthropic",
  },
  {
    label: "Claude Haiku 4.5",
    id: "claude-haiku-4-5-20251001",
    provider: "anthropic",
  },
  { label: "GPT-5.5", id: "gpt-5.5", provider: "openai" },
  { label: "GPT-5.5 Pro", id: "gpt-5.5-pro", provider: "openai" },
  { label: "GPT-5.4", id: "gpt-5.4", provider: "openai" },
  { label: "GPT-5.4 Pro", id: "gpt-5.4-pro", provider: "openai" },
  { label: "GPT-5.4 Mini", id: "gpt-5.4-mini", provider: "openai" },
  { label: "GPT-5.4 Nano", id: "gpt-5.4-nano", provider: "openai" },
  { label: "GPT-5.3 Codex", id: "gpt-5.3-codex", provider: "openai" },
  { label: "DeepSeek Chat (V4)", id: "deepseek-chat", provider: "deepseek" },
  {
    label: "DeepSeek V4 Pro",
    id: "deepseek/deepseek-v4-pro",
    provider: "deepseek",
  },
  {
    label: "DeepSeek V4 Flash",
    id: "deepseek/deepseek-v4-flash",
    provider: "deepseek",
  },
  { label: "DeepSeek Reasoner", id: "deepseek-reasoner", provider: "deepseek" },
  { label: "OpenRouter Auto", id: "openrouter/auto", provider: "openrouter" },
  {
    label: "DeepSeek V4 Pro",
    id: "deepseek/deepseek-v4-pro",
    provider: "openrouter",
  },
  {
    label: "DeepSeek V4 Flash",
    id: "deepseek/deepseek-v4-flash",
    provider: "openrouter",
  },
  { label: "Qwen 3.7 Plus", id: "qwen/qwen3.7-plus", provider: "openrouter" },
  { label: "MiniMax M3", id: "minimax/minimax-m3", provider: "openrouter" },
  {
    label: "Qwen 3.5 Plus",
    id: "qwen/qwen3.5-plus-20260420",
    provider: "openrouter",
  },
  { label: "MiMo V2 Pro", id: "xiaomi/mimo-v2-pro", provider: "openrouter" },
  {
    label: "Qwen 3.7 Max",
    id: "qwen/qwen3.7-max",
    provider: "openrouter",
  },
  { label: "MiMo V2.5", id: "xiaomi/mimo-v2.5", provider: "openrouter" },
  {
    label: "MiMo V2.5 Pro",
    id: "xiaomi/mimo-v2.5-pro",
    provider: "openrouter",
  },
  { label: "Gemini 3.5 Flash", id: "gemini-3.5-flash", provider: "google-ai" },
  {
    label: "Gemini 3.1 Flash Lite",
    id: "gemini-3.1-flash-lite",
    provider: "google-ai",
  },
  {
    label: "Gemini 3.1 Pro Preview",
    id: "gemini-3.1-pro-preview",
    provider: "google-ai",
  },
  { label: "Gemini 2.5 Pro", id: "gemini-2.5-pro", provider: "google-ai" },
  { label: "Gemini 2.5 Flash", id: "gemini-2.5-flash", provider: "google-ai" },
  { label: "Codex", id: "codex", provider: "codex" },
  { label: "Codex / GPT-5.5", id: "codex/gpt-5.5", provider: "codex" },
  {
    label: "Codex / GPT-5.3-Codex",
    id: "codex/gpt-5.3-codex",
    provider: "codex",
  },
  { label: "Codex / o3", id: "codex/o3", provider: "codex" },
  { label: "Codex / o4-mini", id: "codex/o4-mini", provider: "codex" },
  { label: "Claude Code", id: "claude-code", provider: "claude-code" },
  {
    label: "Claude Code / Fable 5",
    id: "claude-code/fable-5",
    provider: "claude-code",
  },
  {
    label: "Claude Code / Opus 4.8",
    id: "claude-code/opus-4-8",
    provider: "claude-code",
  },
  // {
  //   label: "Claude Code / Opus 4.7",
  //   id: "claude-code/opus-4-7",
  //   provider: "claude-code",
  // },
  {
    label: "Claude Code / Sonnet 4.6",
    id: "claude-code/sonnet-4-6",
    provider: "claude-code",
  },
  {
    label: "Claude Code / Haiku 4.5",
    id: "claude-code/haiku-4-5",
    provider: "claude-code",
  },
  { label: "Gemini", id: "gemini", provider: "gemini" },
  { label: "Antigravity", id: "agy", provider: "agy" },
  {
    label: "Antigravity / Gemini 3.1 Pro",
    id: "agy/gemini-3-1-pro",
    provider: "agy",
  },
  {
    label: "Antigravity / Gemini 3.5 Flash",
    id: "agy/gemini-3-5-flash",
    provider: "agy",
  },
  {
    label: "Antigravity / Claude Sonnet 4.6",
    id: "agy/claude-sonnet-4-6",
    provider: "agy",
  },
  {
    label: "Antigravity / Claude Opus 4.6",
    id: "agy/claude-opus-4-6",
    provider: "agy",
  },
  { label: "Cline", id: "cline", provider: "cline" },
  { label: "Cursor", id: "cursor", provider: "cursor" },
  { label: "Goose", id: "goose", provider: "goose" },
  {
    label: "Goose / Claude Sonnet 4.6",
    id: "goose/anthropic-claude-sonnet-4-6",
    provider: "goose",
  },
  { label: "Goose / GPT-4o", id: "goose/openai-gpt-4o", provider: "goose" },
  // OpenCode Zen (free + paid)
  { label: "DeepSeek V4 Flash Free", id: "deepseek-v4-flash-free", provider: "opencode-zen" },
  { label: "Nemotron 3 Ultra Free", id: "nemotron-3-ultra-free", provider: "opencode-zen" },
  { label: "Big Pickle", id: "big-pickle", provider: "opencode-zen" },
  { label: "MIMO V2.5 Free", id: "mimo-v2.5-free", provider: "opencode-zen" },
  { label: "North Mini Code Free", id: "north-mini-code-free", provider: "opencode-zen" },
  { label: "Grok Build 0.1", id: "grok-build-0.1", provider: "opencode-zen" },
  { label: "Kimi K2.5", id: "kimi-k2.5", provider: "opencode-zen" },
  // OpenCode Go (OpenAI-compatible)
  { label: "DeepSeek V4 Pro (Go)", id: "deepseek-v4-pro", provider: "opencode-go" },
  { label: "DeepSeek V4 Flash (Go)", id: "deepseek-v4-flash", provider: "opencode-go" },
  { label: "GLM-5.1 (Go)", id: "glm-5.1", provider: "opencode-go" },
  { label: "GLM-5 (Go)", id: "glm-5", provider: "opencode-go" },
  { label: "Kimi K2.7 (Go)", id: "kimi-k2.7", provider: "opencode-go" },
  { label: "Kimi K2.6 (Go)", id: "kimi-k2.6", provider: "opencode-go" },
  { label: "MIMO V2.5 (Go)", id: "mimo-v2.5", provider: "opencode-go" },
  { label: "MIMO V2.5 Pro (Go)", id: "mimo-v2.5-pro", provider: "opencode-go" },
  // OpenCode Go (Anthropic-compatible)
  { label: "MiniMax M3 (Go)", id: "minimax-m3", provider: "opencode-go" },
  { label: "MiniMax M2.7 (Go)", id: "minimax-m2.7", provider: "opencode-go" },
  { label: "MiniMax M2.5 (Go)", id: "minimax-m2.5", provider: "opencode-go" },
  { label: "Qwen 3.7 Max (Go)", id: "qwen3.7-max", provider: "opencode-go" },
  { label: "Qwen 3.7 Plus (Go)", id: "qwen3.7-plus", provider: "opencode-go" },
  { label: "Qwen 3.6 Plus (Go)", id: "qwen3.6-plus", provider: "opencode-go" },
];

function autoLabel(modelId: string, provider: string): string {
  if (!modelId || !provider) return "";
  const known = MODEL_SUGGESTIONS.find(
    (s) => s.id === modelId && s.provider === provider,
  );
  if (known) return known.label;
  const pLabel = PROVIDER_LABELS[provider] || provider;
  return `${modelId} (${pLabel})`;
}

function SortableModelRow({
  model,
  onDelete,
  onConfigure,
}: {
  model: Model;
  onDelete: (id: string) => void;
  onConfigure: (model: Model) => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: model.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-2 px-3 py-2 rounded-md border border-border/40 bg-muted/20"
    >
      <button
        {...attributes}
        {...listeners}
        className="cursor-grab active:cursor-grabbing text-muted-foreground hover:text-foreground p-0.5"
      >
        <GripVertical className="w-3.5 h-3.5" />
      </button>
      <span className="text-xs font-medium flex-1 truncate">{model.label}</span>
      <span
        className={cn(
          "text-[10px] px-1.5 py-0.5 rounded-full font-medium",
          PROVIDER_BADGE_COLORS[model.provider] ??
            "bg-muted text-muted-foreground",
        )}
      >
        {PROVIDER_LABELS[model.provider] || model.provider}
      </span>
      <code className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded font-mono hidden sm:inline">
        {model.id}
      </code>
      <Button
        variant="ghost"
        size="icon-sm"
        className="h-6 w-6 text-muted-foreground hover:text-foreground shrink-0"
        onClick={() => onConfigure(model)}
      >
        <Settings2 className="w-3 h-3" />
      </Button>
      <Button
        variant="ghost"
        size="icon-sm"
        className="h-6 w-6 text-muted-foreground hover:text-destructive shrink-0"
        onClick={() => onDelete(model.id)}
      >
        <Trash2 className="w-3 h-3" />
      </Button>
    </div>
  );
}

function InlineModelForm({
  mode,
  model,
  onSave,
  onCancel,
  onDelete,
}: {
  mode: "add" | "edit";
  model?: Model;
  onSave: (label: string, id: string, provider: string) => void;
  onCancel: () => void;
  onDelete?: () => void;
}) {
  const [provider, setProvider] = useState("");
  const [modelId, setModelId] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);
  const formRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (mode === "edit" && model) {
      setProvider(model.provider);
      setModelId(model.id);
    } else {
      setProvider("");
      setModelId("");
    }
  }, [mode, model]);

  useEffect(() => {
    if (provider) setShowSuggestions(true);
  }, [provider]);

  // Intentionally no manual handleClickOutside here — Popover's onOpenChange handles it,
  // and a portal-based PopoverContent would live outside formRef's DOM hierarchy.

  const filteredSuggestions = useMemo(() => {
    if (!provider) return [];
    return MODEL_SUGGESTIONS.filter((s) => {
      if (s.provider !== provider) return false;
      if (!modelId) return true;
      return (
        s.id.toLowerCase().includes(modelId.toLowerCase()) ||
        s.label.toLowerCase().includes(modelId.toLowerCase())
      );
    });
  }, [provider, modelId]);

  const displayLabel = autoLabel(modelId, provider);

  const handleSave = () => {
    if (!modelId || !provider) return;
    onSave(displayLabel || modelId, modelId, provider);
  };

  return (
    <div
      ref={formRef}
      className="border border-border/60 rounded-lg bg-muted/30 p-3 space-y-3"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold">
          {mode === "add" ? "Add Model" : "Configure Model"}
        </span>
        <Button
          variant="ghost"
          size="icon-sm"
          className="h-5 w-5 text-muted-foreground"
          onClick={onCancel}
        >
          <X className="w-3 h-3" />
        </Button>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1">
          <label className="text-[10px] font-medium text-muted-foreground">
            Provider
          </label>
          <Select
            value={provider || null}
            onValueChange={(v) => {
              setProvider(v ?? "");
              setModelId("");
            }}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Select…" />
            </SelectTrigger>
            <SelectContent>
              {AUTH_CATEGORIES.map((p) => (
                <SelectItem key={p.value} value={p.value} className="text-xs">
                  {p.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <label className="text-[10px] font-medium text-muted-foreground">
            Model ID
          </label>
          <Popover open={showSuggestions} onOpenChange={setShowSuggestions}>
            <PopoverTrigger
              render={
                <Button
                  variant="outline"
                  role="combobox"
                  aria-expanded={showSuggestions}
                  className="w-full h-8 justify-between text-xs font-normal"
                >
                  {modelId ? (
                    modelId
                  ) : (
                    <span className="text-muted-foreground">
                      Select or type a model…
                    </span>
                  )}
                  <ChevronsUpDown className="size-3.5 shrink-0 opacity-50" />
                </Button>
              }
            />
            <PopoverContent className="w-(--anchor-width) p-0" align="start">
              <Command>
                <CommandInput
                  placeholder="Search model…"
                  className="h-8"
                  value={modelId}
                  onValueChange={setModelId}
                />
                <CommandList>
                  <CommandEmpty>
                    {modelId ? (
                      <button
                        className="w-full text-left px-2 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted rounded-sm cursor-pointer"
                        onClick={() => {
                          setModelId(modelId);
                          setShowSuggestions(false);
                        }}
                      >
                        Use &ldquo;{modelId}&rdquo; as custom model ID
                      </button>
                    ) : (
                      "No models found"
                    )}
                  </CommandEmpty>
                  <CommandGroup>
                    {filteredSuggestions.map((s) => (
                      <CommandItem
                        key={s.id}
                        value={s.label}
                        onSelect={() => {
                          setModelId(s.id);
                          setShowSuggestions(false);
                        }}
                        className="text-xs"
                      >
                        <Check
                          className={cn(
                            "size-3.5 mr-2",
                            modelId === s.id ? "opacity-100" : "opacity-0",
                          )}
                        />
                        <span>{s.label}</span>
                        <span className="ml-auto text-[10px] text-muted-foreground">
                          {s.id}
                        </span>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        </div>
      </div>
      <div className="space-y-1">
        <label className="text-[10px] font-medium text-muted-foreground">
          Displayed name
        </label>
        <div className="h-8 flex items-center px-3 rounded-lg border border-input/50 bg-input/20 text-xs text-muted-foreground">
          {displayLabel || (
            <span className="italic">Select provider and model</span>
          )}
        </div>
      </div>
      <div className="flex items-center justify-between pt-1">
        <div>
          {mode === "edit" && onDelete && (
            <Button
              variant="destructive"
              size="sm"
              className="h-7 text-xs"
              onClick={onDelete}
            >
              <Trash2 className="w-3 h-3 mr-1" /> Delete
            </Button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={onCancel}
          >
            Cancel
          </Button>
          <Button
            size="sm"
            className="h-7 text-xs"
            onClick={handleSave}
            disabled={!modelId || !provider || !displayLabel}
          >
            <Check className="w-3 h-3 mr-1" /> {mode === "add" ? "Add" : "Save"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function _acpErrorMsg(err: unknown): string {
  const msg =
    typeof err === "string"
      ? err
      : err instanceof Error
        ? err.message
        : "Unknown error";
  try {
    const parsed = JSON.parse(msg.replace(/^\d+\s*/, ""));
    return parsed.detail ?? msg;
  } catch {
    return msg;
  }
}

export function ModelsTab() {
  const { data: credentials = [], isLoading } = useCredentials();
  const addCredential = useAddCredential();
  const deleteCredential = useDeleteCredential();
  const [newName, setNewName] = useState("");
  const [newValue, setNewValue] = useState("");
  const [newProvider, setNewProvider] = useState("");

  const { data: statusData } = useStatus();
  const connectMut = useConnect();
  const disconnectMut = useDisconnect();
  const registerMut = useRegister();
  const connectedNames = statusData?.sessions ?? [];
  const [acpAgent, setAcpAgent] = useState("");
  const [acpError, setAcpError] = useState("");
  const { data: configsData } = useConfigs();
  const deleteAgentMut = useDeleteAgent();
  const registeredAcpAgents = useMemo(
    () => configsData?.configs ?? [],
    [configsData],
  );
  const acpAgentLabels: Record<string, string> = useMemo(
    () => Object.fromEntries(ACP_AGENTS_META.map((a) => [a.name, a.label])),
    [],
  );

  const { data: models = [] } = useModels();
  const addModel = useAddModel();
  const deleteModel = useDeleteModel();
  const updateModels = useUpdateModels();
  const resetModels = useResetModels();

  const [showForm, setShowForm] = useState<"add" | "edit" | null>(null);
  const [editTarget, setEditTarget] = useState<Model | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
  );

  const groupedModels: Record<string, Model[]> = {};
  for (const m of models) {
    (groupedModels[m.provider] ??= []).push(m);
  }

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;
      const oldIndex = models.findIndex((m) => m.id === active.id);
      const newIndex = models.findIndex((m) => m.id === over.id);
      if (oldIndex === -1 || newIndex === -1) return;
      updateModels.mutate(arrayMove(models, oldIndex, newIndex));
    },
    [models, updateModels],
  );

  const handleAddSave = (label: string, id: string, provider: string) => {
    addModel.mutate({ id, label, provider });
    setShowForm(null);
  };

  const handleEditSave = (label: string, id: string, provider: string) => {
    if (!editTarget) return;
    const updated = models.map((m) =>
      m.id === editTarget.id ? { ...m, label, id, provider } : m,
    );
    updateModels.mutate(updated);
    setEditTarget(null);
    setShowForm(null);
  };

  const handleEditDelete = () => {
    if (!editTarget) return;
    deleteModel.mutate(editTarget.id);
    setEditTarget(null);
    setShowForm(null);
  };

  const handleAddClick = () => {
    setEditTarget(null);
    setShowForm("add");
  };

  const handleConfigureClick = (model: Model) => {
    setEditTarget(model);
    setShowForm("edit");
  };

  const handleCancelForm = () => {
    setShowForm(null);
    setEditTarget(null);
  };

  const isAcpProvider = (provider: string | null) =>
    provider &&
    [
      "codex",
      "claude-code",
      "gemini",
      "agy",
      "cline",
      "cursor",
      "goose",
    ].includes(provider);

  const handleAddCred = async () => {
    if (!newName || !newValue) return;
    await addCredential.mutateAsync({
      name: newName,
      value: newValue,
      provider: newProvider || undefined,
    });
    setNewName("");
    setNewValue("");
    setNewProvider("");
  };

  const handleAddAcpAgent = async () => {
    if (!acpAgent) return;
    const meta = ACP_AGENTS_META.find((a) => a.name === acpAgent);
    if (!meta) return;
    setAcpError("");
    try {
      await registerMut.mutateAsync({
        name: meta.name,
        command: meta.command,
        args: meta.args ?? [],
        credentials_ref: meta.credentials_ref ?? null,
      });
    } catch (e) {
      setAcpError((e as Error).message);
      return;
    }
    try {
      await connectMut.mutateAsync(meta.name);
    } catch {
      deleteAgentMut.mutate(meta.name);
      return;
    }
    setAcpAgent("");
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Configured Models</h3>
        <button
          onClick={() =>
            apiFetch("/api/config/open", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ scope: "global" }),
            })
          }
          className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
          title="Open config file in editor"
        >
          <ExternalLink className="w-3 h-3" />
          Edit file
        </button>
      </div>
      <Separator />

      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={models.map((m) => m.id)}
          strategy={verticalListSortingStrategy}
        >
          <div className="space-y-2">
            {models.length === 0 && (
              <p className="text-xs text-muted-foreground">
                No models configured.
              </p>
            )}
            {Object.entries(groupedModels).map(([provider, providerModels]) => (
              <div key={provider} className="space-y-1">
                <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider px-1 pt-1">
                  {PROVIDER_LABELS[provider] || provider}
                </h4>
                {providerModels.map((m) => (
                  <SortableModelRow
                    key={m.id}
                    model={m}
                    onDelete={deleteModel.mutate}
                    onConfigure={handleConfigureClick}
                  />
                ))}
              </div>
            ))}
          </div>
        </SortableContext>
      </DndContext>

      {showForm && (
        <InlineModelForm
          mode={showForm}
          model={editTarget ?? undefined}
          onSave={showForm === "add" ? handleAddSave : handleEditSave}
          onCancel={handleCancelForm}
          onDelete={showForm === "edit" ? handleEditDelete : undefined}
        />
      )}

      <div className="flex items-center justify-between pt-1">
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs"
          onClick={() => resetModels.mutate()}
          disabled={resetModels.isPending}
        >
          <RotateCcw className="w-3 h-3 mr-1" /> Reset to defaults
        </Button>
        <Button
          size="sm"
          className="h-7 text-xs"
          onClick={handleAddClick}
          disabled={!!showForm}
        >
          <Plus className="w-3.5 h-3.5 mr-1" /> Model
        </Button>
      </div>

      <Separator />
      <h3 className="text-sm font-medium">API Credentials</h3>
      <div className="space-y-2">
        {credentials.length === 0 && !isLoading && (
          <p className="text-xs text-muted-foreground">
            No credentials stored.
          </p>
        )}
        {credentials.map((cred) => {
          const isAcp = isAcpProvider(cred.provider);
          const isConnected = cred.provider
            ? connectedNames.includes(cred.provider)
            : false;

          return (
            <div
              key={cred.name}
              className="flex items-center gap-2 px-3 py-2 rounded-md border border-border/60"
            >
              <Key className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
              <span className="text-xs font-mono flex-1">{cred.name}</span>
              {cred.provider && (
                <span
                  className={cn(
                    "text-[10px] px-1.5 py-0.5 rounded-full font-medium",
                    PROVIDER_BADGE_COLORS[cred.provider] ??
                      "bg-muted text-muted-foreground",
                  )}
                >
                  {cred.provider}
                </span>
              )}
              {isAcp && isConnected && (
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground font-medium">
                  Connected
                </span>
              )}
              {isAcp && isConnected && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="h-6 w-6 text-muted-foreground hover:text-destructive"
                  onClick={() => disconnectMut.mutate(cred.provider!)}
                >
                  <WifiOff className="w-3 h-3" />
                </Button>
              )}
              {isAcp && !isConnected && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="h-6 w-6 text-muted-foreground"
                  onClick={() => connectMut.mutate(cred.provider!)}
                >
                  <Wifi className="w-3 h-3" />
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon-sm"
                className="h-6 w-6 text-muted-foreground hover:text-destructive"
                onClick={() => deleteCredential.mutate(cred.name)}
              >
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          );
        })}
      </div>
      <Separator />
      <div className="space-y-3">
        <h4 className="text-xs font-medium">ACP Agents</h4>
        {registeredAcpAgents.length > 0 && (
          <div className="space-y-1">
            {registeredAcpAgents.map((a) => {
              const isConn = connectedNames.includes(a.name);
              return (
                <div
                  key={a.name}
                  className="flex items-center gap-2 px-3 py-2 rounded-md border border-border/60"
                >
                  <span className="text-xs font-medium flex-1">
                    {acpAgentLabels[a.name] ?? a.name}
                  </span>
                  <span className="text-[10px] text-muted-foreground font-mono truncate max-w-[200px]">
                    {a.command} {a.args?.join(" ")}
                  </span>
                  {isConn && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground font-medium">
                      Connected
                    </span>
                  )}
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="h-6 w-6 text-muted-foreground hover:text-destructive"
                    onClick={() => deleteAgentMut.mutate(a.name)}
                  >
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </div>
              );
            })}
          </div>
        )}
        <div className="flex items-center gap-2">
          <Select value={acpAgent} onValueChange={(v) => { if (v !== null) setAcpAgent(v) }}>
            <SelectTrigger className="flex-1 h-8 text-xs">
              <SelectValue placeholder="Select ACP agent..." />
            </SelectTrigger>
            <SelectContent>
              {ACP_AGENTS_META.map((a) => (
                <SelectItem key={a.name} value={a.name} className="text-xs">
                  {a.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            className="h-8 text-xs shrink-0"
            onClick={handleAddAcpAgent}
            disabled={
              !acpAgent || registerMut.isPending || connectMut.isPending
            }
          >
            {registerMut.isPending || connectMut.isPending ? (
              <>
                <Loader2 className="w-3 h-3 mr-1 animate-spin" /> Adding
              </>
            ) : (
              <>
                <Plus className="w-3 h-3 mr-1" /> Add & Connect
              </>
            )}
          </Button>
        </div>
        {connectMut.isError && (
          <p className="text-[10px] text-destructive">
            {_acpErrorMsg(connectMut.error)}
          </p>
        )}
        {acpError && (
          <p className="text-[10px] text-destructive">
            {_acpErrorMsg(acpError)}
          </p>
        )}
      </div>
      <Separator />
      <div className="space-y-3">
        <h4 className="text-xs font-medium">Add Credential</h4>
        <div className="flex items-center gap-2">
          <Input
            placeholder="Name (e.g. ANTHROPIC_API_KEY)"
            className="flex-1 h-8 text-xs"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2">
          <Input
            placeholder="Value"
            type="password"
            className="flex-1 h-8 text-xs"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
          />
          <Select
            value={newProvider || null}
            onValueChange={(v) => setNewProvider(v ?? "")}
          >
            <SelectTrigger className="w-28 h-8 text-xs">
              <SelectValue placeholder="Provider" />
            </SelectTrigger>
            <SelectContent>
              {AUTH_CATEGORIES.map((p) => (
                <SelectItem key={p.value} value={p.value} className="text-xs">
                  {p.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            className="h-8 text-xs"
            onClick={handleAddCred}
            disabled={!newName || !newValue}
          >
            <Plus className="w-3 h-3 mr-1" /> Add
          </Button>
        </div>
      </div>
    </div>
  );
}
