"""
Script para probar la conexión a PostgreSQL y consultar vistas específicas
"""
import asyncio
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

from app.db.connection import get_connection
from app.db import business_data

async def test_connection():
    """Probar conexión a la base de datos"""
    print("🔍 Probando conexión a PostgreSQL...")
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Test básico de conexión
                cur.execute("SELECT version();")
                version = cur.fetchone()
                print(f"✅ Conexión exitosa!")
                print(f"   PostgreSQL version: {version[0]}")
                
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False
    
    return True

async def test_view(view_name: str):
    """Probar consulta de una vista específica"""
    print(f"\n🔍 Probando vista: {view_name}")
    
    try:
        # Intentar consultar la vista
        results = await business_data.query_view(view_name, limit=10)
        
        if results:
            print(f"✅ Vista encontrada! {len(results)} registros encontrados")
            print(f"\n📊 Primeros registros:")
            for i, row in enumerate(results[:5], 1):
                print(f"\n   Registro {i}:")
                for key, value in row.items():
                    print(f"     {key}: {value}")
            
            if len(results) > 5:
                print(f"\n   ... y {len(results) - 5} registros más")
            
            return True
        else:
            print(f"⚠️  Vista existe pero no tiene datos")
            return True
            
    except Exception as e:
        print(f"❌ Error consultando vista: {e}")
        return False

async def list_all_views():
    """Listar todas las vistas disponibles"""
    print("\n🔍 Listando todas las vistas disponibles...")
    
    try:
        views = await business_data.list_available_views()
        
        if views:
            print(f"✅ Encontradas {len(views)} vistas:")
            for view in views:
                print(f"   - {view}")
        else:
            print("⚠️  No se encontraron vistas")
            
    except Exception as e:
        print(f"❌ Error listando vistas: {e}")

async def main():
    """Función principal"""
    print("=" * 60)
    print("🧪 TEST DE CONEXIÓN A POSTGRESQL")
    print("=" * 60)
    
    # Test 1: Conexión básica
    if not await test_connection():
        print("\n❌ No se pudo conectar a la base de datos")
        print("   Verifica tu DATABASE_URL en .env")
        return
    
    # Test 2: Listar vistas
    await list_all_views()
    
    # Test 3: Vista específica
    view_name = "v_monthly_sales_costs"
    await test_view(view_name)
    
    print("\n" + "=" * 60)
    print("✅ Test completado")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())

