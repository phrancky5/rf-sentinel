/**
 * SettingsContext — persisted UI settings backed by the SQLite /api/settings endpoint.
 *
 * Provides theme colors, chart options and font size to the whole app.
 * On first load defaults are used; any change is immediately saved to the DB.
 */
import {
  createContext, useContext, useState, useCallback, useEffect, type ReactNode,
} from 'react';

// ── Default values ─────────────────────────────────────────────────────────
export interface AppSettings {
  // Spectrum chart colors
  spectrumLine:    string;
  spectrumFill:    string;
  maxHoldColor:    string;
  vfoColor:        string;
  gridColor:       string;
  axisColor:       string;
  // UI chrome
  accentColor:     string;   // cyan-ish highlight used in buttons / header
  bgColor:         string;
  // Peak markers
  markerColor:     string;
  markerMinProminenceDb: number;
  markerMinSpacingMhz:   number;
  // Typography
  uiFontSize:      number;   // px, applied to <html>
}

export const DEFAULT_SETTINGS: AppSettings = {
  spectrumLine:    '#00d4ff',
  spectrumFill:    'rgba(0,212,255,0.12)',
  maxHoldColor:    'rgba(255,100,50,0.25)',
  vfoColor:        '#44ff44',
  gridColor:       'rgba(255,255,255,0.08)',
  axisColor:       '#606070',
  accentColor:     '#06b6d4',
  bgColor:         '#0a0e1a',
  markerColor:     'rgba(251,191,36,0.88)',
  markerMinProminenceDb: 3,
  markerMinSpacingMhz:   0.3,
  uiFontSize:      14,
};

// ── Context ────────────────────────────────────────────────────────────────
interface SettingsCtx {
  settings: AppSettings;
  update: (patch: Partial<AppSettings>) => void;
  reset:  () => void;
  saving: boolean;
}

const Ctx = createContext<SettingsCtx | null>(null);

export function useSettings(): SettingsCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('useSettings must be inside SettingsProvider');
  return c;
}

async function fetchSettings(): Promise<Partial<AppSettings>> {
  try {
    const r = await fetch('/api/settings');
    if (!r.ok) return {};
    return await r.json();
  } catch {
    return {};
  }
}

async function persistSettings(s: AppSettings): Promise<void> {
  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(s),
  });
}

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [saving, setSaving] = useState(false);

  // Load on mount
  useEffect(() => {
    fetchSettings().then(saved => {
      if (Object.keys(saved).length) {
        setSettings(prev => ({ ...prev, ...saved }));
      }
    });
  }, []);

  // Apply font size to <html> element whenever it changes
  useEffect(() => {
    document.documentElement.style.fontSize = `${settings.uiFontSize}px`;
  }, [settings.uiFontSize]);

  const update = useCallback((patch: Partial<AppSettings>) => {
    setSettings(prev => {
      const next = { ...prev, ...patch };
      setSaving(true);
      persistSettings(next).finally(() => setSaving(false));
      return next;
    });
  }, []);

  const reset = useCallback(() => {
    setSettings(DEFAULT_SETTINGS);
    setSaving(true);
    persistSettings(DEFAULT_SETTINGS).finally(() => setSaving(false));
  }, []);

  return <Ctx.Provider value={{ settings, update, reset, saving }}>{children}</Ctx.Provider>;
}
