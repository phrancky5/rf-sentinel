/**
 * peakMarkerPlugin — draws frequency markers at prominent spectral dips.
 *
 * Detects local minima that sit below the smoothed baseline by at least
 * `minProminenceDb` dB and renders an amber dashed line + rotated frequency
 * label for each one.
 */
import uPlot from 'uplot';
import type { SpectrumFrame } from '../SpectrumChart';

export interface PeakMarkerOpts {
  /** Minimum dip depth vs smoothed baseline to qualify as a marker (dB, default 3) */
  minProminenceDb?: number;
  /** Minimum frequency separation between markers (MHz, default 0.3) */
  minSpacingMhz?: number;
  /** Maximum number of markers rendered (default 50) */
  maxMarkers?: number;
}

interface Marker {
  freq: number;
  power: number;
  prominence: number;
}

/** Causal sliding-window mean — O(n), avoids repeated slice allocation. */
function movingAverage(arr: number[], half: number): Float64Array {
  const n = arr.length;
  const out = new Float64Array(n);
  let sum = 0;
  let cnt = 0;
  for (let i = 0; i <= Math.min(half, n - 1); i++) { sum += arr[i]; cnt++; }
  for (let i = 0; i < n; i++) {
    out[i] = sum / cnt;
    const addIdx = i + half + 1;
    const remIdx = i - half;
    if (addIdx < n) { sum += arr[addIdx]; cnt++; }
    if (remIdx >= 0) { sum -= arr[remIdx]; cnt--; }
  }
  return out;
}

export function findDips(
  freqs: number[],
  power: number[],
  opts: PeakMarkerOpts = {},
): Marker[] {
  const { minProminenceDb = 3, minSpacingMhz = 0.3, maxMarkers = 50 } = opts;
  const n = power.length;
  if (n < 20) return [];

  // Adaptive windows based on actual frequency resolution
  const freqStep = Math.max(1e-6, (freqs[n - 1] - freqs[0]) / (n - 1)); // MHz/bin
  const smoothHalf = Math.max(10, Math.round(4.0 / freqStep));   // 4 MHz baseline width
  const localHalf  = Math.max(2,  Math.round(0.04 / freqStep));  // 40 kHz local window

  const baseline = movingAverage(power, smoothHalf);
  const candidates: Marker[] = [];

  for (let i = localHalf; i < n - localHalf; i++) {
    // Local minimum check
    let isMin = true;
    for (let j = i - localHalf; j <= i + localHalf; j++) {
      if (j !== i && power[j] <= power[i]) { isMin = false; break; }
    }
    if (!isMin) continue;

    const prominence = baseline[i] - power[i];
    if (prominence >= minProminenceDb) {
      candidates.push({ freq: freqs[i], power: power[i], prominence });
    }
  }

  // Keep most-prominent first, then enforce minimum spacing (greedy NMS)
  candidates.sort((a, b) => b.prominence - a.prominence);
  const kept: Marker[] = [];
  for (const c of candidates) {
    if (kept.length >= maxMarkers) break;
    if (kept.some(k => Math.abs(k.freq - c.freq) < minSpacingMhz)) continue;
    kept.push(c);
  }

  return kept.sort((a, b) => a.freq - b.freq);
}

export default function peakMarkerPlugin(
  frameRef: React.MutableRefObject<SpectrumFrame | null>,
  optsRef: React.MutableRefObject<PeakMarkerOpts>,
  colorRef: React.MutableRefObject<string>,
): uPlot.Plugin {
  return {
    hooks: {
      draw: (u: uPlot) => {
        const frame = frameRef.current;
        if (!frame || frame.freqs_mhz.length < 20) return;

        const markers = findDips(frame.freqs_mhz, frame.power_db, optsRef.current);
        if (!markers.length) return;

        const { ctx, bbox } = u;
        const dpr = uPlot.pxRatio;
        const bottom = bbox.top + bbox.height;

        ctx.save();
        // Clip to the plot area so nothing bleeds into the axes
        ctx.beginPath();
        ctx.rect(bbox.left, bbox.top, bbox.width, bbox.height);
        ctx.clip();

        for (const m of markers) {
          const xPx = u.valToPos(m.freq, 'x', true);
          const yPx = u.valToPos(m.power, 'y', true);

          if (xPx < bbox.left || xPx > bbox.left + bbox.width) continue;

          const top = bbox.top;
          const dipY = Math.max(top, Math.min(yPx, bottom));

          // ── Dashed vertical guide line from top of plot → dip ────────────
          ctx.beginPath();
          ctx.strokeStyle = colorRef.current.replace(/[\d.]+\)$/, '0.45)');
          ctx.lineWidth = 1 * dpr;
          ctx.setLineDash([3 * dpr, 3 * dpr]);
          ctx.moveTo(xPx, top);
          ctx.lineTo(xPx, dipY);
          ctx.stroke();
          ctx.setLineDash([]);

          // ── Downward-pointing triangle just below the top edge ────────────
          const t = 4 * dpr;
          const triY = top + t * 1.5;
          ctx.beginPath();
          ctx.fillStyle = colorRef.current;
          ctx.moveTo(xPx,     triY + t);           // tip, pointing down
          ctx.lineTo(xPx - t, triY - t * 0.7);
          ctx.lineTo(xPx + t, triY - t * 0.7);
          ctx.closePath();
          ctx.fill();

          // ── Rotated frequency label near the top of the line ─────────────
          const label = m.freq.toFixed(3);
          const fontSize = Math.round(9 * dpr);
          ctx.font = `${fontSize}px monospace`;
          ctx.fillStyle = colorRef.current;
          ctx.save();
          ctx.translate(xPx, top + 6 * dpr);
          ctx.rotate(Math.PI / 2);        // text reads top-to-bottom, left side of line
          ctx.textAlign = 'left';
          ctx.textBaseline = 'middle';
          ctx.fillText(label, 3 * dpr, 0);
          ctx.restore();
        }

        ctx.restore();
      },
    },
  };
}
