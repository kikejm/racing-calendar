# 🏎️ Racing Calendar Generator 2026
Este sistema automatizado genera y publica un calendario deportivo del motor en formato .ics (iCalendar), optimizado para dispositivos móviles y compatible con Google Calendar, Apple Calendar y Outlook.

Cubre las temporadas completas de F1 y GT World Challenge Europe 2026 (más próximamente).

## 📂 Estructura del Proyecto
* **`data/schedule.json`**: La base de datos central. Contiene las fechas, sesiones detalladas (P1, Qualy, Carrera) y canales de retransmisión.

* **`src/validate.py`**: Script de seguridad. Valida la sintaxis del JSON y el formato de fechas antes de procesar nada.

* **`src/generator.py`**: El motor del proyecto. Transforma los datos en eventos de calendario siguiendo el estándar RFC 5545.

* **`.github/workflows/update_calendar.yml`**: Automatización CI/CD. Ejecuta el generador y actualiza la web cada vez que detecta cambios.

## 🚀 Cómo usar este repositorio
1. Actualización de Datos
Para añadir o modificar una carrera, simplemente edita el archivo data/schedule.json. Al hacer push a la rama main, la GitHub Action validará los datos y actualizará el archivo público automáticamente.

2. Ejecución Local (Opcional)
Si quieres probar los cambios en tu ordenador:

```bash
pip install -r requirements.txt
python src/validate.py
python src/generator.py
```

## 🌐 Suscripción Automática (Recomendado)
No importes el archivo manualmente. Para tener las actualizaciones en tiempo real en tu móvil, añade el calendario por URL:

* Copia este enlace: https://github.com/kikejm/racing-calendar/racing_pro_2026.ics

* En Google Calendar, haz clic en el icono + junto a "Otros calendarios".

* Selecciona Desde URL y pega el enlace.

* Pulsa Añadir calendario.

## 🛠️ Detalles Técnicos y Análisis
### Optimización Visual (Mobile First)
El script limpia los títulos largos para evitar el truncamiento en pantallas pequeñas. Prioriza la sesión actual (ej: 🏎️ Qualy | GP España) en lugar de repetir el nombre completo del Gran Premio al inicio.

### Prevención de Duplicados
Cada evento posee un UID único basado en el nombre de la sesión y la fecha. Esto permite que, si un horario cambia, Google Calendar actualice el evento existente en lugar de crear uno repetido.

### Validación de Integridad
El paso de validación en el flujo de trabajo (validate.py) actúa como un cortafuegos. Si olvidas una coma o escribes mal una fecha en el JSON, la automatización se detendrá, protegiendo tu calendario de datos corruptos.

### ⚠️ Notas Importantes
Latencia: Google Calendar suele refrescar las suscripciones por URL cada 12-24 horas.

Zonas Horarias: Los horarios introducidos en el JSON se procesan como UTC por defecto para evitar discrepancias según donde te encuentres.
