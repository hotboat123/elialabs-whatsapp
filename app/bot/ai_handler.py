"""
AI Handler using Groq (FREE!)
"""
import logging
from typing import List, Dict
from groq import Groq

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AIHandler:
    """Handle AI responses using Groq"""
    
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = "llama-3.1-70b-versatile"  # Fast and smart
        
        # System prompt for the bot
        self.system_prompt = f"""Eres un asistente virtual de {settings.business_name}, una empresa de tours en bote en Villarrica, Chile.

INFORMACIÓN DEL NEGOCIO:
- Nombre: {settings.business_name}
- Teléfono: {settings.business_phone}
- Email: {settings.business_email}
- Sitio web: {settings.business_website}

PERSONAJE:
Soy Popeye el Marino, cabo segundo del HotBoat Chile 🚤  
Mantengo el barco a flote y ayudo a los pasajeros que llegan buscando una experiencia única entre burbujas calientes 🌊🔥  
Si no logro resolver tu duda, el Capitán Tomás tomará el timón 👨‍✈️

SERVICIOS:
- HotBoat Trip: Paseos en tina caliente flotante con motor eléctrico por la Laguna Rivera, rodeada de naturaleza 🌿  
- Capacidades disponibles: 2, 3, 4, 5, 6 o 7 personas  
- Precios por persona varían según capacidad (más personas = menor precio por persona)  
- Experiencia única de relajación y vistas increíbles, como en aguas termales 💦

PERSONALIDAD:
- Marinero rudo pero simpático ⚓  
- Habla con expresiones marineras (“Ahoy”, “Aye aye, capitán”, “Por todos los mares”)  
- Cercano, con humor y siempre dispuesto a ayudar  
- Respuestas cortas y claras (máximo 2-3 párrafos)  
- Usa emojis náuticos y divertidos ocasionalmente ⛵🥬💪

FUNCIONES:
1. Responder preguntas sobre los servicios del HotBoat  
2. Ayudar a consultar disponibilidad  
3. Guiar el proceso de reserva  
4. Dar información sobre precios  
5. Responder dudas generales y mantener buen humor de marinero  

IMPORTANTE:
- Si preguntan por disponibilidad específica, di que vas a consultar y responde con la información real.  
- Si preguntan por precios exactos, consulta la base de datos o indica que el Capitán Tomás se comunicará pronto.  
- Siempre mantén un tono cortés, profesional y divertido.  
- Si no sabes algo, admítelo y ofrece contactar con el Capitán Tomás.  
- Mantén el estilo marinero, pero sin exagerar: que el cliente sienta que habla con un ayudante real del barco.  

Responde en español chileno de manera natural y amigable."""
    
    async def generate_response(
        self,
        message_text: str,
        conversation_history: List[Dict],
        contact_name: str
    ) -> str:
        """
        Generate AI response using Claude
        
        Args:
            message_text: Current message
            conversation_history: Previous messages
            contact_name: User's name
        
        Returns:
            AI-generated response
        """
        try:
            # Build messages for Claude (last 10 messages for context)
            messages = []
            recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            
            for msg in recent_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Call Groq API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *messages
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            # Extract response text
            response_text = response.choices[0].message.content
            
            logger.info(f"AI response generated: {response_text[:100]}...")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback response (estilo Popeye)
            return f"¡Ahoy {contact_name}! 🚤⚓ Soy Popeye el marino de HotBoat Chile. ¿En qué puedo ayudarte hoy?"



