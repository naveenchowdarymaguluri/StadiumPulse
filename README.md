# StadiumPulse 🏟️

**StadiumPulse** is a high-performance, real-time GenAI-enabled stadium intelligence and operations system designed for the FIFA World Cup 2026. It integrates a FastAPI backend, a thread-safe Firestore wrapper with local in-memory mock fallback, Google Vertex AI (Gemini 2.5 Flash) reasoning, and a WCAG-compliant React/Tailwind operational console with keyboard-navigable SVG maps.

---

## 🛠️ Project Structure
```text
backend/app/main.py               # Core FastAPI Server & Isolated Math Pipelines
backend/app/logging_config.py      # Production-grade JSON structured logging
backend/app/services/              
  ├── firestore_service.py         # Thread-safe Firestore SDK connector (with SQLite/Dict fallback)
  └── gemini_service.py            # Gemini 2.5 Flash reasoning layer (with rules fallback)
backend/app/models/schemas.py      # Strict validation boundaries using Pydantic v2
src/components/
  ├── Dashboard.tsx                # Operational commands, sliders & preset simulators
  ├── InteractiveMap.tsx           # Interactive SVG layout representing Zones A-F
  └── AlertFeed.tsx                # Auto-refreshing warning notifications & multilingual selector
Dockerfile                         # Production multi-stage Docker builder
docker-compose.yml                 # Application and local Firestore emulator service orchestrator
package.json                       # React & Tailwind node dependencies
tsconfig.json                      # TypeScript compilation compiler options
```

---

## 🧮 Safety-Critical Mathematical Formulation

To prevent hallucinations in emergency routing, calculations are computed deterministically in standard code, isolated from the generative model:

1. **Crowd Density ($D$)**:
   $$D = \left( \frac{N_{\text{active}}}{C_{\text{max}}} \right) \times 100$$
2. **NOAA Heat Index ($H$)**: Standard multi-parameter empirical formulation.
3. **Composite Risk Index ($R$)**:
   $$R = \alpha \cdot D + \beta \cdot \left( \frac{H - H_{\text{baseline}}}{H_{\text{critical}} - H_{\text{baseline}}} \right)$$
   Where:
   * Base thresholds: $H_{\text{baseline}} = 75.0^{\circ}\text{F}$, $H_{\text{critical}} = 105.0^{\circ}\text{F}$.
   * Weights: $\alpha = 0.6$, $\beta = 0.4$.
   * **Critical Override**: If $R \ge 0.85$, the zone status programmatically triggers a `CRITICAL` state, writing system alarms and forcing immediate crowd-diversion alerts.

---

## ⚡ Deployment & Startup

### Method A: Local Node + Python (No Docker)
1. **Start Backend (FastAPI)**:
   ```bash
   pip install -r requirements.txt
   uvicorn backend.app.main:app --port 8000 --reload
   ```
2. **Start Frontend (Vite React)**:
   ```bash
   npm install
   npm run dev
   ```
   Navigate to `http://localhost:5173`.

### Method B: Docker Compose (Local Stack)
```bash
docker-compose up --build
```
This boots up the FastAPI container, serving compiled React static files under `/`, and sets up a local Firestore database emulator.
