import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google")
warnings.filterwarnings("ignore", category=DeprecationWarning)
import time
import uuid
import threading
import math
import os
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.logging_config import configure_logging
from backend.app.models.schemas import TelemetryInput, ZoneState, IncidentReport, ReasoningRequest, RecommendationCard
from backend.app.services.firestore_service import FirestoreService, ZONE_DEFAULTS
from backend.app.services.gemini_service import GeminiService
import structlog

# Initialize logging configuration
configure_logging()
logger = structlog.get_logger()

# Initialize Services
db_service = FirestoreService()
gemini_service = GeminiService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Bootstrap the Firestore database asynchronously on startup
    await db_service.bootstrap_async()
    yield

# Instantiate FastAPI application
app = FastAPI(
    title="StadiumPulse API",
    description="Real-time GenAI-enabled stadium intelligence and operations system for the FIFA World Cup 2026",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration (securely configured in production via ALLOWED_ORIGINS)
allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "*")
allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Token-Bucket Rate Limiter Middleware (Per-IP)
class TokenBucketRateLimiter(BaseHTTPMiddleware):
    def __init__(self, app, rate_limit: float = 10.0, capacity: float = 20.0):
        super().__init__(app)
        self.rate_limit = rate_limit  # tokens added per second
        self.capacity = capacity      # max token capacity
        self.buckets = {}             # ip -> (tokens, last_refill_time)
        self.lock = threading.Lock()

    async def dispatch(self, request: Request, call_next) -> Response:
        # Exclude documentation or health paths from rate limits
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        # Handle X-Forwarded-For headers to get actual client IP behind reverse proxies
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()

        with self.lock:
            if client_ip not in self.buckets:
                self.buckets[client_ip] = (self.capacity, now)

            tokens, last_refill = self.buckets[client_ip]
            # Refill tokens according to elapsed time
            elapsed = now - last_refill
            tokens = min(self.capacity, tokens + elapsed * self.rate_limit)

            if tokens >= 1.0:
                tokens -= 1.0
                self.buckets[client_ip] = (tokens, now)
                allowed = True
            else:
                self.buckets[client_ip] = (tokens, now)
                allowed = False

        if not allowed:
            logger.warning("Rate limit exceeded for client", client_ip=client_ip, path=request.url.path)
            return Response(
                content='{"detail": "Rate limit exceeded. Too many requests. Refilling tokens..."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json"
            )

        return await call_next(request)

app.add_middleware(TokenBucketRateLimiter, rate_limit=15.0, capacity=30.0)


# ----------------- DETERMINISTIC MATHEMATICAL PIPELINES -----------------

def calculate_heat_index(T: float, R: float) -> float:
    """
    Computes the NOAA Multi-Parameter Heat Index (apparent temperature) in Fahrenheit.
    Formula applies standard NOAA regression formulation including low/high relative humidity adjustments.
    """
    # For temperatures below 80F or humidity below 40%, NOAA recommends direct temperature
    if T < 80.0 or R < 40.0:
        return T

    # Multi-parameter empirical coefficients
    c1 = -42.379
    c2 = 2.04901523
    c3 = 10.14333127
    c4 = -0.22475541
    c5 = -0.00683783
    c6 = -0.05481717
    c7 = 0.00122874
    c8 = 0.00085282
    c9 = -0.00000199

    H = (
        c1
        + c2 * T
        + c3 * R
        + c4 * T * R
        + c5 * (T**2)
        + c6 * (R**2)
        + c7 * (T**2) * R
        + c8 * T * (R**2)
        + c9 * (T**2) * (R**2)
    )

    # NOAA Adjustments:
    # 1. Subtraction adjustment for low humidity (< 13%) and temperatures between 80F and 112F
    if 80.0 <= T <= 112.0 and R < 13.0:
        adjustment = ((13.0 - R) / 4.0) * math.sqrt((17.0 - abs(T - 95.0)) / 17.0)
        H -= adjustment
    # 2. Addition adjustment for high humidity (> 85%) and temperatures between 80F and 87F
    elif 80.0 <= T <= 87.0 and R > 85.0:
        adjustment = ((R - 85.0) / 10.0) * ((87.0 - T) / 5.0)
        H += adjustment

    return round(H, 2)

def calculate_risk_index(density_pct: float, heat_index: float) -> float:
    """
    Computes Composite Risk Index:
    R = alpha * D + beta * ((H - H_baseline) / (H_critical - H_baseline))
    where alpha = 0.6, beta = 0.4, H_baseline = 75.0, H_critical = 105.0.
    """
    alpha = 0.6
    beta = 0.4
    h_baseline = 75.0
    h_critical = 105.0

    # Normalize density (D) to [0.0, 1.0]
    d_factor = min(1.0, max(0.0, density_pct / 100.0))

    # Normalize Heat Index (H) factor to [0.0, 1.0]
    if heat_index <= h_baseline:
        h_factor = 0.0
    else:
        h_factor = min(1.0, (heat_index - h_baseline) / (h_critical - h_baseline))

    R = alpha * d_factor + beta * h_factor
    return round(R, 3)

# ----------------- API ENDPOINTS -----------------

@app.get("/health")
def health_check() -> Dict[str, Any]:
    """
    Confirms backend service, mock fallbacks, and internal systems health.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z",
        "database_mode": "fallback_in_memory" if db_service.use_fallback else "firestore_cloud",
        "genai_mode": "fallback_rules" if not gemini_service.client_active else "gemini_api"
    }

@app.get("/api/zones", response_model=List[ZoneState])
async def get_zones() -> List[Dict[str, Any]]:
    """
    Retrieves the current operational states of all 6 stadium zones.
    """
    try:
        zones = await db_service.get_all_zones_async()
        # Ensure zones are ordered properly
        zones = sorted(zones, key=lambda z: z['zone_id'])
        return zones
    except Exception as e:
        logger.error("Failed to fetch zone configurations.", error=str(e))
        raise HTTPException(status_code=500, detail="Database retrieval failed")

@app.post("/api/telemetry")
async def post_telemetry(payload: TelemetryInput) -> Dict[str, Any]:
    """
    Ingests IoT telemetry, executes calculations, writes to DB, and flags anomalies.
    """
    trace_id = str(uuid.uuid4())
    logger.info("Ingesting IoT telemetry payload", zone_id=payload.zone_id, trace_id=trace_id)

    try:
        # Determine capacity: Use payload capacity or DB default
        if payload.capacity:
            capacity = payload.capacity
        else:
            capacity = ZONE_DEFAULTS[payload.zone_id]['capacity']

        # 1. Deterministic Crowd Density: D = (N_active / C_max) * 100
        density = (payload.occupancy / capacity) * 100.0
        
        # 2. Deterministic NOAA Heat Index
        heat_index = calculate_heat_index(payload.temperature, payload.humidity)
        
        # 3. Deterministic Composite Risk Index
        risk_index = calculate_risk_index(density, heat_index)

        # 4. Critical status assessment and color-code logic
        status_state = "SAFE"
        if risk_index >= 0.85:
            status_state = "CRITICAL"
        elif risk_index >= 0.4:
            status_state = "ELEVATED"

        # Step-free route configuration
        step_free_routes = ZONE_DEFAULTS[payload.zone_id]['step_free_routes']
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "") + "Z"

        # Document updates to insert into Firestore / Mock fallback
        zone_update = {
            'zone_id': payload.zone_id,
            'occupancy': payload.occupancy,
            'capacity': capacity,
            'density_pct': round(density, 2),
            'temperature': payload.temperature,
            'humidity': payload.humidity,
            'heat_index': heat_index,
            'risk_index': risk_index,
            'status': status_state,
            'last_updated': timestamp,
            'step_free_routes': step_free_routes
        }

        # Update Zone Record
        await db_service.update_zone_async(payload.zone_id, zone_update)

        # Write system alert warning logs if critical override active
        if status_state == "CRITICAL":
            alert_payload = {
                'alert_id': str(uuid.uuid4()),
                'zone_id': payload.zone_id,
                'severity': "CRITICAL",
                'message': f"Critical crowd/thermal threat detected in {payload.zone_id}. Risk: {risk_index:.2f}. Heat Index: {heat_index:.1f}°F.",
                'timestamp': timestamp
            }
            await db_service.add_alert_async(alert_payload)
            logger.warn("CRITICAL ZONE RISK STATE DETECTED", zone_id=payload.zone_id, risk_index=risk_index)

        return {"status": "success", "zone_id": payload.zone_id, "data": zone_update}

    except Exception as e:
        logger.error("Telemetry update failed.", trace_id=trace_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process telemetry payload: {str(e)}")

@app.get("/api/alerts")
async def get_alerts() -> List[Dict[str, Any]]:
    """
    Fetches the history logs of active system alerts and notifications.
    """
    try:
        alerts = await db_service.get_all_alerts_async()
        return alerts
    except Exception as e:
        logger.error("Failed to query alerts store.", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts logs")

@app.post("/api/reason", response_model=List[RecommendationCard])
async def trigger_reasoning(request: Optional[ReasoningRequest] = None) -> List[Dict[str, Any]]:
    """
    Aggregates telemetry + incident feeds and queries the GenAI layer for recommendations.
    """
    try:
        if request is None:
            # Aggregate live data directly from DB
            zones_data = await db_service.get_all_zones_async()
            incidents_data = await db_service.get_all_incidents_async()
            weather = "Ambient 95°F, Sunny, 65% Humidity. High heat load across open structures."
        else:
            zones_data = [z.model_dump() for z in request.zones]
            incidents_data = [i.model_dump() for i in request.incidents]
            weather = request.weather_summary

        # Call cognitive intelligence service (Gemini SDK with rules fallback)
        recommendations = gemini_service.generate_recommendations(
            zones=zones_data,
            incidents=incidents_data,
            weather_summary=weather
        )

        return recommendations
    except Exception as e:
        logger.error("Cognitive reasoning engine failed.", error=str(e))
        raise HTTPException(status_code=500, detail="GenAI intelligence processing failed")

@app.post("/api/incidents")
async def post_incident(incident: IncidentReport) -> Dict[str, Any]:
    """
    Submits a mock incident report to ground GenAI diagnostics (e.g. simulated heart attacks).
    """
    try:
        await db_service.add_incident_async(incident.model_dump())
        logger.info("New incident logged", incident_id=incident.incident_id, priority=incident.priority)
        return {"status": "success", "incident_id": incident.incident_id}
    except Exception as e:
        logger.error("Failed to post incident.", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to store incident report")

@app.get("/api/incidents")
async def get_incidents() -> List[Dict[str, Any]]:
    """
    Fetches the list of active incidents.
    """
    try:
        return await db_service.get_all_incidents_async()
    except Exception as e:
        logger.error("Failed to fetch incidents.", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve incidents")

# Serve React static assets in production if directory exists
static_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "dist")
if os.path.exists(static_path):
    app.mount("/", StaticFiles(directory=static_path, html=True), name="static")
    logger.info("Mounted production static React assets directory", path=static_path)
else:
    logger.warning("Production static directory not found, API only mode active", path=static_path)
