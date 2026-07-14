import os
import threading
import asyncio
from typing import List, Dict, Any, Generator, AsyncGenerator
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
                # Instantiate Firestore client
                self.db = firestore.Client()
                logger.info("Firestore client initialized successfully.", database="production")
                
                # Check connection and pre-populate if needed
                self._bootstrap_firestore_db()
            except Exception as e:
                logger.warning("Failed to connect to Firestore. Activating local mock fallback.", error=str(e))
                self.use_fallback = True
        else:
            logger.info("No GCP credentials found. Activating in-memory thread-safe database fallback.", database="in_memory")
            self.use_fallback = True

    def _bootstrap_firestore_db(self):
        """Helper to create initial zone documents in Firestore if they don't exist"""
        try:
            for zone_id, defaults in ZONE_DEFAULTS.items():
                doc_ref = self.db.collection('zones').document(zone_id)
                if not doc_ref.get().exists:
                    doc_ref.set({
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
            logger.error("Failed to bootstrap Firestore database.", error=str(e))
            self.use_fallback = True

    # 1. FETCH ZONE STATE (Sync and Async)
    def get_zone_sync(self, zone_id: str) -> Dict[str, Any]:
        if self.use_fallback:
            with self.fallback_lock:
                zone = self.fallback_db['zones'].get(zone_id)
                if not zone:
                    raise KeyError(f"Zone {zone_id} not found.")
                return dict(zone)
        else:
            doc = self.db.collection('zones').document(zone_id).get()
            if not doc.exists:
                raise KeyError(f"Zone {zone_id} not found in Firestore.")
            return doc.to_dict()

    async def get_zone_async(self, zone_id: str) -> Dict[str, Any]:
        # Run blocking Firestore/fallback get inside run_in_executor to ensure true concurrency
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get_zone_sync, zone_id)

    # 2. UPDATE ZONE STATE (Sync and Async)
    def update_zone_sync(self, zone_id: str, data: Dict[str, Any]) -> None:
        if self.use_fallback:
            with self.fallback_lock:
                if zone_id not in self.fallback_db['zones']:
                    raise KeyError(f"Zone {zone_id} not found.")
                self.fallback_db['zones'][zone_id].update(data)
                logger.debug("Local store zone updated.", zone_id=zone_id, update_data=data)
        else:
            self.db.collection('zones').document(zone_id).update(data)
            logger.debug("Firestore zone updated.", zone_id=zone_id, update_data=data)

    async def update_zone_async(self, zone_id: str, data: Dict[str, Any]) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.update_zone_sync, zone_id, data)

    # 3. FETCH ALL ZONES (Sync and Async)
    def get_all_zones_sync(self) -> List[Dict[str, Any]]:
        if self.use_fallback:
            with self.fallback_lock:
                return [dict(zone) for zone in self.fallback_db['zones'].values()]
        else:
            docs = self.db.collection('zones').stream()
            return [doc.to_dict() for doc in docs]

    async def get_all_zones_async(self) -> List[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get_all_zones_sync)

    # 4. STREAM ACTIVE ZONES (Sync and Async Generator)
    def stream_zones_sync(self) -> Generator[List[Dict[str, Any]], None, None]:
        # Mock streaming by returning the current snap and sleeping or yielding
        yield self.get_all_zones_sync()

    async def stream_zones_async(self) -> AsyncGenerator[List[Dict[str, Any]], None]:
        yield await self.get_all_zones_async()

    # 5. ALERTS HISTORY (Sync and Async)
    def get_all_alerts_sync(self) -> List[Dict[str, Any]]:
        if self.use_fallback:
            with self.fallback_lock:
                return list(self.fallback_db['alerts'])
        else:
            docs = self.db.collection('alerts').order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
            return [doc.to_dict() for doc in docs]

    async def get_all_alerts_async(self) -> List[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get_all_alerts_sync)

    def add_alert_sync(self, alert_data: Dict[str, Any]) -> None:
        if self.use_fallback:
            with self.fallback_lock:
                self.fallback_db['alerts'].insert(0, alert_data)
        else:
            self.db.collection('alerts').add(alert_data)

    async def add_alert_async(self, alert_data: Dict[str, Any]) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.add_alert_sync, alert_data)

    # 6. INCIDENTS HISTORY (Sync and Async)
    def get_all_incidents_sync(self) -> List[Dict[str, Any]]:
        if self.use_fallback:
            with self.fallback_lock:
                return list(self.fallback_db['incidents'])
        else:
            docs = self.db.collection('incidents').stream()
            return [doc.to_dict() for doc in docs]

    async def get_all_incidents_async(self) -> List[Dict[str, Any]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get_all_incidents_sync)

    def add_incident_sync(self, incident_data: Dict[str, Any]) -> None:
        if self.use_fallback:
            with self.fallback_lock:
                self.fallback_db['incidents'].insert(0, incident_data)
        else:
            self.db.collection('incidents').add(incident_data)

    async def add_incident_async(self, incident_data: Dict[str, Any]) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.add_incident_sync, incident_data)
