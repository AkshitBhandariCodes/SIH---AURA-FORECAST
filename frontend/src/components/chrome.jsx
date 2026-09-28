import {
  Activity,
  CalendarDays,
  Gauge,
  Landmark,
  Layers,
  MapPin,
  Satellite,
  Server,
  ShieldCheck,
  TriangleAlert,
} from 'lucide-react';

/* Tricolour hairline + Government of India strip */
export function GovStrip({ stamp, onFontStep }) {
  return (
    <>
      <div className="flex h-1.5 shrink-0" aria-hidden>
        <span className="flex-1 bg-[#ff9933]" />
        <span className="flex-1 bg-white" />
        <span className="flex-1 bg-[#138808]" />
      </div>
      <div className="no-print flex shrink-0 flex-wrap items-center justify-between gap-2 bg-[#07192f] px-5 py-1 text-[11.5px] text-slate-100">
        <div className="font-semibold tracking-wide">
          भारत सरकार &nbsp;|&nbsp; GOVERNMENT OF INDIA &nbsp;·&nbsp; पृथ्वी
          विज्ञान मंत्रालय &nbsp;|&nbsp; Ministry of Earth Sciences
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden text-slate-300 md:inline">{stamp}</span>
          <button
            onClick={() => onFontStep(-1)}
            className="rounded border border-white/30 px-2 py-0.5 hover:bg-white/10"
            title="Decrease text size"
          >
            A−
          </button>
          <button
            onClick={() => onFontStep(1)}
            className="rounded border border-white/30 px-2 py-0.5 hover:bg-white/10"
            title="Increase text size"
          >
            A+
          </button>
        </div>
      </div>
    </>
  );
}

/* Main product header */
export function Header({ status, skill, onApi }) {
  return (
    <header className="flex shrink-0 flex-wrap items-center gap-3.5 border-b border-slate-300/80 bg-[#f8fafc] px-5 py-2 shadow-xs">
      <div className="flex h-12 w-11 shrink-0 items-center justify-center">
        <img
          src="/emblem.svg"
          alt="State Emblem of India - Satyameva Jayate"
          className="h-full w-auto object-contain filter drop-shadow-sm"
          onError={(e) => {
            e.currentTarget.onerror = null;
            e.currentTarget.src =
              'https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg';
          }}
        />
      </div>
      <div className="min-w-0">
        <div className="flex flex-wrap items-baseline gap-2">
          <h1 className="text-lg font-black tracking-tight text-navy-900">
            AURA-CAST
          </h1>
          <span className="rounded bg-saffron-500/10 px-1.5 py-0.2 text-[11px] font-bold text-saffron-600">
            पूर्वानुमान विश्वसनीयता एवं बस्ट चेतावनी प्रणाली
          </span>
        </div>
        <p className="flex flex-wrap items-center gap-1.5 text-[11.5px] text-slate-600">
          <Landmark className="h-3 w-3 text-navy-700" />
          <span className="font-semibold text-navy-800">
            National Meteorological Forecast Reliability & Bust Prediction Platform
          </span>
          <span className="text-slate-400">·</span>
          <span>MoES · NCMRWF · IMD</span>
          <span className="text-slate-400">·</span>
          <span className="font-semibold text-emerald-800 bg-emerald-50 px-1.5 py-0.2 rounded border border-emerald-200 text-[11px]">
            Team AURA FARMERS
          </span>
        </p>
      </div>
      <div className="ml-auto flex flex-wrap items-center gap-2">
        <button
          onClick={onApi}
          className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-white px-2.5 py-1 text-[11px] font-bold text-navy-800 shadow-xs hover:border-navy-700 hover:bg-slate-50 transition"
          title="Open AURA-CAST Operational REST API"
        >
          <Server className="h-3.5 w-3.5 text-navy-700" />
          REST API
        </button>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-blue-300 bg-blue-50/80 px-2.5 py-1 text-[11px] font-bold text-navy-800 shadow-xs">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          ACTIVE
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300 bg-emerald-50/80 px-2.5 py-1 text-[11px] font-bold text-emerald-800 shadow-xs">
          <Activity className="h-3 w-3" />
          {skill}
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50/80 px-2.5 py-1 text-[11px] font-bold text-amber-900 shadow-xs">
          <Satellite className="h-3 w-3" />
          {status}
        </span>
      </div>
    </header>
  );
}

/* KPI cards */
export function KpiStrip({ warnings, critical, meanFci, top, leadDay, date, total }) {
  const meanColor =
    meanFci >= 80
      ? 'text-emerald-700'
      : meanFci >= 50
        ? 'text-amber-700'
        : 'text-red-700';
  const cards = [
    {
      label: 'Active Bust Warnings (P ≥ 50%)',
      value: `${warnings} / ${total ?? '–'}`,
      sub: `Day ${leadDay} · ${date}`,
      accent: 'border-l-amber-500',
      icon: TriangleAlert,
    },
    {
      label: 'Critical Danger Zones (P ≥ 75%)',
      value: String(critical),
      sub: 'Priority alert for forecasters',
      accent: 'border-l-red-600',
      valueClass: 'text-red-700',
      icon: ShieldCheck,
    },
    {
      label: 'All-India Mean Confidence (FCI)',
      value: `${meanFci.toFixed(1)}%`,
      sub: 'FCI = 100 × (1 − P Bust)',
      accent: 'border-l-emerald-600',
      valueClass: meanColor,
      icon: Gauge,
    },
    {
      label: 'Highest-Risk Subdivision',
      value: top?.subdivision_name ?? '–',
      sub: top
        ? `P(Bust) ${(top.bust_probability * 100).toFixed(1)}% · FCI ${top.confidence_index}%`
        : '–',
      accent: 'border-l-navy-600',
      small: true,
      icon: MapPin,
    },
    {
      label: 'Operational Lead Window',
      value: `Day ${leadDay}`,
      sub: 'Day 1–10 medium-range cycle',
      accent: 'border-l-navy-700',
      icon: CalendarDays,
    },
  ];
  return (
    <section className="grid shrink-0 grid-cols-2 gap-2 px-5 pt-2 xl:grid-cols-5">
      {cards.map((c) => (
        <div
          key={c.label}
          className={`rounded-lg border border-slate-300/80 border-l-4 bg-[#f8fafc] px-3 py-1.5 shadow-xs ${c.accent}`}
        >
          <div className="flex items-center gap-1.5 text-[9.5px] font-bold uppercase tracking-wider text-slate-600">
            <c.icon className="h-3 w-3" />
            {c.label}
          </div>
          <div
            className={`mt-0.5 font-extrabold tabular-nums leading-tight ${c.small ? 'text-xs pt-0.5' : 'text-lg'} ${c.valueClass ?? 'text-navy-900'}`}
          >
            {c.value}
          </div>
          <div className="truncate text-[10px] text-slate-500">
            {c.sub}
          </div>
        </div>
      ))}
    </section>
  );
}

/* Clean 5-step use-flow breadcrumb */
const STEPS = [
  { icon: CalendarDays, label: 'Initialisation cycle' },
  { icon: Gauge, label: 'Scrub lead time (D1–D10)' },
  { icon: Layers, label: 'Layer diagnostics' },
  { icon: MapPin, label: 'Inspect subdivision & cities' },
  { icon: ShieldCheck, label: 'Advisory & export' },
];

export function WorkflowSteps({ activeStep, onNavigate }) {
  return (
    <nav
      aria-label="Operational Workflow"
      className="no-print flex shrink-0 items-center gap-1 overflow-x-auto px-5 pt-3"
    >
      {STEPS.map((s, i) => {
        const n = i + 1;
        const done = n < activeStep;
        const active = n === activeStep;
        return (
          <div key={s.label} className="flex items-center">
            <button
              onClick={() => onNavigate?.(n)}
              title={`Workflow Stage ${n}: ${s.label}`}
              aria-current={active ? 'step' : undefined}
              className={`flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-bold transition hover:-translate-y-px hover:shadow-sm ${
                active
                  ? 'border-navy-700 bg-navy-700 text-white'
                  : done
                    ? 'border-emerald-300 bg-emerald-50 text-emerald-800 hover:border-emerald-500'
                    : 'border-slate-300/80 bg-[#f8fafc] text-slate-700 hover:border-navy-600 hover:text-navy-800'
              }`}
            >
              <s.icon className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">
                {n}. {s.label}
              </span>
              <span className="sm:hidden">{n}</span>
            </button>
            {n < STEPS.length && (
              <div className="mx-1 h-px w-4 bg-slate-300" aria-hidden />
            )}
          </div>
        );
      })}
    </nav>
  );
}

export function Footer() {
  return (
    <footer className="flex shrink-0 flex-wrap justify-between items-center gap-2 bg-[#07192f] px-5 py-2.5 text-[11px] text-slate-300 border-t border-slate-700">
      <div>
        <b className="text-white">AURA-CAST:</b> National Numerical Weather Prediction (NWP) Forecast Reliability & Bust Prediction Platform · MoES · NCMRWF · IMD
      </div>
      <div>
        <span className="rounded bg-emerald-900/60 px-2 py-0.5 font-semibold text-emerald-300 border border-emerald-700/60">
          Engineered by Team AURA FARMERS
        </span>
      </div>
    </footer>
  );
}
