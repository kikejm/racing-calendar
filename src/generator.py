import json
from datetime import timezone, timedelta
from dateutil import parser
from icalendar import Calendar, Event

def generate_ics(data_path, output_file):
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cal = Calendar()
    cal.add('prodid', '-//RacingManager//ES')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')

    for entry in data:
        base_title = entry['title']
        clean_title = base_title.replace("🏎️ ", "").replace("🏁 ", "").split(",")[0]
        icon = "🏎️" if "🏎️" in base_title else "🏁"
        desc = entry.get('description', '')

        # Lógica para sesiones detalladas (F1, GT World...)
        if 'sessions' in entry:
            for s in entry['sessions']:
                event = Event()
                # Forzamos UTC para mantener consistencia con el diseño anterior
                start = parser.parse(s['start']).replace(tzinfo=timezone.utc)
                end = parser.parse(s['end']).replace(tzinfo=timezone.utc)
                
                # UID consistente para evitar duplicados en actualizaciones
                uid_str = f"{base_title}_{s['name']}_{start.strftime('%Y%m%d')}".replace(' ', '_')
                
                event.add('summary', f"{icon} {s['name']} | {clean_title}")
                event.add('dtstart', start)
                event.add('dtend', end)
                event.add('description', desc)
                event.add('uid', f"{uid_str}@racing.com")
                
                cal.add_component(event)
        
        # Lógica para eventos de día completo
        else:
            event = Event()
            start = parser.parse(entry['start']).date()
            # RFC 5545: Eventos de día completo terminan el día siguiente al real
            end = parser.parse(entry['end']).date() + timedelta(days=1)
            
            uid_str = f"{base_title}_{start.strftime('%Y%m%d')}".replace(' ', '_')
            
            event.add('summary', base_title)
            event.add('dtstart', start)
            event.add('dtend', end)
            event.add('description', desc)
            event.add('uid', f"{uid_str}@racing.com")
            
            cal.add_component(event)

    # Escribir en binario (wb) ya que icalendar devuelve bytes codificados
    with open(output_file, 'wb') as f:
        f.write(cal.to_ical())

if __name__ == "__main__":
    generate_ics('data/schedule.json', 'racing_schedule.ics')