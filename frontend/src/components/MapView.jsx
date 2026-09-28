import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Info, ZoomIn, ZoomOut } from 'lucide-react';
import { SUBDIVISION_CITIES, bustColor, rainColor } from '../lib';

function colorFor(r, layer) {
  if (layer === 'prob') return bustColor(r.bust_probability);
  if (layer === 'rain') return rainColor(r.forecast_precip_mm);
  return r.status_color;
}

const LEGENDS = {
  fci: {
    title: 'Confidence Index (FCI)',
    rows: [
      ['#15803d', 'High 80–100% · Reliable'],
      ['#d97706', 'Moderate 50–79% · Monitor'],
      ['#dc2626', 'Bust Alert <50% · Unreliable'],
    ],
  },
  prob: {
    title: 'Bust Probability P(Bust)',
    rows: [
      ['#15803d', 'Low <30% · Consistent'],
      ['#d97706', 'Elevated 30–60% · Watch Spread'],
      ['#dc2626', 'High >60% · High Error Risk'],
    ],
  },
  rain: {
    title: 'NWP Rainfall Guidance',
    rows: [
      ['#9ecfe8', 'Light <15.5 mm/day'],
      ['#0e7fc4', 'Moderate 15.5–64.4 mm/day'],
      ['#0b3d6b', 'Heavy ≥64.5 mm/day'],
    ],
  },
};

/**
 * Full-height central Leaflet Map with robust ResizeObserver,
 * instant tile invalidation, subdivision rectangles, and polygon warning zones.
 */
export default function MapView({
  regions,
  polygons,
  layer,
  selected,
  onSelect,
  stats,
  showPolygons,
}) {
  const divRef = useRef(null);
  const mapRef = useRef(null);
  const rectLayerRef = useRef(null);
  const polyLayerRef = useRef(null);

  // Initialize Leaflet map once
  useEffect(() => {
    if (!divRef.current || mapRef.current) return;

    const map = L.map(divRef.current, {
      center: [22.0, 79.5],
      zoom: 5,
      minZoom: 4,
      maxZoom: 9,
      zoomControl: false,
      attributionControl: true,
    });
    mapRef.current = map;

    // Esri World Street Map (no API key) + OSM fallback.
    // NOTE: cartocdn basemaps now require an API key (watermark/blank tiles).
    const primary = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
      {
        maxZoom: 18,
        attribution: 'Esri, HERE, Garmin, OpenStreetMap contributors',
      },
    );
    const fallback = L.tileLayer(
      'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
      { maxZoom: 18, attribution: '© OpenStreetMap contributors' },
    );
    let tileErrs = 0;
    primary.on('tileerror', () => {
      tileErrs += 1;
      if (tileErrs > 6 && map.hasLayer(primary)) {
        map.removeLayer(primary);
        if (!map.hasLayer(fallback)) fallback.addTo(map);
      }
    });
    primary.addTo(map);
    if (map.attributionControl) {
      map.attributionControl.setPrefix('ForecastGuard AI · MoES/NCMRWF pilot');
    }

    const rectGroup = L.layerGroup().addTo(map);
    const polyGroup = L.layerGroup().addTo(map);
    rectLayerRef.current = rectGroup;
    polyLayerRef.current = polyGroup;

    // Critical: ResizeObserver ensures Leaflet tiles always fill 100% of available space!
    const ro = new ResizeObserver(() => {
      if (mapRef.current) {
        mapRef.current.invalidateSize();
      }
    });
    ro.observe(divRef.current);

    // Staggered size invalidation for layout settlement
    const t1 = setTimeout(() => map.invalidateSize(), 100);
    const t2 = setTimeout(() => map.invalidateSize(), 300);
    const t3 = setTimeout(() => map.invalidateSize(), 600);

    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
      ro.disconnect();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Sync regional rectangles
  useEffect(() => {
    const group = rectLayerRef.current;
    if (!group || !regions || !regions.length) return;
    group.clearLayers();

    regions.forEach((r) => {
      const active = r.subdivision_id === selected;
      const bounds = [
        [r.lat_range[0], r.lon_range[0]],
        [r.lat_range[1], r.lon_range[1]],
      ];
      const fill = colorFor(r, layer);
      const cities = (SUBDIVISION_CITIES[r.subdivision_id] || []).join(', ');

      const rect = L.rectangle(bounds, {
        color: active ? '#0a2240' : '#475569',
        weight: active ? 3.5 : 1.2,
        fillColor: fill,
        fillOpacity: active ? 0.65 : 0.45,
      });

      rect.on('click', () => onSelect(r.subdivision_id));

      rect.bindTooltip(
        `<b>${r.subdivision_name}</b>${cities ? `<br><span style="color:#475569;font-size:10.5px;">Stations: ${cities}</span>` : ''}<br>FCI: <b>${r.confidence_index}%</b> · P(Bust): <b>${(r.bust_probability * 100).toFixed(1)}%</b><br>NWP Rain: <b>${r.forecast_precip_mm} mm</b>`,
        { sticky: true, className: 'fg-tip' },
      );

      group.addLayer(rect);
    });

    if (mapRef.current) {
      mapRef.current.invalidateSize();
    }
  }, [regions, layer, selected, onSelect]);

  // Warning polygons overlay
  useEffect(() => {
    const group = polyLayerRef.current;
    if (!group) return;
    group.clearLayers();
    if (!polygons?.features) return;

    L.geoJSON(polygons, {
      style: (f) => ({
        color: f.properties.severity === 'CRITICAL' ? '#b91c1c' : '#b45309',
        weight: 2,
        dashArray: '6 4',
        fillOpacity: 0,
      }),
    }).addTo(group);
  }, [polygons]);

  // Toggle polygon visibility
  useEffect(() => {
    const map = mapRef.current;
    const group = polyLayerRef.current;
    if (!map || !group) return;
    if (showPolygons) {
      if (!map.hasLayer(group)) group.addTo(map);
    } else if (map.hasLayer(group)) {
      map.removeLayer(group);
    }
  }, [showPolygons]);

  const legend = LEGENDS[layer];

  return (
    <div
      id="fg-map"
      className="relative flex h-full min-h-[460px] w-full flex-col overflow-hidden rounded-xl border border-slate-300/80 bg-[#f8fafc] shadow-sm lg:min-h-0"
    >
      {/* Top Stat Pills Overlay */}
      <div className="pointer-events-none absolute left-3 top-3 z-[800] flex flex-wrap gap-1.5">
        <span className="rounded-md bg-navy-900/90 px-2.5 py-1 text-[11px] font-bold text-white shadow-xs backdrop-blur-xs">
          Active Warnings: <b className="tabular-nums text-amber-300">{stats.warnings}</b>
        </span>
        <span className="rounded-md bg-navy-900/90 px-2.5 py-1 text-[11px] font-bold text-white shadow-xs backdrop-blur-xs">
          Critical Risk: <b className="tabular-nums text-red-300">{stats.critical}</b>
        </span>
        <span className="rounded-md bg-navy-900/90 px-2.5 py-1 text-[11px] font-bold text-white shadow-xs backdrop-blur-xs">
          Mean FCI: <b className="tabular-nums text-emerald-300">{stats.meanFci}</b>
        </span>
        <span className="rounded-md bg-navy-900/90 px-2.5 py-1 text-[11px] font-bold text-slate-200 shadow-xs backdrop-blur-xs">
          Layer: {stats.layerLabel}
        </span>
      </div>

      {/* Zoom Controls Overlay */}
      <div className="absolute right-3 top-3 z-[800] flex flex-col gap-1">
        <button
          onClick={() => mapRef.current?.zoomIn()}
          className="flex h-7 w-7 items-center justify-center rounded-md border border-slate-300 bg-white/95 text-navy-900 shadow-xs hover:bg-slate-100"
          title="Zoom In"
        >
          <ZoomIn className="h-4 w-4" />
        </button>
        <button
          onClick={() => mapRef.current?.zoomOut()}
          className="flex h-7 w-7 items-center justify-center rounded-md border border-slate-300 bg-white/95 text-navy-900 shadow-xs hover:bg-slate-100"
          title="Zoom Out"
        >
          <ZoomOut className="h-4 w-4" />
        </button>
      </div>

      {/* Full-Height Leaflet Container */}
      <div ref={divRef} className="h-full w-full flex-1 relative min-h-[380px]" />

      {/* Floating Legend */}
      <div className="absolute bottom-9 left-3 z-[800] rounded-lg border border-slate-300/80 bg-white/95 p-2 text-[10.5px] shadow-sm backdrop-blur-xs">
        <b className="text-[10px] uppercase tracking-wider text-navy-900">
          {legend.title}
        </b>
        {legend.rows.map(([c, t]) => (
          <div key={t} className="mt-0.5 flex items-center gap-1.5 text-slate-700">
            <span
              className="h-2.5 w-2.5 rounded-xs border border-black/20 shrink-0"
              style={{ background: c }}
            />
            <span className="truncate">{t}</span>
          </div>
        ))}
      </div>

      {/* Bottom Subtitle */}
      <div className="flex shrink-0 items-center justify-between border-t border-slate-200/90 bg-[#f8fafc] px-3 py-1.5 text-[10.5px] text-slate-500">
        <span className="flex items-center gap-1 truncate">
          <Info className="h-3 w-3 shrink-0 text-slate-400" />
          <span>IMD Subdivisions & City Stations · Click region to inspect</span>
        </span>
        <span className="shrink-0">{stats.updated}</span>
      </div>
    </div>
  );
}
