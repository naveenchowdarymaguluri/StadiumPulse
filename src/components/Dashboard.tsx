import React, { useState, useEffect } from 'react';
import { InteractiveMap, Zone } from './InteractiveMap';
import { AlertFeed, Alert, RecommendationCard } from './AlertFeed';

export default function Dashboard() {
  const [zones, setZones] = useState<Zone[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [recommendations, setRecommendations] = useState<RecommendationCard[]>([]);
  
  const [selectedZoneId, setSelectedZoneId] = useState<string | null>('ZONE_A');
  const [loadingZones, setLoadingZones] = useState(true);
  const [loadingAI, setLoadingAI] = useState(false);
  const [simulating, setSimulating] = useState(false);
  
  // Custom Sliders State (for the selected zone)
  const [sliderOccupancy, setSliderOccupancy] = useState(5000);
  const [sliderTemp, setSliderTemp] = useState(75.0);
  const [sliderHumidity, setSliderHumidity] = useState(40.0);

  // Sync sliders to selected zone's current telemetry
  useEffect(() => {
    if (selectedZoneId && zones.length > 0) {
      const activeZone = zones.find(z => z.zone_id === selectedZoneId);
      if (activeZone) {
        setSliderOccupancy(activeZone.occupancy);
        setSliderTemp(activeZone.temperature);
        setSliderHumidity(activeZone.humidity);
      }
    }
  }, [selectedZoneId, zones]);

  // Load telemetry states and alert logs
  const fetchTelemetryData = async () => {
    try {
      const zonesRes = await fetch('/api/zones');
      if (zonesRes.ok) {
        const data = await zonesRes.json();
        setZones(data);
      }
      
      const alertsRes = await fetch('/api/alerts');
      if (alertsRes.ok) {
        const data = await alertsRes.json();
        setAlerts(data);
      }
    } catch (e) {
      console.error("Failed to load telemetry from backend: ", e);
    } finally {
      setLoadingZones(false);
    }
  };

  // Poll backend telemetry every 3 seconds for real-time visualization
  useEffect(() => {
    fetchTelemetryData();
    const interval = setInterval(fetchTelemetryData, 3000);
    return () => clearInterval(interval);
  }, []);

  // Dispatch live telemetry simulation payload to backend
  const sendTelemetryPayload = async (zone_id: string, occupancy: number, temp: number, humidity: number, capacity?: number) => {
    try {
      const res = await fetch('/api/telemetry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          zone_id,
          occupancy,
          temperature: temp,
          humidity,
          capacity
        })
      });
      if (!res.ok) {
        console.error("Telemetry update failed", await res.text());
      }
    } catch (e) {
      console.error("Telemetry payload transmission failed: ", e);
    }
  };

  // Trigger Gemini AI Reasoning layer
  const handleTriggerAI = async () => {
    setLoadingAI(true);
    try {
      const res = await fetch('/api/reason', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (res.ok) {
        const data = await res.json();
        setRecommendations(data);
      } else {
        console.error("GenAI reasoning matrix returned error status");
      }
    } catch (e) {
      console.error("Failed to trigger GenAI reasoner: ", e);
    } finally {
      setLoadingAI(false);
    }
  };

  // Helper to submit a simulated emergency incident to backend
  const postMockIncident = async (incident: {
    incident_id: string;
    zone_id: string;
    title: string;
    description: string;
    priority: 'P1' | 'P2' | 'P3' | 'P4';
    status: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED';
  }) => {
    try {
      await fetch('/api/incidents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...incident,
          timestamp: new Date().toISOString()
        })
      });
    } catch (e) {
      console.error("Incident logging failed: ", e);
    }
  };

  // Simulation Scenario A: South Entrance Bottleneck + Thermal Stress
  const triggerScenarioA = async () => {
    setSimulating(true);
    // ZONE_A capacity is 15,000. Send density > 90% (14,100 people)
    // Ambient Temp: 94°F, Humidity: 72% -> HI = 112°F (Extreme danger)
    await sendTelemetryPayload('ZONE_A', 14100, 94.0, 72.0, 15000);
    // Lower load in surrounding zones
    await sendTelemetryPayload('ZONE_B', 3200, 80.0, 45.0, 20000);
    await sendTelemetryPayload('ZONE_C', 4500, 81.0, 40.0, 18000);
    await sendTelemetryPayload('ZONE_D', 4100, 80.5, 42.0, 25000);
    await sendTelemetryPayload('ZONE_E', 2100, 79.0, 48.0, 12000);
    await sendTelemetryPayload('ZONE_F', 5800, 82.0, 38.0, 30000);
    
    // Refresh states and automatically trigger AI analysis
    await fetchTelemetryData();
    setSelectedZoneId('ZONE_A');
    await handleTriggerAI();
    setSimulating(false);
  };

  // Simulation Scenario B: Medical Emergency Upper Tier C (Priority 1)
  const triggerScenarioB = async () => {
    setSimulating(true);
    // Telemetry: Zone C high density (81%), but heat is moderate (Temp 81°F, Humid 45%)
    await sendTelemetryPayload('ZONE_C', 14500, 81.0, 45.0, 18000);
    
    // Log Priority 1 Medical collapse
    await postMockIncident({
      incident_id: `inc-${Date.now()}`,
      zone_id: 'ZONE_C',
      title: 'Fan Collapse in Section 312',
      description: 'Potential heat exhaustion or cardiac event at row S seat 14. Wheelchair companion present.',
      priority: 'P1',
      status: 'OPEN'
    });
    
    await fetchTelemetryData();
    setSelectedZoneId('ZONE_C');
    await handleTriggerAI();
    setSimulating(false);
  };

  // Reset all simulation events to Normal operating state
  const resetNormalOperations = async () => {
    setSimulating(true);
    // Set all zones to safe operating parameters
    await sendTelemetryPayload('ZONE_A', 4500, 75.0, 40.0, 15000);
    await sendTelemetryPayload('ZONE_B', 6200, 76.0, 38.0, 20000);
    await sendTelemetryPayload('ZONE_C', 5100, 74.0, 42.0, 18000);
    await sendTelemetryPayload('ZONE_D', 7500, 75.5, 40.0, 25000);
    await sendTelemetryPayload('ZONE_E', 3200, 74.5, 41.0, 12000);
    await sendTelemetryPayload('ZONE_F', 8100, 76.5, 39.0, 30000);
    
    // Clear incident stores if needed (by re-fetching baseline configuration)
    await fetch('/api/incidents'); // Querying clear logs
    
    await fetchTelemetryData();
    setRecommendations([]);
    setSimulating(false);
  };

  // Save manual slider updates
  const handleSliderSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedZoneId) return;
    
    const zone = zones.find(z => z.zone_id === selectedZoneId);
    if (!zone) return;

    await sendTelemetryPayload(selectedZoneId, sliderOccupancy, sliderTemp, sliderHumidity, zone.capacity);
    await fetchTelemetryData();
  };

  return (
    <div className="min-h-screen bg-[#0A0E1A] text-[#F3F4F6] flex flex-col font-sans">
      {/* Premium Header */}
      <header className="border-b border-brand-border bg-brand-dark/95 backdrop-blur-md sticky top-0 z-50 px-6 py-4 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {/* Soccer Ball Brand Icon */}
          <svg className="h-9 w-9 text-brand-accent animate-spin-slow" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8 0-1.85.63-3.55 1.69-4.9L10 12v3l4 1.5 2.5-2.5 1.5.5c.6-1.35.91-2.85.91-4.5 0-4.41-3.59-8-8-8v2h-3l-1.5 1.5.5 1.5L5.09 9.09C5.03 9.39 5 9.69 5 10c0 .31.03.61.09.91l3.59 2.59 1.5-.5 2.5 2.5L14 14v-3l4.31-4.9c1.06 1.35 1.69 3.05 1.69 4.9 0 4.41-3.59 8-8 8z" />
          </svg>
          <div>
            <h1 className="text-2xl font-black tracking-wider text-white uppercase">
              Stadium<span className="text-brand-accent">Pulse</span>
            </h1>
            <p className="text-[10px] text-brand-accent font-bold tracking-widest uppercase">
              FIFA World Cup 2026 Operations Console
            </p>
          </div>
        </div>

        {/* Global Match Clock and Server Health Indicators */}
        <div className="flex items-center gap-6">
          <div className="hidden sm:block text-right">
            <span className="text-xs text-brand-muted block uppercase tracking-wider">Tournament Clock</span>
            <span className="font-mono text-white font-bold text-sm">Matchday 18 - 17:35 UTC</span>
          </div>
          
          <div className="bg-brand-card px-4 py-2 rounded-lg border border-brand-border flex items-center gap-3">
            <span className="h-2.5 w-2.5 rounded-full bg-brand-accent animate-ping" />
            <span className="text-xs font-bold text-white uppercase tracking-wider">Server Operational</span>
          </div>
        </div>
      </header>

      {/* Main Dashboard Layout */}
      <main className="flex-1 p-6 grid grid-cols-1 xl:grid-cols-3 gap-6">
        
        {/* Left Col: Scenario Simulators & Telemetry Sliders (1/3 width on wide) */}
        <div className="space-y-6">
          
          {/* Emergency Simulators Panel */}
          <div className="bg-brand-card border border-brand-border rounded-xl p-6 shadow-2xl">
            <h2 className="text-lg font-bold text-white mb-3 flex items-center gap-2">
              <span>🎮</span> Tournament Crisis Simulators
            </h2>
            <p className="text-xs text-brand-muted mb-4">
              Inject real-time matchday events to ground safety calculations and verify the Gemini AI reasoning output.
            </p>

            <div className="space-y-3">
              <button
                onClick={triggerScenarioA}
                disabled={simulating}
                className="w-full text-left p-3.5 bg-red-950/40 hover:bg-red-950/60 border border-red-800/40 hover:border-red-500 rounded-lg transition-all focusable text-xs font-bold block"
              >
                <div className="text-red-400 font-bold mb-1 flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-red-500 animate-ping" />
                  Scenario A: South Entrance Bottleneck
                </div>
                <div className="text-red-200/70 font-normal leading-relaxed">
                  Triggers 91% occupancy under South Entrance canopy during extreme heat stress (HI 112°F).
                </div>
              </button>

              <button
                onClick={triggerScenarioB}
                disabled={simulating}
                className="w-full text-left p-3.5 bg-amber-950/40 hover:bg-amber-950/60 border border-amber-800/40 hover:border-amber-500 rounded-lg transition-all focusable text-xs font-bold block"
              >
                <div className="text-amber-400 font-bold mb-1 flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-amber-500 animate-ping" />
                  Scenario B: Upper Tier C Medical Incident
                </div>
                <div className="text-amber-200/70 font-normal leading-relaxed">
                  Triggers a Priority 1 emergency collapse in high density upper seating row section.
                </div>
              </button>

              <button
                onClick={resetNormalOperations}
                disabled={simulating}
                className="w-full py-2.5 bg-brand-dark hover:bg-brand-border/60 text-center font-bold text-xs text-brand-accent rounded-lg border border-brand-accent transition-all focusable block"
              >
                Reset Stadium to Normal Operations
              </button>
            </div>
          </div>

          {/* Telemetry Manual Overlay Slider Controller */}
          <div className="bg-brand-card border border-brand-border rounded-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <span>🎛️</span> Telemetry Fine-Tuning
              </h2>
              {selectedZoneId && (
                <span className="text-xs bg-brand-dark px-2.5 py-0.5 rounded border border-brand-border text-white font-bold uppercase tracking-wider">
                  {selectedZoneId.replace('_', ' ')}
                </span>
              )}
            </div>
            <p className="text-xs text-brand-muted mb-4">
              Select a zone on the map to modify local IoT sensors. Submit slider adjustments to trigger recalculations.
            </p>

            {selectedZoneId ? (
              <form onSubmit={handleSliderSubmit} className="space-y-4">
                {/* Occupancy Slider */}
                <div>
                  <div className="flex justify-between text-xs font-semibold mb-1">
                    <span className="text-brand-muted">Occupancy Count</span>
                    <span className="text-white font-mono">{sliderOccupancy.toLocaleString()} Pax</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max={zones.find(z => z.zone_id === selectedZoneId)?.capacity || 20000}
                    value={sliderOccupancy}
                    onChange={(e) => setSliderOccupancy(parseInt(e.target.value))}
                    className="w-full h-1.5 bg-brand-dark rounded-lg appearance-none cursor-pointer accent-brand-accent"
                  />
                </div>

                {/* Temperature Slider */}
                <div>
                  <div className="flex justify-between text-xs font-semibold mb-1">
                    <span className="text-brand-muted">Ambient Temperature</span>
                    <span className="text-white font-mono">{sliderTemp.toFixed(1)}°F</span>
                  </div>
                  <input
                    type="range"
                    min="-10"
                    max="130"
                    step="0.5"
                    value={sliderTemp}
                    onChange={(e) => setSliderTemp(parseFloat(e.target.value))}
                    className="w-full h-1.5 bg-brand-dark rounded-lg appearance-none cursor-pointer accent-brand-accent"
                  />
                </div>

                {/* Humidity Slider */}
                <div>
                  <div className="flex justify-between text-xs font-semibold mb-1">
                    <span className="text-brand-muted">Relative Humidity</span>
                    <span className="text-white font-mono">{sliderHumidity.toFixed(1)}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={sliderHumidity}
                    onChange={(e) => setSliderHumidity(parseFloat(e.target.value))}
                    className="w-full h-1.5 bg-brand-dark rounded-lg appearance-none cursor-pointer accent-brand-accent"
                  />
                </div>

                <button
                  type="submit"
                  className="w-full py-2 bg-brand-accent hover:bg-emerald-600 text-brand-dark font-bold text-xs rounded-lg transition focusable uppercase tracking-wider mt-2"
                >
                  Apply IoT Sensor Update
                </button>
              </form>
            ) : (
              <p className="text-xs text-center text-brand-muted italic py-6">
                Click on a zone on the stadium vector map to unlock fine-tuning.
              </p>
            )}
          </div>
        </div>

        {/* Center & Right Cols: Interactive Map & Live Feeds (2/3 width on wide) */}
        <div className="xl:col-span-2 space-y-6">
          {/* Interactive Map Visualizer */}
          {loadingZones ? (
            <div className="bg-brand-card border border-brand-border rounded-xl p-12 text-center h-[400px] flex items-center justify-center">
              <span className="text-brand-muted text-sm animate-pulse">Connecting to IoT Stream Gateway...</span>
            </div>
          ) : (
            <InteractiveMap
              zones={zones}
              selectedZoneId={selectedZoneId}
              onSelectZone={(id) => setSelectedZoneId(id)}
            />
          )}

          {/* Alert Feed Console */}
          <AlertFeed
            alerts={alerts}
            recommendations={recommendations}
            loadingAI={loadingAI}
            onRefreshAI={handleTriggerAI}
          />
        </div>
      </main>
    </div>
  );
}
