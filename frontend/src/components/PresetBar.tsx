interface Preset {
  label: string;
  freq: number;
  rate: number;
}

interface Props {
  activeFreq: number;
  onSelect: (freq: number, rate: number) => void;
}

const PRESETS: Preset[] = [
  { label: 'FM Radio', freq: 98.0, rate: 2.048 },
  { label: 'Airband', freq: 127.0, rate: 2.048 },
  { label: 'PMR446', freq: 446.1, rate: 1.0 },
  { label: '433 IoT', freq: 433.9, rate: 2.048 },
  { label: '868 LoRa', freq: 868.0, rate: 2.048 },
  { label: 'GSM 900', freq: 947.0, rate: 2.048 },
  { label: 'ADS-B', freq: 1090.0, rate: 2.048 },
];

export default function PresetBar({ activeFreq, onSelect }: Props) {
  return (
    <div>
      <label className="text-xs text-gray-500 uppercase tracking-wider mb-1.5 block">
        Presets
      </label>
      <div className="flex flex-wrap gap-1.5">
        {PRESETS.map(p => (
          <button
            key={p.label}
            onClick={() => onSelect(p.freq, p.rate)}
            className={`px-2 py-1 text-xs rounded border transition-all
              ${activeFreq === p.freq
                ? 'border-cyan-500/50 text-cyan-300 bg-cyan-500/10'
                : 'border-gray-700 text-gray-400 hover:border-gray-600 hover:text-gray-300'
              }`}
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  );
}
