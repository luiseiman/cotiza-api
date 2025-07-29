from supabase import create_client
import os
from dotenv import load_dotenv
import datetime
import json

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

def parsear_cotizacion(data):
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except Exception as e:
            print("❌ No se pudo decodificar el mensaje en parsear_cotizacion:", e)
            return None

    symbol = None
    ts = None
    bid_price = bid_size = offer_price = offer_size = last_price = last_size = None

    try:
        symbol = data["instrumentId"]["symbol"]
        ts_raw = data.get("timestamp", None)
        if ts_raw:
            ts = datetime.datetime.utcfromtimestamp(ts_raw/1000).isoformat()
        else:
            ts = datetime.datetime.utcnow().isoformat()

        md = data.get("marketData", {})

        # BI puede ser lista o dict o None
        bi = md.get("BI")
        if isinstance(bi, list) and len(bi) > 0:
            bid = bi[0]
        elif isinstance(bi, dict):
            bid = bi
        else:
            bid = {}

        # OF puede ser lista o dict o None
        of = md.get("OF")
        if isinstance(of, list) and len(of) > 0:
            offer = of[0]
        elif isinstance(of, dict):
            offer = of
        else:
            offer = {}

        # LA puede ser dict o None
        la = md.get("LA")
        if isinstance(la, dict):
            last = la
        else:
            last = {}

        bid_price = bid.get("price")
        bid_size = bid.get("size")
        offer_price = offer.get("price")
        offer_size = offer.get("size")
        last_price = last.get("price")
        last_size = last.get("size")
    except Exception as e:
        print("❌ Error al parsear campos:", e)

    return {
        "symbol": symbol,
        "timestamp": ts,
        "bid_price": bid_price,
        "bid_size": bid_size,
        "offer_price": offer_price,
        "offer_size": offer_size,
        "last_price": last_price,
        "last_size": last_size,
        "raw": data
    }

def guardar_en_supabase(data):
    registro = parsear_cotizacion(data)
    if not registro:
        print("❌ Registro no válido, no se guarda.")
        return
    supabase.table("cotizaciones_historicas").insert(registro).execute()
    supabase.table("ultima_cotizacion").upsert(registro, on_conflict=["symbol"]).execute()