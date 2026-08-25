# ChangeLog - gestion_finca

## [2026-04-07 23:56]

### Tipo de Cambio
- Creación

### Archivo(s) Afectado(s)
- directives/gestion_finca_SOP.md
- scripts/app.py
- scripts/database.py
- db/schemas/schema.sql
- templates/base.html
- templates/index.html

### Descripción Técnica
Creación inicial de la estructura de proyecto siguiendo las normativas globales. Configuración de Flask con rutas personalizadas apoyadas por base de datos en SQLite para el control de la finca agrícola.

### Motivo
Bootstrap y scaffolding del proyecto inicial según los requerimientos dictados en el prompt de la orden, para preparar la aplicación de campo que medirá rendimientos y gastos en la cosecha de almendras.

### Impacto Esperado
Establecer un esqueleto sólido de carpetas y bases de código, permitiendo posteriormente expandir fácilmente los diferentes endpoints para inserción de datos.

---

## [2026-04-08 00:05]

### Tipo de Cambio
- Modificació / Localització

### Archivo(s) Afectado(s)
- templates/base.html
- templates/index.html
- scripts/app.py

### Descripción Técnica
Traducció completa de la interfície d'usuari (front-end) al català. S'han actualitzat els títols, botons, etiquetes de les targetes i comentaris en el codi de les plantilles. S'ha ajustat la lògica interna del backend per mantenir coherència amb el benefici net.

### Motivo
Petició de l'usuari per disposar del programari en la seva llengua pròpia.

### Impacto Esperado
Millora de l'experiència d'usuari i facilitat d'ús per l'agricultor en el camp.

---

## [2026-04-08 00:10]

### Tipo de Cambio
- Funcionalitat / CRUD

### Archivo(s) Afectado(s)
- scripts/app.py
- templates/index.html
- templates/labor_form.html [NEW]
- templates/production_form.html [NEW]
- templates/expense_form.html [NEW]
- templates/history.html [NEW]

### Descripción Técnica
Implementació de tota la lògica CRUD per a les operacions de la finca. Backend en anglès amb rutes RESTful i gestió de base de datos SQLite. Front-end totalment en català amb formularis adaptatius i vista d'historial amb capacitat d'esborrament.

### Motivo
Activar els botons del dashboard que prèviament eren només visuals, convertint l'aplicació en una eina funcional de registre.

### Impacto Esperado
Possibilitat real de gestionar la finca des del mòbil, desant dades i consultant el resum econòmic en temps real.

---

## [2026-04-08 00:20]

### Tipo de Cambio
- Funcionalitat / Informes i Exportació

### Archivo(s) Afectado(s)
- scripts/app.py
- templates/reports.html [NEW]
- templates/index.html

### Descripción Técnica
Implementació de rutes d'informes estadístics (agrupació de despeses per tipus) i sistema d'exportació de dades a format CSV per a ús extern en Excel. S'han afegit els botons de descàrrega i la vista de resums al dashboard.

### Motivo
Complir amb els requeriments d'anàlisi de dades de l'agricultor i facilitar el trasllat d'informació a gestories o per a ús propi en fulls de càlcul.

### Impacto Esperado
Capacitat d'anàlisi de la rendibilitat per tipus de despesa i portabilitat total de la informació generada.

---

## [2026-04-08 00:25]

### Tipo de Cambio
- UI / UX / CRUD Avançat

### Archivo(s) Afectado(s)
- templates/base.html
- templates/history.html
- scripts/app.py
- templates/labor_form.html
- templates/production_form.html
- templates/expense_form.html

### Descripción Técnica
Implementació d'una barra de navegació persistent (Sticky Navbar) per a millorar la visibilitat de l'historial i tots els formularis ara tornen a funcionar correctament amb el model relacional.

### Motivo
Solucionar problemes de navegació reportats per l'usuari i completar el cicle CRUD per permetre la correcció d'errors en les dades introduïdes.

### Impacto Esperado
Navegació molt més intuïtiva i control total sobre les dades (Edició/Eliminació/Cerca).

---

## [2026-04-08 00:35]

### Tipo de Cambio
- Desplegament / UX

### Archivo(s) Afectado(s)
- run_finca.bat [NEW]

### Descripción Técnica
Creació d'un fitxer d'automatització script batch (.bat) per a entorns Windows. L'script gestiona l'activació de l'entorn virtual (si existeix), la instal·lació silenciosa de dependències, l'arrencada del servidor Flask i l'obertura automàtica de la URL al navegador predeterminat de l'usuari.

### Motivo
Facilitar l'ús de l'aplicació per a un perfil d'usuari no tècnic (agricultor), permetent l'execució amb un simple doble clic sense dependre de la línia de comandes.

### Impacto Esperado
Simplicitat total d'ús. L'aplicació se sent com un programari natiu de Windows per a l'usuari final.

---

## [2026-04-08 00:45]

### Tipo de Cambio
- Refactorització / Empaquetat Professional

### Archivo(s) Afectado(s)
- config.ini [NEW]
- scripts/config.py [NEW]
- scripts/database.py
- launcher.py [NEW]
- scripts/publish.py [NEW]

### Descripción Técnica
Desacoblament de la configuració de la base de dades mitjançant un fitxer `config.ini` extern. Implementació d'un script `launcher.py` que gestiona de forma concurrent l'arrencada del servidor i l'obertura del navegador. Creat un script `publish.py` per automatitzar la generació d'un binari `.exe` utilitzant PyInstaller, incloent totes les dependències i recursos (templates, esquemes).

### Motivo
Atendre la petició de l'usuari per a una solució més robusta i amigable (executable) i permetre la configuració personalitzada de la ruta de dades sense tocar el codi.

### Impacto Esperado
Capacitat de distribució del programari com una carpeta autònoma amb un executable, facilitant l'ús professional i la portabilitat.
