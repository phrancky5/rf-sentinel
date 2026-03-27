import { createContext, useContext, useState, useCallback, useRef, type ReactNode } from 'react';
import { useWebSocket, type LogEntry } from './hooks/useWebSocket';
import { useAudioPlayer } from './hooks/useAudioPlayer';
import { type JobInfo, setVfo, toggleAudio, getScan, cancelJob, deleteScan } from './api';
import type { SpectrumFrame } from './components/SpectrumChart';
import type { ControlPanelHandle } from './components/ControlPanel';

export type { LogEntry };

const WS_URL = `ws://${window.location.hostname}:8900/api/ws`;
const AUDIO_WS_URL = `ws://${window.location.hostname}:8900/api/ws/audio`;

interface AppContextValue {
  liveActive: boolean;
  liveFrame: SpectrumFrame | null;
  audioEnabled: boolean;
  vfoFreq: number | null;
  jobs: JobInfo[];
  selectedJob: JobInfo | null;
  connected: boolean;
  logs: LogEntry[];

  handleLiveToggle: (active: boolean) => void;
  handleAudioToggle: (enabled: boolean) => void;
  handleFreqClick: (freq_mhz: number) => void;
  handleSelectJob: (job: JobInfo | null) => void;
  handleCancelJob: (jobId: string) => void;
  handleDeleteScan: (scanId: string) => void;
  handleScanPeakClick: (freq_mhz: number) => void;
  clearLogs: () => void;
  setVolume: (v: number) => void;
  controlPanelRef: React.RefObject<ControlPanelHandle>;
}

const AppContext = createContext<AppContextValue | null>(null);

export function useApp(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}

export function AppProvider({ children }: { children: ReactNode }) {
  const audio = useAudioPlayer(AUDIO_WS_URL);
  const controlPanelRef = useRef<ControlPanelHandle>(null);
  const [selectedJob, setSelectedJob] = useState<JobInfo | null>(null);
  const [liveActive, setLiveActive] = useState(false);
  const [liveFrame, setLiveFrame] = useState<SpectrumFrame | null>(null);
  const [audioEnabled, setAudioEnabled] = useState(false);
  const [vfoFreq, setVfoFreq] = useState<number | null>(null);
  const audioRef = useRef(audio);
  audioRef.current = audio;
  const vfoRef = useRef<number | null>(null);
  vfoRef.current = vfoFreq;

  const handleSpectrum = useCallback((data: any) => {
    const freqs: number[] = data.freqs_mhz;
    setLiveFrame({
      freqs_mhz: freqs,
      power_db: data.power_db,
    });
    const center = (freqs[0] + freqs[freqs.length - 1]) / 2;
    const prev = vfoRef.current;
    if (prev != null && prev >= freqs[0] && prev <= freqs[freqs.length - 1]) return;
    if (prev != null) {
      setAudioEnabled(false);
      audioRef.current.stop();
    }
    setVfoFreq(center);
    setVfo(center).catch(() => setVfoFreq(null));
  }, []);

  const { connected, logs, clearLogs, jobs, setJobs } = useWebSocket(WS_URL, handleSpectrum);

  const handleSelectJob = useCallback(async (job: JobInfo | null) => {
    if (!job) { setSelectedJob(null); return; }
    if (job.params.spectrum_data) { setSelectedJob(job); return; }
    if (job.status === 'complete') {
      try {
        const full = await getScan(job.id);
        setJobs(prev => prev.map(j => j.id === job.id ? full : j));
        setSelectedJob(full);
      } catch { setSelectedJob(job); }
      return;
    }
    setSelectedJob(job);
  }, [setJobs]);

  const handleFreqClick = useCallback((freq_mhz: number) => {
    if (!liveActive) return;
    setVfoFreq(freq_mhz);
    setVfo(freq_mhz).catch(() => setVfoFreq(null));
    if (!audioEnabled) {
      toggleAudio({ enabled: true, demod_mode: 'fm' }).catch(() => {});
      setAudioEnabled(true);
      audio.start();
    }
  }, [liveActive, audioEnabled, audio]);

  const handleLiveToggle = useCallback((active: boolean) => {
    setLiveActive(active);
    if (!active) {
      setLiveFrame(null);
      setAudioEnabled(false);
      setVfoFreq(null);
      audio.stop();
    }
  }, [audio]);

  const handleAudioToggle = useCallback((enabled: boolean) => {
    setAudioEnabled(enabled);
    if (enabled) audio.start(); else audio.stop();
  }, [audio]);

  const handleCancelJob = useCallback((jobId: string) => {
    cancelJob(jobId).catch(() => {});
  }, []);

  const handleDeleteScan = useCallback((scanId: string) => {
    deleteScan(scanId).then(() => {
      setJobs(prev => prev.filter(j => j.id !== scanId));
      setSelectedJob(prev => prev?.id === scanId ? null : prev);
    }).catch(() => {});
  }, [setJobs]);

  const handleScanPeakClick = useCallback((freq_mhz: number) => {
    controlPanelRef.current?.goLiveAt(freq_mhz);
  }, []);

  return (
    <AppContext.Provider value={{
      liveActive, liveFrame, audioEnabled, vfoFreq,
      jobs, selectedJob,
      connected, logs,
      handleLiveToggle, handleAudioToggle, handleFreqClick,
      handleSelectJob, handleCancelJob, handleDeleteScan,
      handleScanPeakClick, clearLogs,
      setVolume: audio.setVolume,
      controlPanelRef,
    }}>
      {children}
    </AppContext.Provider>
  );
}
