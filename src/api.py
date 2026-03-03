import json
import logging
import re
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import NAMESPACE_DNS, uuid5
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
        "NASCAR": "🏁",
        "MOTOGP": "🏍️",
        "DEFAULT": "🏆"
    }
    
    # Palabras clave para detectar categorías automáticamente.
    # ⚠️  ORDEN IMPORTA: NASCAR debe ir ANTES que F1 porque ambos usan el emoji 🏎️.
    CATEGORY_KEYWORDS: Dict[str, List[str]] = {
        "nascar": ["nascar", "cup series", "daytona 500", "brickyard", "southern 500"],
        "f1": ["🏎️", "formula 1", "f1", "grand prix"],
        "gt": ["🏁", "gt", "grand touring", "endurance"],
        "motogp": ["🏍️", "motogp", "moto gp"],
    }

    SESSION_ALIASES: Dict[str, List[str]] = {
        # ── Generic aliases (backward compatibility) ──────────────────────
        "practice":     ["p1", "p2", "p3", "fp1", "fp2", "fp3", "práctica",
                         "practica", "warm up", "warmup", "practice", "libres",
                         "free practice", "shakedown"],
        "qualifying":   ["qualy", "qualifying", "clasificación", "clasificacion"],
        # "sprint" and "sprint_qualy" handled specially in _is_session_match
        "sprint":       [],
        "sprint_qualy": [],
        "race":         ["carrera", "race", "grand prix"],
        # ── Specific — F1 ─────────────────────────────────────────────────
        "p1":           ["p1"],
        "p2":           ["p2"],
        "p3":           ["p3"],
        # ── Specific — GT / MotoGP ────────────────────────────────────────
        "fp1":          ["fp1", "free practice 1"],
        "fp2":          ["fp2", "free practice 2"],
        # ── Specific — MotoGP ─────────────────────────────────────────────
        "practica":     ["práctica", "practica"],
        "warmup":       ["warm up", "warmup"],
        "q1":           ["q1"],
        "q2":           ["q2"],
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

    def _determine_category(self, event: EventModel) -> str:
        title_lower = event.title.lower()
        # Check title keywords first (order of dict matters — nascar before f1)
        for cat, keywords in self.settings.CATEGORY_KEYWORDS.items():
            if any(k in title_lower for k in keywords):
                return cat
        # Fallback: check categories array from the event
        for cat_tag in event.categories:
            cat_lower = cat_tag.lower()
            if cat_lower in self.settings.CATEGORY_KEYWORDS:
                return cat_lower
        return "other"

    def _clean_title(self, title: str) -> str:
        """Elimina iconos del título usando el regex pre-compilado."""
        return self.settings.icon_regex.sub("", title).strip()

    def _is_session_match(self, session_name: str, requested_filters: Set[str]) -> bool:
        """
        Returns True if session_name matches any filter key.

        Matching strategy:
        - "sprint"       → contains 'sprint' AND does NOT contain 'qual'/'clasif'
        - "sprint_qualy" → contains 'sprint' AND contains 'qual' or 'clasif'
        - Everything else → word-boundary substring match (so "p1" won't hit "fp1")
        """
        name_lower = session_name.lower().strip()
        # Pad the session name with spaces for clean word-boundary checks
        padded_name = f" {name_lower} "

        for filter_key in requested_filters:
            # ── Sprint special cases ──────────────────────────────────────
            if filter_key == "sprint":
                if "sprint" in name_lower and "qual" not in name_lower and "clasif" not in name_lower:
                    return True
                continue

            if filter_key == "sprint_qualy":
                if "sprint" in name_lower and ("qual" in name_lower or "clasif" in name_lower):
                    return True
                continue

            # ── Normal word-boundary matching ─────────────────────────────
            aliases = self.settings.SESSION_ALIASES.get(filter_key, [filter_key])
            for alias in aliases:
                padded_alias = f" {alias} "
                # Match if alias is a whole word in the session name,
                # OR the entire session name equals the alias.
                if padded_alias in padded_name or name_lower == alias:
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
                           event_data: EventModel, session_name: str, is_all_day: bool = False, zone: Optional[ZoneInfo] = None,) -> Event:
        evt = Event()
        evt.add('summary', summary)

        if zone and isinstance(start, datetime):
            start = start.astimezone(zone)
        if zone and isinstance(end, datetime):
            end = end.astimezone(zone)

        evt.add('dtstart', start)
        
        if is_all_day and isinstance(end, date) and not isinstance(end, datetime):
             evt.add('dtend', end + timedelta(days=1))
        else:
            evt.add('dtend', end)

        desc_text = self._format_description(event_data, session_name, is_html=False)
        desc_html = self._format_description(event_data, session_name, is_html=True)
        evt.add('description', desc_text)
        evt.add('X-ALT-DESC', desc_html, parameters={'FMTTYPE': 'text/html'})

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

        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("description", f"Arranca: {summary}")
        alarm.add("trigger", timedelta(minutes=-15))
        evt.add_component(alarm)

        return evt

    def generate_calendar(
        self,
        events: List[EventModel],
        filter_cats: Optional[Set[str]] = None,
        filter_sessions: Optional[Set[str]] = None,        # generic fallback
        cat_session_filters: Optional[Dict[str, Set[str]]] = None,  # per-category
        target_tz: Optional[str] = None,
    ) -> Calendar:
        cal = Calendar()
        cal.add('prodid', '-//RacingManager//Dynamic//ES')
        cal.add('version', '2.0')
        cal.add('x-wr-calname', 'Racing Schedule')
        cal.add('x-published-ttl', 'PT1H')
        
        zone: Optional[ZoneInfo] = None
        if target_tz:
            try:
                zone = ZoneInfo(target_tz)
                cal.add('x-wr-timezone', target_tz)   # Google Calendar lo lee
                logger.info(f"Calendario generado en zona: {target_tz}")
            except (ZoneInfoNotFoundError, KeyError):
                logger.warning(f"Zona horaria desconocida '{target_tz}', usando UTC")

        for entry in events:
            category = self._determine_category(entry)
            if filter_cats and category not in filter_cats:
                continue

            # Per-category session filter takes precedence over the global one
            effective_sessions: Optional[Set[str]] = None
            if cat_session_filters:
                effective_sessions = cat_session_filters.get(category)
            if effective_sessions is None:
                effective_sessions = filter_sessions

            icon = self.settings.ICONS.get(category.upper(), self.settings.ICONS["DEFAULT"])
            clean_title = self._clean_title(entry.title)

            if entry.sessions:
                for session in entry.sessions:
                    if effective_sessions:
                        if not self._is_session_match(session.name, effective_sessions):
                            continue
                    
                    summary = f"{icon} {session.name} | {clean_title}"
                    seed = f"{entry.title}|{session.name}|{session.start.isoformat()}"
                    
                    evt = self._create_ical_event(seed, summary, session.start, session.end, entry, session.name, zone=zone)
                    cal.add_component(evt)

            elif entry.start and entry.end:
                # For events without sessions (e.g. NASCAR races), include when 'race'
                # is in the effective filter, or no filter is applied
                if effective_sessions and 'race' not in effective_sessions:
                    continue
                summary = f"{icon} {clean_title}"
                evt = self._create_ical_event(
                    f"{entry.title}|main", summary,
                    entry.start.date(), entry.end.date(),
                    entry, clean_title, is_all_day=True, zone=zone
                )
                cal.add_component(evt)

        return cal

# --- 4. Capa de Infraestructura (Carga de Datos) ---
class DataLoader:
    """Maneja la lectura de todos los archivos JSON del directorio de datos."""
    def __init__(self, settings: AppSettings):
        self.data_dir = settings.DATA_PATH.parent

    def load_events(self) -> List[EventModel]:
        events = []
        json_files = sorted(self.data_dir.glob("*.json"))
        
        if not json_files:
            logger.warning(f"No se encontraron archivos JSON en: {self.data_dir}")
            return []

        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                file_events = 0
                for item in data:
                    try:
                        events.append(EventModel(**item))
                        file_events += 1
                    except (ValueError, KeyError) as e:
                        logger.warning(f"Evento inválido en {json_file.name}: {e}")
                logger.info(f"Cargados {file_events} eventos desde {json_file.name}")
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error cargando {json_file}: {e}")
        
        return events

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
    settings = get_settings()
    logger.info(f"API Iniciada. Entorno: {settings.LOG_LEVEL}")
    if not settings.DATA_PATH.parent.exists():
        logger.warning(f"⚠️ Directorio de datos no encontrado: {settings.DATA_PATH.parent}")
    yield
    logger.info("API Detenida.")

app = FastAPI(
    title="Racing Calendar API",
    version="2.1.0",
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
    cats:           Optional[List[str]] = Query(None, description="Categorías: f1, gt, nascar, motogp"),
    sessions:       Optional[List[str]] = Query(None, description="Sesiones genéricas (compat): race, qualifying, practice, sprint"),
    # ── Per-category session filters (generated by the frontend) ──────────────
    f1_sessions:    Optional[List[str]] = Query(None, description="Sesiones F1: p1, p2, p3, sprint_qualy, qualifying, sprint, race"),
    gt_sessions:    Optional[List[str]] = Query(None, description="Sesiones GT: fp1, fp2, qualifying, race"),
    nascar_sessions:Optional[List[str]] = Query(None, description="Sesiones NASCAR: race"),
    motogp_sessions:Optional[List[str]] = Query(None, description="Sesiones MotoGP: fp1, fp2, practica, warmup, q1, q2, sprint, race"),
    tz:              Optional[str]       = Query(None, description="IANA timezone, e.g. Europe/Madrid"),
    loader:  DataLoader      = Depends(get_data_loader),
    service: CalendarService = Depends(get_calendar_service),
):
    """
    Endpoint principal. Retorna el archivo .ics para suscripción en Google Calendar/Outlook.

    Si se envían parámetros per-categoría (f1_sessions, motogp_sessions…) tienen
    prioridad sobre el parámetro genérico 'sessions'.
    """
    try:
        events = loader.load_events()

        cat_set     = {c.lower() for c in cats}     if cats     else None
        session_set = {s.lower() for s in sessions} if sessions else None

        # Build per-category session filter dict (only include categories that have params)
        _raw = {
            "f1":     f1_sessions,
            "gt":     gt_sessions,
            "nascar": nascar_sessions,
            "motogp": motogp_sessions,
        }
        cat_session_filters: Optional[Dict[str, Set[str]]] = {
            cat: {s.lower() for s in vals}
            for cat, vals in _raw.items()
            if vals is not None
        } or None

        calendar_obj = service.generate_calendar(
            events,
            filter_cats=cat_set,
            filter_sessions=session_set,
            cat_session_filters=cat_session_filters,
            target_tz=tz,
        )

        return Response(
            content=calendar_obj.to_ical(),
            media_type="text/calendar",
            headers={"Content-Disposition": "attachment; filename=racing_schedule.ics"},
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
    uvicorn.run(app, host="0.0.0.0", port=8080)