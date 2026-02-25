interface Props {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step: number;
  unit: string;
}

export default function ParamSlider({ label, value, onChange, min, max, step, unit }: Props) {
  return (
    <div>
      <div className="flex justify-between mb-1">
        <label className="text-xs text-gray-400">{label}</label>
        <span className="text-xs text-cyan-300 font-mono">
          {value % 1 === 0 ? value : value.toFixed(step < 1 ? 3 : 1)} {unit}
        </span>
      </div>
      <input
        type="range"
        value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        min={min}
        max={max}
        step={step}
        className="w-full h-1.5 bg-gray-700 rounded-lg appearance-none cursor-pointer
          [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3
          [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full
          [&::-webkit-slider-thumb]:bg-cyan-400 [&::-webkit-slider-thumb]:cursor-pointer"
      />
    </div>
  );
}
