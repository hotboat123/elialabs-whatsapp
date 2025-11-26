"""Hardcoded responses for the WhatsApp demo script."""
from typing import Optional, Dict, Any


class DemoScriptHandler:
    """Provide scripted answers for specific demo prompts."""

    SALES_ALERT_PROMPT = "alerta si las ventas diarias bajan un 20% del promedio"
    ROAS_ALERT_PROMPT = "alerta si el roas es menor a 3"
    ROAS_WINDOW_PROMPTS = {
        "48 horas",
        "48h",
        "48 horas.",
        "48 hrs",
        "48hrs",
    }

    SALES_ALERT_RESPONSE = (
        "Perfecto! ✨ He configurado tu alerta de ventas:\n\n"
        "🔔 Alerta activada:\n"
        "- Condición: Ventas diarias < -20% del promedio\n"
        "- Frecuencia: Revisaré tus ventas cada hora\n"
        "- Notificación: Te enviaré un mensaje por WhatsApp\n\n"
        "Así optimizarás tus campañas a tiempo y maximizarás tu inversión en marketing 💰"
    )

    ROAS_ALERT_RESPONSE = (
        "Excelente elección 🚀 Puedo activar una alerta cuando alguna de tus campañas "
        "tenga ROAS menor a 3, pero necesito que definamos el período de análisis.\n\n"
        "Por ejemplo:\n"
        "“En las últimas 48 horas, tu anuncio Lápices Mágicos tuvo un ROAS de 2.5 "
        "(menor a 3).”\n\n"
        "🕒 ¿Para qué ventana de tiempo quieres medir el ROAS?\n\n"
        "Ejemplos: últimas 24 horas, 48 horas, 7 días…"
    )

    ROAS_WINDOW_RESPONSE = (
        "Perfecto ✅ Tu alerta de ROAS ya está configurada:\n\n"
        "📊 Alerta de ROAS configurada\n\n"
        "Ventana de tiempo: últimas 48 horas\n\n"
        "Condición: ROAS < 3x en cualquier campaña\n\n"
        "Frecuencia: monitoreo continuo\n\n"
        "Notificación: te avisaré por WhatsApp apenas detecte una campaña bajo ese umbral\n\n"
        "Listo, desde ahora te aviso antes de que tus campañas se vuelvan poco rentables 😉"
    )

    def get_response(self, message_text: str, conversation: Dict[str, Any]) -> Optional[str]:
        """
        Return a scripted response when the incoming message matches the demo prompts.
        """
        if not message_text:
            return None

        metadata = conversation.setdefault("metadata", {})
        script_state = metadata.setdefault("demo_script", {})
        awaiting_window = script_state.get("awaiting_roas_window", False)

        normalized = self._normalize(message_text)

        if awaiting_window:
            if normalized in self.ROAS_WINDOW_PROMPTS:
                script_state["awaiting_roas_window"] = False
                return self.ROAS_WINDOW_RESPONSE
            return None

        if normalized == self.SALES_ALERT_PROMPT:
            return self.SALES_ALERT_RESPONSE

        if normalized == self.ROAS_ALERT_PROMPT:
            script_state["awaiting_roas_window"] = True
            return self.ROAS_ALERT_RESPONSE

        return None

    @staticmethod
    def _normalize(text: str) -> str:
        """Normalize text for comparison."""
        return " ".join(text.lower().strip().split())


