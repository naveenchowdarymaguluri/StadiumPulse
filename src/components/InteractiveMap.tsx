import React from 'react';

export interface Zone {
  zone_id: string;
  occupancy: number;
  capacity: number;
  density_pct: number;
  temperature: number;
  humidity: number;
  heat_index: number;
  risk_index: number;
  status: 'SAFE' | 'ELEVATED' | 'CRITICAL';
  last_updated: string;
  step_free_routes: string[];
}

interface InteractiveMapProps {
  zones: Zone[];
  selectedZoneId: string | null;
  onSelectZone: (zoneId: string) => void;
}

export const InteractiveMap: React.FC<InteractiveMapProps> = ({
  zones,
  selectedZoneId,
  onSelectZone,
}) => {
  // Mapping zone IDs to SVG visual polygon paths and label positioning
  const svgZones = [
    {
      id: 'ZONE_A',
      name: 'Zone A (North West)',
      points: '50,50 300,50 250,150 100,150',
      labelX: 175,
      labelY: 100,
    },
    {
      id: 'ZONE_B',
      name: 'Zone B (North East)',
      points: '300,50 550,50 500,150 350,150',
      labelX: 425,
      labelY: 100,
    },
    {
      id: 'ZONE_C',
      name: 'Zone C (East Gates)',
      points: '550,50 550,350 450,280 500,150',
      labelX: 510,
      labelY: 200,
    },
    {
      id: 'ZONE_D',
      name: 'Zone D (South East)',
      points: '300,350 550,350 450,280 350,250',
      labelX: 410,
      labelY: 300,
    },
    {
      id: 'ZONE_E',
      name: 'Zone E (South West)',
      points: '50,350 300,350 250,250 150,280',
      labelX: 190,
      labelY: 300,
    },
    {
      id: 'ZONE_F',
      name: 'Zone F (West Gates)',
      points: '50,50 50,350 150,280 100,150',
      labelX: 90,
      labelY: 200,
    },
  ];

  // Helper to determine the risk status color codes
  const getStatusColors = (zoneData?: Zone) => {
    if (!zoneData) return { fill: 'fill-[#1F2937]', stroke: 'stroke-[#374151]' };
    
    const risk = zoneData.risk_index;
    if (risk < 0.4) {
      return {
        fill: 'fill-emerald-800 hover:fill-emerald-700 active:fill-emerald-900',
        stroke: 'stroke-emerald-400',
        badge: 'bg-emerald-900/80 text-emerald-300 border-emerald-500'
      };
    } else if (risk < 0.85) {
      return {
        fill: 'fill-amber-800 hover:fill-amber-700 active:fill-amber-900',
        stroke: 'stroke-amber-400',
        badge: 'bg-amber-900/80 text-amber-300 border-amber-500'
      };
    } else {
      return {
        fill: 'fill-red-800 hover:fill-red-700 active:fill-red-900 animate-pulse',
        stroke: 'stroke-red-400',
        badge: 'bg-red-900/80 text-red-300 border-red-500'
      };
    }
  };

  const getStatusText = (zoneData?: Zone) => {
    if (!zoneData) return 'No Data';
    return `${zoneData.status} (Risk: ${zoneData.risk_index.toFixed(2)})`;
  };

  return (
    <div className="bg-brand-card border border-brand-border rounded-xl p-6 shadow-2xl relative overflow-hidden flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <span className="h-3 w-3 bg-brand-accent rounded-full animate-ping" />
            Live Vector Matchday Map
          </h2>
          <p className="text-sm text-brand-muted">Click or select a polygon zone vector to inspect telemetry.</p>
        </div>
        <div className="flex gap-4 text-xs font-semibold">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 bg-emerald-700 border border-emerald-400 rounded-sm" />
            <span>Safe (&lt;0.4)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 bg-amber-700 border border-amber-400 rounded-sm" />
            <span>Elevated (&lt;0.85)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-3 bg-red-700 border border-red-400 rounded-sm" />
            <span>Critical (&ge;0.85)</span>
          </div>
        </div>
      </div>

      {/* SVG Viewport Container */}
      <div className="flex-1 flex items-center justify-center p-4 bg-brand-dark/40 rounded-lg border border-brand-border/40">
        <svg 
          viewBox="0 0 600 400" 
          className="w-full max-h-[380px] select-none"
          aria-label="FIFA World Cup Stadium Zone Map"
          role="img"
        >
          {/* Pitch Field Representation */}
          <rect 
            x="220" 
            y="150" 
            width="160" 
            height="100" 
            rx="8" 
            className="fill-green-950/60 stroke-emerald-600/40 stroke-2"
          />
          <circle cx="300" cy="200" r="25" className="fill-none stroke-emerald-600/40 stroke-2" />
          <line x1="300" y1="150" x2="300" y2="250" className="stroke-emerald-600/40 stroke-2" />
          <text x="300" y="205" textAnchor="middle" className="fill-emerald-500/50 text-[10px] uppercase font-bold tracking-widest">
            Field
          </text>

          {/* Render the clickable Stadium Zones */}
          {svgZones.map((sz) => {
            const data = zones.find(z => z.zone_id === sz.id);
            const isSelected = selectedZoneId === sz.id;
            const colors = getStatusColors(data);
            
            return (
              <g key={sz.id}>
                <polygon
                  points={sz.points}
                  tabIndex={0}
                  role="button"
                  aria-label={`${sz.name}: status ${getStatusText(data)}`}
                  className={`
                    ${colors.fill} 
                    ${colors.stroke} 
                    stroke-2 cursor-pointer 
                    transition-all duration-300
                    focusable
                    ${isSelected ? 'stroke-white stroke-[3px] filter drop-shadow-[0_0_12px_rgba(255,255,255,0.4)]' : 'opacity-85'}
                  `}
                  onClick={() => onSelectZone(sz.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onSelectZone(sz.id);
                    }
                  }}
                />
                {/* Zone Name Label */}
                <text
                  x={sz.labelX}
                  y={sz.labelY}
                  textAnchor="middle"
                  className={`pointer-events-none fill-white font-bold text-sm tracking-wider filter drop-shadow-[0_2px_2px_rgba(0,0,0,0.8)]`}
                >
                  {sz.id.replace('ZONE_', '')}
                </text>
                {/* Micro occupancy tracker on SVG */}
                <text
                  x={sz.labelX}
                  y={sz.labelY + 16}
                  textAnchor="middle"
                  className="pointer-events-none fill-[#F3F4F6] text-[10px] font-medium opacity-90 filter drop-shadow-[0_1px_1px_rgba(0,0,0,0.8)]"
                >
                  {data ? `${(data.density_pct).toFixed(0)}% Cap` : 'Offline'}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Under-map metadata detail overlay */}
      {selectedZoneId && (() => {
        const activeZone = zones.find(z => z.zone_id === selectedZoneId);
        if (!activeZone) return null;
        const colors = getStatusColors(activeZone);

        return (
          <div className="mt-4 p-4 bg-brand-dark/80 border border-brand-border rounded-lg animate-fadeIn">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
              <h3 className="font-bold text-white text-base">
                Inspection Console: {selectedZoneId.replace('_', ' ')}
              </h3>
              <span className={`text-xs px-2.5 py-0.5 rounded-full border ${colors.badge} font-bold`}>
                {activeZone.status} (Risk: {activeZone.risk_index.toFixed(2)})
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm mt-3 border-t border-brand-border/40 pt-3">
              <div>
                <span className="text-brand-muted text-xs block">Crowd Occupancy</span>
                <span className="font-semibold text-white">
                  {activeZone.occupancy.toLocaleString()} / {activeZone.capacity.toLocaleString()} ({activeZone.density_pct.toFixed(1)}%)
                </span>
              </div>
              <div>
                <span className="text-brand-muted text-xs block">Heat Index (NOAA)</span>
                <span className="font-semibold text-white">
                  {activeZone.heat_index.toFixed(1)}°F (Ambient {activeZone.temperature.toFixed(1)}°F)
                </span>
              </div>
              <div>
                <span className="text-brand-muted text-xs block">Relative Humidity</span>
                <span className="font-semibold text-white">{activeZone.humidity.toFixed(1)}%</span>
              </div>
              <div>
                <span className="text-brand-muted text-xs block">Last Updated</span>
                <span className="font-semibold text-white">
                  {new Date(activeZone.last_updated).toLocaleTimeString()}
                </span>
              </div>
            </div>

            <div className="mt-4 bg-brand-dark/40 p-3 rounded border border-brand-border/20">
              <span className="text-xs font-bold text-brand-accent block mb-1.5 uppercase tracking-wider">
                ♿ WCAG Accessibility & Emergency Wayfinding Paths
              </span>
              <ul className="list-disc pl-4 text-xs text-brand-text space-y-1">
                {activeZone.step_free_routes.map((route, i) => (
                  <li key={i}>{route}</li>
                ))}
              </ul>
            </div>
          </div>
        );
      })()}
    </div>
  );
};
