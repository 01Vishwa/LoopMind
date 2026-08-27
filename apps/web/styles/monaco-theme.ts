// VERA Monaco Editor themes.
//
// Two variants — dark (Catppuccin Mocha) and light (Catppuccin Latte) — keyed
// to the `--vera-code-*` design tokens so the editor chrome matches the code
// pane in both themes. Applied at runtime via `monaco.editor.defineTheme()`.
//
// Usage (e.g. in CodePane):
//   import { defineVeraMonacoThemes, veraMonacoThemeName } from "@/styles/monaco-theme";
//   defineVeraMonacoThemes(monacoInstance);
//   editor.updateOptions({ theme: veraMonacoThemeName(isLight) });

export interface MonacoTokenRule {
  token: string;
  foreground?: string;
  background?: string;
  fontStyle?: string;
}

export interface MonacoThemeData {
  base: "vs" | "vs-dark" | "hc-black" | "hc-light";
  inherit: boolean;
  rules: MonacoTokenRule[];
  colors: Record<string, string>;
}

/** Minimal structural type for the parts of `monaco` we touch. */
export interface MonacoEditorNamespace {
  editor: {
    defineTheme(themeName: string, themeData: MonacoThemeData): void;
    setTheme(themeName: string): void;
  };
}

export const VERA_MONACO_DARK = "vera-dark";
export const VERA_MONACO_LIGHT = "vera-light";

// ── Dark — Catppuccin Mocha ────────────────────────────────────────────────
export const veraMonacoDark: MonacoThemeData = {
  base: "vs-dark",
  inherit: true,
  rules: [
    { token: "", foreground: "CDD6F4", background: "11111B" },
    { token: "comment", foreground: "585B70", fontStyle: "italic" },
    { token: "keyword", foreground: "CBA6F7" },
    { token: "string", foreground: "A6E3A1" },
    { token: "number", foreground: "FAB387" },
    { token: "type", foreground: "89DCEB" },
    { token: "class", foreground: "89B4FA" },
    { token: "function", foreground: "89B4FA" },
    { token: "variable", foreground: "CDD6F4" },
    { token: "variable.predefined", foreground: "F38BA8" },
    { token: "operator", foreground: "89DCEB" },
    { token: "delimiter", foreground: "CDD6F4" },
    { token: "identifier", foreground: "CDD6F4" },
    { token: "constant", foreground: "FAB387" },
    { token: "regexp", foreground: "FAB387" },
  ],
  colors: {
    "editor.background": "#11111B",
    "editor.foreground": "#CDD6F4",
    "editor.lineHighlightBackground": "#181825",
    "editor.selectionBackground": "#45475A",
    "editorCursor.foreground": "#F5C2E7",
    "editorLineNumber.foreground": "#585B70",
    "editorLineNumber.activeForeground": "#CDD6F4",
    "editorGutter.background": "#11111B",
    "editorIndentGuide.background1": "#2A2A3F",
    "editorWhitespace.foreground": "#2A2A3F",
    "scrollbarSlider.background": "#45475A60",
    "scrollbarSlider.hoverBackground": "#585B70",
    "scrollbarSlider.activeBackground": "#6C7086",
  },
};

// ── Light — Catppuccin Latte ───────────────────────────────────────────────
export const veraMonacoLight: MonacoThemeData = {
  base: "vs",
  inherit: true,
  rules: [
    { token: "", foreground: "4C4F69", background: "EFF1F5" },
    { token: "comment", foreground: "9CA0B0", fontStyle: "italic" },
    { token: "keyword", foreground: "8839EF" },
    { token: "string", foreground: "40A02B" },
    { token: "number", foreground: "FE640B" },
    { token: "type", foreground: "179299" },
    { token: "class", foreground: "1E66F5" },
    { token: "function", foreground: "1E66F5" },
    { token: "variable", foreground: "4C4F69" },
    { token: "variable.predefined", foreground: "D20F39" },
    { token: "operator", foreground: "179299" },
    { token: "delimiter", foreground: "4C4F69" },
    { token: "identifier", foreground: "4C4F69" },
    { token: "constant", foreground: "FE640B" },
    { token: "regexp", foreground: "FE640B" },
  ],
  colors: {
    "editor.background": "#EFF1F5",
    "editor.foreground": "#4C4F69",
    "editor.lineHighlightBackground": "#E6E9EF",
    "editor.selectionBackground": "#ACB0BE",
    "editorCursor.foreground": "#DC8A78",
    "editorLineNumber.foreground": "#9CA0B0",
    "editorLineNumber.activeForeground": "#4C4F69",
    "editorGutter.background": "#EFF1F5",
    "editorIndentGuide.background1": "#CCD0DA",
    "editorWhitespace.foreground": "#CCD0DA",
    "scrollbarSlider.background": "#ACB0BE60",
    "scrollbarSlider.hoverBackground": "#9CA0B0",
    "scrollbarSlider.activeBackground": "#8C8FA1",
  },
};

/** Backwards-compatible alias for the previous single-theme export. */
export const catppuccinMochaTheme: MonacoThemeData = veraMonacoDark;

/** Registers both VERA themes on a Monaco instance (idempotent). */
export function defineVeraMonacoThemes(monaco: MonacoEditorNamespace): void {
  monaco.editor.defineTheme(VERA_MONACO_DARK, veraMonacoDark);
  monaco.editor.defineTheme(VERA_MONACO_LIGHT, veraMonacoLight);
}

/** Resolves the registered theme name for the active color scheme. */
export function veraMonacoThemeName(isLight: boolean): string {
  return isLight ? VERA_MONACO_LIGHT : VERA_MONACO_DARK;
}
