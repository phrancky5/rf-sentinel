/**
 * SettingsPanel — slide-in drawer for editing UI/chart settings.
 */
import { useState } from 'react';
import { useSettings, type AppSettings } from '../SettingsContext';

// ── Small reusable controls ────────────────────────────────────────────────

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <span className="text-xs text-gray-400 flex-1 min-w-0">{label}</span>
      <div className="flex-shrink-0">{children}</div>
    </div>
  );
}

function ColorPicker({
  value, onChange,
}: { value: string; onChange: (v: string) => void }) {
  // Only simple hex colors are supported in <input type="color">
  // For rgba colors we show a text input alongside.
  const isHex = /^#[0-9a-fA-F]{3,8}$/.test(value);
  return (
    <div className="flex items-center gap-1.5">
      {isHex && (
        <input
          type="color"
          value={value.slice(0, 7)}
          onChange={e => onChange(e.target.value)}
          className="w-7 h-7 rounded cursor-pointer border border-gray-700 bg-transparent p-0.5"
        />
      )}
      <input
        type="text"
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-36 px-2 py-1 text-xs font-mono rounded border border-gray-700 bg-gray-900 text-gray-200 focus:outline-none focus:border-cyan-600"
      />
    </div>
  );
}

function NumInput({
  value, min, max, step = 1, onChange,
}: { value: number; min: number; max: number; step?: number; onChange: (v: number) => void }) {
  return (
    <input
      type="number"
      value={value}
      min={min}
      max={max}
      step={step}
      onChange={e => onChange(Number(e.target.value))}
      className="w-20 px-2 py-1 text-xs font-mono rounded border border-gray-700 bg-gray-900 text-gray-200 focus:outline-none focus:border-cyan-600 text-right"
    />
  );
}

type ColorKey = Extract<keyof AppSettings, 'spectrumLine' | 'spectrumFill' | 'maxHoldColor' | 'vfoColor' | 'gridColor' | 'axisColor' | 'accentColor' | 'bgColor' | 'markerColor'>;

const COLOR_FIELDS: { key: ColorKey; label: string }[] = [
  { key: 'spectrumLine',  label: 'Spectrum line' },
  { key: 'spectrumFill',  label: 'Spectrum fill' },
  { key: 'maxHoldColor',  label: 'Max hold' },
  { key: 'vfoColor',      label: 'VFO line' },
  { key: 'gridColor',     label: 'Grid' },
  { key: 'axisColor',     label: 'Axis' },
  { key: 'accentColor',   label: 'UI accent' },
  { key: 'bgColor',       label: 'Background' },
  { key: 'markerColor',   label: 'Peak markers' },
];

// ── Panel ──────────────────────────────────────────────────────────────────

export default function SettingsPanel({ onClose }: { onClose: () => void }) {
  const { settings, update, reset, saving } = useSettings();
  const [section, setSection] = useState<'colors' | 'markers' | 'fonts'>('colors');

  const tab = (s: typeof section, label: string) => (
    <button
      onClick={() => setSection(s)}
      className={`px-3 py-1 text-xs rounded transition-all ${s === section ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-600/40' : 'text-gray-500 hover:text-gray-300'}`}
    >
      {label}
    </button>
  );

  return (
    // Backdrop
    <div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      {/* Drawer — stop click propagation so clicking inside doesn't close */}
      <div
        className="w-80 h-full bg-[#0d1120] border-l border-gray-800 flex flex-col shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
          <h2 className="text-sm font-semibold text-gray-100">Settings</h2>
          <div className="flex items-center gap-2">
            {saving && <span className="text-[10px] text-cyan-500 animate-pulse">Saving…</span>}
            <button
              onClick={reset}
              className="text-[10px] text-gray-500 hover:text-red-400 transition-colors px-1.5 py-0.5 rounded border border-gray-700 hover:border-red-500/40"
            >
              Reset defaults
            </button>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-white transition-colors text-lg leading-none"
            >
              ×
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 px-4 py-2 border-b border-gray-800/50">
          {tab('colors',  'Colors')}
          {tab('markers', 'Markers')}
          {tab('fonts',   'Display')}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-4 py-2">
          {section === 'colors' && (
            <div>
              <p className="text-[10px] text-gray-600 mb-2 uppercase tracking-wider">Chart & UI colors</p>
              <div className="divide-y divide-gray-800/50">
                {COLOR_FIELDS.map(({ key, label }) => (
                  <Row key={key} label={label}>
                    <ColorPicker
                      value={settings[key]}
                      onChange={v => update({ [key]: v } as Partial<AppSettings>)}
                    />
                  </Row>
                ))}
              </div>
            </div>
          )}

          {section === 'markers' && (
            <div>
              <p className="text-[10px] text-gray-600 mb-2 uppercase tracking-wider">Frequency peak markers</p>
              <div className="divide-y divide-gray-800/50">
                <Row label="Min prominence (dB)">
                  <NumInput
                    value={settings.markerMinProminenceDb}
                    min={0.5} max={30} step={0.5}
                    onChange={v => update({ markerMinProminenceDb: v })}
                  />
                </Row>
                <Row label="Min spacing (MHz)">
                  <NumInput
                    value={settings.markerMinSpacingMhz}
                    min={0.01} max={10} step={0.01}
                    onChange={v => update({ markerMinSpacingMhz: v })}
                  />
                </Row>
              </div>
            </div>
          )}

          {section === 'fonts' && (
            <div>
              <p className="text-[10px] text-gray-600 mb-2 uppercase tracking-wider">Display</p>
              <div className="divide-y divide-gray-800/50">
                <Row label="UI font size (px)">
                  <NumInput
                    value={settings.uiFontSize}
                    min={10} max={22} step={1}
                    onChange={v => update({ uiFontSize: v })}
                  />
                </Row>
                <Row label="Marker text size (px)">
                  <NumInput
                    value={settings.markerFontSize}
                    min={8} max={20} step={1}
                    onChange={v => update({ markerFontSize: v })}
                  />
                </Row>
                <Row label="Axis tick text size (px)">
                  <NumInput
                    value={settings.axisTickFontSize}
                    min={8} max={20} step={1}
                    onChange={v => update({ axisTickFontSize: v })}
                  />
                </Row>
                <Row label="Axis label text size (px)">
                  <NumInput
                    value={settings.axisLabelFontSize}
                    min={8} max={24} step={1}
                    onChange={v => update({ axisLabelFontSize: v })}
                  />
                </Row>
              </div>
            </div>
          )}
        </div>

        <div className="px-4 py-3 border-t border-gray-800 text-[10px] text-gray-600">
          Settings are persisted to SQLite automatically.
        </div>
      </div>
    </div>
  );
}
