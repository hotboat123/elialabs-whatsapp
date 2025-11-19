"""
AI Handler using OpenAI SDK with Groq backend (OpenAI-compatible API)
Supports MCP (Model Context Protocol) servers and database queries
"""
import logging
import json
from typing import List, Dict, Optional, Any
from openai import OpenAI

from app.config import get_settings
from app.db import business_data
from app.bot import marketing_analysis
from app.bot.context_builder import build_business_context

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
        # Validate API key is configured
        if not settings.groq_api_key or not settings.groq_api_key.strip():
            logger.error("GROQ_API_KEY is not configured! Please set it as an environment variable.")
            raise ValueError("GROQ_API_KEY is required but not set in environment variables")
        
        # Use OpenAI SDK but point to Groq's OpenAI-compatible API
        try:
            self.client = OpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1"  # Groq's OpenAI-compatible endpoint
            )
            logger.info("Groq client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {e}")
            raise
        
        # Updated to latest Groq model (llama-3.1-70b-versatile was decommissioned)
        self.model = "llama-3.3-70b-versatile"  # Groq model name
        self.primary_mcp_tool_name = settings.openai_mcp_tool_name
        
        if MCP_AVAILABLE:
            self.mcp_handler = MCPHandler()
            self._initialize_mcp_servers()
        else:
            self.mcp_handler = None
        
        # System prompt for the bot
        self.system_prompt = f"""Eres un asistente analítico para el dueño de {settings.business_name}, una tienda en línea de e-commerce.

INFORMACIÓN DEL NEGOCIO:
- Nombre: {settings.business_name}
- Email: {settings.business_email}
- Sitio web: {settings.business_website}

ROL:
Eres {settings.bot_name}, un asistente analítico y de reportes que ayuda al dueño de la tienda a entender el rendimiento del negocio, tomar decisiones informadas y analizar métricas clave.

FUNCIONES PRINCIPALES:
1. **Reportes de Ventas**: Consultar ventas del mes, día, semana, productos más vendidos, etc.
2. **Análisis de Marketing**: Gastos de marketing, ROI de campañas, resultados de anuncios, conversiones
3. **Métricas Financieras**: Ingresos, gastos, margen de ganancia, proyecciones
4. **Análisis de Productos**: Productos más vendidos, stock bajo, productos sin movimiento
5. **Análisis de Clientes**: Clientes nuevos, clientes recurrentes, segmentación
6. **Reportes Personalizados**: Cualquier consulta específica sobre el negocio

ACCESO A BASE DE DATOS:
Tienes acceso completo a la base de datos del negocio para generar reportes y análisis:
- Vistas de ventas y pedidos
- Vistas de marketing y gastos publicitarios
- Vistas de productos e inventario
- Vistas de clientes y comportamiento
- Vistas de métricas financieras
- Cualquier otra vista de analytics configurada

CUANDO PREGUNTEN POR REPORTES O MÉTRICAS:
- SIEMPRE consulta la base de datos primero
- Presenta los datos de forma clara y estructurada
- Calcula porcentajes, tendencias y comparaciones cuando sea relevante
- Usa formato de números legible (ej: $1,234.56 en lugar de 1234.56)
- Si no hay datos disponibles, indícalo claramente

FORMATO DE RESPUESTAS:
- Usa emojis para hacer los reportes más visuales (📊 📈 📉 💰 📦)
- Presenta datos en formato de lista o tabla cuando sea apropiado
- Incluye comparaciones (vs mes anterior, vs promedio, etc.)
- Resalta insights importantes o tendencias notables

PERSONALIDAD:
- Profesional y enfocado en datos
- Directo y claro en las respuestas
- Responde en español de manera natural
- Sé conciso pero completo en los reportes

IMPORTANTE:
- Siempre consulta la base de datos cuando pregunten por métricas, reportes o análisis
- Presenta los datos de forma clara y accionable
- Si no hay datos, indícalo claramente
- Responde en español de manera natural

Responde en español de manera natural y profesional."""
    
    def _initialize_mcp_servers(self):
        """
        Initialize MCP servers from configuration
        Can be extended to load from environment variables or config file
        """
        if not settings.openai_mcp_url:
            logger.info("No MCP servers configured in settings.")
            return
        
        tool_name = settings.openai_mcp_tool_name or "openai_chat"
        logger.info("Registering OpenAI MCP server with tool '%s'", tool_name)
        
        self.mcp_handler.add_mcp_server(
            "openai",
            {
                "url": settings.openai_mcp_url,
                "api_key": settings.openai_mcp_api_key,
                "tools": [
                    {
                        "name": tool_name,
                        "description": "Genera respuestas usando el servidor MCP con OpenAI.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "conversation": {
                                    "type": "array",
                                    "description": "Historial de mensajes sin el prompt del sistema.",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "role": {"type": "string"},
                                            "content": {"type": "string"},
                                        },
                                        "required": ["role", "content"],
                                    },
                                },
                                "system_prompt": {
                                    "type": "string",
                                    "description": "Prompt del sistema completo.",
                                },
                                "business_context": {
                                    "type": "string",
                                    "description": "Contexto opcional proveniente de la base de datos.",
                                },
                                "message_text": {
                                    "type": "string",
                                    "description": "Último mensaje del usuario para inferir el contexto requerido.",
                                },
                                "phone_number": {
                                    "type": "string",
                                    "description": "Teléfono del contacto para consultas personalizadas.",
                                },
                                "metadata": {
                                    "type": "object",
                                    "description": "Información adicional (contacto, teléfono, etc.).",
                                },
                                "temperature": {
                                    "type": "number",
                                    "description": "Temperatura opcional para la respuesta.",
                                },
                                "max_tokens": {
                                    "type": "integer",
                                    "description": "Máximo de tokens para la respuesta.",
                                },
                            },
                            "required": ["conversation", "system_prompt"],
                        },
                    }
                ],
            },
        )
    
    async def generate_response(
        self,
        message_text: str,
        conversation_history: List[Dict],
        contact_name: str,
        phone_number: Optional[str] = None
    ) -> str:
        """
        Generate AI response using Groq via OpenAI SDK with database access
        
        Args:
            message_text: Current message
            conversation_history: Previous messages
            contact_name: User's name
            phone_number: User's phone number (for querying orders)
        
        Returns:
            AI-generated response
        """
        try:
            context_data = None
            
            # Build messages for AI (last 10 messages for context)
            recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            conversation_messages = [
                {
                    "role": msg["role"],
                    "content": msg["content"]
                }
                for msg in recent_history
            ]
            
            # Try to delegate the whole response to the primary MCP server (OpenAI)
            primary_mcp_response = await self._try_primary_mcp_response(
                conversation_messages=conversation_messages,
                context_data=None,  # Let MCP server build its own DB context
                message_text=message_text,
                contact_name=contact_name,
                phone_number=phone_number
            )
            if primary_mcp_response:
                return primary_mcp_response
            
            messages = list(conversation_messages)
            
            # Build business context only for Groq fallback
            try:
                context_data = await build_business_context(message_text, phone_number)
            except Exception as db_error:
                logger.warning(f"Could not get business context (non-critical): {db_error}")
                context_data = None
            
            # Add business context if available (for Groq fallback)
            if context_data:
                context_message = f"\n\n[INFORMACIÓN DE LA BASE DE DATOS]\n{context_data}\n"
                messages.append({
                    "role": "system",
                    "content": context_message
                })
            else:
                # Add a note if we tried to get context but couldn't (for debugging)
                logger.debug("No business context available, proceeding with AI-only response")
            
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
            
            logger.info(f"Calling Groq API with model: {self.model}, messages: {len(api_params['messages'])}")
            
            try:
                response = self.client.chat.completions.create(**api_params)
            except Exception as api_error:
                logger.error(f"Groq API call failed: {type(api_error).__name__}: {api_error}")
                # Check for specific error types
                error_str = str(api_error).lower()
                if "api key" in error_str or "authentication" in error_str or "401" in error_str:
                    raise ValueError(f"Invalid Groq API key. Please check GROQ_API_KEY environment variable.")
                elif "rate limit" in error_str or "429" in error_str:
                    raise ValueError(f"Rate limit exceeded. Please try again in a moment.")
                elif "model" in error_str or "404" in error_str:
                    raise ValueError(f"Model '{self.model}' not found. Please check model name.")
                else:
                    raise  # Re-raise original error
            
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
            logger.error(f"Error generating AI response: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            
            error_str = str(e).lower()
            
            # Check for specific error types and provide helpful messages
            if "api key" in error_str or "authentication" in error_str or "invalid groq api key" in error_str:
                logger.error("GROQ_API_KEY is missing or invalid!")
                return f"""⚠️ **Error de configuración**

No se pudo conectar con el servicio de IA.

**Problema:** La clave de API de Groq no está configurada o es inválida.

**Solución:** Contacta al administrador para verificar la configuración de GROQ_API_KEY.

Mientras tanto, puedes intentar otra pregunta más tarde."""
            
            elif "rate limit" in error_str or "429" in error_str:
                return f"""⚠️ **Límite de solicitudes alcanzado**

He alcanzado el límite de solicitudes al servicio de IA.

**Solución:** Espera unos segundos e intenta nuevamente.

Si el problema persiste, contacta: 📧 {settings.business_email}"""
            
            elif "model" in error_str or "404" in error_str or "not found" in error_str:
                logger.error(f"Model '{self.model}' not available!")
                return f"""⚠️ **Error de configuración**

El modelo de IA no está disponible.

**Solución:** Contacta al administrador para verificar la configuración del modelo.

Mientras tanto, puedes intentar otra pregunta más tarde."""
            
            elif "database" in error_str or "connection" in error_str or "postgres" in error_str:
                return f"""⚠️ **Error de conexión a la base de datos**

No pude conectarme a la base de datos para consultar los datos.

**Posibles soluciones:**
1. Verifica que DATABASE_URL esté configurada correctamente
2. Revisa que el servicio PostgreSQL esté activo
3. Intenta nuevamente en unos momentos

Si el problema persiste, contacta al equipo técnico.

Puedes intentar con otra pregunta mientras tanto."""
            
            # Generic error response with more helpful info
            return f"""⚠️ **Error técnico**

Disculpa, tuve un problema procesando tu solicitud.

**Detalles del error:** {type(e).__name__}

**Intenta:**
1. Reformular tu pregunta de forma más simple
2. Escribir directamente lo que necesitas (ej: "ventas del mes", "gastos de marketing")
3. Esperar unos segundos y volver a intentar

Si el problema persiste:
📧 {settings.business_email}

¿Puedes intentar de nuevo?"""
    
    async def generate_marketing_performance_report(self, scope: str) -> str:
        """Generate a structured marketing performance report for the requested scope."""

        normalized_scope = marketing_analysis.normalize_scope(scope)
        if not normalized_scope:
            return (
                "Necesito saber el nivel que quieres analizar. Indica si prefieres "
                "*campañas*, *conjuntos de anuncios* o *anuncios*."
            )

        try:
            marketing_data = await business_data.get_marketing_report(limit=200)
        except Exception as error:
            logger.error("Error retrieving marketing data: %s", error)
            return (
                "⚠️ No pude consultar los datos de marketing en este momento. "
                "Intenta nuevamente más tarde."
            )

        if not marketing_data:
            return (
                "⚠️ No encontré registros recientes en la vista de marketing. "
                "Verifica que la vista tenga datos para continuar con el análisis."
            )

        try:
            return marketing_analysis.build_marketing_report(marketing_data, normalized_scope)
        except Exception as error:
            logger.error("Error building marketing report: %s", error)
            return (
                "⚠️ Hubo un problema creando el análisis de marketing. "
                "Revisa que la vista incluya nombres, montos y conversiones."
            )

    async def _try_primary_mcp_response(
        self,
        conversation_messages: List[Dict[str, str]],
        context_data: Optional[str],
        message_text: str,
        contact_name: str,
        phone_number: Optional[str],
    ) -> Optional[str]:
        """Route the full response to the MCP OpenAI server if available."""
        if not self.mcp_handler or not self.mcp_handler.enabled:
            return None
        
        tool_name = self.primary_mcp_tool_name
        if not tool_name or not self.mcp_handler.has_tool(tool_name):
            return None
        
        arguments: Dict[str, Any] = {
            "conversation": conversation_messages,
            "system_prompt": self.system_prompt,
            "business_context": context_data,
            "message_text": message_text,
            "phone_number": phone_number,
            "metadata": {
                "contact_name": contact_name,
                "phone_number": phone_number,
            },
            "temperature": 0.7,
            "max_tokens": 500,
        }
        
        try:
            tool_result = await self.mcp_handler.call_mcp_tool(tool_name, arguments)
        except Exception as exc:
            logger.error(
                "Error calling MCP tool '%s': %s", tool_name, exc, exc_info=True
            )
            return None
        
        if not tool_result:
            return None
        
        if isinstance(tool_result, dict):
            if tool_result.get("error"):
                logger.error(
                    "MCP tool '%s' returned error response: %s",
                    tool_name,
                    tool_result["error"],
                )
                return None
            
            content = tool_result.get("content") or tool_result.get("message")
            if content:
                logger.info(
                    "Responding using MCP tool '%s' via OpenAI server", tool_name
                )
                return content
        
        elif isinstance(tool_result, str):
            logger.info("Responding using MCP tool '%s' (string payload)", tool_name)
            return tool_result
        
        logger.debug(
            "MCP tool '%s' returned unsupported payload type: %s",
            tool_name,
            type(tool_result),
        )
        return None



