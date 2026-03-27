import { toggleAudio } from '../api';

export type DemodMode = 'fm' | 'am';

const audioPanel = 'rounded-lg border border-gray-700/50 bg-gray-800/30 p-2.5 space-y-2';
const demodBtn = 'px-2.5 py-1 rounded text-xs font-mono transition-all';
const demodBtnActive = 'bg-cyan-600 text-white';
const demodBtnInactive = 'bg-gray-700/50 text-gray-400 hover:text-gray-200';
const audioBtnOn = 'bg-green-600/80 text-white hover:bg-green-500';
const audioBtnOff = 'bg-gray-700/50 text-gray-400 hover:text-gray-200';

interface Props {
  liveActive: boolean;
  audioEnabled: boolean;
  onToggle: (enabled: boolean) => void;
  demodMode: DemodMode;
  onDemodModeChange: (mode: DemodMode) => void;
  volume: number;
  onVolumeChange: (v: number) => void;
}

export default function AudioControls({ liveActive, audioEnabled, onToggle, demodMode, onDemodModeChange, volume, onVolumeChange }: Props) {
  const handleToggle = async () => {
    const next = !audioEnabled;
    try {
      await toggleAudio({ enabled: next, demod_mode: demodMode });
      onToggle(next);
    } catch (e) {
      console.error('[AudioControls] audio toggle failed:', e);
    }
  };

  const handleModeChange = async (mode: DemodMode) => {
    onDemodModeChange(mode);
    if (audioEnabled) {
      try {
        await toggleAudio({ enabled: true, demod_mode: mode });
        onToggle(true);
      } catch (e) {
        console.error('[AudioControls] demod mode switch failed:', e);
      }
    }
  };

  if (!liveActive) return null;

  return (
    <div className={audioPanel}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-400 uppercase tracking-wider">Audio</span>
        <button
          onClick={handleToggle}
          className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${audioEnabled ? audioBtnOn : audioBtnOff}`}
        >
          {audioEnabled ? '🔊 ON' : '🔇 OFF'}
        </button>
      </div>

      <div className="flex gap-1.5">
        {(['fm', 'am'] as DemodMode[]).map(m => (
          <button
            key={m}
            onClick={() => handleModeChange(m)}
            className={`${demodBtn} ${demodMode === m ? demodBtnActive : demodBtnInactive}`}
          >
            {m.toUpperCase()}
          </button>
        ))}
      </div>

      {audioEnabled && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 w-8">Vol</span>
          <input
            type="range"
            min={0}
            max={100}
            value={volume}
            onChange={e => onVolumeChange(Number(e.target.value))}
            className="flex-1 h-1 accent-cyan-500"
          />
          <span className="text-xs text-gray-500 w-7 text-right">{volume}%</span>
        </div>
      )}
    </div>
  );
}
