"""
FAQ Handler - predefined responses for business analytics questions
"""
import logging
from typing import Optional
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FAQHandler:
    """Handle frequently asked analytics questions with predefined answers"""
    
    def __init__(self):
        business_name = settings.business_name
        
        self.faqs = {
            # Ayuda general
            "ayuda": f"""📊 **¿Cómo puedo ayudarte?**

Puedo consultar reportes y métricas de {business_name}:

📈 **Ventas y Ingresos**
- "¿Cuánto vendimos este mes?"
- "Ventas del día"
- "Ingresos de la semana"

💰 **Marketing y Anuncios**
- "¿Cuánto gastamos en marketing?"
- "Resultados de los anuncios"
- "ROI de las campañas"

📦 **Productos**
- "Productos más vendidos"
- "Top productos del mes"

💵 **Financiero**
- "Gastos del mes"
- "Margen de ganancia"
- "Análisis financiero"

¿Qué te gustaría revisar?""",
            
            "help": "ayuda",  # Alias
            "comandos": "ayuda",  # Alias
            "que puedo preguntar": "ayuda",  # Alias
            
            # Ventas
            "ventas": """📈 **Consultar Ventas**

Puedo mostrarte:
• Ventas del mes actual
• Ventas por día/semana
• Comparación con meses anteriores
• Productos más vendidos

Pregúntame:
- "¿Cuánto vendimos este mes?"
- "Ventas de hoy"
- "Ventas de la semana"

Consultando la base de datos...""",
            
            "venta": "ventas",  # Alias
            "ingresos": "ventas",  # Alias
            "revenue": "ventas",  # Alias
            "facturación": "ventas",  # Alias
            "facturacion": "ventas",  # Alias
            
            # Marketing
            "marketing": """📱 **Reportes de Marketing**

Puedo mostrarte:
• Gastos en publicidad
• Resultados de campañas
• ROI de anuncios
• Conversiones por canal

Pregúntame:
- "¿Cuánto gastamos en marketing este mes?"
- "Resultados de los anuncios"
- "ROI de las campañas"

Consultando la base de datos...""",
            
            "publicidad": "marketing",  # Alias
            "anuncios": "marketing",  # Alias
            "anuncio": "marketing",  # Alias
            "ads": "marketing",  # Alias
            "campaña": "marketing",  # Alias
            "campana": "marketing",  # Alias
            
            # Productos
            "productos más vendidos": """📦 **Productos Más Vendidos**

Puedo mostrarte:
• Top productos del mes
• Productos con mejor desempeño
• Productos por categoría
• Análisis de ventas por producto

Pregúntame:
- "Productos más vendidos"
- "Top productos del mes"
- "Qué productos venden mejor"

Consultando la base de datos...""",
            
            "top productos": "productos más vendidos",  # Alias
            "best sellers": "productos más vendidos",  # Alias
            "productos vendidos": "productos más vendidos",  # Alias
            
            # Financiero
            "gastos": """💰 **Análisis de Gastos**

Puedo mostrarte:
• Gastos del mes
• Gastos por categoría
• Gastos de marketing
• Costos operativos
• Margen de ganancia

Pregúntame:
- "¿Cuánto gastamos este mes?"
- "Gastos de marketing"
- "Análisis financiero"

Consultando la base de datos...""",
            
            "gasto": "gastos",  # Alias
            "costos": "gastos",  # Alias
            "financiero": "gastos",  # Alias
            "margen": "gastos",  # Alias
            
            # Reportes generales
            "reporte": """📊 **Reportes Disponibles**

Puedo generar reportes de:
• Ventas e ingresos
• Marketing y publicidad
• Productos y stock
• Clientes y comportamiento
• Métricas financieras

Pregúntame:
- "Reporte del mes"
- "Métricas de hoy"
- "Análisis general"

Consultando la base de datos...""",
            
            "reportes": "reporte",  # Alias
            "métricas": "reporte",  # Alias
            "metricas": "reporte",  # Alias
            "análisis": "reporte",  # Alias
            "analisis": "reporte",  # Alias
            "dashboard": "reporte",  # Alias
        }
    
    def get_response(self, message: str) -> Optional[str]:
        """
        Get FAQ response if message matches a question
        
        Args:
            message: User's message
        
        Returns:
            FAQ response or None
        """
        message_lower = message.lower().strip()
        
        # Check for exact matches or keywords
        for keyword, response in self.faqs.items():
            if keyword in message_lower:
                # If response is an alias, get the actual response
                if isinstance(response, str) and response in self.faqs:
                    response = self.faqs[response]
                
                logger.info(f"FAQ match found for keyword: {keyword}")
                return response
        
        return None


