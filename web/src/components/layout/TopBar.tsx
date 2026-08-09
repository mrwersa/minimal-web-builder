import {
  Code2,
  Command as CommandIcon,
  Eye,
  LogOut,
  Monitor,
  Moon,
  Redo2,
  Smartphone,
  Sparkles,
  Sun,
  Tablet,
  Undo2,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useAuthStore } from "../../authStore";
import { useStore, VIEWPORT_WIDTHS, type CanvasViewport } from "../../store";
import { useTheme } from "../../theme";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import { Label } from "../ui/label";
import { Separator } from "../ui/separator";
import { Switch } from "../ui/switch";
import { Tabs, TabsList, TabsTrigger } from "../ui/tabs";
import { ToggleGroup, ToggleGroupItem } from "../ui/toggle-group";
import { Tooltip, TooltipContent, TooltipTrigger } from "../ui/tooltip";

const VIEWPORTS: Array<[CanvasViewport, string, typeof Monitor]> = [
  ["desktop", "Desktop", Monitor],
  ["tablet", "Tablet", Tablet],
  ["mobile", "Mobile", Smartphone],
];

function IconAction({
  label,
  icon,
  onClick,
  disabled,
}: {
  label: string;
  icon: React.ReactNode;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={label}
          title={label}
          onClick={onClick}
          disabled={disabled}
        >
          {icon}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

export default function TopBar({
  view,
  onViewChange,
  onOpenPalette,
}: {
  view: "canvas" | "code";
  onViewChange: (view: "canvas" | "code") => void;
  onOpenPalette: () => void;
}) {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const authSubmitting = useAuthStore((state) => state.submitting);
  const code = useStore((state) => state.code);
  const busy = useStore((state) => state.busy);
  const error = useStore((state) => state.error);
  const undo = useStore((state) => state.undo);
  const redo = useStore((state) => state.redo);
  const undoStack = useStore((state) => state.undoStack);
  const redoStack = useStore((state) => state.redoStack);
  const editing = useStore((state) => state.editing);
  const viewport = useStore((state) => state.viewport);
  const zoom = useStore((state) => state.zoom);
  const saveState = useStore((state) => state.saveState);
  const activeJobId = useStore((state) => state.activeJobId);
  const cancelGeneration = useStore((state) => state.cancelGeneration);
  const setStore = useStore((state) => state.set);
  const { preference, resolved, setPreference } = useTheme();

  const status = busy
    ? { label: "Generating", variant: "default" as const }
    : error
      ? { label: "Error", variant: "destructive" as const }
      : saveState === "conflict"
        ? { label: "Conflict", variant: "warning" as const }
        : saveState === "saving"
          ? { label: "Saving", variant: "secondary" as const }
          : code
            ? { label: "Ready", variant: "success" as const }
            : { label: "Idle", variant: "outline" as const };

  const widthLabel =
    VIEWPORT_WIDTHS[viewport] === null ? "Fluid" : `${VIEWPORT_WIDTHS[viewport]}px`;

  return (
    <header className="flex h-12 shrink-0 items-center gap-2 border-b bg-surface px-3">
      <div className="flex items-center gap-2 pr-1">
        <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
          <Sparkles className="h-4 w-4" />
        </div>
        <span className="hidden text-sm font-semibold md:inline">Web Builder</span>
      </div>

      <Separator orientation="vertical" className="h-6" />

      <div className="flex items-center gap-0.5">
        <IconAction
          label="Undo (Ctrl+Z)"
          icon={<Undo2 />}
          onClick={undo}
          disabled={undoStack.length === 0}
        />
        <IconAction
          label="Redo (Ctrl+Shift+Z)"
          icon={<Redo2 />}
          onClick={redo}
          disabled={redoStack.length === 0}
        />
      </div>

      <Separator orientation="vertical" className="h-6" />

      <ToggleGroup
        type="single"
        value={viewport}
        onValueChange={(value) => value && setStore("viewport", value as CanvasViewport)}
        aria-label="Viewport presets"
      >
        {VIEWPORTS.map(([value, label, Icon]) => (
          <Tooltip key={value}>
            <TooltipTrigger asChild>
              <ToggleGroupItem value={value} aria-label={`${label} viewport`}>
                <Icon />
              </ToggleGroupItem>
            </TooltipTrigger>
            <TooltipContent>{label}</TooltipContent>
          </Tooltip>
        ))}
      </ToggleGroup>
      <span className="w-12 text-xs tabular-nums text-muted-foreground">
        {widthLabel}
      </span>

      <div className="flex items-center gap-0.5">
        <IconAction
          label="Zoom out"
          icon={<ZoomOut />}
          onClick={() => setStore("zoom", Math.max(0.5, zoom - 0.25))}
          disabled={zoom <= 0.5}
        />
        <span className="w-10 text-center text-xs tabular-nums text-muted-foreground">
          {Math.round(zoom * 100)}%
        </span>
        <IconAction
          label="Zoom in"
          icon={<ZoomIn />}
          onClick={() => setStore("zoom", Math.min(1.5, zoom + 0.25))}
          disabled={zoom >= 1.5}
        />
      </div>

      <Separator orientation="vertical" className="h-6" />

      <div className="flex items-center gap-2">
        <Label htmlFor="wysiwyg" className="cursor-pointer">
          Edit
        </Label>
        <Switch
          id="wysiwyg"
          aria-label="WYSIWYG editing"
          checked={editing}
          onCheckedChange={(value) => setStore("editing", value)}
          disabled={!code || busy}
        />
      </div>

      <div className="ml-auto flex items-center gap-2">
        <Tabs value={view} onValueChange={(value) => onViewChange(value as "canvas" | "code")}>
          <TabsList>
            <TabsTrigger value="canvas">
              <Eye /> Preview
            </TabsTrigger>
            <TabsTrigger value="code" disabled={!code}>
              <Code2 /> Code
            </TabsTrigger>
          </TabsList>
        </Tabs>

        {busy && activeJobId && (
          <Button
            variant="outline"
            size="sm"
            onClick={() => void cancelGeneration()}
          >
            <X /> Stop
          </Button>
        )}

        <Badge variant={status.variant}>
          <span
            className={
              busy
                ? "h-1.5 w-1.5 animate-pulse rounded-full bg-current"
                : "h-1.5 w-1.5 rounded-full bg-current"
            }
          />
          {status.label}
        </Badge>

        <Separator orientation="vertical" className="h-6" />

        <IconAction
          label="Open command palette"
          icon={<CommandIcon />}
          onClick={onOpenPalette}
        />
        <IconAction
          label={resolved === "dark" ? "Switch to light theme" : "Switch to dark theme"}
          icon={resolved === "dark" ? <Sun /> : <Moon />}
          onClick={() => setPreference(resolved === "dark" ? "light" : "dark")}
        />

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label="Account menu">
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-muted text-[10px] font-semibold uppercase text-muted-foreground">
                {user?.email?.slice(0, 2) ?? "??"}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel className="truncate">{user?.email}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={() => setPreference(preference === "system" ? "light" : "system")}
            >
              {preference === "system" ? "Use a fixed theme" : "Follow system theme"}
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              disabled={authSubmitting}
              onSelect={() => void logout()}
            >
              <LogOut /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
