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
            # Try to get relevant business data based on the message (non-blocking)
            context_data = None
            try:
                context_data = await self._get_business_context(message_text, phone_number)
            except Exception as db_error:
                # Log but don't fail - bot can still respond without DB context
                logger.warning(f"Could not get business context (non-critical): {db_error}")
                context_data = None
            
            # Build messages for AI (last 10 messages for context)
            messages = []
            recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
            
            for msg in recent_history:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Add business context if available
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
    
    async def _get_business_context(self, message: str, phone_number: Optional[str] = None) -> Optional[str]:
        """
        Get relevant business analytics data from database based on the message
        
        Args:
            message: User's message
            phone_number: User's phone number (not used for owner analytics)
        
        Returns:
            Context string with business analytics data or None
        """
        message_lower = message.lower()
        context_parts = []
        
        try:
            # Wrap all DB queries in try-except to prevent errors from breaking the flow
            # Check for sales/revenue queries (including numbers)
            if any(word in message_lower for word in ['ventas', 'venta', 'ingresos', 'revenue', 'facturación', 'facturacion', 'mes', 'meses', 'día', 'dia', 'semana', 'costos', 'gastos']) or message_lower.strip() in ['1', 'uno']:
                # Try monthly sales costs first (specific view)
                try:
                    sales_data = await business_data.get_monthly_sales_costs(limit=50)
                    if not sales_data:
                        # Fallback to general sales report
                        try:
                            sales_data = await business_data.get_sales_report(limit=50)
                        except Exception as fallback_error:
                            logger.warning(f"Fallback sales report also failed: {fallback_error}")
                            sales_data = []
                    
                    if sales_data:
                        context_parts.append(f"REPORTE DE VENTAS Y COSTOS ({len(sales_data)} registros encontrados):")
                        for record in sales_data[:10]:  # Limit to 10 for context
                            record_info = ", ".join([f"{k}: {v}" for k, v in record.items() if v is not None][:5])
                            context_parts.append(f"- {record_info}")
                    else:
                        context_parts.append("⚠️ No se encontraron datos de ventas en la base de datos. La vista puede estar vacía o no existir.")
                except Exception as e:
                    logger.warning(f"Error getting sales data (non-critical): {e}")
                    # Don't add error to context - let bot respond without DB data
                    context_parts.append("⚠️ No se pudo consultar la base de datos en este momento.")
            
            # Check for marketing/advertising queries (including numbers)
            if any(word in message_lower for word in ['marketing', 'anuncios', 'anuncio', 'publicidad', 'ads', 'campaña', 'campana', 'roi']) or message_lower.strip() in ['2', 'dos']:
                try:
                    marketing_data = await business_data.get_marketing_report(limit=50)
                    if marketing_data:
                        context_parts.append(f"REPORTE DE MARKETING ({len(marketing_data)} registros encontrados):")
                        for record in marketing_data[:10]:
                            record_info = ", ".join([f"{k}: {v}" for k, v in record.items() if v is not None][:5])
                            context_parts.append(f"- {record_info}")
                    else:
                        context_parts.append("⚠️ No se encontraron datos de marketing en la base de datos")
                except Exception as e:
                    logger.error(f"Error getting marketing data: {e}")
                    context_parts.append(f"❌ Error consultando marketing: {str(e)}")
            
            # Check for product analytics queries (including numbers)
            if any(word in message_lower for word in ['productos más vendidos', 'top productos', 'productos vendidos', 'productos populares', 'productos']) or message_lower.strip() in ['4', 'cuatro']:
                try:
                    products = await business_data.get_top_products(limit=20)
                    if products:
                        context_parts.append(f"PRODUCTOS MÁS VENDIDOS ({len(products)} encontrados):")
                        for product in products[:10]:
                            product_info = ", ".join([f"{k}: {v}" for k, v in product.items() if v is not None][:5])
                            context_parts.append(f"- {product_info}")
                    else:
                        context_parts.append("⚠️ No se encontraron datos de productos en la base de datos")
                except Exception as e:
                    logger.error(f"Error getting products data: {e}")
                    context_parts.append(f"❌ Error consultando productos: {str(e)}")
            
            # Check for financial queries (including numbers)
            if any(word in message_lower for word in ['financiero', 'financieros', 'gastos', 'costos', 'margen', 'ganancia', 'utilidad']) or message_lower.strip() in ['5', 'cinco']:
                try:
                    financial_data = await business_data.get_financial_report(limit=50)
                    if financial_data:
                        context_parts.append(f"REPORTE FINANCIERO ({len(financial_data)} registros encontrados):")
                        for record in financial_data[:10]:
                            record_info = ", ".join([f"{k}: {v}" for k, v in record.items() if v is not None][:5])
                            context_parts.append(f"- {record_info}")
                    else:
                        context_parts.append("⚠️ No se encontraron datos financieros en la base de datos")
                except Exception as e:
                    logger.error(f"Error getting financial data: {e}")
                    context_parts.append(f"❌ Error consultando datos financieros: {str(e)}")
            
            # Check for general analytics/reports (including numbers)
            if any(word in message_lower for word in ['reporte', 'reportes', 'análisis', 'analisis', 'métricas', 'metricas', 'estadísticas', 'estadisticas', 'dashboard']) or message_lower.strip() in ['6', 'seis']:
                try:
                    # Try to get general analytics
                    analytics_data = await business_data.get_general_analytics(limit=50)
                    if analytics_data:
                        context_parts.append(f"ANÁLISIS GENERAL ({len(analytics_data)} registros encontrados):")
                        for record in analytics_data[:10]:
                            record_info = ", ".join([f"{k}: {v}" for k, v in record.items() if v is not None][:5])
                            context_parts.append(f"- {record_info}")
                    else:
                        context_parts.append("⚠️ No se encontraron datos de analytics en la base de datos")
                except Exception as e:
                    logger.error(f"Error getting analytics data: {e}")
                    context_parts.append(f"❌ Error consultando analytics: {str(e)}")
            
            if context_parts:
                return "\n".join(context_parts)
            
        except Exception as e:
            # Log error but don't break the flow - bot can still respond without DB context
            logger.warning(f"Error getting business context (non-critical): {e}")
            # Return None to allow bot to continue without DB data
            return None
        
        return None



