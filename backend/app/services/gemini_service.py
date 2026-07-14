import os
import json
import structlog
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from google.generativeai.types import GenerateContentResponse

logger = structlog.get_logger()

# Predefined stadium safety guidelines for grounding
STADIUM_SAFETY_GUIDELINES = """
FIFA World Cup 2026 Stadium Operations Safety Manual:
1. Crowd Density Limits: Under standard operation, zone density should remain below 80%. If density exceeds 85%, activate secondary exit channels.
2. Heat Stress Protocol: If the local Heat Index exceeds 105°F, operations staff must deploy misting fans, open shading canopies, and distribute emergency water.
3. Accessible Wayfinding: Maintain clear, step-free access paths (elevators/ramps) for wheelchair and mobility-impaired guests at all times. In emergency evacuations, designate specific elevators for PwD routing.
4. Security Triage: Critical medical emergencies (Priority 1) require clearing surrounding access corridors immediately to allow stretcher access.
"""

class GeminiService:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.client_active = False
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
                self.client_active = True
                logger.info("Gemini service client configured successfully.", model="gemini-2.5-flash")
            except Exception as e:
                logger.warning("Failed to configure Google Generative AI client. Activating rule-based fallback service.", error=str(e))
        else:
            logger.info("GEMINI_API_KEY not found in environment. Activating rule-based fallback service.")

    def generate_recommendations(self, zones: List[Dict[str, Any]], incidents: List[Dict[str, Any]], weather_summary: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Processes real-time stadium state telemetry and returns a list of recommendation cards.
        If the Gemini API is unreachable, it delegates to a high-fidelity deterministic fallback.
        """
        # Grounding context preparation
        system_instruction = f"""
        You are the StadiumPulse GenAI Tournament Intelligence Engine for the FIFA World Cup 2026.
        Analyze real-time stadium zone metrics, weather conditions, active incident logs, and stadium safety guidelines to generate actionable crowd routing and safety warnings.
        
        {STADIUM_SAFETY_GUIDELINES}
        
        Analyze inputs causally: e.g., high heat index values (>105°F) cause crowd clustering under shaded concourses (e.g., Zone A/B entrances), creating physical bottleneck risks.
        For zones exceeding risk index thresholds (Risk >= 0.85), prioritize crowd diversion recommendations, step-free evacuation routing, and hydration distribution.
        
        You must return a raw JSON array of objects representing "Recommendation Cards". DO NOT wrap in markdown formatting (like ```json), write ONLY the raw JSON text.
        Each Recommendation Card must adhere strictly to this schema:
        {{
          "zone_id": "string (one of: ZONE_A, ZONE_B, ZONE_C, ZONE_D, ZONE_E, ZONE_F)",
          "severity": "CRITICAL" | "WARNING" | "INFO",
          "confidence": float (0.0 to 1.0),
          "causal_analysis": "string explaining how density, heat index, and incidents interact",
          "action_items": ["string - clear operational tasks"],
          "multilingual_alerts": {{
            "en": "string",
            "es": "string",
            "fr": "string"
          }}
        }}
        """

        prompt = f"""
        Current Telemetry States:
        {json.dumps(zones, indent=2)}

        Current Open Incidents:
        {json.dumps(incidents, indent=2)}

        Current Weather Summary:
        {weather_summary or "Clear weather, ambient 80F"}
        """

        if self.client_active:
            try:
                # Use structured JSON schema option if supported
                generation_config = {
                    "response_mime_type": "application/json"
                }
                
                response: GenerateContentResponse = self.model.generate_content(
                    contents=[
                        {"role": "user", "parts": [system_instruction + "\n\nInput Telemetry:\n" + prompt]}
                    ],
                    generation_config=generation_config
                )
                
                cleaned_text = response.text.strip()
                # Strip markdown fence blocks if the model returned them anyway
                if cleaned_text.startswith("```"):
                    lines = cleaned_text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines[-1].startswith("```"):
                        lines = lines[:-1]
                    cleaned_text = "\n".join(lines).strip()
                
                cards = json.loads(cleaned_text)
                if isinstance(cards, dict) and "recommendations" in cards:
                    cards = cards["recommendations"]
                
                if isinstance(cards, list):
                    logger.info("Successfully generated recommendations from Gemini API.", card_count=len(cards))
                    return cards
                else:
                    logger.warning("Gemini did not return an array. Falling back to synthetic generator.")
            except Exception as e:
                logger.error("Gemini API generation failed. Activating deterministic fallback.", error=str(e))
                
        # Return highly-accurate rule-based synthetic cards as fallback
        return self._generate_synthetic_recommendations(zones, incidents, weather_summary)

    def _generate_synthetic_recommendations(self, zones: List[Dict[str, Any]], incidents: List[Dict[str, Any]], weather_summary: Optional[str]) -> List[Dict[str, Any]]:
        """
        Generates mathematically logical recommendation cards deterministically to handle
        stadium scenarios when AI API is unavailable.
        """
        logger.info("Generating synthetic recommendation cards.")
        cards = []
        
        # Check active incidents
        p1_incidents = [inc for inc in incidents if inc.get('priority') == 'P1' and inc.get('status') != 'RESOLVED']
        
        for zone in zones:
            zone_id = zone['zone_id']
            risk = zone.get('risk_index', 0.0)
            density = zone.get('density_pct', 0.0)
            heat_index = zone.get('heat_index', 70.0)
            
            # Find if there is an open incident in this zone
            zone_incidents = [inc for inc in incidents if inc.get('zone_id') == zone_id and inc.get('status') != 'RESOLVED']
            
            # Scenario A & Rule Override: Risk >= 0.85
            if risk >= 0.85 or zone.get('status') == 'CRITICAL':
                action_items = [
                    f"Initiate crowd diversion from {zone_id} immediately to adjacent lower-occupancy zones.",
                    f"Open secondary step-free gates and direct mobility-impaired guests using: {', '.join(zone.get('step_free_routes', []))}.",
                ]
                if heat_index >= 105.0:
                    action_items.append("Deploy mobile water misting plazas and distribute emergency hydration pouches.")
                
                cards.append({
                    "zone_id": zone_id,
                    "severity": "CRITICAL",
                    "confidence": 0.98,
                    "causal_analysis": f"Critical crowd load (Density {density:.1f}%) and environmental heat stress (HI {heat_index:.1f}°F) has exceeded safe operating limits. Flow channels are blocked, necessitating immediate routing intervention.",
                    "action_items": action_items,
                    "multilingual_alerts": {
                        "en": f"CRITICAL ALERT: {zone_id} is congested. For safety, proceed to lower density concourses. Step-free routing is available.",
                        "es": f"ALERTA CRÍTICA: {zone_id} congestionado. Por seguridad, diríjase a pasillos con menor densidad. Rutas accesibles disponibles.",
                        "fr": f"ALERTE CRITIQUE: La {zone_id} est encombrée. Pour votre sécurité, veuillez vous diriger vers des halls moins denses."
                    }
                })
            
            # Scenario B: Medical Emergency in Zone
            elif any(inc.get('priority') == 'P1' for inc in zone_incidents):
                p1_inc = next(inc for inc in zone_incidents if inc.get('priority') == 'P1')
                cards.append({
                    "zone_id": zone_id,
                    "severity": "CRITICAL",
                    "confidence": 0.95,
                    "causal_analysis": f"Priority 1 Medical Incident ({p1_inc.get('title')}) reported in {zone_id}. High zone occupancy ({density:.1f}%) creates access bottlenecks for emergency medical responders.",
                    "action_items": [
                        "Dispatch emergency responders immediately via designated step-free routes.",
                        "Direct local stewards to clear section entry aisles and maintain route clearance.",
                        "Provide physical assistance to companion of the patient using step-free exits."
                    ],
                    "multilingual_alerts": {
                        "en": f"MEDICAL EMERGENCY in {zone_id}. Clear access routes immediately for responding medical teams.",
                        "es": f"EMERGENCIA MÉDICA en {zone_id}. Despeje las rutas de acceso de inmediato para el equipo médico.",
                        "fr": f"URGENCE MÉDICALE dans la {zone_id}. Dégagez immédiatement les voies d'accès pour les secours."
                    }
                })
                
            # Warning Zone: Risk >= 0.4
            elif risk >= 0.4:
                cards.append({
                    "zone_id": zone_id,
                    "severity": "WARNING",
                    "confidence": 0.85,
                    "causal_analysis": f"Elevated occupant levels (Density {density:.1f}%) combined with heat factors. Early bottleneck tendencies detected in transition gateways.",
                    "action_items": [
                        "Deploy auxiliary team to monitor exit queue lengths.",
                        "Update digital wayfinding displays to highlight alternative exit directions."
                    ],
                    "multilingual_alerts": {
                        "en": f"WARNING: Increased crowd density in {zone_id}. Please follow directional signs.",
                        "es": f"ADVERTENCIA: Mayor densidad de personas en {zone_id}. Siga las señales de dirección.",
                        "fr": f"AVERTISSEMENT: Densité de foule accrue dans la {zone_id}. Veuillez suivre la signalisation."
                    }
                })
                
            # Safe Zone
            else:
                cards.append({
                    "zone_id": zone_id,
                    "severity": "INFO",
                    "confidence": 0.90,
                    "causal_analysis": f"Zone operating within standard safety boundaries (Density {density:.1f}%). All exit and emergency vectors are clear.",
                    "action_items": [
                        "Continue routine surveillance and metric collection."
                    ],
                    "multilingual_alerts": {
                        "en": f"INFO: {zone_id} is operating normally. Thank you for your cooperation.",
                        "es": f"INFO: {zone_id} funcionando normalmente. Gracias por su cooperación.",
                        "fr": f"INFO: La {zone_id} fonctionne normalement. Merci pour votre coopération."
                    }
                })
                
        return cards
