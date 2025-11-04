"""
FAQ Handler - predefined responses for common questions
"""
import logging
from typing import Optional
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FAQHandler:
    """Handle frequently asked questions with predefined answers"""
    
    def __init__(self):
        # Get business info from settings
        business_name = settings.business_name
        business_phone = settings.business_phone
        business_email = settings.business_email
        business_website = settings.business_website
        
        self.faqs = {
            # Información general
            "info": f"""ℹ️ **Información sobre {business_name}:**

🏢 Somos una tienda en línea especializada en productos de calidad

📍 Visita nuestro sitio web: {business_website}
📧 Email: {business_email}
📱 WhatsApp: {business_phone}

¿En qué más puedo ayudarte?""",
            
            "información": "info",  # Alias
            "quienes son": "info",  # Alias
            "quienes somos": "info",  # Alias
            "sobre": "info",  # Alias
            
            # Precios
            "precio": f"""💰 **Información de Precios:**

💵 Nuestros precios están disponibles en nuestro sitio web
🌐 Visita: {business_website}

📦 Los precios varían según el producto
✨ Ofrecemos descuentos especiales y ofertas periódicas

¿Hay algún producto específico del que quieras saber el precio?""",
            
            "precios": "precio",  # Alias
            "valor": "precio",  # Alias
            "valores": "precio",  # Alias
            "cuanto cuesta": "precio",  # Alias
            "cuánto cuesta": "precio",  # Alias
            
            # Envíos
            "envío": f"""🚚 **Política de Envíos:**

📦 Realizamos envíos a todo el país
⏱️ Tiempo de entrega: 3-5 días hábiles (varía según ubicación)
💰 Costos de envío: Se calculan al momento de la compra
📍 Envíos gratuitos: Consulta en nuestro sitio web las condiciones

Para más detalles, visita: {business_website}

¿Necesitas información sobre un envío específico?""",
            
            "envíos": "envío",  # Alias
            "envio": "envío",  # Alias
            "envios": "envío",  # Alias
            "entrega": "envío",  # Alias
            "cuanto tarda": "envío",  # Alias
            "tiempo de entrega": "envío",  # Alias
            "cuándo llega": "envío",  # Alias
            
            # Devoluciones
            "devolución": f"""🔄 **Política de Devoluciones:**

✅ Aceptamos devoluciones dentro de los primeros 14 días desde la compra
📦 El producto debe estar en su estado original (sin usar, con etiquetas)
💰 El reembolso se realiza al método de pago original
🚚 Los costos de envío de devolución corren por cuenta del cliente

Para más información, contacta a: {business_email}

¿Necesitas procesar una devolución?""",
            
            "devoluciones": "devolución",  # Alias
            "devolucion": "devolución",  # Alias
            "reembolso": "devolución",  # Alias
            "cancelar pedido": "devolución",  # Alias
            
            # Contacto
            "contacto": f"""📞 **Contáctanos:**

📱 WhatsApp: {business_phone}
📧 Email: {business_email}
🌐 Sitio web: {business_website}

⏰ Horarios de atención:
Lunes a Viernes: 9:00 - 18:00
Sábados: 10:00 - 14:00

¡Estamos aquí para ayudarte! 😊""",
            
            "contactanos": "contacto",  # Alias
            "hablar": "contacto",  # Alias
            "hablar con": "contacto",  # Alias
            
            # Pedidos
            "pedido": f"""📦 **Consulta de Pedidos:**

Para consultar el estado de tu pedido:
1. Revisa tu email de confirmación
2. Visita: {business_website}
3. O escríbenos a: {business_email} con tu número de pedido

📋 Necesitaremos:
• Número de pedido
• Email usado en la compra

¿Tienes tu número de pedido?""",
            
            "pedidos": "pedido",  # Alias
            "estado": "pedido",  # Alias
            "donde esta": "pedido",  # Alias
            "dónde está": "pedido",  # Alias
            "seguimiento": "pedido",  # Alias
            
            # Métodos de pago
            "pago": f"""💳 **Métodos de Pago:**

Aceptamos múltiples formas de pago:
💳 Tarjetas de crédito y débito
📱 Transferencias bancarias
💰 Efectivo (en puntos de recogida)
🌐 PayPal y otros métodos digitales

Todos los pagos son procesados de forma segura.

Visita {business_website} para ver todos los métodos disponibles.

¿Tienes alguna duda sobre el pago?""",
            
            "pagos": "pago",  # Alias
            "como pagar": "pago",  # Alias
            "métodos de pago": "pago",  # Alias
            "tarjeta": "pago",  # Alias
            
            # Garantía
            "garantía": f"""✅ **Garantía de Productos:**

🛡️ Todos nuestros productos tienen garantía de fábrica
⏰ Tiempo de garantía: Varía según el producto (consulta al momento de la compra)
📋 Para activar la garantía, conserva tu factura o comprobante de compra

Para más información: {business_email}

¿Necesitas hacer efectiva una garantía?""",
            
            "garantia": "garantía",  # Alias
            "defecto": "garantía",  # Alias
            "roto": "garantía",  # Alias
            
            # Catálogo/Productos
            "productos": f"""🛍️ **Nuestros Productos:**

📦 Tenemos una amplia variedad de productos disponibles
🌐 Visita nuestro catálogo completo en: {business_website}
🔍 Puedes buscar por categorías o usar el buscador

¿Hay algún tipo de producto específico que buscas?""",
            
            "producto": "productos",  # Alias
            "catálogo": "productos",  # Alias
            "catalogo": "productos",  # Alias
            "que venden": "productos",  # Alias
            "qué venden": "productos",  # Alias
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


