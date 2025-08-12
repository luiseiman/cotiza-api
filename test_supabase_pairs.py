from supabase import create_client
import os
from dotenv import load_dotenv
load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")
print("URL:", url[-24:])  # debug mínimo
print("KEY tipo:", "service" if "service" in (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or "") else "anon/other")

supabase = create_client(url, key)
res = supabase.table("terminal_ratio_pairs").select("*").limit(3).execute()
print("Rows:", len(res.data))
print(res.data)
