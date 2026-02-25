import { useState } from 'react';
import { startScan, startWaterfall, startSweep } from '../api';
import ModeSelector, { Mode } from './ModeSelector';
import PresetBar from './PresetBar';
import ParamSlider from './ParamSlider';

interface Props {
  onJobStarted: () => void;
}

export default function ControlPanel({ onJobStarted }: Props) {
  const [mode, setMode] = useState<Mode>('scan');
  const [freqMhz, setFreqMhz] = useState(98.0);
  const [rateMsps, setRateMsps] = useState(1.024);
  const [duration, setDuration] = useState(2.0);
  const [gain, setGain] = useState(30.0);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);
    try {
      if (mode === 'scan') {
        await startScan({ freq_mhz: freqMhz, sample_rate_msps: rateMsps, duration, gain });
      } else if (mode === 'waterfall') {
        await startWaterfall({ freq_mhz: freqMhz, sample_rate_msps: rateMsps, duration, gain });
      } else {
        await startSweep({ gain });
      }
      onJobStarted();
    } catch (e) {
      console.error('Failed to start job:', e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <ModeSelector mode={mode} onChange={setMode} />

      {mode !== 'sweep' && (
        <PresetBar
          activeFreq={freqMhz}
          onSelect={(freq, rate) => { setFreqMhz(freq); setRateMsps(rate); }}
        />
      )}

      {mode !== 'sweep' && (
        <div className="space-y-3">
          <ParamSlider label="Frequency" value={freqMhz} onChange={setFreqMhz}
            min={24} max={1766} step={0.1} unit="MHz" />
          <ParamSlider label="Sample Rate" value={rateMsps} onChange={setRateMsps}
            min={0.25} max={2.56} step={0.064} unit="Msps" />
          <ParamSlider label="Duration" value={duration} onChange={setDuration}
            min={0.5} max={30} step={0.5} unit="s" />
        </div>
      )}

      <ParamSlider label="Gain" value={gain} onChange={setGain}
        min={0} max={50} step={1} unit="dB" />

      <button
        onClick={handleSubmit}
        disabled={loading}
        className={`w-full py-2.5 rounded-lg font-medium text-sm transition-all
          ${loading
            ? 'bg-gray-700 text-gray-400 cursor-wait'
            : 'bg-cyan-600 hover:bg-cyan-500 text-white glow-accent'
          }`}
      >
        {loading ? 'Starting...' : `Run ${mode.charAt(0).toUpperCase() + mode.slice(1)}`}
      </button>
    </div>
  );
}
