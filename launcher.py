import os
import sys
import threading
import webbrowser
import time
from scripts.app import app

def open_browser():
    # Esperem un moment a que el servidor estigui amunt
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    print("Iniciant Gestio Finca Ametllers...")
    
    # Inicialitzar base de dades si no existeix
    try:
        from scripts.database import init_db
        from scripts.app import seed_data
        print("Verificant/Inicialitzant base de dades...")
        init_db()
        seed_data()
    except Exception as e:
        print(f"Error inicialitzant DB: {e}")

    # Fil per obrir el navegador
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Executar Flask
    app.run(host="127.0.0.1", port=5000, debug=False)
