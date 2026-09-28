import { useCallback, useEffect, useMemo, useState } from 'react';
import { TriangleAlert } from 'lucide-react';
import {
  Footer,
  GovStrip,
  Header,
  KpiStrip,
} from './components/chrome';
import ControlPanel from './components/ControlPanel';
import MapView from './components/MapView';
import Inspector from './components/Inspector';
import { ApiModal } from './components/OutcomesPanel';
import {
  downloadBlob,
  fetchConfidenceMap,
  fetchDates,
  fetchExplanation,
  fetchHealth,
  fetchWarningPolygons,
} from './api';
import { FALLBACK_DATES, LAYERS } from './lib';

const SKILL_BADGE = 'Operational Model: ROC-AUC 0.990 · Brier 0.017';

export default function App() {
  const [dates, setDates] = useState(FALLBACK_DATES);
  const [initDate, setInitDate] = useState('2019-07-15');
  const [leadDay, setLeadDay] = useState(4);
  const [layer, setLayer] = useState('fci');
  const [showPoly, setShowPoly] = useState(true);
  const [selected, setSelected] = useState('KONKAN_GOA');
  const [conf, setConf] = useState(null);
  const [poly, setPoly] = useState(null);
  const [explain, setExplain] = useState(null);
  const [status, setStatus] = useState('Connecting…');
  const [apiDown, setApiDown] = useState(false);
  const [updated, setUpdated] = useState('–');
  const [apiOpen, setApiOpen] = useState(false);

  /* Available init dates + health, once. */
  useEffect(() => {
    fetchDates()
      .then((d) => {
        if (d.dates?.length) setDates(d.dates);
      })
      .catch(() => {});
    fetchHealth()
      .then((h) =>
        setStatus(
          h.model_ready
            ? 'Operational · Model Online'
            : 'Operational · Active',
        ),
      )
      .catch(() => setStatus('Backend Offline'));
  }, []);

  /* Confidence map + polygons per run/lead. */
  useEffect(() => {
    let live = true;
    setStatus('Loading…');
    Promise.all([
      fetchConfidenceMap(initDate, leadDay),
      fetchWarningPolygons(initDate, leadDay),
    ])
      .then(([c, p]) => {
        if (!live) return;
        setConf(c);
        setPoly(p);
        setApiDown(false);
        setStatus(`Cycle ${c.init_date} · Day ${c.lead_day}`);
        setUpdated(new Date().toLocaleString('en-IN'));
      })
      .catch(() => {
        if (!live) return;
        setApiDown(true);
        setStatus('API Offline — start: python src/api/server.py');
      });
    return () => {
      live = false;
    };
  }, [initDate, leadDay]);

  /* Explanation per region/lead. */
  useEffect(() => {
    let live = true;
    setExplain(null);
    fetchExplanation(selected, leadDay)
      .then((e) => live && setExplain(e))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [selected, leadDay]);

  const regions = useMemo(() => conf?.regions ?? [], [conf]);

  const kpis = useMemo(() => {
    if (!regions.length)
      return { warnings: 0, critical: 0, meanFci: 0, top: null };
    const warnings = regions.filter((r) => r.is_bust_warning).length;
    const critical = regions.filter((r) => r.bust_probability >= 0.75).length;
    const meanFci =
      regions.reduce((s, r) => s + r.confidence_index, 0) / regions.length;
    const top = [...regions].sort(
      (a, b) => b.bust_probability - a.bust_probability,
    )[0];
    return { warnings, critical, meanFci, top };
  }, [regions]);

  const region = useMemo(
    () => regions.find((r) => r.subdivision_id === selected) ?? regions[0],
    [regions, selected],
  );

  const handleSelect = useCallback((id) => {
    setSelected(id);
  }, []);

  const fontStep = useCallback((d) => {
    const el = document.documentElement;
    const cur = parseFloat(getComputedStyle(el).fontSize) || 16;
    el.style.fontSize = `${Math.min(19, Math.max(13, cur + d))}px`;
  }, []);

  const handleExportCSV = useCallback(() => {
    if (!conf) return;
    const rows = [
      ['subdivision_id', 'subdivision_name', 'lead_day', 'forecast_mm', 'p_bust', 'fci', 'category'],
    ];
    conf.regions.forEach((r) =>
      rows.push([
        r.subdivision_id,
        `"${r.subdivision_name}"`,
        r.lead_day,
        r.forecast_precip_mm,
        r.bust_probability,
        r.confidence_index,
        r.confidence_category,
      ]),
    );
    downloadBlob(
      new Blob([rows.map((r) => r.join(',')).join('\n')], { type: 'text/csv' }),
      `confidence-map_${initDate}_day${leadDay}.csv`,
    );
  }, [conf, initDate, leadDay]);

  const handleExportGeoJSON = useCallback(() => {
    if (!poly) return;
    downloadBlob(
      new Blob([JSON.stringify(poly, null, 2)], {
        type: 'application/geo+json',
      }),
      `warning-zones_${initDate}_day${leadDay}.geojson`,
    );
  }, [poly, initDate, leadDay]);

  return (
    <div className="flex min-h-screen flex-col bg-[#eef2f7] lg:h-screen lg:overflow-hidden text-slate-800">
      <GovStrip
        stamp="Operational Forecast Cycle: 15 July 2019 (00 UTC) · Active Synoptic System"
        onFontStep={fontStep}
      />
      <Header
        status={status}
        skill={SKILL_BADGE}
        onApi={() => setApiOpen(true)}
      />

      {apiDown && (
        <div className="mx-5 mt-2 flex items-center gap-2 rounded-xl border border-red-300 bg-red-50 px-4 py-2 text-sm font-semibold text-red-800">
          <TriangleAlert className="h-4 w-4 shrink-0" />
          API unreachable. Start the backend with:{' '}
          <code className="rounded bg-red-100 px-1.5 py-0.5 font-mono text-xs">
            python src/api/server.py
          </code>
        </div>
      )}

      <KpiStrip
        warnings={kpis.warnings}
        critical={kpis.critical}
        meanFci={kpis.meanFci}
        top={kpis.top}
        leadDay={leadDay}
        date={initDate}
        total={regions.length}
      />

      {/* Main 3-Column Operational Layout: Left Cities/Controls, Center Full Map, Right Inspector */}
      <main className="grid min-h-0 flex-1 gap-2.5 px-5 py-2 lg:grid-cols-[330px_minmax(0,1fr)_370px]">
        <ControlPanel
          dates={dates}
          initDate={initDate}
          onInitDate={setInitDate}
          leadDay={leadDay}
          onLeadDay={setLeadDay}
          layer={layer}
          onLayer={setLayer}
          showPoly={showPoly}
          onTogglePoly={() => setShowPoly((v) => !v)}
          regions={regions}
          selected={region?.subdivision_id ?? selected}
          onSelect={handleSelect}
        />
        <MapView
          regions={regions}
          polygons={showPoly ? poly : null}
          layer={layer}
          selected={region?.subdivision_id ?? selected}
          onSelect={handleSelect}
          showPolygons={showPoly}
          stats={{
            warnings: kpis.warnings,
            critical: kpis.critical,
            meanFci: `${kpis.meanFci.toFixed(1)}%`,
            layerLabel: LAYERS[layer].label,
            updated,
          }}
        />
        <Inspector
          region={region}
          explain={explain}
          initDate={initDate}
          leadDay={leadDay}
          onPrint={() => window.print()}
          onGeoJSON={handleExportGeoJSON}
          onCSV={handleExportCSV}
        />
      </main>

      <Footer />

      <ApiModal
        open={apiOpen}
        onClose={() => setApiOpen(false)}
        initDate={initDate}
        leadDay={leadDay}
        subdivision={region?.subdivision_id ?? selected}
      />
    </div>
  );
}
