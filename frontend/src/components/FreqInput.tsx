import { useRef } from 'react';

const FREQ_STEPS = [1000, 100, 10, 1, 0.1];
const arrowBtn = 'w-full flex justify-center text-xs leading-none text-gray-500 hover:text-cyan-300 transition-colors select-none cursor-pointer';
const digitInput = 'w-[22px] text-center text-base font-mono text-cyan-300 bg-transparent outline-none caret-cyan-400 [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none';

interface Props {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
}

export default function FreqInput({ label, value, onChange, min, max }: Props) {
  const clamp = (v: number) => Math.min(max, Math.max(min, +v.toFixed(1)));
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const str = Math.floor(value).toString().padStart(4, '0');
  const tenths = Math.round((value % 1) * 10);
  const digits = [+str[0], +str[1], +str[2], +str[3], tenths];

  const setDigit = (i: number, d: number) => {
    const cur = [...digits];
    cur[i] = d;
    const v = cur[0] * 1000 + cur[1] * 100 + cur[2] * 10 + cur[3] + cur[4] * 0.1;
    onChange(clamp(v));
    if (i < 4) inputRefs.current[i + 1]?.focus();
  };

  const handleKey = (i: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    const d = parseInt(e.key);
    if (!isNaN(d) && d >= 0 && d <= 9) {
      e.preventDefault();
      setDigit(i, d);
      return;
    }
    if (e.key === 'ArrowUp') { e.preventDefault(); onChange(clamp(value + FREQ_STEPS[i])); }
    if (e.key === 'ArrowDown') { e.preventDefault(); onChange(clamp(value - FREQ_STEPS[i])); }
    if (e.key === 'ArrowRight' && i < 4) { e.preventDefault(); inputRefs.current[i + 1]?.focus(); }
    if (e.key === 'ArrowLeft' && i > 0) { e.preventDefault(); inputRefs.current[i - 1]?.focus(); }
    if (e.key === '.' && i < 4) { e.preventDefault(); inputRefs.current[4]?.focus(); }
  };

  return (
    <div>
      <label className="text-xs text-gray-400 mb-1 block">{label}</label>
      <div className="flex items-center justify-end">
        {digits.map((d, i) => (
          <div key={i} className="flex items-center">
            {i === 4 && <span className="text-base font-mono text-gray-500 leading-tight mx-px">.</span>}
            <div className="flex flex-col items-center" style={{ width: 22 }}>
              <button className={arrowBtn} onClick={() => onChange(clamp(value + FREQ_STEPS[i]))}>▲</button>
              <input
                ref={el => { inputRefs.current[i] = el; }}
                type="text"
                inputMode="numeric"
                value={d}
                readOnly
                onKeyDown={e => handleKey(i, e)}
                onFocus={e => e.target.select()}
                className={digitInput}
              />
              <button className={arrowBtn} onClick={() => onChange(clamp(value - FREQ_STEPS[i]))}>▼</button>
            </div>
          </div>
        ))}
        <span className="text-xs text-gray-500 ml-1.5">MHz</span>
      </div>
    </div>
  );
}
