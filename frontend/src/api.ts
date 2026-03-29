const API = '';

async function post(url: string, body?: object): Promise<Response> {
  const res = await fetch(`${API}${url}`, {
    method: 'POST',
    ...(body && {
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${text}`);
  }
  return res;
}

export interface JobResponse {
  job_id: string;
  status: string;
}

export interface JobInfo {
  id: string;
  type: string;
  status: 'pending' | 'running' | 'complete' | 'error' | 'cancelled';
  params: Record<string, any>;
  error: string | null;
  created_at: string;
  duration_s: number | null;
}

export interface SavedFrequency {
  id: number;
  freq_mhz: number;
  description: string;
  scan_id: string | null;
  preset_band: string | null;
  created_at: string;
}

export interface SdrDeviceInfo {
  type: string;
  index: number;
  label: string;
  serial: string;
  alias: string;
}

export async function startScan(params: {
  start_mhz: number; stop_mhz: number; duration: number; gain: number;
  bias_tee?: boolean; preset_band?: string | null; device?: string;
  device_index?: number;
}): Promise<JobResponse> {
  return (await post('/api/scan', params)).json();
}

// ── Live mode ──────────────────────────────────────────

export async function startLive(params: {
  start_mhz: number; stop_mhz: number; gain: number;
  audio_enabled?: boolean; demod_mode?: string; bias_tee?: boolean;
  device?: string; device_index?: number;
}): Promise<{ status: string; start_mhz: number; stop_mhz: number }> {
  return (await post('/api/live/start', params)).json();
}

export async function retuneLive(params: {
  start_mhz: number; stop_mhz: number; gain: number;
}): Promise<{ status: string }> {
  return (await post('/api/live/retune', params)).json();
}

export async function stopLive(): Promise<{ status: string }> {
  return (await post('/api/live/stop')).json();
}

export async function toggleAudio(params: {
  enabled: boolean; demod_mode: string;
}): Promise<{ audio_enabled: boolean; demod_mode: string }> {
  return (await post('/api/live/audio', params)).json();
}

export async function setVfo(freq_mhz: number): Promise<{ vfo_freq_mhz: number }> {
  return (await post('/api/live/vfo', { freq_mhz })).json();
}

// ── Scan history ──────────────────────────────────────

export interface ScanSummary {
  id: string;
  start_mhz: number;
  stop_mhz: number;
  duration: number;
  gain: number;
  created_at: string;
  duration_s: number | null;
}

export async function listScans(
  limit = 50, offset = 0,
): Promise<{ scans: ScanSummary[]; total: number }> {
  const res = await fetch(`${API}/api/scans?limit=${limit}&offset=${offset}`);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

export async function getScan(scanId: string): Promise<JobInfo> {
  const res = await fetch(`${API}/api/scans/${scanId}`);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

export async function cancelJob(jobId: string): Promise<{ status: string }> {
  return (await post(`/api/jobs/${jobId}/cancel`)).json();
}

export async function deleteScan(scanId: string): Promise<{ status: string }> {
  const res = await fetch(`${API}/api/scans/${scanId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

export async function saveScanNote(scanId: string, note: string): Promise<JobInfo> {
  return (await post(`/api/scans/${scanId}/note`, { note })).json();
}

export async function listSavedFrequencies(limit = 200): Promise<{ items: SavedFrequency[] }> {
  const res = await fetch(`${API}/api/frequencies?limit=${limit}`);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

export async function saveFrequency(params: {
  freq_mhz: number; description: string; scan_id?: string | null; preset_band?: string | null;
}): Promise<SavedFrequency> {
  return (await post('/api/frequencies', params)).json();
}

export async function deleteFrequency(freqId: number): Promise<{ status: string }> {
  const res = await fetch(`${API}/api/frequencies/${freqId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

// ── Device enumeration ────────────────────────────────

export async function listDevices(): Promise<{ devices: SdrDeviceInfo[] }> {
  const res = await fetch(`${API}/api/devices`);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

export async function setDeviceAlias(serial: string, alias: string): Promise<{ status: string }> {
  return (await post('/api/devices/alias', { serial, alias })).json();
}
