import { useCallback, useEffect, useRef, useState } from 'react';
import {
  JobInfo, SavedFrequency, deleteFrequency, listSavedFrequencies, saveFrequency, saveScanNote,
} from '../api';
import { useApp } from '../AppContext';
import SpectrumChart, { ChartView } from './SpectrumChart';
import DualRangeSlider from './DualRangeSlider';
import WaterfallCanvas from './WaterfallCanvas';

function EmptyState() {
  return (
    <div className="flex items-center justify-center h-full text-gray-600">
      <div className="text-center">
        <div className="text-4xl mb-3 opacity-30">📡</div>
        <p className="text-sm">Select a job to view results</p>
      </div>
    </div>
  );
}

function LoadingState({ job }: { job: JobInfo }) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <div className="animate-pulse text-cyan-400 text-lg mb-2">⟳</div>
        <p className="text-sm text-gray-400">
          {job.status === 'pending' ? 'Queued...' : 'Processing...'}
        </p>
        <p className="text-xs text-gray-600 mt-1 capitalize">
          {job.type} — {job.params.start_mhz}–{job.params.stop_mhz} MHz
        </p>
      </div>
    </div>
  );
}

function ErrorState({ job }: { job: JobInfo }) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center max-w-md">
        <div className="text-red-400 text-lg mb-2">✗</div>
        <p className="text-sm text-red-300 mb-2">Job failed</p>
        <pre className="text-xs text-red-400/70 bg-red-900/10 rounded p-3 text-left whitespace-pre-wrap">
          {job.error}
        </pre>
      </div>
    </div>
  );
}

function JobHeader({ job }: { job: JobInfo }) {
  return (
    <div className="flex items-center justify-between px-3 py-2 border-b border-gray-700/50">
      <div className="flex items-center gap-3">
        <span className="text-sm text-gray-200 capitalize font-medium">{job.type}</span>
        <span className="text-xs text-cyan-400 font-mono">
          {job.params.start_mhz}–{job.params.stop_mhz} MHz
        </span>
        {job.duration_s && (
          <span className="text-xs text-gray-500">{job.duration_s}s</span>
        )}
      </div>
    </div>
  );
}

function ScanMetaPanel({ job, prefillFreqMhz }: { job: JobInfo; prefillFreqMhz: number | null }) {
  const { updateJobInState } = useApp();
  const [note, setNote] = useState(job.params.note ?? '');
  const [savingNote, setSavingNote] = useState(false);
  const [freqMhz, setFreqMhz] = useState('');
  const [description, setDescription] = useState('');
  const [savingFreq, setSavingFreq] = useState(false);
  const [items, setItems] = useState<SavedFrequency[]>([]);

  useEffect(() => {
    setNote(job.params.note ?? '');
    setFreqMhz('');
    setDescription('');
  }, [job.id, job.params.note]);

  useEffect(() => {
    if (prefillFreqMhz == null) return;
    setFreqMhz(prefillFreqMhz.toFixed(4));
  }, [prefillFreqMhz]);

  useEffect(() => {
    listSavedFrequencies().then(res => {
      setItems(res.items.filter(item => item.scan_id === job.id));
    }).catch(() => {});
  }, [job.id]);

  const onSaveNote = async () => {
    setSavingNote(true);
    try {
      const updated = await saveScanNote(job.id, note);
      updateJobInState(updated);
    } finally {
      setSavingNote(false);
    }
  };

  const onSaveFrequency = async () => {
    const freq = Number(freqMhz);
    if (!Number.isFinite(freq) || !description.trim()) return;
    setSavingFreq(true);
    try {
      const saved = await saveFrequency({
        freq_mhz: freq,
        description: description.trim(),
        scan_id: job.id,
        preset_band: job.params.preset_band ?? null,
      });
      setItems(prev => [saved, ...prev]);
      setDescription('');
    } finally {
      setSavingFreq(false);
    }
  };

  const onDeleteFrequency = async (freqId: number) => {
    await deleteFrequency(freqId);
    setItems(prev => prev.filter(item => item.id !== freqId));
  };

  return (
    <div className="border-b border-gray-700/50 px-3 py-3 space-y-3 bg-gray-900/20">
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-xs text-gray-500 uppercase tracking-wider">Preset Band</span>
        <span className="text-xs px-2 py-1 rounded border border-cyan-500/20 bg-cyan-500/10 text-cyan-300">
          {job.params.preset_band || 'Manual'}
        </span>
      </div>

      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs text-gray-500 uppercase tracking-wider">Scan Note</label>
          <button
            onClick={onSaveNote}
            disabled={savingNote}
            className="px-2 py-1 rounded text-xs bg-cyan-600/20 text-cyan-300 hover:bg-cyan-600/30 disabled:opacity-50"
          >
            {savingNote ? 'Saving...' : 'Save Note'}
          </button>
        </div>
        <textarea
          value={note}
          onChange={e => setNote(e.target.value)}
          rows={3}
          placeholder="Add your notes for this scan"
          className="w-full px-2 py-2 text-sm rounded border border-gray-700 bg-gray-950/70 text-gray-200 focus:outline-none focus:border-cyan-600 resize-y"
        />
      </div>

      <div>
        <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Save Frequency</div>
        <div className="text-[11px] text-gray-500 mb-1.5">Click spectrum to prefill. Double-click to jump live.</div>
        <div className="flex flex-wrap gap-2">
          <input
            value={freqMhz}
            onChange={e => setFreqMhz(e.target.value)}
            placeholder="Frequency MHz"
            className="w-36 px-2 py-1.5 text-sm font-mono rounded border border-gray-700 bg-gray-950/70 text-gray-200 focus:outline-none focus:border-cyan-600"
          />
          <input
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Description"
            className="flex-1 min-w-[16rem] px-2 py-1.5 text-sm rounded border border-gray-700 bg-gray-950/70 text-gray-200 focus:outline-none focus:border-cyan-600"
          />
          <button
            onClick={onSaveFrequency}
            disabled={savingFreq}
            className="px-3 py-1.5 rounded text-sm bg-green-600/20 text-green-300 hover:bg-green-600/30 disabled:opacity-50"
          >
            {savingFreq ? 'Saving...' : 'Save'}
          </button>
        </div>
        {items.length > 0 && (
          <div className="mt-2 space-y-1.5 max-h-40 overflow-y-auto">
            {items.map(item => (
              <div key={item.id} className="flex items-center justify-between gap-3 rounded border border-gray-800 bg-gray-950/40 px-2 py-1.5">
                <div className="min-w-0">
                  <div className="text-sm font-mono text-cyan-300">{item.freq_mhz.toFixed(4)} MHz</div>
                  <div className="text-xs text-gray-400 truncate">{item.description}</div>
                </div>
                <button
                  onClick={() => onDeleteFrequency(item.id)}
                  className="text-xs text-red-400 hover:text-red-300"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ScanResult({
  job,
  onFreqClick,
  onFreqDoubleClick,
}: {
  job: JobInfo;
  onFreqClick?: (freq_mhz: number) => void;
  onFreqDoubleClick?: (freq_mhz: number) => void;
}) {
  const [chartView, setChartView] = useState<ChartView | null>(null);
  const [dataDbRange, setDataDbRange] = useState<[number, number]>([-120, -20]);
  const [dbRange, setDbRange] = useState<[number, number] | null>(null);
  const dataDbRef = useRef(dataDbRange);

  const onDataDbRange = useCallback((min: number, max: number) => {
    const r: [number, number] = [Math.floor(min), Math.ceil(max)];
    if (r[0] !== dataDbRef.current[0] || r[1] !== dataDbRef.current[1]) {
      dataDbRef.current = r;
      setDataDbRange(r);
    }
  }, []);

  const wd = job.params.waterfall_data;
  if (!wd) return <p className="text-gray-500 text-sm">No waterfall data available</p>;

  const sd = job.params.spectrum_data;
  const frame = sd ? {
    freqs_mhz: sd.freqs_mhz,
    power_db: sd.power_db,
  } : null;

  const sliderLo = dbRange ? dbRange[0] : dataDbRange[0];
  const sliderHi = dbRange ? dbRange[1] : dataDbRange[1];

  return (
    <div className="flex flex-col h-full">
      {frame && (
        <div className="flex-[2] min-h-0">
          <SpectrumChart
            frame={frame}
            mode="scan"
            onFreqClick={onFreqClick}
            onFreqDoubleClick={onFreqDoubleClick}
            onViewChange={setChartView}
          />
        </div>
      )}
      <div className="flex-1 min-h-0 flex">
        <div className="flex-1 min-w-0">
          <WaterfallCanvas resultData={wd} view={chartView} dbRange={dbRange} onDataDbRange={onDataDbRange} />
        </div>
        <div className="flex-shrink-0 py-1" style={{ width: 24 }}>
          <DualRangeSlider
            lo={sliderLo} hi={sliderHi}
            min={dataDbRange[0]} max={dataDbRange[1]}
            onChange={(lo, hi) => setDbRange([lo, hi])}
            onReset={() => setDbRange(null)}
            vertical snapStep={1} precision={0}
          />
        </div>
      </div>
    </div>
  );
}

export default function ResultView() {
  const { selectedJob: job, handleScanPeakClick } = useApp();
  const [prefillFreqMhz, setPrefillFreqMhz] = useState<number | null>(null);

  if (!job) return <EmptyState />;
  if (job.status === 'pending' || job.status === 'running') return <LoadingState job={job} />;
  if (job.status === 'error') return <ErrorState job={job} />;

  return (
    <div className="flex flex-col h-full">
      <JobHeader job={job} />
      <ScanMetaPanel job={job} prefillFreqMhz={prefillFreqMhz} />
      <div className="flex-1 min-h-0">
        <ScanResult job={job} onFreqClick={setPrefillFreqMhz} onFreqDoubleClick={handleScanPeakClick} />
      </div>
    </div>
  );
}
