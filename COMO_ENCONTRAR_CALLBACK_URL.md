# 🔗 Cómo Encontrar tu Callback URL

La **Callback URL** es la dirección donde Meta (WhatsApp) enviará los mensajes de tus clientes. Esta es la guía paso a paso para encontrarla.

---

## 📍 ¿Qué es la Callback URL?

La Callback URL tiene este formato:
```
https://tu-app.railway.app/webhook
```

Donde:
- `https://tu-app.railway.app` = Tu URL pública de Railway
- `/webhook` = El endpoint donde tu aplicación recibe mensajes

---

## 🚀 Opción 1: Si ya tienes la app desplegada en Railway

### Paso 1: Ir a Railway

1. Ve a: https://railway.app
2. Inicia sesión en tu cuenta
3. Selecciona tu proyecto

### Paso 2: Encontrar la URL pública

1. Dentro de tu proyecto, selecciona el **servicio** que contiene tu aplicación (el que tiene FastAPI/Python)
2. Ve a la pestaña **Settings** (Configuración)
3. Busca la sección **"Domains"** o **"Public Domain"**
4. Verás una URL como:
   ```
   https://elialabs-whatsapp-production.up.railway.app
   ```

### Paso 3: Formar la Callback URL

Toma tu URL pública y agrega `/webhook` al final:

**Ejemplo:**
- URL pública: `https://elialabs-whatsapp-production.up.railway.app`
- **Callback URL**: `https://elialabs-whatsapp-production.up.railway.app/webhook`

---

## 🆕 Opción 2: Si aún no tienes deploy

Si aún no has desplegado tu aplicación:

1. **Primero haz el deploy** siguiendo el README
2. **Luego** obtén la URL pública de Railway
3. **Finalmente** usa esa URL + `/webhook` como Callback URL

---

## 🧪 Cómo Verificar que tu Callback URL Funciona

### Test 1: Verificar que el servidor está activo

Abre en tu navegador:
```
https://tu-app.railway.app/health
```

Deberías ver:
```json
{
  "status": "healthy",
  "database": "connected",
  "whatsapp_api": "configured"
}
```

### Test 2: Verificar el endpoint webhook

Abre en tu navegador:
```
https://tu-app.railway.app/webhook?hub.mode=subscribe&hub.verify_token=TU_TOKEN&hub.challenge=test123
```

Si el token es correcto, deberías ver: `test123`

---

## 📝 Ejemplo Completo

**Mi URL pública en Railway:**
```
https://elialabs-whatsapp-production.up.railway.app
```

**Mi Callback URL para Meta:**
```
https://elialabs-whatsapp-production.up.railway.app/webhook
```

**Mi Verify Token (el mismo que en `WHATSAPP_VERIFY_TOKEN`):**
```
MiTokenSecreto123
```

---

## 🔧 Configurar en Meta

Una vez que tengas tu Callback URL:

1. Ve a: https://developers.facebook.com/
2. Selecciona tu App de WhatsApp
3. Ve a **WhatsApp** → **Configuration**
4. En la sección **Webhook**, click **"Edit"**
5. Pega tu Callback URL
6. Pega tu Verify Token
7. Selecciona **"messages"** en Webhook fields
8. Click **"Verify and Save"**

---

## ❓ Preguntas Frecuentes

### ¿Puedo usar localhost como Callback URL?

❌ **No.** Meta necesita una URL pública accesible desde internet. Localhost solo funciona en tu computadora.

### ¿Necesito HTTPS?

✅ **Sí.** Meta requiere HTTPS para los webhooks. Railway proporciona HTTPS automáticamente.

### ¿Puedo cambiar la URL después?

✅ **Sí.** Puedes actualizar la Callback URL en Meta cuando quieras, pero necesitarás verificar el webhook nuevamente.

### ¿Qué pasa si no funciona la verificación?

Verifica:
- ✅ La URL es correcta (incluye `/webhook`)
- ✅ El Verify Token coincide exactamente con `WHATSAPP_VERIFY_TOKEN`
- ✅ Tu aplicación está desplegada y funcionando
- ✅ El endpoint `/webhook` está accesible (prueba con el test de arriba)

---

## 📞 Si tienes problemas

1. Revisa los logs de Railway para ver errores
2. Verifica que tu aplicación esté corriendo
3. Asegúrate que el puerto 8000 esté configurado correctamente
4. Revisa que `WHATSAPP_VERIFY_TOKEN` sea el mismo en Railway y Meta

---

**¡Listo!** Con esta información podrás configurar tu webhook correctamente. 🚀

