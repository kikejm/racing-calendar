import json
import logging
import sys
import argparse
from dataclasses import dataclass
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any, Union
from uuid import uuid5, NAMESPACE_DNS
from icalendar import Calendar, Event

# --- Constants ---
PROD_ID = '-//RacingManager//ES'
VERSION = '2.0'
# Namespace para UUIDv5 (puedes usar cualquier string de dominio que prefieras)
RACING_NAMESPACE = NAMESPACE_DNS 

@dataclass
class RacingEvent:
    """Representación normalizada de un evento."""
    summary: str
    start: Union[datetime, date]
    end: Union[datetime, date]
    description: str
    uid: str

class EventTransformer:
    def __init__(self):
        # Mantenemos los iconos del diseño original
        self.icons = {"F1": "🏎️", "GT": "🏁", "DEFAULT": "🏆"}

    def _clean_title(self, title: str) -> str:
        """Limpia iconos y corta por la primera coma."""
        for icon in self.icons.values():
            title = title.replace(icon, "")
        return title.split(",")[0].strip()

    def _parse_iso(self, date_str: str) -> datetime:
        dt = datetime.fromisoformat(date_str)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

    def _generate_uuid5(self, seed: str) -> str:
        """Genera un UUIDv5 basado en un string determinista."""
        return str(uuid5(RACING_NAMESPACE, seed))

    def process_entry(self, entry: Dict[str, Any]) -> List[RacingEvent]:
        events = []
        base_title = entry.get('title', 'Event')
        clean_title = self._clean_title(base_title)

        if "🏎️" in base_title:
            cat_key = "F1"
        elif "🏁" in base_title:
            cat_key = "GT"
        else:
            cat_key = "DEFAULT"
            
        icon = self.icons[cat_key]
        desc = entry.get('description', '')

        if 'sessions' in entry:
            for s in entry['sessions']:
                try:
                    start = self._parse_iso(s['start'])
                    end = self._parse_iso(s['end'])
                    # Seed para UUID: Título + Nombre Sesión + Fecha (sin hora para permitir mover la hora sin duplicar)
                    seed = f"{base_title}_{s['name']}_{start.strftime('%Y%m%d')}"
                    
                    events.append(RacingEvent(
                        summary=f"{icon} {s['name']} | {clean_title}",
                        start=start,
                        end=end,
                        description=desc,
                        uid=f"{self._generate_uuid5(seed)}@racing.com"
                    ))
                except Exception as e:
                    logging.error(f"Error en sesión de {base_title}: {e}")
        else:
            # Lógica para eventos de día completo
            try:
                start_d = self._parse_iso(entry['start']).date()
                end_d = self._parse_iso(entry['end']).date() + timedelta(days=1)
                seed = f"{base_title}_{start_d.strftime('%Y%m%d')}"
                
                events.append(RacingEvent(
                    summary=base_title,
                    start=start_d,
                    end=end_d,
                    description=desc,
                    uid=f"{self._generate_uuid5(seed)}@racing.com"
                ))
            except Exception as e:
                logging.error(f"Error en evento {base_title}: {e}")
        
        return events

def main():
    # Usamos valores por defecto en argparse para no romper GitHub Actions
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs='?', default="data/schedule.json")
    parser.add_argument("output", nargs='?', default="racing_schedule.ics")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    transformer = EventTransformer()
    
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cal = Calendar()
        cal.add('prodid', PROD_ID)
        cal.add('version', VERSION)

        for entry in data:
            for revent in transformer.process_entry(entry):
                event = Event()
                event.add('summary', revent.summary)
                event.add('dtstart', revent.start)
                event.add('dtend', revent.end)
                event.add('description', revent.description)
                event.add('uid', revent.uid)
                cal.add_component(event)

        with open(args.output, 'wb') as f:
            f.write(cal.to_ical())
        logging.info(f"Calendario generado con UUIDv5 en {args.output}")

    except Exception as e:
        logging.critical(f"Fallo total: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()