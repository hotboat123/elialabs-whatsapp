# 📊 Configuración de Vistas de Base de Datos

El bot ahora puede consultar vistas específicas de PostgreSQL para responder con datos reales del negocio.

---

## 🎯 ¿Qué hace esto?

El bot automáticamente consulta la base de datos cuando detecta palabras clave relacionadas con:
- **Productos**: "producto", "productos", "catálogo", "precio"
- **Pedidos**: "pedido", "pedidos", "orden", "compra"
- **Stock**: "stock", "inventario", "disponibilidad"

---

## 🔍 Cómo Funciona

### 1. Detección Automática

Cuando un cliente pregunta algo como:
- "¿Qué productos tienen?"
- "Quiero ver mi pedido"
- "¿Tienen stock de X?"

El bot automáticamente:
1. Detecta las palabras clave
2. Consulta las vistas correspondientes en PostgreSQL
3. Usa esa información para generar una respuesta precisa

### 2. Vistas que Busca Automáticamente

El bot intenta encontrar estas vistas (en orden de prioridad):

**Para Productos:**
- `v_products`
- `view_products`
- `products_view`
- `productos`
- `v_productos`
- `products`

**Para Pedidos:**
- `v_orders`
- `view_orders`
- `orders_view`
- `pedidos`
- `v_pedidos`
- `orders`

**Para Stock:**
- `v_stock`
- `view_stock`
- `stock_view`
- `inventario`
- `v_inventario`
- `stock`

**Para Clientes:**
- `v_customers`
- `view_customers`
- `customers_view`
- `clientes`
- `v_clientes`
- `customers`

---

## ⚙️ Configuración

### Opción 1: Sin Configuración (Automático)

El bot intentará encontrar las vistas automáticamente. Solo necesitas tener las vistas en tu base de datos con nombres comunes.

### Opción 2: Especificar Vistas (Recomendado)

En Railway o en tu `.env`, puedes controlar qué vistas puede consultar el bot:

```env
DB_VIEWS_ENABLED=v_products,v_orders,v_stock,v_customers
```

Si quieres que pueda acceder **a todas las vistas** que tus credenciales permiten, simplemente deja la variable vacía (o elimínala). En ese caso no habrá restricciones y el MCP podrá consultar cualquier vista de PostgreSQL.

---

## 📋 Crear Vistas en PostgreSQL

Si aún no tienes vistas, puedes crearlas así:

### Ejemplo: Vista de Productos

```sql
CREATE VIEW v_products AS
SELECT 
    id,
    name as nombre,
    description as descripcion,
    price as precio,
    stock as cantidad,
    category as categoria
FROM products
WHERE active = true;
```

### Ejemplo: Vista de Pedidos

```sql
CREATE VIEW v_orders AS
SELECT 
    id,
    order_number as numero_pedido,
    customer_phone as phone,
    customer_name as nombre,
    total,
    status as estado,
    created_at as fecha
FROM orders
ORDER BY created_at DESC;
```

### Ejemplo: Vista de Stock

```sql
CREATE VIEW v_stock AS
SELECT 
    product_id,
    product_name,
    quantity as cantidad,
    available as disponible
FROM inventory
WHERE available > 0;
```

---

## 🧪 Probar las Vistas

### 1. Listar Vistas Disponibles

```bash
curl https://tu-app.railway.app/db/views
```

Respuesta:
```json
{
  "views": ["v_products", "v_orders", "v_stock"],
  "total": 3
}
```

### 2. Consultar una Vista Específica

```bash
curl https://tu-app.railway.app/db/views/v_products?limit=10
```

---

## 💡 Ejemplos de Uso

### Cliente pregunta: "¿Qué productos tienen?"

El bot:
1. Detecta "productos"
2. Consulta `v_products` o vista similar
3. Responde con información real de los productos

### Cliente pregunta: "¿Dónde está mi pedido?"

El bot:
1. Detecta "pedido"
2. Obtiene el número de teléfono del cliente
3. Consulta `v_orders` filtrando por teléfono
4. Responde con el estado real del pedido

---

## 🔧 Personalización Avanzada

### Consultar Vistas Personalizadas

Si tienes vistas con nombres específicos, puedes agregarlas al código en `app/db/business_data.py`:

```python
# Agregar a la lista de posibles nombres
possible_names = [
    'tu_vista_personalizada',
    'v_products',
    # ... otras vistas
]
```

### Filtros Personalizados

Las funciones aceptan filtros opcionales:

```python
# En business_data.py puedes agregar más filtros
filters = {'category': 'electronica', 'active': True}
products = await business_data.query_view('v_products', filters=filters)
```

---

## 📝 Estructura de Datos Esperada

Las vistas deben retornar datos en formato estándar. El bot puede manejar cualquier estructura, pero es recomendable:

**Productos:**
- `id`, `name`/`nombre`, `price`/`precio`, `description`/`descripcion`, `stock`/`cantidad`

**Pedidos:**
- `id`, `phone`/`customer_phone`, `status`/`estado`, `total`, `created_at`/`fecha`

**Stock:**
- `product_id`, `quantity`/`cantidad`, `available`/`disponible`

---

## ⚠️ Consideraciones de Seguridad

1. **Solo lectura**: Las vistas deben ser de solo lectura (SELECT)
2. **Permisos**: El usuario de la base de datos debe tener permisos de SELECT en las vistas
3. **Datos sensibles**: No incluyas información sensible (contraseñas, tokens) en las vistas

---

## 🐛 Troubleshooting

### El bot no encuentra productos

1. Verifica que la vista existe:
   ```sql
   SELECT * FROM information_schema.views WHERE table_name = 'v_products';
   ```

2. Prueba la vista directamente:
   ```sql
   SELECT * FROM v_products LIMIT 5;
   ```

3. Verifica los logs del bot para ver qué vistas está intentando

### El bot no consulta la base de datos

1. Verifica que `DATABASE_URL` esté configurada correctamente
2. Revisa los logs para ver si hay errores de conexión
3. Asegúrate que las vistas tienen nombres reconocibles

---

## 📚 Documentación Adicional

- Ver `app/db/business_data.py` para funciones disponibles
- Ver `app/bot/ai_handler.py` para cómo se usa el contexto
- Endpoint de prueba: `GET /db/views` para listar vistas disponibles

---

**¡Con esto el bot tendrá acceso a datos reales de tu negocio!** 🚀

