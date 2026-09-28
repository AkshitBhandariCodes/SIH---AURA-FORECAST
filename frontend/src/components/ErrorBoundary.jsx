import React from 'react';
import { TriangleAlert } from 'lucide-react';

/** Last-resort catcher: render error instead of a white screen. */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  componentDidCatch(error, info) {
    // Also visible to the boot watchdog via window.__fgErrors.
    if (window.__fgErrors) {
      window.__fgErrors.push(String((error && error.message) || error));
    }
    console.error('ForecastGuard render error:', error, info);
  }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="mx-auto my-[8vh] max-w-xl rounded-2xl border-2 border-red-600 bg-white p-6 text-sm text-slate-700">
        <h1 className="flex items-center gap-2 text-base font-extrabold text-red-700">
          <TriangleAlert className="h-5 w-5" />
          Something broke while rendering the dashboard
        </h1>
        <pre className="mt-3 overflow-auto rounded-lg bg-slate-100 p-3 font-mono text-xs">
          {String(this.state.error?.message || this.state.error)}
        </pre>
        <button
          onClick={() => window.location.reload()}
          className="mt-4 rounded-lg bg-navy-700 px-4 py-2 text-xs font-bold text-white"
        >
          Reload dashboard
        </button>
      </div>
    );
  }
}
