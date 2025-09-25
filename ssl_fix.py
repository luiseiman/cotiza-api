#!/usr/bin/env python3
"""
Script para aplicar corrección SSL en pyRofex
"""

import ssl
import os

def apply_ssl_fix():
    """Aplica la corrección SSL para macOS"""
    print("🔒 Aplicando corrección SSL...")
    
    # Configurar contexto SSL
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # Configurar variables de entorno
    os.environ['PYTHONHTTPSVERIFY'] = '0'
    os.environ['SSL_VERIFY'] = 'False'
    
    print("✅ Corrección SSL aplicada")
    return ssl_context

if __name__ == "__main__":
    apply_ssl_fix()
