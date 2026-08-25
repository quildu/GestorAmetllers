import os
import subprocess
import sys

def publish():
    print("Iniciant proces d'empaquetat (Publish)...")
    
    # 1. Intentar tancar el llançador si està obert (per evitar bloqueig de fitxers)
    print("Verificant que no hi hagi instancies de 'launcher.exe' actives...")
    try:
        if os.name == 'nt':
            # Només matem el launcher.exe, NO el python.exe (perquè ens matariem a nosaltres mateixos)
            subprocess.run(["taskkill", "/F", "/IM", "launcher.exe", "/T"], capture_output=True)
    except:
        pass

    # 2. Instal·lar PyInstaller si no hi es
    try:
        import PyInstaller
    except ImportError:
        print("Instal·lant PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 3. Comanda de PyInstaller a traves de python per evitar errors de PATH a Windows
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--console", 
        "--add-data", "templates;templates",
        "--add-data", "db/schemas;db/schemas",
        "launcher.py"
    ]
    
    subprocess.check_call(cmd)
    
    # 4. Copiar fitxers de configuració perquè siguin visibles i editables pel usuari
    print("Copiant fitxers de configuració a la carpeta de distribució...")
    import shutil
    dist_dir = os.path.join("dist", "launcher")
    
    if os.path.exists(".env"):
        shutil.copy(".env", dist_dir)
        print(f"Fitxer .env copiat a {dist_dir}")

    print("\n✅ PUBLICACIÓ FINALITZADA AMB ÈXIT!")
    print(f"Trobaràs l'aplicació a: {os.path.abspath(dist_dir)}")
    print("Pots editar el fitxer .env d'aquella carpeta per canviar la ruta de la base de dades.")
    
    print("\n" + "="*50)
    echo = "FET! L'aplicacio es a la carpeta 'dist/launcher'"
    print(echo)
    print("Recorda copiar la carpeta 'db' si tens dades existents.")
    print("="*50)

if __name__ == "__main__":
    publish()
