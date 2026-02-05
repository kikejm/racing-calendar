import json
import logging
import re
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import NAMESPACE_DNS, uuid5

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from icalendar import Alarm, Calendar, Event, vGeo
from pydantic import BaseModel, ConfigDict, Field, model_validator, computed_field
from pydantic_settings import BaseSettings

# --- 1. Configuración (Logging y Settings) ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("RacingCalendarAPI")

class AppSettings(BaseSettings):
    """
    Configuración centralizada.
    Puede sobreescribirse con variables de entorno (ej: APP_LOG_LEVEL=DEBUG).
    """
    DATA_PATH: Path = Path("data/schedule.json")
    LOG_LEVEL: str = "INFO"
    
    # Mapeo de categorías e iconos
    ICONS: Dict[str, str] = {
        "F1": "🏎️", 
        "GT": "🏁", 
        "DEFAULT": "🏆"
    }
    
    # Palabras clave para detectar categorías automáticamente
    CATEGORY_KEYWORDS: Dict[str, List[str]] = {
        "f1": ["🏎️", "formula 1", "f1", "grand prix"],
        "gt": ["🏁", "gt", "grand touring", "endurance"]
    }

    SESSION_ALIASES: Dict[str, List[str]] = {
        "practice": ["p1", "p2", "p3", "practice", "libres", "entrenamientos", "shakedown"],
        "qualifying": ["qualy", "qualifying", "clasificación", "pole", "pre-qualifying"],
        "sprint": ["sprint"],
        "race": ["carrera", "race", "grand prix"]
    }

    model_config = ConfigDict(env_prefix="APP_")

    @computed_field
    def icon_regex(self) -> re.Pattern:
        """
        Compila el regex una sola vez al iniciar la configuración.
        """
        escaped_icons = [re.escape(icon) for icon in self.ICONS.values()]
        return re.compile("|".join(escaped_icons))

# --- 2. Modelos de Dominio (Pydantic) ---
class TimeAwareModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, frozen=True)

    def ensure_utc(self, dt: datetime) -> datetime:
        """Garantiza que el datetime tenga zona horaria UTC."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

class SessionModel(TimeAwareModel):
    name: str
    start: datetime
    end: datetime

    @model_validator(mode='after')
    def validate_session(self) -> 'SessionModel':
        # Normalización forzada a UTC
        # Nota: En Pydantic v2, modificamos los campos directamente si el modelo no fuera frozen,
        # pero al ser frozen, Pydantic maneja la validación durante la instanciación.
        # Aquí validamos la lógica.
        if self.start >= self.end:
            raise ValueError(f"La sesión '{self.name}' tiene duración inválida (Start >= End).")
        return self

class EventModel(TimeAwareModel):
    title: str
    description: str = ""
    location: Optional[str] = None
    geo_lat: Optional[float] = None
    geo_lon: Optional[float] = None
    url: Optional[str] = None
    broadcasters: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    status: str = "CONFIRMED"
    priority: int = 0
    sequence: int = 0
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    sessions: List[SessionModel] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_event(self) -> 'EventModel':
        # Validación de consistencia
        if not self.sessions and (not self.start or not self.end):
            raise ValueError("El evento requiere sesiones definidas o fechas start/end globales.")

        if self.start and self.end:
            if self.start >= self.end:
                raise ValueError(f"El evento '{self.title}' termina antes de empezar.")
        return self

# --- 3. Capa de Servicio (Lógica de Negocio) ---
class CalendarService:
    """
    Genera objetos iCalendar basados en los modelos de dominio.
    Agnóstico de FastAPI o de la fuente de datos.
    """
    def __init__(self, settings: AppSettings):
        self.settings = settings

    def _determine_category(self, title: str) -> str:
        title_lower = title.lower()
        for cat, keywords in self.settings.CATEGORY_KEYWORDS.items():
            if any(k in title_lower for k in keywords):
                return cat
        return "other"

    def _clean_title(self, title: str) -> str:
        """Elimina iconos del título usando el regex pre-compilado."""
        return self.settings.icon_regex.sub("", title).strip()

    def _is_session_match(self, session_name: str, requested_filters: Set[str]) -> bool:
        """
        Comprueba si el nombre de la sesión (ej: 'Carrera') coincide con 
        alguno de los filtros solicitados (ej: 'race').
        """
        name_lower = session_name.lower()
        
        for filter_key in requested_filters:
            # Obtener alias válidos para este filtro (ej: para 'race' -> ['carrera', 'race', ...])
            # Si el filtro no está en el mapa, usamos la propia palabra clave
            valid_aliases = self.settings.SESSION_ALIASES.get(filter_key, [filter_key])
            
            # Si ALGUNO de los alias está en el nombre de la sesión, es match
            if any(alias in name_lower for alias in valid_aliases):
                return True
                
        return False

    def _format_description(self, event: EventModel, session_name: str, is_html: bool = False) -> str:
        lines = []
        if is_html:
            lines.append(f"<b>{session_name}</b><br>")
            if event.broadcasters:
                lines.append(f"📺 <b>TV:</b> {', '.join(event.broadcasters)}<br>")
            if event.location:
                lines.append(f"📍 {event.location}<br>")
            if event.url:
                lines.append(f"🔗 <a href='{event.url}'>Info Oficial</a><br>")
            if event.description:
                lines.append(f"<br><i>{event.description}</i>")
            return "".join(lines)
        else:
            lines.append(session_name)
            if event.broadcasters:
                lines.append(f"📺 TV: {', '.join(event.broadcasters)}")
            if event.location:
                lines.append(f"📍 {event.location}")
            if event.url:
                lines.append(f"🔗 {event.url}")
            if event.description:
                lines.append(f"\n{event.description}")
            return "\n".join(lines)

    def _create_ical_event(self, uid_seed: str, summary: str, start: datetime | date, end: datetime | date, 
                           event_data: EventModel, session_name: str, is_all_day: bool = False) -> Event:
        evt = Event()
        evt.add('summary', summary)
        evt.add('dtstart', start)
        
        if is_all_day and isinstance(end, date) and not isinstance(end, datetime):
             evt.add('dtend', end + timedelta(days=1))
        else:
            evt.add('dtend', end)

        # Descripciones (Texto plano + HTML)
        desc_text = self._format_description(event_data, session_name, is_html=False)
        desc_html = self._format_description(event_data, session_name, is_html=True)
        evt.add('description', desc_text)
        evt.add('X-ALT-DESC', desc_html, parameters={'FMTTYPE': 'text/html'})

        # Metadatos extendidos
        if event_data.location:
            evt.add('location', event_data.location)
        if event_data.geo_lat is not None and event_data.geo_lon is not None:
            evt.add('geo', vGeo((event_data.geo_lat, event_data.geo_lon)))
        if event_data.url:
            evt.add('url', event_data.url)
        if event_data.categories:
            evt.add('categories', event_data.categories)
            
        evt.add('priority', event_data.priority)
        evt.add('status', event_data.status)
        evt.add('sequence', event_data.sequence)
        evt.add('transp', 'TRANSPARENT')
        
        evt.add('dtstamp', datetime.now(timezone.utc))
        uid = f"{uuid5(NAMESPACE_DNS, uid_seed)}@racing-manager.com"
        evt.add('uid', uid)

        # Alarma (Notificación 15 min antes)
        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", f"Arranca: {summary}")
        alarm.add("trigger", timedelta(minutes=-15))
        evt.add_component(alarm)

        return evt

    def generate_calendar(self, events: List[EventModel], filter_cats: Optional[Set[str]] = None, filter_sessions: Optional[Set[str]] = None) -> Calendar:
        cal = Calendar()
        cal.add('prodid', '-//RacingManager//Dynamic//ES')
        cal.add('version', '2.0')
        cal.add('x-wr-calname', 'Racing Schedule')
        cal.add('x-published-ttl', 'PT1H')

        for entry in events:
            category = self._determine_category(entry.title)
            if filter_cats and category not in filter_cats:
                continue

            icon = self.settings.ICONS.get(category.upper(), self.settings.ICONS["DEFAULT"])
            clean_title = self._clean_title(entry.title)

            if entry.sessions:
                for session in entry.sessions:
                    if filter_sessions:
                        if not self._is_session_match(session.name, filter_sessions):
                            continue
                    
                    summary = f"{icon} {session.name} | {clean_title}"
                    seed = f"{entry.title}|{session.name}|{session.start.isoformat()}"
                    
                    evt = self._create_ical_event(seed, summary, session.start, session.end, entry, session.name)
                    cal.add_component(evt)

            elif entry.start and entry.end:
                if filter_sessions: 
                    continue
                summary = f"{icon} {clean_title}"
                evt = self._create_ical_event(f"{entry.title}|main", summary, entry.start.date(), entry.end.date(), 
                                            entry, clean_title, is_all_day=True)
                cal.add_component(evt)

        return cal

# --- 4. Capa de Infraestructura (Carga de Datos) ---
class DataLoader:
    """Maneja la lectura del archivo JSON."""
    def __init__(self, settings: AppSettings):
        self.path = settings.DATA_PATH

    def load_events(self) -> List[EventModel]:
        if not self.path.exists():
            return []
        
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return [EventModel(**item) for item in data]
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error cargando datos: {e}")
            return []

# --- 5. Inyección de Dependencias ---
@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()

def get_data_loader(settings: AppSettings = Depends(get_settings)) -> DataLoader:
    return DataLoader(settings)

def get_calendar_service(settings: AppSettings = Depends(get_settings)) -> CalendarService:
    return CalendarService(settings)

# --- 6. Aplicación Web (FastAPI) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicio
    settings = get_settings()
    logger.info(f"API Iniciada. Entorno: {settings.LOG_LEVEL}")
    if not settings.DATA_PATH.exists():
        logger.warning(f"⚠️ Archivo de datos no encontrado: {settings.DATA_PATH}")
    yield
    # Cierre
    logger.info("API Detenida.")

app = FastAPI(
    title="Racing Calendar API",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/calendar.ics", tags=["Calendar"])
async def get_calendar_ics(
    cats: Optional[List[str]] = Query(None, description="Filtro categorías: f1, gt"),
    sessions: Optional[List[str]] = Query(None, description="Filtro sesiones: race, qualy"),
    loader: DataLoader = Depends(get_data_loader),
    service: CalendarService = Depends(get_calendar_service)
):
    """
    Endpoint principal. Retorna el archivo .ics para suscripción en Google Calendar/Outlook.
    """
    try:
        events = loader.load_events()
        
        # Normalizar filtros a Sets para búsqueda O(1)
        cat_set = set(c.lower() for c in cats) if cats else None
        session_set = set(s.lower() for s in sessions) if sessions else None

        calendar_obj = service.generate_calendar(events, cat_set, session_set)
        
        return Response(
            content=calendar_obj.to_ical(), 
            media_type="text/calendar",
            headers={"Content-Disposition": "attachment; filename=racing_schedule.ics"}
        )
    except Exception as e:
        logger.error(f"Error fatal: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc)}

app.mount("/data", StaticFiles(directory="data"), name="data")
app.mount("/", StaticFiles(directory="public", html=True), name="static")

if __name__ == "__main__":
    # Ejecución directa para desarrollo
    uvicorn.run(app, host="0.0.0.0", port=8080)