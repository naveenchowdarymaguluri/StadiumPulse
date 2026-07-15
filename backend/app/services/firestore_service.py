import os
import threading
from typing import List, Dict, Any, AsyncGenerator
from google.cloud import firestore
import structlog

logger = structlog.get_logger()

# Predefined capacities and accessibility routes for World Cup zones
ZONE_DEFAULTS = {
    'ZONE_A': {'capacity': 15000, 'step_free_routes': ["South-East Elevator Bank A to Exit 1", "Main West Access Ramp"]},
    'ZONE_B': {'capacity': 20000, 'step_free_routes': ["North Concourse Elevator B to Exit 4", "North Ramp Gate B"]},
    'ZONE_C': {'capacity': 18000, 'step_free_routes': ["East concourse Lift C-2 to Parking Lot A", "Level 1 Concourse Flat Corridor"]},
    'ZONE_D': {'capacity': 25000, 'step_free_routes': ["South Ramp Elevators D-1 & D-2", "Level 2 Transit Link"]},
    'ZONE_E': {'capacity': 12000, 'step_free_routes': ["West Tunnel Escalator (Wheelchair Override)", "Exit Gate 8 Ramp"]},
    'ZONE_F': {'capacity': 30000, 'step_free_routes': ["Central Lift Plaza to Skybox Level", "South-West Ramp to Gate 12"]}
}

class FirestoreService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(FirestoreService, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.db = None
        self.use_fallback = False
        self.fallback_db = {
            'zones': {},
            'alerts': [],
            'incidents': []
        }
        self.fallback_lock = threading.Lock()
        
        # Initialize default zone records in local store
        for zone_id, defaults in ZONE_DEFAULTS.items():
            self.fallback_db['zones'][zone_id] = {
                'zone_id': zone_id,
                'occupancy': 0,
                'capacity': defaults['capacity'],
                'density_pct': 0.0,
                'temperature': 70.0,
                'humidity': 40.0,
                'heat_index': 70.0,
                'risk_index': 0.0,
                'status': 'SAFE',
                'last_updated': '2026-07-14T12:00:00Z',
                'step_free_routes': defaults['step_free_routes']
            }

        # Check for Google Credentials or Firestore Emulator Host
        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")
        
        if cred_path or emulator_host:
            try:
                # Instantiate Firestore AsyncClient for native asynchronous performance
                self.db = firestore.AsyncClient()
                logger.info("Firestore AsyncClient initialized successfully.", database="production")
            except Exception as e:
                logger.warning("Failed to connect to Firestore. Activating local mock fallback.", error=str(e))
                self.use_fallback = True
        else:
            logger.info("No GCP credentials found. Activating in-memory thread-safe database fallback.", database="in_memory")
            self.use_fallback = True

    async def bootstrap_async(self):
        """Helper to create initial zone documents in Firestore if they don't exist"""
        if self.use_fallback:
            return
        try:
            for zone_id, defaults in ZONE_DEFAULTS.items():
                doc_ref = self.db.collection('zones').document(zone_id)
                doc_snap = await doc_ref.get()
                if not doc_snap.exists:
                    await doc_ref.set({
                        'zone_id': zone_id,
                        'occupancy': 0,
                        'capacity': defaults['capacity'],
                        'density_pct': 0.0,
                        'temperature': 70.0,
                        'humidity': 40.0,
                        'heat_index': 70.0,
                        'risk_index': 0.0,
                        'status': 'SAFE',
                        'last_updated': '2026-07-14T12:00:00Z',
                        'step_free_routes': defaults['step_free_routes']
                    })
            logger.info("Firestore database successfully bootstrapped.")
        except Exception as e:
            logger.error("Failed to bootstrap Firestore database asynchronously.", error=str(e))
            self.use_fallback = True

    # 1. FETCH ZONE STATE (Async Only)
    async def get_zone_async(self, zone_id: str) -> Dict[str, Any]:
        if self.use_fallback:
            with self.fallback_lock:
                zone = self.fallback_db['zones'].get(zone_id)
                if not zone:
                    raise KeyError(f"Zone {zone_id} not found.")
                return dict(zone)
        else:
            doc = await self.db.collection('zones').document(zone_id).get()
            if not doc.exists:
                raise KeyError(f"Zone {zone_id} not found in Firestore.")
            return doc.to_dict()

    # 2. UPDATE ZONE STATE (Async Only)
    async def update_zone_async(self, zone_id: str, data: Dict[str, Any]) -> None:
        if self.use_fallback:
            with self.fallback_lock:
                if zone_id not in self.fallback_db['zones']:
                    raise KeyError(f"Zone {zone_id} not found.")
                self.fallback_db['zones'][zone_id].update(data)
                logger.debug("Local store zone updated.", zone_id=zone_id, update_data=data)
        else:
            await self.db.collection('zones').document(zone_id).update(data)
            logger.debug("Firestore zone updated.", zone_id=zone_id, update_data=data)

    # 3. FETCH ALL ZONES (Async Only)
    async def get_all_zones_async(self) -> List[Dict[str, Any]]:
        if self.use_fallback:
            with self.fallback_lock:
                return [dict(zone) for zone in self.fallback_db['zones'].values()]
        else:
            docs = self.db.collection('zones').stream()
            zones_data = []
            async for doc in docs:
                zones_data.append(doc.to_dict())
            return zones_data

    # 4. STREAM ACTIVE ZONES (Async Generator)
    async def stream_zones_async(self) -> AsyncGenerator[List[Dict[str, Any]], None]:
        yield await self.get_all_zones_async()

    # 5. ALERTS HISTORY (Async Only)
    async def get_all_alerts_async(self) -> List[Dict[str, Any]]:
        if self.use_fallback:
            with self.fallback_lock:
                return list(self.fallback_db['alerts'])
        else:
            query = self.db.collection('alerts').order_by('timestamp', direction=firestore.Query.DESCENDING)
            docs = query.stream()
            alerts_data = []
            async for doc in docs:
                alerts_data.append(doc.to_dict())
            return alerts_data

    async def add_alert_async(self, alert_data: Dict[str, Any]) -> None:
        if self.use_fallback:
            with self.fallback_lock:
                self.fallback_db['alerts'].insert(0, alert_data)
        else:
            await self.db.collection('alerts').add(alert_data)

    # 6. INCIDENTS HISTORY (Async Only)
    async def get_all_incidents_async(self) -> List[Dict[str, Any]]:
        if self.use_fallback:
            with self.fallback_lock:
                return list(self.fallback_db['incidents'])
        else:
            docs = self.db.collection('incidents').stream()
            incidents_data = []
            async for doc in docs:
                incidents_data.append(doc.to_dict())
            return incidents_data

    async def add_incident_async(self, incident_data: Dict[str, Any]) -> None:
        if self.use_fallback:
            with self.fallback_lock:
                self.fallback_db['incidents'].insert(0, incident_data)
        else:
            await self.db.collection('incidents').add(incident_data)
