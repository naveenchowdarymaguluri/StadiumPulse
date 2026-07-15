import React, { useState } from 'react';

export interface Alert {
  alert_id: string;
  zone_id: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  message: string;
  timestamp: string;
}

export interface RecommendationCard {
  zone_id: string;
  severity: 'CRITICAL' | 'WARNING' | 'INFO';
  confidence: number;
  causal_analysis: string;
  action_items: string[];
  multilingual_alerts: {
    en: string;
    es: string;
    fr: string;
  };
}

interface AlertFeedProps {
  alerts: Alert[];
  recommendations: RecommendationCard[];
  loadingAI: boolean;
  onRefreshAI: () => void;
}

export const AlertFeed: React.FC<AlertFeedProps> = ({
  alerts,
  recommendations,
  loadingAI,
  onRefreshAI,
}) => {
  const [filterSeverity, setFilterSeverity] = useState<'ALL' | 'CRITICAL' | 'WARNING' | 'INFO'>('ALL');
  const [activeLang, setActiveLang] = useState<'en' | 'es' | 'fr'>('en');
  
  // Pagination State for System Alerts
  const [alertPage, setAlertPage] = useState(1);
  const itemsPerPage = 5;

  // Filter recommendations based on severity
  const filteredRecs = recommendations.filter((rec) => {
    if (filterSeverity === 'ALL') return true;
    return rec.severity === filterSeverity;
  });

  // Filter system alerts
  const filteredAlerts = alerts.filter((alert) => {
    if (filterSeverity === 'ALL') return true;
    return alert.severity === filterSeverity;
  });

  // Paginated System Alerts
  const totalAlertPages = Math.max(1, Math.ceil(filteredAlerts.length / itemsPerPage));
  const startIndex = (alertPage - 1) * itemsPerPage;
  const paginatedAlerts = filteredAlerts.slice(startIndex, startIndex + itemsPerPage);

  const getSeverityBadgeClass = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
        return 'bg-red-950/80 text-red-300 border-red-700';
      case 'WARNING':
        return 'bg-amber-950/80 text-amber-300 border-amber-700';
      default:
        return 'bg-blue-950/80 text-blue-300 border-blue-700';
    }
  };

  return (
    <div className="bg-brand-card border border-brand-border rounded-xl p-6 shadow-2xl flex flex-col h-full">
      {/* Title block */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 border-b border-brand-border/40 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            🚨 Operation Logs & GenAI Triage
          </h2>
          <p className="text-sm text-brand-muted">Real-time alerts, incident reports, and translation aids.</p>
        </div>

        {/* Translation trigger */}
        <div className="flex items-center gap-2 bg-brand-dark/80 p-1 rounded-lg border border-brand-border">
          <span className="text-xs text-brand-muted px-2">Translate AI:</span>
          {(['en', 'es', 'fr'] as const).map((lang) => (
            <button
              key={lang}
              onClick={() => setActiveLang(lang)}
              aria-pressed={activeLang === lang}
              className={`px-3 py-1 rounded text-xs font-bold uppercase transition-all duration-200 focusable ${
                activeLang === lang
                  ? 'bg-brand-accent text-brand-dark shadow'
                  : 'text-brand-text hover:bg-brand-card'
              }`}
            >
              {lang}
            </button>
          ))}
        </div>
      </div>

      {/* Filter and GenAI Trigger buttons */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
        {/* Severity filter selectors */}
        <div className="flex flex-wrap gap-2">
          {(['ALL', 'CRITICAL', 'WARNING', 'INFO'] as const).map((sev) => (
            <button
              key={sev}
              onClick={() => {
                setFilterSeverity(sev);
                setAlertPage(1); // Reset page on filter change
              }}
              aria-pressed={filterSeverity === sev}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold border transition-all duration-200 focusable ${
                filterSeverity === sev
                  ? 'bg-brand-text text-brand-dark border-brand-text'
                  : 'bg-brand-dark text-brand-muted border-brand-border hover:text-white'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>

        <button
          onClick={onRefreshAI}
          disabled={loadingAI}
          className="px-4 py-2 bg-brand-accent hover:bg-emerald-600 disabled:bg-emerald-800/50 text-brand-dark font-bold rounded-lg text-xs transition-all duration-200 flex items-center gap-1.5 shadow focusable disabled:cursor-not-allowed"
        >
          {loadingAI ? (
            <>
              <svg className="animate-spin h-3.5 w-3.5 text-brand-dark" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>Analyzing...</span>
            </>
          ) : (
            <>
              <span>✨ Trigger GenAI Reasoner</span>
            </>
          )}
        </button>
      </div>

      {/* Main split grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 min-h-[400px]">
        {/* Left half: GenAI cognitive suggestions */}
        <div className="border border-brand-border/40 rounded-xl p-4 bg-brand-dark/20 flex flex-col">
          <h3 className="text-sm font-bold text-brand-accent uppercase tracking-wider mb-3 flex items-center justify-between">
            <span>Vertex AI Grounded Actions</span>
            <span className="text-[10px] text-brand-muted font-normal lowercase">Powered by gemini-2.5-flash</span>
          </h3>

          <div aria-live="polite" className="space-y-4 overflow-y-auto flex-1 max-h-[480px] pr-1">
            {filteredRecs.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-brand-muted">
                <span className="text-2xl mb-2">💡</span>
                <p className="text-xs">No active AI suggestions. Click "Trigger GenAI Reasoner" above to synthesize active telemetry.</p>
              </div>
            ) : (
              filteredRecs.map((rec, idx) => (
                <div key={idx} className="bg-brand-dark/80 border border-brand-border rounded-lg p-4 space-y-3 animate-fadeIn">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-white">{rec.zone_id.replace('_', ' ')}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-brand-muted">Conf: {(rec.confidence * 100).toFixed(0)}%</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded border ${getSeverityBadgeClass(rec.severity)} font-bold`}>
                        {rec.severity}
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-brand-text leading-relaxed bg-brand-card/40 p-2.5 rounded border border-brand-border/20">
                    <span className="font-semibold block text-brand-accent mb-1">Causal Explanation:</span>
                    {rec.causal_analysis}
                  </p>

                  <div className="space-y-1.5">
                    <span className="text-[11px] font-bold text-brand-muted uppercase block">Emergency Dispatch Items:</span>
                    <ul className="list-disc pl-4 text-xs text-brand-text space-y-1">
                      {rec.action_items.map((item, i) => (
                        <li key={i}>{item}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="border-t border-brand-border/40 pt-2.5">
                    <span className="text-[10px] font-bold text-amber-500 block mb-1">Broadcast PA System Alert ({activeLang.toUpperCase()}):</span>
                    <p className="text-xs italic text-amber-200 bg-amber-950/20 p-2 rounded border border-amber-900/40">
                      "{rec.multilingual_alerts[activeLang]}"
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right half: System Telemetry Alerts */}
        <div className="border border-brand-border/40 rounded-xl p-4 bg-brand-dark/20 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-3">
              Telemetry Alarm Log
            </h3>
            
            <div aria-live="polite" className="space-y-3 overflow-y-auto max-h-[420px] pr-1">
              {paginatedAlerts.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-brand-muted">
                  <span className="text-2xl mb-2">✅</span>
                  <p className="text-xs">No active telemetry alarms found for this severity filter.</p>
                </div>
              ) : (
                paginatedAlerts.map((alert) => (
                  <div key={alert.alert_id} className="bg-brand-dark/80 border border-brand-border rounded-lg p-3 flex gap-3 items-start animate-fadeIn">
                    <span className={`text-xs px-2 py-1 rounded border font-bold shrink-0 ${getSeverityBadgeClass(alert.severity)}`}>
                      {alert.severity}
                    </span>
                    <div className="space-y-1">
                      <p className="text-xs font-semibold text-white">{alert.message}</p>
                      <div className="flex items-center gap-3 text-[10px] text-brand-muted">
                        <span>Zone: {alert.zone_id.replace('ZONE_', '')}</span>
                        <span>•</span>
                        <span>{new Date(alert.timestamp).toLocaleTimeString()}</span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Pagination Controls */}
          {filteredAlerts.length > itemsPerPage && (
            <div className="flex items-center justify-between border-t border-brand-border/40 pt-4 mt-4">
              <span className="text-xs text-brand-muted">
                Showing {startIndex + 1}-{Math.min(startIndex + itemsPerPage, filteredAlerts.length)} of {filteredAlerts.length} alarms
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setAlertPage(p => Math.max(1, p - 1))}
                  disabled={alertPage === 1}
                  className="px-3 py-1 bg-brand-dark hover:bg-brand-card disabled:opacity-40 text-xs text-white border border-brand-border rounded focusable transition disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <button
                  onClick={() => setAlertPage(p => Math.min(totalAlertPages, p + 1))}
                  disabled={alertPage === totalAlertPages}
                  className="px-3 py-1 bg-brand-dark hover:bg-brand-card disabled:opacity-40 text-xs text-white border border-brand-border rounded focusable transition disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
