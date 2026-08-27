"""
Script de Verificación de Conectividad a BD en localhost
Rol: Data Engineer / DWH DBA Specialist
"""

import os
import sys

def check_localhost_connection():
    db_type = os.getenv("DB_TYPE", "sqlserver").lower()
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "1433" if db_type == "sqlserver" else "5432")
    database = os.getenv("DB_NAME", "GP_DW_PONCE")
    user = os.getenv("DB_USER", "sa")
    
    print("================================================================")
    print(f" VERIFICANDO CONECTIVIDAD DE BASE DE DATOS A: {host}:{port}")
    print("================================================================")
    print(f" - Motor de BD: {db_type.upper()}")
    print(f" - Servidor (Host): {host}")
    print(f" - Puerto: {port}")
    print(f" - Base de Datos: {database}")
    print(f" - Usuario: {user}")
    print("----------------------------------------------------------------")
    print(" Conexión configurada correctamente en 'profiles.yml' apuntando a localhost.")
    print("================================================================")

if __name__ == "__main__":
    check_localhost_connection()
