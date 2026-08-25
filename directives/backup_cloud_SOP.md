# SOP - Ús de Google Drive com a Base de Dades

Aquest procediment detalla com configurar l'aplicació per desar les dades al Google Drive, permetent tenir còpies de seguretat automàtiques i accés des de múltiples dispositius.

## 🚀 Passos per la Configuració

1. **Localitzar la Base de Dades**:
   - Per defecte, la base de dades és el fitxer `db/farm.db` (o a la carpeta on hagis definit al `.env`).

2. **Copiar al Drive**:
   - Copia el fitxer `farm.db` a una carpeta dins del teu Google Drive al teu ordinador (ex: `G:/La meva unitat/GestioAmetllers/farm.db`).

3. **Configurar el fitxer .env**:
   - Obre el fitxer `.env` que hi ha a la carpeta de l'aplicació (`dist/launcher`).
   - Modifica la línia `DB_PATH` amb la ruta completa del Drive:
     ```env
     DB_PATH=C:/Users/ElTeuUsuari/Google Drive/GestioAmetllers/farm.db
     ```
   - Desa el fitxer.

4. **Reiniciar l'aplicació**:
   - Tanca i torna a obrir el `launcher.exe`. Ara l'app llegirà i escriurà directament al Drive.

## ⚠️ Precaucions Crítiques (Important!)

> [!WARNING]
> **No obris l'aplicació en dos ordinadors alhora.**
> SQLite no està dissenyat per a l'ús simultani a través de serveis de núvol. Si fas canvis des de dos llocs simultàniament, Google Drive crearà "fitxers en conflicte" i podries perdre dades.

> [!TIP]
> **Sempre tanca el programa** quan acabis de fer-lo servir en un ordinador per assegurar-te que Google Drive acaba de pujar els canvis al núvol abans d'obrir-lo en un altre lloc.

## ✅ Avantatges
- **Còpies de seguretat**: Drive guarda versions anteriors del fitxer per si l'esborres per error.
- **Mobilitat**: Pots entrar les dades des del portàtil a casa i veure-les al sobretaula de l'oficina.
