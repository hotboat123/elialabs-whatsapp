# 🔧 Variables de Entorno Requeridas en Railway

Este error indica que faltan variables de entorno en Railway. Aquí está la lista completa de variables **OBLIGATORIAS** que debes configurar:

---

## ✅ Variables OBLIGATORIAS (Sin estas no funcionará)

### 1. Base de Datos
```env
DATABASE_URL=postgresql://postgres:password@host.railway.app:5432/railway
```
**Cómo obtenerla:**
- Ve a tu servicio PostgreSQL en Railway
- Ve a **Variables**
- Copia el valor de `DATABASE_URL`

### 2. WhatsApp Business API
```env
WHATSAPP_API_TOKEN=tu_token_de_meta
WHATSAPP_PHONE_NUMBER_ID=tu_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=tu_business_account_id
WHATSAPP_VERIFY_TOKEN=tu_token_personalizado
```
**Cómo obtenerlas:**
- Ve a https://developers.facebook.com/
- Selecciona tu App de WhatsApp
- Ve a **WhatsApp** → **API Setup**
- Copia: Access Token, Phone Number ID
- Ve a **Settings** → **Business Info** → Copia Business Account ID
- Crea un Verify Token personalizado (ej: `MiToken123`)

### 3. Groq AI (GRATIS - OBLIGATORIO)
```env
GROQ_API_KEY=tu_groq_api_key
```
**Cómo obtenerla:**
1. Ve a: https://console.groq.com/
2. Crea una cuenta (gratis, sin tarjeta)
3. Ve a **API Keys** → **Create API Key**
4. Copia la key (empieza con `gsk_...`)

---

## 🎨 Variables OPCIONALES (Tienen valores por defecto)

Si no las configuras, se usarán valores genéricos:

```env
BOT_NAME=Asistente Virtual
BUSINESS_NAME=Mi Tienda
BUSINESS_PHONE=+1234567890
BUSINESS_EMAIL=info@mitienda.com
BUSINESS_WEBSITE=https://mitienda.com
```

**Para Happy Lapiz, deberías configurar:**
```env
BUSINESS_NAME=Happy Lapiz
BUSINESS_EMAIL=cliente@happylapiz.cl
BUSINESS_WEBSITE=https://happylapiz.cl
```

---

## 📝 Cómo Agregar Variables en Railway

### Paso 1: Ir a Variables
1. Ve a tu proyecto en Railway
2. Selecciona el **servicio** de tu aplicación (no el PostgreSQL)
3. Ve a la pestaña **Variables**

### Paso 2: Agregar Variables
1. Click en **"+ New Variable"** o **"Add Variable"**
2. En **Key**: Pega el nombre (ej: `GROQ_API_KEY`)
3. En **Value**: Pega el valor
4. Click **Add** o **Save**

### Paso 3: Repetir para Todas
Agrega todas las variables obligatorias una por una.

### Paso 4: Reiniciar
Después de agregar todas las variables, Railway debería reiniciar automáticamente. Si no, puedes hacerlo manualmente desde **Deployments**.

---

## ✅ Checklist Completo

Antes de deployar, asegúrate de tener:

- [ ] `DATABASE_URL` (de tu PostgreSQL)
- [ ] `WHATSAPP_API_TOKEN`
- [ ] `WHATSAPP_PHONE_NUMBER_ID`
- [ ] `WHATSAPP_BUSINESS_ACCOUNT_ID`
- [ ] `WHATSAPP_VERIFY_TOKEN`
- [ ] `GROQ_API_KEY` ⚠️ **ESTA ES LA QUE FALTA**
- [ ] `BUSINESS_NAME` (opcional, pero recomendado)
- [ ] `BUSINESS_EMAIL` (opcional, pero recomendado)
- [ ] `BUSINESS_WEBSITE` (opcional, pero recomendado)

---

## 🚨 Error Actual

El error específico que tienes es:

```
groq_api_key
  Field required
```

**Solución:** Agrega `GROQ_API_KEY` en Railway con tu API key de Groq.

---

## 🔗 Links Útiles

- **Groq Console**: https://console.groq.com/
- **Meta Developers**: https://developers.facebook.com/
- **Railway Dashboard**: https://railway.app

---

## 💡 Tips

1. **Groq es GRATIS**: No necesitas tarjeta de crédito
2. **Variables sensibles**: No las compartas públicamente
3. **Reinicio automático**: Railway reinicia cuando cambias variables
4. **Verificación**: Después de agregar todas, verifica en los logs que no haya más errores

---

**¡Una vez que agregues `GROQ_API_KEY`, el deploy debería funcionar!** 🚀

