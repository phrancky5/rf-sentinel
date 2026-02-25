interface Preset {
  label: string;
  startMhz: number;
  stopMhz: number;
}

interface Props {
  activeStart: number;
  activeStop: number;
  onSelect: (startMhz: number, stopMhz: number) => void;
}

const PRESETS: Preset[] = [
  { label: 'FM Radio',  startMhz: 87.5,   stopMhz: 108.0 },
  { label: 'Airband',   startMhz: 118.0,   stopMhz: 137.0 },
  { label: 'PMR446',    startMhz: 446.0,   stopMhz: 446.2 },
  { label: '433 IoT',   startMhz: 433.0,   stopMhz: 434.8 },
  { label: '868 LoRa',  startMhz: 867.0,   stopMhz: 869.0 },
  { label: 'GSM 900',   startMhz: 935.0,   stopMhz: 960.0 },
  { label: 'ADS-B',     startMhz: 1089.0,  stopMhz: 1091.0 },
];

export default function PresetBar({ activeStart, activeStop, onSelect }: Props) {
  return (
    <div>
      <label className="text-xs text-gray-500 uppercase tracking-wider mb-1.5 block">
        Presets
      </label>
      <div className="flex flex-wrap gap-1.5">
        {PRESETS.map(p => (
          <button
            key={p.label}
            onClick={() => onSelect(p.startMhz, p.stopMhz)}
            className={`px-2 py-1 text-xs rounded border transition-all
              ${activeStart === p.startMhz && activeStop === p.stopMhz
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
