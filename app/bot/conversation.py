"""
Conversation manager - handles message flow and context
"""
import logging
from typing import Dict, Optional
from datetime import datetime

from app.bot.ai_handler import AIHandler
from app.bot.faq import FAQHandler
from app.db.leads import get_or_create_lead, get_conversation_history
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ConversationManager:
    """Manages conversations with users"""
    
    def __init__(self):
        self.ai_handler = AIHandler()
        self.faq_handler = FAQHandler()
        # In-memory conversation storage (use Redis or DB in production)
        self.conversations: Dict[str, dict] = {}
    
    async def process_message(
        self,
        from_number: str,
        message_text: str,
        contact_name: str,
        message_id: str
    ) -> Optional[str]:
        """
        Process incoming message and generate response
        
        Args:
            from_number: Sender's phone number
            message_text: Message text
            contact_name: Sender's name
            message_id: WhatsApp message ID
        
        Returns:
            Response text or None
        """
        try:
            # Get or create conversation context (loads history from DB)
            conversation = await self.get_conversation(from_number, contact_name)
            
            logger.info(f"Processing message from {contact_name}: {message_text}")
            
            # Check if it's the first message - send welcome message
            # Check BEFORE adding the message to history
            is_first = self._is_first_message(conversation)
            is_greeting = self._is_greeting_message(message_text)
            
            # Add message to history
            conversation["messages"].append({
                "role": "user",
                "content": message_text,
                "timestamp": datetime.now().isoformat(),
                "message_id": message_id
            })
            
            # Always show welcome message on first interaction, regardless of greeting
            if is_first:
                logger.info("First message with greeting - sending welcome message")
                # Use custom welcome message if provided, otherwise use default
                if settings.welcome_message:
                    response = settings.welcome_message
                else:
                    response = f"""📊 ¡Hola! Soy {settings.bot_name}, tu asistente analítico 📈

Estoy aquí para ayudarte a analizar el rendimiento de {settings.business_name}:

• 📈 Reportes de ventas del mes
• 💰 Análisis de ingresos y gastos
• 📱 Resultados de marketing y anuncios
• 📦 Productos más vendidos
• 👥 Análisis de clientes
• 📊 Cualquier métrica del negocio

¿Qué te gustaría revisar hoy?"""
            # Check if it's a FAQ question
            elif self.faq_handler.get_response(message_text):
                logger.info("Responding with FAQ answer")
                response = self.faq_handler.get_response(message_text)
            
            # Use AI for general conversation
            else:
                logger.info("Using AI handler for response")
                response = await self.ai_handler.generate_response(
                    message_text=message_text,
                    conversation_history=conversation["messages"],
                    contact_name=contact_name,
                    phone_number=from_number
                )
            
            # Add response to history
            conversation["messages"].append({
                "role": "assistant",
                "content": response,
                "timestamp": datetime.now().isoformat()
            })
            
            # Update last interaction
            conversation["last_interaction"] = datetime.now().isoformat()
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            import traceback
            traceback.print_exc()
            return "Disculpa, tuve un problema procesando tu mensaje. ¿Podrías intentar de nuevo?"
    
    async def get_conversation(self, phone_number: str, contact_name: str) -> dict:
        """
        Get or create conversation context, loading history from database if available
        """
        # Check if already in memory
        if phone_number not in self.conversations:
            # Load lead info and conversation history from database
            lead = await get_or_create_lead(phone_number, contact_name)
            history = await get_conversation_history(phone_number, limit=50)
            
            self.conversations[phone_number] = {
                "phone": phone_number,
                "name": contact_name,
                "messages": history if history else [],
                "created_at": datetime.now().isoformat(),
                "last_interaction": datetime.now().isoformat(),
                "metadata": {
                    "lead_status": lead.get("lead_status") if lead else "unknown",
                    "lead_id": lead.get("id") if lead else None
                }
            }
            
            if history:
                logger.info(f"Loaded {len(history)} messages from history for {phone_number}")
        
        # Update name if different
        if contact_name and self.conversations[phone_number]["name"] != contact_name:
            self.conversations[phone_number]["name"] = contact_name
        
        return self.conversations[phone_number]
    
    def _is_greeting_message(self, message: str) -> bool:
        """
        Check if message is a greeting or first contact
        
        Args:
            message: User message
        
        Returns:
            True if message is a greeting
        """
        message_lower = message.lower().strip()
        greetings = [
            "hola", "hi", "hey", "hello", "buenos días", "buenas tardes", 
            "buenas noches", "buen día", "saludos", "qué tal", "que tal",
            "ahoy", "buen día", "día", "hey", "hi", "buenas"
        ]
        
        # Check if message is just a greeting
        if message_lower in greetings:
            return True
        
        # Check if message starts with a greeting
        for greeting in greetings:
            if message_lower.startswith(greeting):
                return True
        
        return False
    
    def _is_first_message(self, conversation: dict) -> bool:
        """
        Check if this is the first message in the conversation.
        We check BEFORE adding the new message, so we look for empty history.
        """
        messages = conversation.get("messages", [])
        
        # If no messages in history, it's definitely the first
        if len(messages) == 0:
            return True
        
        # Count only user messages (not bot responses)
        user_messages = [msg for msg in messages if msg.get("role") == "user"]
        
        # If no user messages yet (only bot responses or empty), it's the first user message
        return len(user_messages) == 0



