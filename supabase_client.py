import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Cargar .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
# Aceptar múltiples nombres de clave: service role > key > anon
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_ANON_KEY")
)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("[supabase] FALTAN SUPABASE_URL / SUPABASE_KEY en .env. No se puede iniciar sin DB.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_active_pairs(user_id: str = None):
    """Trae los pares desde terminal_ratio_pairs. Si existe 'active', filtra por True; si no, devuelve todos."""
    try:
        # Siempre traer todos primero (evita error 42703 si 'active' no existe)
        data = supabase.table("terminal_ratio_pairs").select("*").execute()
        pairs = data.data or []

        # Filtrar por 'active' solo si la columna existe
        if any(isinstance(p, dict) and ('active' in p) for p in pairs):
            pairs = [p for p in pairs if p.get("active") is True]

        print(f"[supabase] Obtenidos {len(pairs)} pares de terminal_ratio_pairs")
        return pairs
    except Exception as e:
        print(f"[supabase] error get_active_pairs: {e}")
        return []


def list_rules(user_id: str, client_id: str = None, active: bool = True):
    """Lista reglas de trading. client_id es opcional."""
    try:
        query = supabase.table("trading_rules").select("*")
        if user_id:
            query = query.eq("user_id", user_id)
        if client_id:
            query = query.eq("client_id", client_id)
        if active:
            query = query.eq("active", True)
        data = query.execute()
        return data.data or []
    except Exception as e:
        print(f"[supabase] error list_rules: {e}")
        return []


def create_rule(rule: dict):
    try:
        return supabase.table("trading_rules").insert(rule).execute()
    except Exception as e:
        print(f"[supabase] error create_rule: {e}")
        return None


def delete_rule(rule_id: int):
    try:
        return supabase.table("trading_rules").delete().eq("id", rule_id).execute()
    except Exception as e:
        print(f"[supabase] error delete_rule: {e}")
        return None


def get_last_ratio_data(base_symbol: str, quote_symbol: str, user_id: str = None):
    """Obtiene el último registro de ratios para reutilizar valores calculados."""
    try:
        query = supabase.table("terminal_ratios_history").select("*")
        query = query.eq("base_symbol", base_symbol)
        query = query.eq("quote_symbol", quote_symbol)
        if user_id:
            query = query.eq("user_id", user_id)
        
        # Ordenar por asof descendente y tomar el primero
        data = query.order("asof", desc=True).limit(1).execute()
        
        if data.data and len(data.data) > 0:
            last_record = data.data[0]
            print(f"[supabase] 📊 Último registro encontrado para {base_symbol}/{quote_symbol}, ID: {last_record.get('id')}")
            return last_record
        else:
            print(f"[supabase] ⚠️ No hay registros históricos para {base_symbol}/{quote_symbol}")
            return None
            
    except Exception as e:
        print(f"[supabase] error get_last_ratio_data: {e}")
        return None


def guardar_en_supabase(tabla: str, row: dict):
    """Función de compatibilidad para guardar datos en Supabase."""
    try:
        # Verificar que la tabla existe antes de intentar insertar
        if not tabla or not row:
            return None
            
        # Limpiar datos antes de insertar
        clean_row = {}
        for key, value in row.items():
            if value is not None:
                if isinstance(value, float):
                    if not (value == float('inf') or value == float('-inf')):
                        clean_row[key] = value
                else:
                    clean_row[key] = value
        
        if not clean_row:
            return None
            
        print(f"[supabase] Intentando insertar en {tabla}: {clean_row}")
        resp = supabase.table(tabla).insert(clean_row).execute()
        
        # Verificar si la inserción fue exitosa basándose en los datos retornados
        if hasattr(resp, 'data') and resp.data:
            # Si hay datos retornados con ID, la inserción fue exitosa
            inserted_data = resp.data
            if isinstance(inserted_data, list) and len(inserted_data) > 0:
                first_record = inserted_data[0]
                if 'id' in first_record and first_record['id'] is not None:
                    print(f"[supabase] ✅ Inserción exitosa en {tabla}, ID: {first_record['id']}")
                    return resp
        
        # Si no se pudo verificar el éxito, asumir que falló
        print(f"[supabase] ❌ No se pudo verificar el éxito de la inserción en {tabla}")
        return None
        
    except Exception as e:
        print(f"[supabase] error guardar_en_supabase en {tabla}: {e}")
        return None