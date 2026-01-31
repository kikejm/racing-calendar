import json
from datetime import datetime, timedelta
from dateutil import parser

def format_dt(dt):
    return dt.strftime('%Y%m%dT%H%M%SZ')

def generate_ics(data_path, output_file):
    with open(data_path, 'r', encoding='utf-8') as f:
        events = json.load(f)

    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//RacingManager//ES", "CALSCALE:GREGORIAN"]

    for event in events:
        desc = event.get('description', '')
        
        if 'sessions' in event:
            for s in event['sessions']:
                start = parser.parse(s['start'])
                end = parser.parse(s['end'])
                uid = f"{event['title']}_{s['name']}_{start.strftime('%Y%m%d')}".replace(' ', '_')
                clean_title = event['title'].replace("🏎️ ", "").replace("🏁 ", "").split(",")[0]
                icon = "🏎️" if "🏎️" in event['title'] else "🏁"
                
                lines.extend([
                    "BEGIN:VEVENT",
                    f"SUMMARY:{icon} {s['name']} | {clean_title}",
                    f"DTSTART:{format_dt(start)}",
                    f"DTEND:{format_dt(end)}",
                    f"DESCRIPTION:{desc}",
                    f"UID:{uid}@racing.com",
                    "END:VEVENT"
                ])
        else:
            start = parser.parse(event['start'])
            end = parser.parse(event['end']) + timedelta(days=1)
            uid = f"{event['title']}_{start.strftime('%Y%m%d')}".replace(' ', '_')
            
            lines.extend([
                "BEGIN:VEVENT",
                f"SUMMARY:{event['title']}",
                f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
                f"DESCRIPTION:{desc}",
                f"UID:{uid}@racing.com",
                "END:VEVENT"
            ])

    lines.append("END:VCALENDAR")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))

if __name__ == "__main__":
    generate_ics('data/schedule.json', 'racing_schedule.ics')