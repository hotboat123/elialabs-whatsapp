# Configuración de Claude Sonnet 4.5

## 🎯 Estado Actual

El bot está configurado para usar **Claude Sonnet 4.5** (`claude-sonnet-4-20250514`) como modelo principal, con fallback automático a modelos anteriores si no está disponible.

### Cadena de Fallback

1. **Claude Sonnet 4** (20250514) - Modelo principal
2. **Claude 3.5 Sonnet** (20241022) - Primera alternativa
3. **Claude 3.5 Sonnet** (20240620) - Segunda alternativa
4. **Claude 3 Sonnet** (20240229) - Tercera alternativa
5. **Claude 3 Haiku** (20240307) - Fallback garantizado (siempre disponible)

## 🔑 Requisitos para Claude Sonnet 4.5

Claude Sonnet 4.5 requiere:

1. **Tier de API superior** en Anthropic
2. **Créditos suficientes** en tu cuenta
3. **Región habilitada** (disponible en la mayoría de regiones)

### Verificar tu Tier de Anthropic

1. Ve a tu [Console de Anthropic](https://console.anthropic.com/)
2. Haz clic en tu perfil (esquina superior derecha)
3. Ve a **"Settings" > "Plans & Billing"**
4. Verifica tu tier actual:
   - **Free Tier**: Solo Haiku disponible
   - **Build Tier**: Sonnet 3.5 y anteriores
   - **Scale Tier**: Todos los modelos incluido Sonnet 4.5

### Actualizar tu Tier

Si ves errores 404 para Sonnet 4.5, necesitas:

1. Agregar un método de pago en Anthropic Console
2. Esperar aprobación (usualmente instantánea)
3. O solicitar acceso manual en [Anthropic Support](https://support.anthropic.com/)

## ⚙️ Configuración en Railway

### Opción 1: Usar Sonnet 4.5 (Recomendado si tienes tier superior)

En las **Variables de Entorno** de Railway:

```bash
ANTHROPIC_API_KEY=sk-ant-api03-xxx  # Tu API key
ANTHROPIC_MCP_MODEL=claude-sonnet-4-20250514
ANTHROPIC_MCP_FALLBACK_MODELS=claude-3-5-sonnet-20241022,claude-3-5-sonnet-20240620,claude-3-sonnet-20240229,claude-3-haiku-20240307
```

### Opción 2: Usar Sonnet 3.5 (Si no tienes acceso a Sonnet 4.5 aún)

```bash
ANTHROPIC_API_KEY=sk-ant-api03-xxx
ANTHROPIC_MCP_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_MCP_FALLBACK_MODELS=claude-3-5-sonnet-20240620,claude-3-sonnet-20240229,claude-3-haiku-20240307
```

### Opción 3: Usar Haiku (Tier gratuito o testing)

```bash
ANTHROPIC_API_KEY=sk-ant-api03-xxx
ANTHROPIC_MCP_MODEL=claude-3-haiku-20240307
# No necesitas fallbacks, Haiku siempre funciona
```

## 📊 Verificar qué Modelo está Usando

En los **logs de Railway**, busca:

### ✅ Sonnet 4.5 funcionando:
```
INFO:httpx:HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"
INFO:app.bot.mcp_handler:MCP tool 'openai_chat' executed successfully
```
(Sin warnings de "model not available")

### ⚠️ Usando fallback (Haiku):
```
WARNING:openai_mcp_server:Claude model 'claude-sonnet-4-20250514' not available (404). Trying next fallback...
WARNING:openai_mcp_server:Claude model 'claude-3-5-sonnet-20241022' not available (404). Trying next fallback...
...
INFO:httpx:HTTP Request: POST https://api.anthropic.com/v1/messages "HTTP/1.1 200 OK"
```
(Varios warnings seguidos de 200 OK = está usando Haiku)

## 💰 Costos Aproximados

Por millón de tokens de entrada/salida:

| Modelo | Entrada | Salida | Velocidad |
|--------|---------|--------|-----------|
| Claude Sonnet 4.5 | $3.00 | $15.00 | Más lento |
| Claude 3.5 Sonnet | $3.00 | $15.00 | Medio |
| Claude 3 Haiku | $0.25 | $1.25 | Más rápido |

### Recomendación:

- **Producción con usuarios reales**: Sonnet 4.5 (mejor calidad)
- **Testing o bajo presupuesto**: Haiku (más económico)
- **Balance**: Sonnet 3.5

## 🔧 Troubleshooting

### Problema: Error 404 para todos los modelos Sonnet

**Solución**: Tu API key no tiene acceso a modelos Sonnet. 

1. Verifica que tu API key sea válida:
   ```bash
   curl https://api.anthropic.com/v1/messages \
     -H "x-api-key: $ANTHROPIC_API_KEY" \
     -H "anthropic-version: 2023-06-01" \
     -H "content-type: application/json" \
     -d '{"model":"claude-3-haiku-20240307","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
   ```

2. Si funciona con Haiku pero no con Sonnet, necesitas upgrade de tier

### Problema: Error 401 Unauthorized

**Solución**: API key inválida o no configurada.

1. Revisa que `ANTHROPIC_API_KEY` esté correctamente configurada en Railway
2. Genera una nueva API key en [Anthropic Console](https://console.anthropic.com/settings/keys)

### Problema: Error 429 Rate Limit

**Solución**: Has excedido tu límite de requests.

1. Espera unos minutos
2. Considera upgrade de tier para límites más altos
3. O usa Haiku (límites más generosos)

## 🎓 Recursos

- [Anthropic API Docs](https://docs.anthropic.com/)
- [Model Comparison](https://docs.anthropic.com/en/docs/about-claude/models)
- [Pricing](https://www.anthropic.com/pricing)
- [Console](https://console.anthropic.com/)

## 📝 Notas Técnicas

- El código intenta automáticamente todos los modelos en orden
- Si todos fallan, regresa a Haiku (garantizado)
- Los logs muestran claramente qué modelo se está usando
- El cambio de modelo NO requiere redeploy, solo cambio de env var

