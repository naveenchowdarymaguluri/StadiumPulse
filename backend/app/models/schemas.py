from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal

# Static list of valid zone IDs
VALID_ZONE_IDS = ['ZONE_A', 'ZONE_B', 'ZONE_C', 'ZONE_D', 'ZONE_E', 'ZONE_F']

class TelemetryInput(BaseModel):
    zone_id: Literal['ZONE_A', 'ZONE_B', 'ZONE_C', 'ZONE_D', 'ZONE_E', 'ZONE_F'] = Field(
        ..., description="Designated zone identifier, strictly restricted to Zones A-F"
    )
    occupancy: int = Field(
        ..., ge=0, description="Real-time occupant count, must be non-negative"
    )
    capacity: Optional[int] = Field(
        None, gt=0, description="Total zone capacity. Defaults to predefined layout capacity if omitted"
    )
    temperature: float = Field(
        ..., ge=-10.0, le=130.0, description="Ambient air temperature in Fahrenheit (-10.0 to 130.0)"
    )
    humidity: float = Field(
        ..., ge=0.0, le=100.0, description="Relative humidity percentage (0.0 to 100.0)"
    )

class ZoneState(BaseModel):
    zone_id: str
    occupancy: int
    capacity: int
    density_pct: float
    temperature: float
    humidity: float
    heat_index: float
    risk_index: float
    status: Literal['SAFE', 'ELEVATED', 'CRITICAL']
    last_updated: str
    step_free_routes: List[str]

class IncidentReport(BaseModel):
    incident_id: str
    zone_id: str
    title: str
    description: str
    priority: Literal['P1', 'P2', 'P3', 'P4']
    status: Literal['OPEN', 'IN_PROGRESS', 'RESOLVED']
    timestamp: str

class MultilingualAlert(BaseModel):
    en: str
    es: str
    fr: str

class RecommendationCard(BaseModel):
    zone_id: str
    severity: Literal['CRITICAL', 'WARNING', 'INFO']
    confidence: float = Field(..., ge=0.0, le=1.0)
    causal_analysis: str
    action_items: List[str]
    multilingual_alerts: MultilingualAlert

class ReasoningRequest(BaseModel):
    zones: List[ZoneState]
    incidents: List[IncidentReport]
    weather_summary: Optional[str] = "Clear skies, no precipitation forecasted"
