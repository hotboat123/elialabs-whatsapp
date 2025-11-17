# Configuración del Worker de Resúmenes Diarios en Railway

## Paso 1: Configurar Variables de Entorno

En el dashboard de Railway, ve a tu proyecto y agrega estas variables de entorno:

```
DAILY_SUMMARY_TO=+56977577307,+56911111111,+56922222222
```

(Reemplaza con los números de WhatsApp a los que quieres enviar el resumen)

## Paso 2: Crear el Servicio Worker

Railway detectará automáticamente el `Procfile` que tiene dos procesos:
- `web`: Tu API FastAPI (ya existente)
- `worker`: El daemon de resúmenes diarios

### Opción A: Usando Railway CLI (Recomendado)

1. Instala Railway CLI si no lo tienes:
   ```bash
   npm install -g @railway/cli
   ```

2. Autentica:
   ```bash
   railway login
   ```

3. Vincula tu proyecto:
   ```bash
   railway link
   ```

4. Deploy:
   ```bash
   git add .
   git commit -m "Add daily sales summary worker"
   git push railway main
   ```

### Opción B: Desde el Dashboard de Railway

1. En tu proyecto de Railway, ve a la pestaña "Settings"
2. En "Deploy", asegúrate que esté conectado a tu repositorio Git
3. Railway detectará automáticamente el `Procfile`
4. Crea un nuevo servicio:
   - Click en "New Service" → "Empty Service"
   - Nombra el servicio como "daily-summary-worker"
   - En "Settings" → "Deploy" → "Start Command", pon:
     ```
     python send_daily_sales_summary.py --daemon-schedule --at 08:00 --tz America/Santiago
     ```
5. Asegúrate que tenga las mismas variables de entorno (especialmente `DAILY_SUMMARY_TO`)

## Paso 3: Verificar que funciona

1. Ve a los logs del servicio worker en Railway
2. Deberías ver un mensaje como:
   ```
   INFO Iniciando scheduler diario interno a las 08:00 America/Santiago
   INFO Próxima ejecución local: 2025-11-XX 08:00:00, esperando XXXX segundos
   ```

## Notas Importantes

- El worker enviará el resumen de **AYER** cada día a las 8:00 AM (hora de Santiago)
- El proceso se ejecuta 24/7 en Railway
- Si necesitas cambiar los números, solo actualiza la variable `DAILY_SUMMARY_TO` en Railway
- Si quieres cambiar la hora, edita el `Procfile` y haz push de nuevo

## Troubleshooting

Si no funciona:
1. Verifica que la variable `DAILY_SUMMARY_TO` esté configurada
2. Revisa los logs del worker para ver errores
3. Asegúrate que el servicio worker esté "deployed" y "running"

