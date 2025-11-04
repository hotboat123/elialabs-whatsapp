# ⚙️ Guía de Configuración - E-commerce WhatsApp Bot

Esta guía explica cómo configurar el chatbot para tu e-commerce, incluyendo cómo cambiar el número de WhatsApp y la conexión a PostgreSQL.

---

## 📋 Variables de Entorno Necesarias

Todas las configuraciones se hacen a través de variables de entorno. Copia el archivo `env.example` a `.env` y edita los valores.

---

## 🔢 Cómo Cambiar el Número de WhatsApp

Para cambiar a un nuevo número de WhatsApp, necesitas actualizar estas variables:

### 1. En tu archivo `.env` (o en Railway):

```env
# WhatsApp Business API - NUEVO NÚMERO
WHATSAPP_API_TOKEN=tu_nuevo_token_aqui
WHATSAPP_PHONE_NUMBER_ID=tu_nuevo_phone_id_aqui
WHATSAPP_BUSINESS_ACCOUNT_ID=tu_nuevo_business_account_id_aqui
WHATSAPP_VERIFY_TOKEN=tu_token_personalizado_aqui
```

### 2. Dónde obtener estas credenciales:

1. **Ve a Meta for Developers**: https://developers.facebook.com/
2. Selecciona tu App de WhatsApp (o crea una nueva)
3. Ve a **WhatsApp** → **API Setup**
4. Copia:
   - **Access Token** → `WHATSAPP_API_TOKEN`
   - **Phone number ID** → `WHATSAPP_PHONE_NUMBER_ID`
   - **Business Account ID** → `WHATSAPP_BUSINESS_ACCOUNT_ID`
   - **Verify Token** → Crea uno personalizado (ej: `MiTokenSecreto123`)

### 3. Actualizar el Webhook en Meta:

#### Paso 1: Obtener tu Callback URL desde Railway

1. Ve a tu proyecto en Railway: https://railway.app
2. Selecciona tu servicio (el que contiene tu aplicación)
3. Ve a la pestaña **Settings** o **Variables**
4. Busca la sección **"Domains"** o **"Public Domain"**
5. Copia la URL pública (ejemplo: `https://elialabs-whatsapp-production.up.railway.app`)
6. Tu **Callback URL** será: `https://tu-url.railway.app/webhook`

**Ejemplo:**
- Si tu URL pública es: `https://elialabs-whatsapp.up.railway.app`
- Tu Callback URL será: `https://elialabs-whatsapp.up.railway.app/webhook`

#### Paso 2: Configurar el Webhook en Meta

1. Ve a **Meta for Developers**: https://developers.facebook.com/
2. Selecciona tu App de WhatsApp
3. Ve a **WhatsApp** → **Configuration** → **Webhook**
4. Click en **"Edit"** o **"Configure"**
5. En **Callback URL**: Pega tu URL completa con `/webhook`
   - Ejemplo: `https://elialabs-whatsapp.up.railway.app/webhook`
6. En **Verify Token**: Pega el mismo valor que pusiste en `WHATSAPP_VERIFY_TOKEN`
7. En **Webhook fields**: Selecciona `messages`
8. Click **Verify and Save**

**⚠️ IMPORTANTE:** El webhook debe estar accesible públicamente (no funcionará con `localhost`)

### 4. Actualizar información del negocio (opcional):

```env
BUSINESS_PHONE=+1234567890  # Tu nuevo número (para mostrar a clientes)
```

---

## 🗄️ Cómo Cambiar la Conexión a PostgreSQL (Otro Railway)

Para conectarte a otra base de datos PostgreSQL en Railway:

### 1. En Railway:

1. Ve a tu proyecto en Railway
2. Crea o selecciona un servicio **PostgreSQL**
3. Ve a la pestaña **Variables**
4. Copia la variable `DATABASE_URL`

### 2. En tu archivo `.env` (o en Railway):

```env
# PostgreSQL - NUEVA CONEXIÓN
DATABASE_URL=postgresql://postgres:password@hostname.railway.app:5432/railway
```

**Formato típico de Railway:**
```
postgresql://postgres:PASSWORD@HOST.railway.app:PORT/railway
```

### 3. Dónde configurarlo:

#### Opción A: En Railway (Recomendado para producción)
1. Ve a tu servicio de la aplicación en Railway
2. Ve a **Variables**
3. Agrega o edita `DATABASE_URL`
4. Pega el valor completo de tu PostgreSQL

#### Opción B: En archivo `.env` (Para desarrollo local)
1. Edita tu archivo `.env`
2. Cambia `DATABASE_URL` por la nueva conexión

### 4. Verificar la conexión:

Después de cambiar la URL, reinicia la aplicación y verifica:

```bash
# Verificar health check
curl https://tu-app.railway.app/health
```

Deberías ver:
```json
{
  "status": "healthy",
  "database": "connected",
  "whatsapp_api": "configured"
}
```

---

## 🏪 Configuración de Información del Negocio

Personaliza la información de tu e-commerce:

```env
# Información de tu negocio
BOT_NAME=Asistente Virtual
BUSINESS_NAME=Mi Tienda E-commerce
BUSINESS_PHONE=+1234567890
BUSINESS_EMAIL=info@mitienda.com
BUSINESS_WEBSITE=https://mitienda.com
```

### Mensaje de Bienvenida Personalizado (Opcional):

Si quieres un mensaje de bienvenida específico:

```env
WELCOME_MESSAGE=👋 ¡Hola! Bienvenido a Mi Tienda...

Estoy aquí para ayudarte con tus compras.
¿En qué puedo ayudarte hoy?
```

**Nota:** Si no defines `WELCOME_MESSAGE`, se usará un mensaje genérico que incluye el nombre de tu negocio.

---

## 🔑 Otras Configuraciones Importantes

### API de IA (Groq):

```env
GROQ_API_KEY=tu_groq_api_key
```

Obtén tu API key gratuita en: https://console.groq.com/

### Configuración del Servidor:

```env
PORT=8000
HOST=0.0.0.0
ENVIRONMENT=production  # o 'development'
LOG_LEVEL=INFO
```

---

## 📝 Resumen de Cambios Necesarios

### Para cambiar de número de WhatsApp:

✅ `WHATSAPP_API_TOKEN`
✅ `WHATSAPP_PHONE_NUMBER_ID`
✅ `WHATSAPP_BUSINESS_ACCOUNT_ID`
✅ `WHATSAPP_VERIFY_TOKEN`
✅ Actualizar webhook en Meta
✅ `BUSINESS_PHONE` (opcional, para mostrar a clientes)

### Para cambiar de PostgreSQL:

✅ `DATABASE_URL` (nueva conexión de Railway)
✅ Reiniciar la aplicación

---

## ✅ Checklist de Configuración

Antes de poner en producción:

- [ ] Variables de WhatsApp configuradas
- [ ] Webhook configurado en Meta y verificado
- [ ] `DATABASE_URL` apunta a tu PostgreSQL
- [ ] Información del negocio personalizada
- [ ] `GROQ_API_KEY` configurada
- [ ] Health check responde correctamente
- [ ] Probar enviando un mensaje de prueba

---

## 🐛 Solución de Problemas

### Error: "Repository not found" al hacer push
- El repositorio en GitHub no existe aún
- Crea el repositorio en GitHub primero

### Error: "Connection refused" en base de datos
- Verifica que `DATABASE_URL` sea correcta
- Asegúrate que el servicio PostgreSQL esté activo en Railway

### El bot no responde a mensajes
- Verifica que el webhook esté configurado correctamente
- Revisa los logs en Railway
- Confirma que `WHATSAPP_API_TOKEN` sea válido

### Mensajes de error en logs
- Revisa que todas las variables de entorno estén configuradas
- Verifica los permisos de la base de datos
- Confirma que `GROQ_API_KEY` sea válida

---

## 📞 Soporte

Si tienes problemas con la configuración, revisa:
- Los logs de Railway
- La documentación de Meta WhatsApp API
- El archivo `env.example` para referencia

---

**¡Listo!** Con estos cambios tendrás tu chatbot configurado para tu e-commerce con el número y base de datos correctos. 🚀

