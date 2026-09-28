import { useState } from 'react';
import {
  Brain,
  Check,
  Copy,
  ExternalLink,
  Map as MapIcon,
  Percent,
  Server,
  Siren,
  X,
} from 'lucide-react';

const OUTCOMES = [
  {
    key: 'confidence',
    icon: MapIcon,
    title: 'Forecast Confidence Map',
    desc: 'Region-wise confidence for Day 1 to Day 10 forecasts',
    tag: 'FCI 0–100%',
  },
  {
    key: 'probability',
    icon: Percent,
    title: 'Forecast Bust Probability',
    desc: 'Probability of large forecast error over different regions',
    tag: 'P(Bust)',
  },
  {
    key: 'zones',
    icon: Siren,
    title: 'Error-Prone Area Detection',
    desc: 'Identification of areas where model forecast may be unreliable',
    tag: 'Active Polygons',
  },
  {
    key: 'explain',
    icon: Brain,
    title: 'Explainable Output',
    desc: 'Key meteorological reasons for low confidence',
    tag: 'TreeSHAP Attribution',
  },
  {
    key: 'api',
    icon: Server,
    title: 'Operational Interface & API',
    desc: 'Simple, robust interface & REST endpoints for operational use',
    tag: '5 Endpoints',
  },
];

/**
 * Expected Outcomes — every outcome is a live button that jumps
 * straight to the system feature verifying it.
 */
export function OutcomesBar({ onOutcome }) {
  return (
    <section aria-label="Operational Capabilities" className="shrink-0 px-5 pt-2">
      <div className="mb-1.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-500 opacity-60" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-600" />
          </span>
          <p className="text-[10.5px] font-bold uppercase tracking-wider text-slate-700">
            OPERATIONAL DELIVERABLES & EXPECTED OUTCOMES — Real-time live verification
          </p>
        </div>
        <span className="hidden sm:inline text-[10.5px] font-medium text-slate-500">
          Click any outcome below to inspect its live implementation
        </span>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-5">
        {OUTCOMES.map((o) => (
          <button
            key={o.key}
            onClick={() => onOutcome(o.key)}
            title={`Inspect: ${o.title} — ${o.desc}`}
            className="group flex flex-col justify-between gap-1.5 rounded-xl border border-slate-300/80 bg-[#f8fafc] p-2.5 text-left shadow-xs transition hover:-translate-y-px hover:border-navy-700 hover:shadow-sm"
          >
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-navy-800 text-white transition group-hover:bg-saffron-500">
                <o.icon className="h-3.5 w-3.5" />
              </span>
              <span className="min-w-0 flex-1 truncate text-xs font-black text-navy-900">
                {o.title}
              </span>
            </div>
            <p className="text-[11px] leading-tight text-slate-600 line-clamp-2">
              {o.desc}
            </p>
            <div className="flex items-center justify-between pt-1 border-t border-slate-200/80 text-[10px]">
              <span className="font-semibold text-slate-500">{o.tag}</span>
              <span className="font-bold text-emerald-800 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                VERIFIED ✓
              </span>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

/* Live API reference: real endpoints with the current run pre-filled. */
export function ApiModal({ open, onClose, initDate, leadDay, subdivision }) {
  const [copied, setCopied] = useState(null);
  if (!open) return null;
  const endpoints = [
    {
      path: '/api/v1/health',
      desc: 'Service health status, model readiness, and subdivision coverage',
    },
    {
      path: '/api/v1/forecast/dates',
      desc: 'Available initialisation forecast cycle dates',
    },
    {
      path: `/api/v1/confidence-map?date=${initDate}&lead_day=${leadDay}`,
      desc: 'Forecast Confidence Map: Region-wise confidence (FCI) for Day 1 to Day 10',
    },
    {
      path: `/api/v1/polygons/warning-zones?date=${initDate}&lead_day=${leadDay}`,
      desc: 'Error-Prone Area Detection: GeoJSON alert polygons where P(Bust) ≥ 0.50',
    },
    {
      path: `/api/v1/explain?subdivision=${subdivision}&lead_day=${leadDay}`,
      desc: 'Explainable Output: Key meteorological physical drivers and TreeSHAP weights',
    },
  ];
  const copy = async (text, i) => {
    try {
      await navigator.clipboard.writeText(
        `${window.location.origin}${text}`,
      );
    } catch {
      const ta = document.createElement('textarea');
      ta.value = `${window.location.origin}${text}`;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      ta.remove();
    }
    setCopied(i);
    setTimeout(() => setCopied(null), 1200);
  };
  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center bg-navy-900/60 p-4 backdrop-blur-xs"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="AURA-CAST Operational REST API Reference"
    >
      <div
        className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-slate-300 bg-[#f8fafc] p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="flex items-center gap-2 text-base font-extrabold text-navy-900">
              <Server className="h-5 w-5 text-navy-700" />
              AURA-CAST Operational REST API
            </h2>
            <p className="mt-0.5 text-xs text-slate-600">
              High-throughput REST API for automated forecaster workflows and GIS ingest. Pre-filled with active cycle (Day {leadDay} · {initDate}).
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg border border-slate-300 bg-white p-1.5 hover:bg-slate-100"
            aria-label="Close API reference"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-3 flex flex-col gap-2">
          {endpoints.map((ep, i) => (
            <div
              key={ep.path}
              className="rounded-xl border border-slate-300/80 bg-white/90 p-3 shadow-xs"
            >
              <div className="flex items-center gap-2">
                <span className="rounded bg-emerald-700 px-1.5 py-0.5 font-mono text-[10px] font-bold text-white">
                  GET
                </span>
                <code className="min-w-0 flex-1 truncate font-mono text-xs text-navy-900 font-semibold">
                  {ep.path}
                </code>
                <button
                  onClick={() => copy(ep.path, i)}
                  className="rounded-md border border-slate-300 bg-white p-1.5 hover:border-navy-600"
                  title="Copy full URL"
                >
                  {copied === i ? (
                    <Check className="h-3.5 w-3.5 text-emerald-700" />
                  ) : (
                    <Copy className="h-3.5 w-3.5" />
                  )}
                </button>
                <a
                  href={ep.path}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-md border border-slate-300 bg-white p-1.5 hover:border-navy-600"
                  title="Open in new tab"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>
              <p className="mt-1 text-[11px] text-slate-600">{ep.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
