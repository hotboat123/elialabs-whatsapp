"""
AI Handler using OpenAI SDK with Groq backend (OpenAI-compatible API)
Supports MCP (Model Context Protocol) servers
"""
import logging
import json
from typing import List, Dict, Optional, Any
from openai import OpenAI

from app.config import get_settings

try:
    from app.bot.mcp_handler import MCPHandler
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP handler not available - running without MCP support")

logger = logging.getLogger(__name__)
settings = get_settings()


class AIHandler:
    """Handle AI responses using OpenAI SDK with Groq backend and MCP support"""
    
    def __init__(self):
        # Use OpenAI SDK but point to Groq's OpenAI-compatible API
        self.client = OpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1"  # Groq's OpenAI-compatible endpoint
        )
        self.model = "llama-3.1-70b-versatile"  # Groq model name
        
        if MCP_AVAILABLE:
            self.mcp_handler = MCPHandler()
            self._initialize_mcp_servers()
        else:
            self.mcp_handler = None
        
        # System prompt for the bot
        self.system_prompt = f"""Eres un asistente virtual de {settings.business_name}, una tienda en línea de e-commerce.

INFORMACIÓN DEL NEGOCIO:
- Nombre: {settings.business_name}
- Teléfono: {settings.business_phone}
- Email: {settings.business_email}
- Sitio web: {settings.business_website}

ROL:
Eres {settings.bot_name}, un asistente virtual amigable y profesional que ayuda a los clientes con sus consultas sobre productos, pedidos, envíos y servicio al cliente.

FUNCIONES:
1. Responder preguntas sobre productos y servicios  
2. Ayudar con consultas de pedidos  
3. Brindar información sobre envíos y devoluciones  
4. Resolver dudas sobre políticas de la tienda  
5. Ofrecer soporte al cliente de manera amigable y profesional  

PERSONALIDAD:
- Amigable y profesional
- Respuestas claras y concisas (máximo 2-3 párrafos)
- Usa emojis moderadamente para hacer la conversación más amigable
- Siempre mantén un tono cortés y profesional
- Si no sabes algo, admítelo y ofrece contactar con el equipo de soporte

IMPORTANTE:
- Si preguntan por información específica que no tengas, indícales que pueden revisar el sitio web o que contactaremos con ellos pronto.
- Mantén siempre un tono profesional y amigable.
- Responde en español de manera natural y clara.

Responde en español de manera natural y amigable."""
    
    def _initialize_mcp_servers(self):
        """
        Initialize MCP servers from configuration
        Can be extended to load from environment variables or config file
        """
        # Example: Add MCP servers here
        # self.mcp_handler.add_mcp_server("example", {
        #     "url": "https://mcp-server.example.com",
        #     "api_key": None,
        #     "tools": [
        #         {
        #             "name": "get_weather",
        #             "description": "Get current weather",
        #             "parameters": {
        #                 "type": "object",
        #                 "properties": {
        #                     "location": {"type": "string", "description": "City name"}
        #                 }
        #             }
        #         }
        #     ]
        # })
        pass
    
    async def generate_response(
        self,
        message_text: str,
        conversation_history: List[Dict],
        contact_name: str
    ) -> str:
        """
        Generate AI response using Groq via OpenAI SDK
        
        Args:
            message_text: Current message
            conversation_history: Previous messages
            contact_name: User's name
        
        Returns:
            AI-generated response
        """
        try:
            # Build messages for AI (last 10 messages for context)
            messages = []
            recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            
            for msg in recent_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Get available tools from MCP servers if enabled
            tools = None
            if self.mcp_handler and self.mcp_handler.enabled:
                available_tools = self.mcp_handler.get_available_tools()
                if available_tools:
                    tools = available_tools
                    logger.info(f"Using {len(tools)} MCP tools for this request")
            
            # Call Groq API (supports OpenAI-compatible function calling)
            api_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    *messages
                ],
                "max_tokens": 500,
                "temperature": 0.7
            }
            
            # Add tools if MCP is enabled and tools are available
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = "auto"  # Let model decide when to use tools
            
            response = self.client.chat.completions.create(**api_params)
            
            # Extract response text
            message = response.choices[0].message
            
            # Check if model wants to call a tool (MCP function calling)
            if message.tool_calls:
                logger.info(f"Model requested {len(message.tool_calls)} tool calls")
                
                # Process tool calls
                tool_responses = []
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    # Safely parse tool arguments (JSON)
                    try:
                        tool_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in tool arguments: {tool_call.function.arguments}")
                        tool_args = {}
                    
                    # Call MCP tool
                    tool_result = await self.mcp_handler.call_mcp_tool(tool_name, tool_args)
                    
                    tool_responses.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": tool_name,
                        "content": str(tool_result) if tool_result else "Tool execution failed"
                    })
                
                # Make second API call with tool results
                messages_with_tools = [
                    {"role": "system", "content": self.system_prompt},
                    *messages,
                    {"role": "assistant", "content": message.content, "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in message.tool_calls
                    ]},
                    *tool_responses
                ]
                
                # Get final response with tool results
                final_response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages_with_tools,
                    max_tokens=500,
                    temperature=0.7
                )
                
                response_text = final_response.choices[0].message.content
            else:
                # Normal response without tool calls
                response_text = message.content
            
            logger.info(f"AI response generated: {response_text[:100]}...")
            
            return response_text
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback response
            return f"""👋 ¡Hola! Soy {settings.bot_name} de {settings.business_name}

Disculpa, tuve un problema técnico. ¿Podrías intentar de nuevo?

Si el problema persiste, puedes contactarnos directamente:
📧 {settings.business_email}
🌐 {settings.business_website}

¿En qué puedo ayudarte?"""



