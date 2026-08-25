# Directiva - Gestión de Almendros (Almond Farm Manager)

## Objetivo
Desarrollar una aplicación web sencilla en Python (Flask) y bases de datos (SQLite) que actúe como un Cuaderno de Explotación económico y de tareas de campo para una finca de 7 hectáreas de almendros en regadío. El sistema debe estar orientado al agricultor: usable en el móvil, rápido y sin terminología técnica enrevesada.

## Flujo Lógico y Funcionalidades
1. **Labores**: Fecha | Trabajador | Horas | Precio/Hora | Total | Descripción.
2. **Producción/Venta**: Fecha | Kilos | Precio/Kg | Total | Comprador.
3. **Resto de Gastos**: Fecha | Tipo (Abono, Riego, Averías, Fitosanitarios) | Descripción | Importe.
4. **Informes**: Dashboard simple de Ingresos - Gastos = Beneficios.

## Salidas y Entregables
- Scripts idempotentes y robustos.
- Ejecución alojada en `scripts/app.py`.
- Lógica de persistencia en `db/`.

## Restricciones y Casos Borde
- (Ninguno registrado en la etapa inicial)
