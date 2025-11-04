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

**Opciones principales:**
1️⃣ 📈 Ventas e ingresos
2️⃣ 💰 Marketing y anuncios
3️⃣ 📦 Productos más vendidos
4️⃣ 💵 Análisis financiero
5️⃣ 📊 Reportes generales

**Ejemplos:**
- Escribe "1" o "ventas" para ver ventas
- Escribe "2" o "marketing" para ver marketing
- O pregunta directamente

¿Qué te gustaría revisar?""",
            
            "help": "ayuda",  # Alias
            "comandos": "ayuda",  # Alias
            "que puedo preguntar": "ayuda",  # Alias
            "menu": "ayuda",  # Alias
            
            # Ventas - con números
            "ventas": """📈 **Consultar Ventas**

**Opciones disponibles:**
1️⃣ Ventas del mes actual
2️⃣ Ventas de la semana
3️⃣ Ventas de hoy
4️⃣ Comparación con meses anteriores
5️⃣ Productos más vendidos

Escribe el número (1, 2, 3...) o pregunta directamente.

Consultando la base de datos...""",
            
            "venta": "ventas",  # Alias
            "ingresos": "ventas",  # Alias
            "revenue": "ventas",  # Alias
            "facturación": "ventas",  # Alias
            "facturacion": "ventas",  # Alias
            "1": "ventas",  # Número como comando
            "uno": "ventas",  # Alias
            
            # Marketing - con números
            "marketing": """📱 **Reportes de Marketing**

**Opciones disponibles:**
1️⃣ Gastos en publicidad del mes
2️⃣ Resultados de campañas
3️⃣ ROI de anuncios
4️⃣ Conversiones por canal
5️⃣ Análisis de marketing

Escribe el número (1, 2, 3...) o pregunta directamente.

Consultando la base de datos...""",
            
            "publicidad": "marketing",  # Alias
            "anuncios": "marketing",  # Alias
            "anuncio": "marketing",  # Alias
            "ads": "marketing",  # Alias
            "campaña": "marketing",  # Alias
            "campana": "marketing",  # Alias
            "2": "marketing",  # Número como comando
            "dos": "marketing",  # Alias
            
            # Productos - con números
            "productos más vendidos": """📦 **Productos Más Vendidos**

**Opciones disponibles:**
1️⃣ Top productos del mes
2️⃣ Productos con mejor desempeño
3️⃣ Productos por categoría
4️⃣ Análisis de ventas por producto

Escribe el número (1, 2, 3...) o pregunta directamente.

Consultando la base de datos...""",
            
            "top productos": "productos más vendidos",  # Alias
            "best sellers": "productos más vendidos",  # Alias
            "productos vendidos": "productos más vendidos",  # Alias
            "productos": "productos más vendidos",  # Alias
            "4": "productos más vendidos",  # Número como comando
            "cuatro": "productos más vendidos",  # Alias
            
            # Financiero - con números
            "gastos": """💰 **Análisis de Gastos**

**Opciones disponibles:**
1️⃣ Gastos del mes
2️⃣ Gastos por categoría
3️⃣ Gastos de marketing
4️⃣ Costos operativos
5️⃣ Margen de ganancia

Escribe el número (1, 2, 3...) o pregunta directamente.

Consultando la base de datos...""",
            
            "gasto": "gastos",  # Alias
            "costos": "gastos",  # Alias
            "financiero": "gastos",  # Alias
            "margen": "gastos",  # Alias
            "5": "gastos",  # Número como comando
            "cinco": "gastos",  # Alias
            
            # Reportes generales - con números
            "reporte": """📊 **Reportes Disponibles**

**Opciones disponibles:**
1️⃣ Reporte del mes
2️⃣ Métricas de hoy
3️⃣ Análisis general
4️⃣ Dashboard completo
5️⃣ Comparación de períodos

Escribe el número (1, 2, 3...) o pregunta directamente.

Consultando la base de datos...""",
            
            "reportes": "reporte",  # Alias
            "métricas": "reporte",  # Alias
            "metricas": "reporte",  # Alias
            "análisis": "reporte",  # Alias
            "analisis": "reporte",  # Alias
            "dashboard": "reporte",  # Alias
            "6": "reporte",  # Número como comando
            "seis": "reporte",  # Alias
        }
        
        # Mapeo de números a opciones específicas de ventas
        self.sales_options = {
            "1": "ventas del mes",
            "mes": "ventas del mes",
            "2": "ventas de la semana",
            "semana": "ventas de la semana",
            "3": "ventas de hoy",
            "hoy": "ventas de hoy",
            "dia": "ventas de hoy",
            "día": "ventas de hoy",
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
        
        # Check for numbered options in sales context
        if message_lower in self.sales_options:
            # This will be handled by the AI with context
            return None
        
        # Check for exact matches or keywords
        for keyword, response in self.faqs.items():
            if keyword in message_lower:
                # If response is an alias, get the actual response
                if isinstance(response, str) and response in self.faqs:
                    response = self.faqs[response]
                
                logger.info(f"FAQ match found for keyword: {keyword}")
                return response
        
        return None
