import { useState } from 'react';
import { AppProvider, useApp } from './AppContext';
import { APP_VERSION } from './config';
import ControlPanel from './components/ControlPanel';
import LogConsole from './components/LogConsole';
import JobList from './components/JobList';
import ResultView from './components/ResultView';
import SpectrumChart, { type ChartView } from './components/SpectrumChart';
import WaterfallCanvas from './components/WaterfallCanvas';
import SettingsPanel from './components/SettingsPanel';

function Header({ onSettingsOpen }: { onSettingsOpen: () => void }) {
  const { liveActive, audioEnabled, connected } = useApp();
  return (
    <header className="border-b border-gray-800 px-4 py-2.5 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <h1 className="text-base font-bold tracking-tight">
          <span className="text-cyan-400">RF</span>Sentinel
        </h1>
        <span className="text-xs text-gray-600 font-mono">v{APP_VERSION}</span>
      </div>
      <div className="flex items-center gap-3">
        {liveActive && (
          <span className="text-xs px-2 py-0.5 rounded bg-red-500/15 text-red-300 font-mono animate-pulse">
            ● LIVE
          </span>
        )}
        {audioEnabled && (
          <span className="text-xs px-2 py-0.5 rounded bg-green-500/15 text-green-300 font-mono">
            🔊 AUDIO
          </span>
        )}
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-400' : 'bg-red-400'}`} />
          <span className="text-xs text-gray-500">
            {connected ? 'Server online' : 'Disconnected'}
          </span>
        </div>
        <button
          onClick={onSettingsOpen}
          title="Settings"
          className="text-gray-500 hover:text-cyan-400 transition-colors text-base leading-none px-1"
        >
          ⚙
        </button>
      </div>
    </header>
  );
}

function Sidebar() {
  const [jobsOpen, setJobsOpen] = useState(true);
  return (
    <aside className="w-72 border-r border-gray-800 flex flex-col">
      <div className="p-3 border-b border-gray-800/50 flex-shrink-0">
        <ControlPanel />
      </div>
      <div className="flex-1 overflow-y-auto p-3">
        <button
          onClick={() => setJobsOpen(o => !o)}
          className="flex items-center justify-between w-full text-xs text-gray-500 uppercase tracking-wider mb-2 hover:text-gray-200 transition-colors"
        >
          <span>Jobs</span>
          <span className="text-sm text-cyan-400">{jobsOpen ? '▲' : '▼'}</span>
        </button>
        {jobsOpen && <JobList />}
      </div>
    </aside>
  );
}

function MainContent() {
  const { liveActive, liveFrame, audioEnabled, vfoFreq, handleFreqClick } = useApp();
  const [chartView, setChartView] = useState<ChartView | null>(null);

  return (
    <div className="flex-1 min-w-0 flex flex-col">
      <div className="flex-1 border-b border-gray-800 overflow-hidden flex flex-col">
        {liveActive || liveFrame ? (
          <>
            <div className="flex-[2] min-h-0">
              <SpectrumChart
                frame={liveFrame}
                mode="live"
                vfoFreq={audioEnabled ? vfoFreq : null}
                onFreqClick={handleFreqClick}
                onViewChange={setChartView}
              />
            </div>
            <div className="flex-1 min-h-0 border-t border-gray-800/50">
              <WaterfallCanvas frame={liveFrame} view={chartView} />
            </div>
          </>
        ) : (
          <ResultView />
        )}
      </div>
      <LogConsole />
    </div>
  );
}

export default function App() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  return (
    <AppProvider>
      <div className="min-h-screen bg-[#0a0e1a] text-gray-100">
        <Header onSettingsOpen={() => setSettingsOpen(true)} />
        <div className="flex h-[calc(100vh-45px)]">
          <Sidebar />
          <MainContent />
        </div>
        {settingsOpen && <SettingsPanel onClose={() => setSettingsOpen(false)} />}
      </div>
    </AppProvider>
  );
}
