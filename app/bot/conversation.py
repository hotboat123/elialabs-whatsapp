"""
Conversation manager - handles message flow and context
"""
import logging
from typing import Dict, Optional
from datetime import datetime

from app.bot.ai_handler import AIHandler
from app.bot.faq import FAQHandler
from app.bot import marketing_analysis
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
            metadata = conversation.setdefault("metadata", {})
            metadata.setdefault("awaiting_marketing_scope", False)
            message_lower = message_text.lower().strip()
            scope_choice = self._interpret_marketing_scope(message_text)
            
            # Always show welcome message on first interaction, regardless of greeting
            if is_first:
                logger.info("First message with greeting - sending welcome message")
                # Use custom welcome message if provided, otherwise use default
                if settings.welcome_message:
                    response = settings.welcome_message
                else:
                    response = f"""📊 ¡Hola! Soy {settings.bot_name}, tu asistente analítico 📈

Estoy aquí para ayudarte a analizar el rendimiento de {settings.business_name}:

**Opciones disponibles:**
1️⃣ 📈 Ventas del mes
2️⃣ 💰 Ingresos y gastos
3️⃣ 📱 Marketing y anuncios
4️⃣ 📦 Productos más vendidos
5️⃣ 👥 Análisis de clientes
6️⃣ 📊 Reporte general

Simplemente escribe el número (1, 2, 3...) o pregunta directamente.

¿Qué te gustaría revisar hoy?"""
            elif metadata.get("awaiting_marketing_scope") or scope_choice:
                if scope_choice:
                    metadata["awaiting_marketing_scope"] = False
                    response = await self.ai_handler.generate_marketing_performance_report(scope_choice)
                else:
                    response = self._marketing_scope_prompt(reminder=True)
            # Check if it's a number command (1-6)
            elif message_lower in ['1', '2', '3', '4', '5', '6', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis']:
                logger.info(f"Detected number command: {message_text}")
                # Map numbers to FAQ responses (matching welcome message order)
                number_map = {
                    '1': 'ventas', 'uno': 'ventas',
                    '2': 'gastos', 'dos': 'gastos',  # Ingresos y gastos
                    '3': 'marketing', 'tres': 'marketing',  # Marketing y anuncios
                    '4': 'productos más vendidos', 'cuatro': 'productos más vendidos',
                    '5': 'reporte', 'cinco': 'reporte',  # Análisis de clientes (usar reporte general)
                    '6': 'reporte', 'seis': 'reporte'  # Reporte general
                }
                mapped_command = number_map.get(message_lower)
                if mapped_command:
                    if mapped_command == 'marketing':
                        metadata["awaiting_marketing_scope"] = True
                        response = self._marketing_scope_prompt()
                    else:
                        # Always use AI to get actual data, not just FAQ menu
                        response = await self.ai_handler.generate_response(
                            message_text=mapped_command,
                            conversation_history=conversation["messages"],
                            contact_name=contact_name,
                            phone_number=from_number
                        )
                else:
                    response = await self.ai_handler.generate_response(
                        message_text=message_text,
                        conversation_history=conversation["messages"],
                        contact_name=contact_name,
                        phone_number=from_number
                    )
            # Check if it's a FAQ question (but only during the first turn)
            elif is_first and (faq_response := self.faq_handler.get_response(message_text)):
                logger.info("Responding with FAQ answer")
                # If FAQ response says "Consultando la base de datos...", use AI to actually get data
                if "Consultando la base de datos" in faq_response:
                    # Use AI to get actual data
                    response = await self.ai_handler.generate_response(
                        message_text=message_text,
                        conversation_history=conversation["messages"],
                        contact_name=contact_name,
                        phone_number=from_number
                    )
                else:
                    response = faq_response
            
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
            return """⚠️ **Error procesando tu mensaje**

Disculpa, tuve un problema técnico.

**Intenta:**
1. Escribir un número (1, 2, 3...) en lugar de texto
2. Reformular tu pregunta de forma más simple
3. Esperar unos segundos y volver a intentar

¿Puedes intentar de nuevo?"""
    
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
                    "lead_id": lead.get("id") if lead else None,
                    "awaiting_marketing_scope": False
                }
            }
            
            if history:
                logger.info(f"Loaded {len(history)} messages from history for {phone_number}")
        
        # Update name if different
        if contact_name and self.conversations[phone_number]["name"] != contact_name:
            self.conversations[phone_number]["name"] = contact_name
        metadata = self.conversations[phone_number].setdefault("metadata", {})
        metadata.setdefault("awaiting_marketing_scope", False)
        
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

    def _marketing_scope_prompt(self, reminder: bool = False) -> str:
        if reminder:
            header = "No identifiqué la opción. Elige qué nivel de marketing quieres revisar:"
        else:
            header = "Para afinar el análisis de marketing, dime qué nivel quieres revisar:"

        return (
            f"🎯 {header}\n"
            "- Campañas\n"
            "- Conjuntos de anuncios\n"
            "- Anuncios\n\n"
            "Responde con la opción que prefieras."
        )

    def _interpret_marketing_scope(self, message: str) -> Optional[str]:
        if not message:
            return None

        cleaned = message.lower().strip()
        numeric_map = {
            '1': 'campaigns',
            'uno': 'campaigns',
            '2': 'adsets',
            'dos': 'adsets',
            '3': 'ads',
            'tres': 'ads',
        }
        if cleaned in numeric_map:
            return numeric_map[cleaned]

        return marketing_analysis.normalize_scope(message)

