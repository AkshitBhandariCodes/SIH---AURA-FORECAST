// Thin fetch layer over the ForecastGuard REST API (same-origin).

async function getJSON(path) {
  const res = await fetch(path);
  if (!res.ok) {
    const err = new Error(`API ${res.status} for ${path}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export const fetchHealth = () => getJSON('/api/v1/health');
export const fetchDates = () => getJSON('/api/v1/forecast/dates');

export const fetchConfidenceMap = (date, leadDay) =>
  getJSON(`/api/v1/confidence-map?date=${date}&lead_day=${leadDay}`);

export const fetchWarningPolygons = (date, leadDay) =>
  getJSON(`/api/v1/polygons/warning-zones?date=${date}&lead_day=${leadDay}`).catch(
    () => null,
  );

export const fetchExplanation = (subdivision, leadDay) =>
  getJSON(`/api/v1/explain?subdivision=${subdivision}&lead_day=${leadDay}`);

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => {
    URL.revokeObjectURL(url);
    a.remove();
  }, 1000);
}
