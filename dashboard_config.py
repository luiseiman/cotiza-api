"""
Configuración del Dashboard de Ratios

Personaliza aquí los horarios y días en que se ejecuta el refresh automático.
"""

# =====================================================================
# CONFIGURACIÓN DE HORARIOS DE MERCADO
# =====================================================================

# Días de la semana en que se ejecuta el refresh
# 0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes, 5=Sábado, 6=Domingo
DIAS_HABILES = [0, 1, 2, 3, 4]  # Lunes a Viernes

# Horario de inicio (formato 24h)
HORA_INICIO = 10      # 10:00 AM
MINUTO_INICIO = 0

# Horario de fin (formato 24h)
HORA_FIN = 17         # 5:00 PM
MINUTO_FIN = 0

# =====================================================================
# CONFIGURACIÓN DE REFRESH
# =====================================================================

# Intervalo de refresh en segundos (cuando está en horario de mercado)
REFRESH_INTERVAL_SECONDS = 10

# =====================================================================
# EJEMPLOS DE CONFIGURACIONES
# =====================================================================

# Ejemplo 1: Solo Lunes, Miércoles y Viernes de 9:00 a 18:00
# DIAS_HABILES = [0, 2, 4]
# HORA_INICIO = 9
# HORA_FIN = 18

# Ejemplo 2: Todos los días de 8:30 a 17:30
# DIAS_HABILES = [0, 1, 2, 3, 4, 5, 6]
# HORA_INICIO = 8
# MINUTO_INICIO = 30
# HORA_FIN = 17
# MINUTO_FIN = 30

# Ejemplo 3: Solo horario extendido (pre-apertura y post-cierre)
# HORA_INICIO = 8
# MINUTO_INICIO = 0
# HORA_FIN = 19
# MINUTO_FIN = 0

# Ejemplo 4: 24/7 (siempre activo)
# DIAS_HABILES = [0, 1, 2, 3, 4, 5, 6]
# HORA_INICIO = 0
# HORA_FIN = 23
# MINUTO_FIN = 59

# =====================================================================
# CONFIGURACIÓN AVANZADA: MÚLTIPLES HORARIOS
# =====================================================================

# Si necesitas múltiples ventanas horarias (ej: pre-market y market)
# Descomenta esta sección y modifica _is_market_hours() en dashboard_ratios_api.py

# HORARIOS_MERCADO = [
#     {
#         "nombre": "Pre-Market",
#         "dias": [0, 1, 2, 3, 4],
#         "hora_inicio": 8,
#         "minuto_inicio": 30,
#         "hora_fin": 10,
#         "minuto_fin": 0
#     },
#     {
#         "nombre": "Market",
#         "dias": [0, 1, 2, 3, 4],
#         "hora_inicio": 10,
#         "minuto_inicio": 0,
#         "hora_fin": 17,
#         "minuto_fin": 0
#     },
#     {
#         "nombre": "Post-Market",
#         "dias": [0, 1, 2, 3, 4],
#         "hora_inicio": 17,
#         "minuto_inicio": 0,
#         "hora_fin": 18,
#         "minuto_fin": 30
#     }
# ]

# =====================================================================
# FERIADOS (opcional)
# =====================================================================

# Lista de fechas (formato: "YYYY-MM-DD") en que NO se ejecuta el refresh
# Agregar feriados nacionales o días especiales sin mercado
FERIADOS = [
    # "2025-01-01",  # Año Nuevo
    # "2025-03-24",  # Día Nacional de la Memoria
    # "2025-04-02",  # Día del Veterano
    # "2025-05-01",  # Día del Trabajador
    # "2025-05-25",  # Día de la Revolución de Mayo
    # "2025-06-20",  # Día de la Bandera
    # "2025-07-09",  # Día de la Independencia
    # "2025-08-17",  # Aniversario de la muerte del Gral. San Martín
    # "2025-10-12",  # Día del Respeto a la Diversidad Cultural
    # "2025-11-20",  # Día de la Soberanía Nacional
    # "2025-12-08",  # Inmaculada Concepción de María
    # "2025-12-25",  # Navidad
]

# =====================================================================
# ZONA HORARIA
# =====================================================================

# Zona horaria para los cálculos
# Por defecto usa la zona horaria del sistema
# Si necesitas forzar una zona específica, descomenta:
# import pytz
# TIMEZONE = pytz.timezone('America/Argentina/Buenos_Aires')
TIMEZONE = None  # Usa zona horaria del sistema



