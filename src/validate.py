import json
from datetime import datetime
from dateutil import parser
import sys

def validate_schedule(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for i, event in enumerate(data):
            if 'title' not in event or 'description' not in event:
                raise ValueError(f"Error en evento {i}: Faltan campos obligatorios (title/description)")
            
            if 'sessions' in event:
                for s in event['sessions']:
                    parser.parse(s['start'])
                    parser.parse(s['end'])
            else:
                if 'start' not in event or 'end' not in event:
                    raise ValueError(f"Error en evento {i}: No hay sesiones ni fechas de día completo")
                parser.parse(event['start'])
                parser.parse(event['end'])
        
        print("✅ JSON validado correctamente.")
    except Exception as e:
        print(f"❌ Error de validación: {e}")
        sys.exit(1)

if __name__ == "__main__":
    validate_schedule('data/schedule.json')