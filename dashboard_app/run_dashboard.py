"""
Lanzador del Dashboard Web Dinámico de Clientes, Ventas e Inventarios (Grupo Ponce)
Servidor configurado en: http://localhost:8000
"""

import os
import sys
import webbrowser
import time

def main():
    print("=================================================================")
    print(" INICIANDO DASHBOARD WEB DINÁMICO: GRUPO PONCE (DATA MARTS)")
    print(" Módulos: Ventas, Clientes, Churn, LTV e Inventarios")
    print("=================================================================")
    print(" Servidor Backend: FastAPI / Uvicorn (Recarga Activa)")
    print(" Conexión BD: localhost (SQL Server: PB + DYNAMICS)")
    print(" URL de Acceso: http://localhost:8000")
    print("=================================================================")

    app_dir = os.path.join(os.path.dirname(__file__), "backend")
    sys.path.insert(0, app_dir)
    
    import uvicorn

    # Abrir navegador tras 1.5 segundos
    import threading
    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://localhost:8000")

    threading.Thread(target=open_browser, daemon=True).start()
    
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False, app_dir=app_dir)

if __name__ == "__main__":
    main()
