# ─────────────────────────────────────────────────────────────────────────────
#  NOBEL · 125 años de ideas que cambiaron el mundo
#  Dashboard en Streamlit con datos oficiales de la Fundación Nobel
#  Fuente de datos: API oficial de nobelprize.org (v2.1)
#  Imágenes: Wikipedia / Wikimedia Commons
# ─────────────────────────────────────────────────────────────────────────────

import html as htmllib
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from urllib.parse import quote

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ── Configuración general ────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nobel · 125 años de ideas",
    page_icon="🏅",
    layout="wide",
    initial_sidebar_state="collapsed",
)

API_URL = "https://api.nobelprize.org/2.1/laureates"
WIKI_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
HEADERS = {"User-Agent": "NobelDashboard/1.0 (proyecto educativo en Streamlit)"}
CURRENT_YEAR = date.today().year

# Paleta
BG, SURFACE, INK, MUTED, LINE = "#F7F4EC", "#FFFFFF", "#1B1A17", "#6B675E", "#E4DED0"
GOLD, GOLD_DEEP, NAVY = "#B08D3C", "#8A6A22", "#16202E"

CATEGORIES = {
    # clave API: (nombre, ícono, color, institución, año inicial, descripción)
    "Physics": ("Física", "⚛", "#3A5A8C", "Real Academia Sueca de Ciencias", 1901,
                "Descubrimientos que cambiaron la forma de entender la materia, la energía y el universo."),
    "Chemistry": ("Química", "⚗", "#2E7D6B", "Real Academia Sueca de Ciencias", 1901,
                  "Avances en la composición de la materia y en la creación de nuevas moléculas y materiales."),
    "Physiology or Medicine": ("Medicina", "⚕", "#B5473A", "Asamblea Nobel del Instituto Karolinska", 1901,
                               "Hallazgos sobre el funcionamiento del cuerpo humano y la lucha contra las enfermedades."),
    "Literature": ("Literatura", "✒", "#7A4E9C", "Academia Sueca", 1901,
                   "Para la obra más destacada en una dirección ideal, según el testamento de Nobel."),
    "Peace": ("Paz", "☮", "#C9A227", "Comité Noruego del Nobel", 1901,
              "Para quien más haya hecho por la fraternidad entre las naciones y la promoción de la paz."),
    "Economic Sciences": ("Economía", "∑", "#5C6B73", "Real Academia Sueca de Ciencias", 1969,
                          "Creado en 1968 por el Banco Central de Suecia en memoria de Nobel. Se entrega desde 1969."),
}
CAT_ORDER = [v[0] for v in CATEGORIES.values()]
CAT_COLOR = {v[0]: v[2] for v in CATEGORIES.values()}
SCIENCES = ["Física", "Química", "Medicina", "Economía"]

# ── Estilos ──────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,700;1,500&family=Inter:wght@400;500;600&display=swap');
:root {{ --bg:{BG}; --surface:{SURFACE}; --ink:{INK}; --muted:{MUTED}; --line:{LINE}; --gold:{GOLD}; --gold-deep:{GOLD_DEEP}; --navy:{NAVY}; }}
.stApp {{ background: var(--bg); }}
[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer {{ visibility: hidden; }}
.block-container {{ max-width: 1180px; padding-top: 1.2rem; padding-bottom: 4rem; }}
html, body, .stApp, .stApp p, .stApp li, .stApp label, .stMarkdown {{ font-family: 'Inter', sans-serif; color: var(--ink); }}
h1, h2, h3, .serif {{ font-family: 'Playfair Display', serif !important; color: var(--ink); letter-spacing: -0.01em; }}

/* Tabs */
[role="tablist"] {{ gap: 6px; border-bottom: 1px solid var(--line); flex-wrap: wrap; }}
[role="tab"] {{ font-family: 'Inter', sans-serif; font-weight: 500; padding: 10px 14px; background: transparent; }}
[role="tab"] p {{ color: var(--muted) !important; font-size: 15px; }}
[role="tab"][aria-selected="true"] p {{ color: var(--ink) !important; font-weight: 600; }}
[data-baseweb="tab-highlight"], .react-aria-SelectionIndicator {{ background-color: var(--gold) !important; }}
[data-baseweb="tab-border"] {{ display: none; }}

/* Inputs */
[data-baseweb="select"] > div, [data-baseweb="input"] > div, .stTextInput input {{ background: var(--surface) !important; color: var(--ink) !important; border-color: var(--line) !important; }}
[data-testid="stSlider"] [role="slider"] {{ background: var(--gold) !important; box-shadow: none !important; }}

/* Hero */
.hero {{ position: relative; overflow: hidden; border-radius: 22px; padding: 64px 56px 52px;
  background: radial-gradient(1200px 400px at 85% -20%, rgba(176,141,60,.35), transparent 60%), linear-gradient(135deg, #16202E 0%, #1F2C3F 100%);
  color: #F4EFE3; margin-bottom: 28px; }}
.hero .kicker {{ font-size: 12px; letter-spacing: .22em; text-transform: uppercase; color: #D9BF7A; font-weight: 600; }}
.hero h1 {{ color: #FBF7EE !important; font-size: clamp(38px, 6vw, 68px); line-height: 1.02; margin: 14px 0 16px; font-weight: 700; }}
.hero h1 em {{ color: #D9BF7A; font-style: italic; font-weight: 500; }}
.hero p {{ color: #CFC8B8 !important; font-size: 17px; max-width: 640px; line-height: 1.6; margin: 0; }}
.hero .ring {{ position: absolute; right: -60px; top: 50%; transform: translateY(-50%); width: 340px; height: 340px; border-radius: 50%;
  border: 1px solid rgba(217,191,122,.35); box-shadow: 0 0 0 28px rgba(217,191,122,.06), 0 0 0 56px rgba(217,191,122,.04); }}
@media (max-width: 760px) {{ .hero {{ padding: 40px 24px; }} .hero .ring {{ display: none; }} }}

/* Encabezados de sección */
.sec {{ margin: 44px 0 18px; }}
.sec .k {{ font-size: 11.5px; letter-spacing: .2em; text-transform: uppercase; color: var(--gold-deep); font-weight: 600; }}
.sec h2 {{ font-size: clamp(26px, 3.2vw, 36px); margin: 6px 0 6px; font-weight: 700; }}
.sec p {{ color: var(--muted) !important; max-width: 720px; margin: 0; line-height: 1.6; }}

/* KPIs */
.kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; }}
.kpi {{ background: var(--surface); border: 1px solid var(--line); border-radius: 16px; padding: 18px 20px; }}
.kpi .v {{ font-family: 'Playfair Display', serif; font-size: 34px; font-weight: 700; line-height: 1; }}
.kpi .l {{ font-size: 13px; color: var(--muted); margin-top: 8px; }}

/* Tarjetas */
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 18px; }}
.grid-2 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; }}
.card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 18px; padding: 22px; height: 100%;
  transition: transform .2s ease, box-shadow .2s ease; }}
.card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 30px rgba(27,26,23,.07); }}
.card h3 {{ font-size: 21px; margin: 0 0 6px; font-weight: 700; }}
.card p {{ font-size: 14.5px; line-height: 1.6; color: #3E3B35 !important; margin: 8px 0 0; }}
.card .meta {{ font-size: 12.5px; color: var(--muted); }}
.pill {{ display: inline-block; font-size: 11.5px; font-weight: 600; letter-spacing: .04em; padding: 4px 10px; border-radius: 999px; margin: 0 6px 6px 0; }}
.icon {{ width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 22px; margin-bottom: 14px; }}
.stat-row {{ display: flex; gap: 22px; margin-top: 14px; padding-top: 14px; border-top: 1px solid var(--line); }}
.stat-row b {{ font-family: 'Playfair Display', serif; font-size: 20px; display: block; }}
.stat-row span {{ font-size: 12px; color: var(--muted); }}

/* Retratos */
.person {{ display: flex; gap: 16px; align-items: flex-start; }}
.avatar {{ width: 76px; height: 92px; border-radius: 12px; object-fit: cover; object-position: top; flex-shrink: 0; background: #EFE9DC; filter: grayscale(15%); }}
.avatar.mono {{ display: flex; align-items: center; justify-content: center; font-family: 'Playfair Display', serif; font-size: 26px; color: var(--gold-deep); }}

/* Texto editorial */
.prose p {{ font-size: 16.5px; line-height: 1.75; color: #34312C !important; margin: 0 0 14px; }}
.prose p:first-child::first-letter {{ font-family: 'Playfair Display', serif; float: left; font-size: 64px; line-height: .9; padding: 6px 10px 0 0; color: var(--gold-deep); }}
.quote {{ border-left: 3px solid var(--gold); padding: 6px 0 6px 18px; font-family: 'Playfair Display', serif; font-style: italic; font-size: 20px; color: var(--ink); margin: 18px 0; }}
.facts {{ list-style: none; padding: 0; margin: 0; }}
.facts li {{ display: flex; justify-content: space-between; gap: 16px; padding: 11px 0; border-bottom: 1px solid var(--line); font-size: 14.5px; }}
.facts li span:first-child {{ color: var(--muted); }}
.facts li span:last-child {{ text-align: right; font-weight: 500; }}

/* Medalla */
.medal-wrap {{ display: flex; justify-content: center; align-items: center; padding: 10px 0 18px; }}
.medal-photo {{ width: 230px; height: 230px; border-radius: 50%; object-fit: cover; box-shadow: 0 18px 40px rgba(138,106,34,.28); }}
.medal-css {{ width: 220px; height: 220px; border-radius: 50%; display: flex; flex-direction: column; align-items: center; justify-content: center;
  background: radial-gradient(circle at 35% 30%, #F6E3A6 0%, #D9B45A 35%, #A9822F 70%, #7A5A1C 100%);
  box-shadow: inset 0 0 0 10px rgba(255,255,255,.18), inset 0 0 0 12px rgba(122,90,28,.5), 0 18px 40px rgba(138,106,34,.3);
  color: #4A3610; font-family: 'Playfair Display', serif; text-align: center; }}
.medal-css b {{ font-size: 24px; letter-spacing: .12em; }}
.medal-css span {{ font-size: 12px; letter-spacing: .2em; margin-top: 6px; }}
.caption {{ font-size: 12px; color: var(--muted); text-align: center; }}

/* Línea de tiempo */
.tl {{ position: relative; margin: 8px 0 0 8px; padding-left: 34px; border-left: 2px solid var(--line); }}
.tl-item {{ position: relative; padding: 0 0 26px; }}
.tl-item::before {{ content: ""; position: absolute; left: -43px; top: 4px; width: 14px; height: 14px; border-radius: 50%; background: var(--bg); border: 3px solid var(--gold); }}
.tl-item.big::before {{ background: var(--gold); }}
.tl-year {{ font-family: 'Playfair Display', serif; font-size: 22px; font-weight: 700; color: var(--gold-deep); line-height: 1; }}
.tl-title {{ font-weight: 600; margin: 6px 0 2px; font-size: 15.5px; }}
.tl-text {{ font-size: 14.5px; color: #4A463F; line-height: 1.55; max-width: 760px; }}

/* Bloque editorial oscuro */
.dark {{ background: var(--navy); color: #EDE6D6; border-radius: 18px; padding: 26px 28px; }}
.dark h3 {{ color: #FBF7EE !important; font-size: 22px; margin: 0 0 6px; }}
.dark p, .dark li {{ color: #CFC8B8 !important; font-size: 14.5px; line-height: 1.6; }}

.notice {{ background: #FFF8E6; border: 1px solid #EBD9A4; border-radius: 14px; padding: 14px 18px; font-size: 14px; color: #5C4813; }}
.footer {{ margin-top: 60px; padding-top: 22px; border-top: 1px solid var(--line); font-size: 12.5px; color: var(--muted); line-height: 1.7; }}
.footer a {{ color: var(--gold-deep); }}
</style>
""", unsafe_allow_html=True)


# ── Helpers de render ────────────────────────────────────────────────────────
def render(block: str) -> None:
    """Renderiza HTML sin que Markdown lo rompa (sin sangrías ni líneas vacías)."""
    lines = [ln.strip() for ln in block.strip().splitlines()]
    st.markdown("\n".join(ln for ln in lines if ln), unsafe_allow_html=True)


def fmt(n) -> str:
    """Miles con punto, al estilo argentino."""
    return f"{int(n):,}".replace(",", ".")


def chart_title(text: str) -> None:
    render(f'<div class="serif" style="font-size:18px;font-weight:700;margin:4px 0 -4px">{text}</div>')


def esc(text) -> str:
    return htmllib.escape(str(text)) if text is not None else ""


def section(kicker: str, title: str, subtitle: str = "") -> None:
    sub = f"<p>{subtitle}</p>" if subtitle else ""
    render(f'<div class="sec"><div class="k">{kicker}</div><h2>{title}</h2>{sub}</div>')


def pill(text: str, color: str) -> str:
    return f'<span class="pill" style="background:{color}1A;color:{color};">{esc(text)}</span>'


def avatar(img: str | None, name: str) -> str:
    if img:
        return f'<img class="avatar" src="{esc(img)}" alt="{esc(name)}" loading="lazy">'
    initials = "".join(w[0] for w in name.split()[:2]).upper()
    return f'<div class="avatar mono">{esc(initials)}</div>'


def polish(fig, height: int = 380, legend: bool = True):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=24, t=30, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=13, color=INK),
        hoverlabel=dict(bgcolor=SURFACE, bordercolor=LINE, font=dict(family="Inter, sans-serif", color=INK)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None, font=dict(color=MUTED)),
        showlegend=legend,
    )
    fig.update_xaxes(automargin=True, title_text=None, showgrid=False, linecolor=LINE, tickfont=dict(color=MUTED), title_font=dict(color=MUTED))
    fig.update_yaxes(automargin=True, title_text=None, gridcolor="#ECE6D8", zeroline=False, linecolor=LINE, tickfont=dict(color=MUTED), title_font=dict(color=MUTED))
    return fig


def show(fig) -> None:
    st.plotly_chart(fig, theme=None, config={"displayModeBar": False})


def no_data() -> None:
    render('<div class="notice">No se pudieron cargar los datos oficiales en este momento. '
           'Recargá la página en unos minutos.</div>')


# ── Datos oficiales: API de la Fundación Nobel ───────────────────────────────
def tx(value) -> str:
    """Los campos de texto de la API vienen como {'en': ..., 'se': ..., 'no': ...}."""
    if isinstance(value, dict):
        return value.get("en") or next((v for v in value.values() if isinstance(v, str)), "")
    return value if isinstance(value, str) else ""


def year_of(value) -> int | None:
    if isinstance(value, str) and len(value) >= 4 and value[:4].isdigit():
        y = int(value[:4])
        return y if y > 0 else None
    return None


def fetch_laureates() -> list[dict]:
    rows, offset, limit = [], 0, 100
    for _ in range(60):  # tope de seguridad
        r = requests.get(API_URL, params={"offset": offset, "limit": limit}, headers=HEADERS, timeout=30)
        r.raise_for_status()
        payload = r.json()
        batch = payload.get("laureates", [])
        rows.extend(batch)
        total = (payload.get("meta") or {}).get("count") or 0
        offset += limit
        if not batch or len(batch) < limit or (total and offset >= total):
            break
    return rows


@st.cache_data(ttl=60 * 60 * 12, show_spinner=False)
def load_data() -> pd.DataFrame:
    """Una fila por laureado y premio."""
    records = []
    for lau in fetch_laureates():
        is_org = "orgName" in lau
        name = tx(lau.get("knownName")) or tx(lau.get("fullName")) or tx(lau.get("orgName"))
        birth = lau.get("birth") or {}
        place = birth.get("place") or {}
        birth_country = tx(place.get("countryNow")) or tx(place.get("country"))
        birth_year = None if is_org else year_of(birth.get("date"))
        wiki = (lau.get("wikipedia") or {}).get("slug")
        prizes = lau.get("nobelPrizes") or []
        for p in prizes:
            year = p.get("awardYear")
            try:
                year = int(year)
            except (TypeError, ValueError):
                continue
            cat_en = tx(p.get("category"))
            if cat_en not in CATEGORIES:
                continue
            affils = []
            for a in p.get("affiliations") or []:
                affils.append((tx(a.get("name")), tx(a.get("countryNow")) or tx(a.get("country"))))
            records.append({
                "id": str(lau.get("id")),
                "name": name,
                "is_org": is_org,
                "gender": lau.get("gender") if not is_org else "org",
                "birth_year": birth_year,
                "birth_country": birth_country or None,
                "wiki": wiki,
                "year": year,
                "cat_en": cat_en,
                "cat": CATEGORIES[cat_en][0],
                "portion": p.get("portion"),
                "status": p.get("prizeStatus", "received"),
                "motivation": tx(p.get("motivation")).strip().strip('"'),
                "amount": p.get("prizeAmount"),
                "affils": affils,
                "affil_country": affils[0][1] if affils and affils[0][1] else None,
                "n_prizes": len(prizes),
            })
    df = pd.DataFrame(records)
    if df.empty:
        return df
    df["age"] = df["year"] - df["birth_year"]
    df["decade"] = (df["year"] // 10) * 10
    return df.sort_values(["year", "cat"]).reset_index(drop=True)


@st.cache_data(ttl=60 * 60 * 24 * 7, show_spinner=False)
def wiki_images(slugs: tuple) -> dict:
    """Miniaturas de Wikipedia (Wikimedia Commons) en paralelo."""
    def one(slug):
        try:
            r = requests.get(WIKI_URL.format(quote(slug, safe="")), headers=HEADERS, timeout=6)
            if r.ok:
                return slug, (r.json().get("thumbnail") or {}).get("source")
        except Exception:
            pass
        return slug, None
    with ThreadPoolExecutor(max_workers=8) as ex:
        return dict(ex.map(one, slugs))


def norm(s: str) -> str:
    return unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()


# ── Contenido editorial ──────────────────────────────────────────────────────
FAMOUS = [
    ("Marie Curie", "Marie_Curie", "Física 1903 · Química 1911", "Física",
     "Primera mujer en ganar un Nobel y la única persona premiada en dos ciencias distintas, por sus investigaciones sobre la radiactividad."),
    ("Albert Einstein", "Albert_Einstein", "Física 1921", "Física",
     "Premiado por explicar el efecto fotoeléctrico, no por la teoría de la relatividad, que todavía generaba debate."),
    ("Alexander Fleming", "Alexander_Fleming", "Medicina 1945", "Medicina",
     "Descubrió la penicilina. Compartió el premio con Howard Florey y Ernst Chain, que la convirtieron en medicamento."),
    ("Martin Luther King Jr.", "Martin_Luther_King_Jr.", "Paz 1964", "Paz",
     "Lucha no violenta contra la discriminación racial en Estados Unidos. Tenía 35 años al recibirlo."),
    ("Pablo Neruda", "Pablo_Neruda", "Literatura 1971", "Literatura",
     "El poeta chileno fue reconocido por una obra que expresa el destino y los sueños de todo un continente."),
    ("Gabriel García Márquez", "Gabriel_García_Márquez", "Literatura 1982", "Literatura",
     "Novelas y cuentos donde lo fantástico y lo real conviven. «Cien años de soledad» lo llevó a la fama mundial."),
    ("Nelson Mandela", "Nelson_Mandela", "Paz 1993", "Paz",
     "Compartido con F. W. de Klerk por terminar pacíficamente con el apartheid y sentar las bases de una Sudáfrica democrática."),
    ("John Nash", "John_Forbes_Nash_Jr.", "Economía 1994", "Economía",
     "Sus aportes a la teoría de juegos (el «equilibrio de Nash») revolucionaron la economía. Su vida inspiró «Una mente brillante»."),
    ("Malala Yousafzai", "Malala_Yousafzai", "Paz 2014", "Paz",
     "Con 17 años, la persona más joven en recibir un Nobel, por su lucha por el derecho de las niñas a la educación."),
]

ARGENTINA = [
    ("Carlos Saavedra Lamas", "Carlos_Saavedra_Lamas", "Paz", 1936,
     "Como canciller, impulsó la mediación que ayudó a terminar la Guerra del Chaco entre Bolivia y Paraguay y promovió un pacto internacional contra la guerra.",
     "Primer latinoamericano en ganar un Nobel."),
    ("Bernardo Houssay", "Bernardo_Houssay", "Medicina", 1947,
     "Descubrió el papel de la hipófisis anterior en el metabolismo del azúcar, clave para entender la diabetes. Compartió el premio con Carl y Gerty Cori.",
     "Primer latinoamericano en ganar un Nobel científico."),
    ("Luis Federico Leloir", "Luis_Federico_Leloir", "Química", 1970,
     "Descubrió los nucleótidos de azúcar y su función en la formación de los hidratos de carbono. Trabajó en Buenos Aires con recursos muy modestos.",
     "Nació en París, de padres argentinos."),
    ("Adolfo Pérez Esquivel", "Adolfo_Pérez_Esquivel", "Paz", 1980,
     "Reconocido por su defensa de los derechos humanos y la no violencia durante la última dictadura militar, al frente del Servicio Paz y Justicia.",
     "Artista plástico y arquitecto de formación."),
    ("César Milstein", "César_Milstein", "Medicina", 1984,
     "Desarrolló junto a Georges Köhler la técnica para producir anticuerpos monoclonales, hoy esenciales en diagnósticos y tratamientos.",
     "Nacido en Bahía Blanca, investigó en Cambridge."),
]

FAMILIES = [
    ("Los Curie", "La familia más premiada: Marie y Pierre Curie (Física 1903), Marie otra vez (Química 1911) y su hija Irène con su esposo Frédéric Joliot (Química 1935)."),
    ("Padre e hijo Bragg", "William Henry y William Lawrence Bragg compartieron el de Física 1915 por el análisis de cristales con rayos X. Lawrence tenía 25 años."),
    ("Los Bohr", "Niels Bohr ganó Física en 1922 por su modelo del átomo. Su hijo Aage la ganó en 1975."),
    ("Los Thomson", "J. J. Thomson (Física 1906) demostró que el electrón es una partícula. Su hijo George (Física 1937) demostró que también se comporta como onda."),
    ("Los Cori", "Carl y Gerty Cori ganaron Medicina en 1947, compartida con el argentino Bernardo Houssay. Gerty fue la primera mujer premiada en Medicina."),
    ("Los Myrdal", "Gunnar Myrdal ganó Economía (1974) y su esposa Alva Myrdal, Paz (1982), por su trabajo por el desarme."),
    ("Los Moser", "May-Britt y Edvard Moser compartieron Medicina 2014 por descubrir el «GPS interno» del cerebro."),
    ("Duflo y Banerjee", "Esther Duflo y Abhijit Banerjee, pareja, ganaron Economía 2019 junto a Michael Kremer por sus experimentos contra la pobreza."),
]

CONTROVERSIES = [
    ("Gandhi, el gran ausente", "Fue nominado cinco veces y nunca lo ganó. En 1948, el año de su asesinato, el Comité declaró desierto el premio de la Paz."),
    ("Kissinger y Le Duc Tho (1973)", "El Nobel de la Paz por el alto el fuego en Vietnam provocó la renuncia de dos miembros del Comité. Le Duc Tho lo rechazó porque la guerra seguía."),
    ("Los premios prohibidos", "Tras el Nobel de la Paz al pacifista Carl von Ossietzky (1935), preso en un campo de concentración, Hitler prohibió a los alemanes aceptarlo. La URSS forzó a Boris Pasternak a rechazar el de Literatura 1958."),
    ("Obama (2009)", "Lo recibió con menos de un año en la presidencia. Las nominaciones cerraron a días de su asunción, y hasta él dijo sentirse sorprendido."),
    ("Bob Dylan (2016)", "Primer músico en ganar Literatura. Tardó semanas en reaccionar y no viajó a la ceremonia de diciembre."),
    ("Literatura 2018", "Por primera vez en décadas no se entregó: un escándalo dentro de la Academia Sueca obligó a postergarlo y se otorgó en 2019 junto al de ese año."),
]

MILESTONES = [
    (1833, "Nace Alfred Nobel", "Químico, ingeniero e inventor sueco. A lo largo de su vida registró más de 350 patentes.", False),
    (1867, "La dinamita", "Patenta el invento que le daría una enorme fortuna, y también una reputación polémica.", False),
    (1895, "El testamento", "Firma en París el documento que destina la mayor parte de su fortuna a premiar a quienes «más beneficio hayan aportado a la humanidad».", True),
    (1896, "Muere en San Remo", "Fallece el 10 de diciembre. Por eso las ceremonias se celebran cada año en esa fecha.", False),
    (1901, "Primera entrega", "Se otorgan los primeros cinco premios. Wilhelm Röntgen, descubridor de los rayos X, es el primer laureado en Física.", True),
    (1903, "Marie Curie", "Se convierte en la primera mujer en ganar un Nobel. Ocho años después ganaría el segundo.", False),
    (1914, "Primera Guerra Mundial", "Durante el conflicto varias categorías quedan desiertas.", False),
    (1936, "Primer latinoamericano", "El argentino Carlos Saavedra Lamas gana el Nobel de la Paz.", True),
    (1940, "Segunda Guerra Mundial", "Entre 1940 y 1942 casi no hay premios. Alemania prohíbe a sus ciudadanos aceptarlos.", False),
    (1948, "Paz desierto", "El año del asesinato de Gandhi, el Comité no entrega el premio de la Paz.", False),
    (1964, "Sartre dice que no", "Jean-Paul Sartre rechaza el Nobel de Literatura: no aceptaba distinciones oficiales.", False),
    (1969, "Nace Economía", "Se entrega por primera vez el premio de Ciencias Económicas, creado por el Banco Central de Suecia.", True),
    (1974, "Fin de los premios póstumos", "Desde entonces no se puede premiar a alguien fallecido, salvo que muera después del anuncio.", False),
    (2014, "Malala", "Con 17 años, Malala Yousafzai es la persona más joven en recibir un Nobel.", False),
    (2016, "Un músico en Literatura", "Bob Dylan gana «por haber creado nuevas expresiones poéticas dentro de la tradición de la canción».", False),
    (2018, "Literatura en pausa", "Un escándalo en la Academia Sueca posterga el premio de Literatura un año.", False),
    (2020, "Una gala sin gala", "Por la pandemia no hay ceremonia presencial en Estocolmo: los laureados reciben sus medallas en sus países.", False),
]

COUNTRY_FIX = {
    "USA": "United States", "the Netherlands": "Netherlands", "Scotland": "United Kingdom",
    "Northern Ireland": "United Kingdom", "Faroe Islands (Denmark)": "Denmark",
    "Guadeloupe Island": "France", "East Timor": "Timor-Leste", "Czech Republic": "Czechia",
    "Republic of Macedonia": "North Macedonia", "Macedonia": "North Macedonia",
    "Democratic Republic of the Congo": "Democratic Republic of the Congo",
}
LATAM = {"Argentina", "Mexico", "Chile", "Colombia", "Peru", "Venezuela", "Brazil", "Costa Rica",
         "Guatemala", "Saint Lucia", "Trinidad and Tobago", "Uruguay", "Paraguay", "Bolivia", "Ecuador"}

# ── Carga ────────────────────────────────────────────────────────────────────
with st.spinner("Cargando datos oficiales de la Fundación Nobel…"):
    try:
        df = load_data()
    except Exception:
        df = pd.DataFrame()
OK = not df.empty

all_slugs = tuple({s for _, s, *_ in FAMOUS} | {s for _, s, *_ in ARGENTINA} | {"Alfred_Nobel", "Nobel_Prize"})
IMG = wiki_images(all_slugs)

if OK:
    people = df[~df["is_org"]].drop_duplicates("id")
    orgs = df[df["is_org"]].drop_duplicates("id")
    max_year = int(df["year"].max())
    n_laureates = df["id"].nunique()
    n_women = int((people["gender"] == "female").sum())
    n_countries = people["birth_country"].nunique()
    n_prizes = df[["year", "cat"]].drop_duplicates().shape[0]
    latest_amount = df.loc[df["year"] == max_year, "amount"].dropna()
    latest_amount = int(latest_amount.iloc[0]) if not latest_amount.empty else None
else:
    max_year = CURRENT_YEAR

# ── HERO ─────────────────────────────────────────────────────────────────────
render(f"""
<div class="hero">
<div class="ring"></div>
<div class="kicker">Premios Nobel · 1901 – {max_year}</div>
<h1>{max_year - 1901} años de ideas<br><em>que cambiaron el mundo</em></h1>
<p>Quiénes ganaron, por qué y qué nos dicen los datos oficiales sobre el premio más prestigioso del planeta.</p>
</div>
""")

if OK:
    render(f"""
    <div class="kpis">
    <div class="kpi"><div class="v">{fmt(n_laureates)}</div><div class="l">Laureados (personas y organizaciones)</div></div>
    <div class="kpi"><div class="v">{fmt(n_prizes)}</div><div class="l">Premios entregados</div></div>
    <div class="kpi"><div class="v">{n_women}</div><div class="l">Mujeres premiadas</div></div>
    <div class="kpi"><div class="v">{len(orgs)}</div><div class="l">Organizaciones</div></div>
    <div class="kpi"><div class="v">{n_countries}</div><div class="l">Países de nacimiento</div></div>
    </div>
    """)
else:
    no_data()

st.write("")
tabs = st.tabs(["Historia", "Línea de tiempo", "Laureados", "Argentina", "Los datos", "Récords y polémicas", "Explorá"])

# ═════════════════════════════════════════════════════════════════════════════
# 1 · HISTORIA
# ═════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    section("El origen", "Un inventor, una fortuna y un testamento",
            "Cómo el creador de la dinamita terminó dando nombre al reconocimiento más importante de la ciencia, la literatura y la paz.")
    c1, c2 = st.columns([1.55, 1], gap="large")
    with c1:
        render("""
        <div class="prose">
        <p>Alfred Nobel (1833–1896) fue un químico e inventor sueco que hizo fortuna con la dinamita y otros explosivos. Según la historia más difundida, en 1888 un diario francés publicó por error su obituario —había muerto su hermano Ludvig— y lo llamó «el mercader de la muerte». Leerlo lo habría llevado a pensar cómo quería ser recordado.</p>
        <p>En 1895 firmó en París un testamento que sorprendió hasta a su familia: la mayor parte de su fortuna iría a un fondo cuyos intereses se repartirían cada año entre quienes hubieran aportado el mayor beneficio a la humanidad en física, química, medicina, literatura y paz.</p>
        <p>Tras años de disputas legales se creó la Fundación Nobel, y en 1901 se entregaron los primeros premios. Desde entonces, cada 10 de diciembre —aniversario de su muerte— Estocolmo y Oslo celebran las ceremonias más observadas del mundo académico.</p>
        </div>
        <div class="quote">Una medalla, un diploma y una suma de dinero que hoy supera los diez millones de coronas suecas.</div>
        """)
    with c2:
        medal = IMG.get("Nobel_Prize")
        if medal:
            render(f'<div class="medal-wrap"><img class="medal-photo" src="{esc(medal)}" alt="Medalla del Premio Nobel"></div>'
                   '<div class="caption">Medalla del Premio Nobel · Imagen: Wikimedia Commons</div>')
        else:
            render('<div class="medal-wrap"><div class="medal-css"><b>NOBEL</b><span>1833 · 1896</span></div></div>'
                   '<div class="caption">Ilustración de la medalla</div>')
        amount_txt = f"{fmt(latest_amount)} SEK ({max_year})" if OK and latest_amount else "Más de 10 millones de SEK"
        render(f"""
        <ul class="facts" style="margin-top:22px">
        <li><span>No hay trofeo</span><span>Medalla + diploma + dinero</span></li>
        <li><span>Medalla</span><span>Oro de 18 quilates</span></li>
        <li><span>Anverso</span><span>Perfil de Alfred Nobel</span></li>
        <li><span>Premio por categoría</span><span>{amount_txt}</span></li>
        <li><span>Máximo de premiados</span><span>3 personas por premio</span></li>
        </ul>
        """)

    section("La gala", "Dos ciudades, una misma noche",
            "Nobel dejó establecido que el premio de la Paz lo otorgara un comité noruego. Por eso hay dos ceremonias.")
    render("""
    <div class="grid-2">
    <div class="dark">
    <h3>Estocolmo</h3>
    <p>Física, Química, Medicina, Literatura y Economía se entregan en la Sala de Conciertos de Estocolmo, de manos del rey de Suecia. Después, unos 1.300 invitados comparten el banquete en el Salón Azul del Ayuntamiento, uno de los eventos de etiqueta más famosos del mundo.</p>
    </div>
    <div class="dark">
    <h3>Oslo</h3>
    <p>El Nobel de la Paz se entrega en el Ayuntamiento de Oslo, ante la familia real noruega. Cuando Nobel escribió su testamento, Suecia y Noruega formaban una unión; él eligió al Parlamento noruego para elegir al comité de la Paz.</p>
    </div>
    </div>
    """)

    section("Las categorías", "Seis premios, seis mundos",
            "Cinco nacen del testamento de Nobel. El sexto, Economía, se sumó en 1969.")
    cards = []
    for cat_en, (name, icon, color, inst, start, desc) in CATEGORIES.items():
        total = first = "—"
        if OK:
            sub = df[df["cat_en"] == cat_en]
            total = fmt(len(sub))
            fy = sub["year"].min()
            first = ", ".join(sub.loc[sub["year"] == fy, "name"].tolist()) if pd.notna(fy) else "—"
        cards.append(f"""
        <div class="card">
        <div class="icon" style="background:{color}18;color:{color}">{icon}</div>
        <h3>{name}</h3>
        <div class="meta">{inst}</div>
        <p>{desc}</p>
        <p class="meta" style="margin-top:10px">Primer premio: <b>{esc(first)}</b></p>
        <div class="stat-row"><div><b>{start}</b><span>Desde</span></div><div><b>{total}</b><span>Laureados</span></div></div>
        </div>""")
    render('<div class="grid">' + "".join(cards) + "</div>")

# ═════════════════════════════════════════════════════════════════════════════
# 2 · LÍNEA DE TIEMPO
# ═════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    section("Cronología", "De un testamento a la actualidad", "Los momentos que definieron la historia de los premios.")
    items = []
    for y, title, text, big in MILESTONES:
        items.append(f'<div class="tl-item{" big" if big else ""}"><div class="tl-year">{y}</div>'
                     f'<div class="tl-title">{title}</div><div class="tl-text">{text}</div></div>')
    if OK:
        last = df[df["year"] == max_year]
        winners = "; ".join(f"{c}: {', '.join(last.loc[last['cat'] == c, 'name'])}" for c in CAT_ORDER if c in set(last["cat"]))
        items.append(f'<div class="tl-item big"><div class="tl-year">{max_year}</div><div class="tl-title">La edición más reciente</div>'
                     f'<div class="tl-text">{esc(winners)}</div></div>')
    render('<div class="tl">' + "".join(items) + "</div>")

    section("125 años en un solo gráfico", "Cada celda, un premio",
            "Las celdas vacías muestran los años en que una categoría quedó desierta, sobre todo durante las guerras mundiales. Cuanto más oscuro, más laureados compartieron el premio.")
    if OK:
        years = list(range(1901, max_year + 1))
        counts = df.groupby(["cat", "year"]).size().unstack(fill_value=0).reindex(index=CAT_ORDER, columns=years, fill_value=0)
        z = counts.astype(float)
        z.loc["Economía", [y for y in years if y < 1969]] = float("nan")
        hover = [[f"{c} {y}: " + (f"{int(v)} laureado(s)" if v > 0 else ("no existía" if pd.isna(v) else "sin premio"))
                  for y, v in zip(years, row)] for c, row in zip(z.index, z.values)]
        fig = go.Figure(go.Heatmap(
            z=z.values, x=years, y=z.index, zmin=0, zmax=3, xgap=1, ygap=4,
            colorscale=[[0, "#EAE3D3"], [0.0001, "#E6CF8E"], [0.5, "#C29A42"], [1, "#7A5A1C"]],
            showscale=False, text=hover, hoverinfo="text"))
        fig = polish(fig, height=330, legend=False)
        fig.update_yaxes(autorange="reversed", gridcolor="rgba(0,0,0,0)")
        show(fig)

        end = max_year - 1 if max_year >= CURRENT_YEAR else max_year
        gaps = []
        for cat_en, (name, *_rest) in CATEGORIES.items():
            start = CATEGORIES[cat_en][4]
            have = set(df.loc[df["cat_en"] == cat_en, "year"])
            missing = [y for y in range(start, end + 1) if y not in have]
            gaps.append({"Categoría": name, "Años sin premio": len(missing)})
        g = pd.DataFrame(gaps).sort_values("Años sin premio")
        fig = px.bar(g, x="Años sin premio", y="Categoría", orientation="h", text="Años sin premio",
                     color="Categoría", color_discrete_map=CAT_COLOR)
        fig.update_traces(textposition="outside", cliponaxis=False)
        show(polish(fig, height=280, legend=False))
        st.caption("Paz es la categoría que más veces quedó desierta. Si el año en curso todavía no terminó de anunciarse, no se cuenta.")
    else:
        no_data()

# ═════════════════════════════════════════════════════════════════════════════
# 3 · LAUREADOS
# ═════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    section("Nombres propios", "Los laureados más célebres", "Nueve figuras que trascendieron su disciplina.")
    cards = []
    for name, slug, label, cat, text in FAMOUS:
        cards.append(f"""
        <div class="card"><div class="person">{avatar(IMG.get(slug), name)}
        <div>{pill(label, CAT_COLOR[cat])}<h3>{esc(name)}</h3></div></div>
        <p>{esc(text)}</p></div>""")
    render('<div class="grid">' + "".join(cards) + "</div>")

    section("Herencias", "Familias Nobel", "Padres, hijos y parejas que se repartieron premios a lo largo de un siglo.")
    render('<div class="grid">' + "".join(
        f'<div class="card"><h3>{esc(t)}</h3><p>{esc(d)}</p></div>' for t, d in FAMILIES) + "</div>")

# ═════════════════════════════════════════════════════════════════════════════
# 4 · ARGENTINA
# ═════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    section("Orgullo nacional", "Los cinco Nobel argentinos",
            "Dos de la Paz y tres científicos. Argentina es el país latinoamericano con más premios en ciencias.")
    cards = []
    for name, slug, cat, year, text, note in ARGENTINA:
        cards.append(f"""
        <div class="card"><div class="person">{avatar(IMG.get(slug), name)}
        <div>{pill(f"{cat} {year}", CAT_COLOR[cat])}<h3>{esc(name)}</h3><div class="meta">{esc(note)}</div></div></div>
        <p>{esc(text)}</p></div>""")
    render('<div class="grid">' + "".join(cards) + "</div>")

    section("En contexto", "América Latina en el Nobel", "Laureados por país de nacimiento, según los datos oficiales.")
    if OK:
        la = people[people["birth_country"].isin(LATAM)]
        la_counts = la.groupby("birth_country").size().sort_values().reset_index(name="Laureados")
        la_counts["color"] = la_counts["birth_country"].map(lambda c: GOLD if c == "Argentina" else "#CFC6B2")
        fig = go.Figure(go.Bar(x=la_counts["Laureados"], y=la_counts["birth_country"], orientation="h",
                               marker_color=la_counts["color"], text=la_counts["Laureados"], textposition="outside",
                               cliponaxis=False, hovertemplate="%{y}: %{x}<extra></extra>"))
        show(polish(fig, height=max(260, 34 * len(la_counts)), legend=False))
        n_ar = int((people["birth_country"] == "Argentina").sum())
        st.caption(f"Leloir figura como nacido en Francia, por eso los datos oficiales cuentan {n_ar} laureados nacidos en Argentina.")
    else:
        no_data()

# ═════════════════════════════════════════════════════════════════════════════
# 5 · LOS DATOS
# ═════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    if not OK:
        no_data()
    else:
        # Mujeres
        section("Brecha de género", "Las mujeres en el Nobel",
                f"Solo {n_women} de {fmt(len(people))} personas premiadas son mujeres. La brecha se achica, pero lentamente.")
        c1, c2 = st.columns(2, gap="large")
        with c1:
            chart_title("% de mujeres por década")
            dec = people.groupby("decade").agg(total=("id", "size"), women=("gender", lambda s: (s == "female").sum())).reset_index()
            dec["% mujeres"] = (dec["women"] / dec["total"] * 100).round(1)
            dec["Década"] = dec["decade"].astype(int).astype(str) + "s"
            fig = px.bar(dec, x="Década", y="% mujeres", text="% mujeres")
            fig.update_traces(marker_color=GOLD, texttemplate="%{text:.0f}%", textposition="outside", cliponaxis=False)
            show(polish(fig, legend=False))
        with c2:
            chart_title("Laureados por categoría")
            by_cat = people.groupby("cat").agg(total=("id", "size"), women=("gender", lambda s: (s == "female").sum())).reindex(CAT_ORDER).reset_index()
            fig = go.Figure()
            fig.add_bar(y=by_cat["cat"], x=by_cat["total"] - by_cat["women"], name="Hombres", orientation="h", marker_color="#D9D2C2")
            fig.add_bar(y=by_cat["cat"], x=by_cat["women"], name="Mujeres", orientation="h", marker_color=GOLD_DEEP)
            fig.update_layout(barmode="stack")
            fig.update_yaxes(autorange="reversed")
            show(polish(fig))

        # Geografía y fuga de cerebros
        section("Geografía del talento", "¿Dónde nacen y dónde trabajan?",
                "El mapa muestra dónde nacieron los laureados. El balance compara cuántos nacieron en cada país con cuántos trabajaban allí al ganar.")
        geo = people.dropna(subset=["birth_country"]).copy()
        geo["country"] = geo["birth_country"].replace(COUNTRY_FIX)
        gc = geo.groupby("country").size().reset_index(name="Laureados")
        fig = px.choropleth(gc, locations="country", locationmode="country names", color="Laureados",
                            color_continuous_scale=["#F1E8D2", "#D9B45A", "#8A6A22", "#4A3610"], hover_name="country")
        fig.update_geos(showframe=False, showcoastlines=False, projection_type="natural earth",
                        bgcolor="rgba(0,0,0,0)", landcolor="#ECE6D8", showland=True, showcountries=True, countrycolor="#FFFFFF")
        fig.update_layout(coloraxis_colorbar=dict(title=None, thickness=10, len=0.6))
        show(polish(fig, height=460, legend=False))

        sci = df[(~df["is_org"]) & (df["cat"].isin(SCIENCES))].dropna(subset=["birth_country", "affil_country"])
        if not sci.empty:
            born = sci["birth_country"].replace(COUNTRY_FIX).value_counts()
            work = sci["affil_country"].replace(COUNTRY_FIX).value_counts()
            bal = (work.reindex(born.index.union(work.index), fill_value=0) - born.reindex(born.index.union(work.index), fill_value=0))
            bal = bal[bal != 0].sort_values()
            bal = pd.concat([bal.head(8), bal.tail(8)]).drop_duplicates()
            moved = (sci["birth_country"].replace(COUNTRY_FIX) != sci["affil_country"].replace(COUNTRY_FIX)).mean() * 100
            c1, c2 = st.columns([1.6, 1], gap="large")
            with c1:
                chart_title("Balance de talento (ciencias y economía)")
                fig = go.Figure(go.Bar(x=bal.values, y=bal.index, orientation="h",
                                       marker_color=[GOLD_DEEP if v > 0 else "#B5473A" for v in bal.values],
                                       hovertemplate="%{y}: %{x:+d}<extra></extra>"))
                show(polish(fig, height=460, legend=False))
            with c2:
                render(f"""
                <div class="dark" style="margin-top:36px">
                <h3>{moved:.0f}%</h3>
                <p>de los laureados en ciencias y economía trabajaba en un país distinto al de su nacimiento cuando ganó el premio.</p>
                <p>Los valores positivos indican países que «atraen» laureados; los negativos, países que los «exportan».</p>
                </div>""")

        # Edad
        section("El factor tiempo", "¿A qué edad se gana un Nobel?",
                "Los premios científicos llegan cada vez más tarde: hoy suelen reconocer descubrimientos hechos décadas antes.")
        ages = df[(~df["is_org"])].dropna(subset=["age"])
        c1, c2 = st.columns(2, gap="large")
        with c1:
            chart_title("Distribución de edades")
            fig = px.box(ages, x="cat", y="age", color="cat", color_discrete_map=CAT_COLOR,
                         category_orders={"cat": CAT_ORDER}, points="outliers", hover_name="name",
                         labels={"cat": "", "age": "Edad al ganar"})
            show(polish(fig, legend=False))
        with c2:
            chart_title("Edad promedio por década (ciencias)")
            avg = ages[ages["cat"].isin(SCIENCES)].groupby(["decade", "cat"])["age"].mean().reset_index()
            fig = px.line(avg, x="decade", y="age", color="cat", color_discrete_map=CAT_COLOR, markers=True,
                          labels={"decade": "", "age": "Edad promedio", "cat": ""})
            show(polish(fig))

        # Compartidos
        section("Trabajo en equipo", "El fin del genio solitario",
                "En las ciencias, ganar solo es cada vez más raro. La ciencia moderna se hace en equipo.")
        shared = df[df["cat"].isin(SCIENCES)].groupby(["year", "cat"]).size().reset_index(name="n")
        shared["decade"] = (shared["year"] // 10) * 10
        shared["Premiados"] = shared["n"].clip(upper=3).map({1: "1 persona", 2: "2 personas", 3: "3 personas"})
        mix = shared.groupby(["decade", "Premiados"]).size().reset_index(name="cnt")
        mix["%"] = mix["cnt"] / mix.groupby("decade")["cnt"].transform("sum") * 100
        mix["Década"] = mix["decade"].astype(int).astype(str) + "s"
        fig = px.bar(mix, x="Década", y="%", color="Premiados", barmode="stack",
                     color_discrete_map={"1 persona": "#E6CF8E", "2 personas": "#C29A42", "3 personas": "#6E5118"},
                     category_orders={"Premiados": ["1 persona", "2 personas", "3 personas"]})
        fig.update_yaxes(ticksuffix="%", range=[0, 100])
        show(polish(fig, height=360))

        # Instituciones
        section("Las fábricas de Nobel", "Instituciones con más laureados",
                "Afiliación de los premiados al momento de recibir el premio.")
        aff = df[["affils"]].explode("affils").dropna()
        aff["inst"] = aff["affils"].map(lambda t: t[0] if isinstance(t, (tuple, list)) else None)
        top = aff.dropna(subset=["inst"]).query("inst != ''").groupby("inst").size().sort_values().tail(15)
        fig = go.Figure(go.Bar(x=top.values, y=top.index, orientation="h", marker_color=NAVY,
                               text=top.values, textposition="outside", cliponaxis=False,
                               hovertemplate="%{y}: %{x}<extra></extra>"))
        show(polish(fig, height=520, legend=False))

# ═════════════════════════════════════════════════════════════════════════════
# 6 · RÉCORDS Y POLÉMICAS
# ═════════════════════════════════════════════════════════════════════════════
with tabs[5]:
    section("Los extremos", "Récords del Nobel", "Calculados en vivo a partir de los datos oficiales.")
    if OK:
        withage = df[~df["is_org"]].dropna(subset=["age"])
        young = withage.loc[withage["age"].idxmin()]
        old = withage.loc[withage["age"].idxmax()]
        multi = df.groupby(["id", "name"])["year"].apply(lambda s: sorted(set(s))).reset_index()
        multi = multi[multi["year"].map(len) > 1]
        multi_txt = " · ".join(f"{n} ({', '.join(map(str, y))})" for n, y in zip(multi["name"], multi["year"]))
        refused = df[df["status"].isin(["declined", "restricted"])]
        render(f"""
        <div class="grid">
        <div class="card"><div class="meta">Más joven</div><h3>{esc(young['name'])}</h3>
        <p><b>{int(young['age'])} años</b> · {esc(young['cat'])} {int(young['year'])}</p></div>
        <div class="card"><div class="meta">Más longevo al ganar</div><h3>{esc(old['name'])}</h3>
        <p><b>{int(old['age'])} años</b> · {esc(old['cat'])} {int(old['year'])}</p></div>
        <div class="card"><div class="meta">Rechazados o prohibidos</div><h3>{len(refused)} premios</h3>
        <p>{esc(', '.join(f"{n} ({y})" for n, y in zip(refused['name'], refused['year'])))}</p></div>
        </div>""")
        st.write("")
        render(f'<div class="dark"><h3>Ganaron más de una vez</h3><p>{esc(multi_txt)}</p></div>')
    else:
        no_data()

    section("El lado B", "Polémicas y ausencias", "El Nobel también es historia política.")
    render('<div class="grid">' + "".join(
        f'<div class="card"><h3>{esc(t)}</h3><p>{esc(d)}</p></div>' for t, d in CONTROVERSIES) + "</div>")

# ═════════════════════════════════════════════════════════════════════════════
# 7 · EXPLORÁ
# ═════════════════════════════════════════════════════════════════════════════
with tabs[6]:
    if not OK:
        no_data()
    else:
        section("Tu turno", "¿Quién ganó el año en que naciste?", "Elegí un año y mirá quiénes fueron premiados.")
        year = st.slider("Año", 1901, max_year, 2000, label_visibility="collapsed")
        sel = df[df["year"] == year]
        cards = []
        for cat in CAT_ORDER:
            sub = sel[sel["cat"] == cat]
            if cat == "Economía" and year < 1969:
                continue
            if sub.empty:
                body = '<p class="meta">Sin premio este año.</p>'
            else:
                body = "".join(f'<p><b>{esc(r.name)}</b><br><span class="meta"><i>{esc(r.motivation)}</i></span></p>'
                               for r in sub.itertuples())
            cards.append(f'<div class="card">{pill(cat, CAT_COLOR[cat])}{body}</div>')
        render('<div class="grid">' + "".join(cards) + "</div>")
        st.caption("Las motivaciones se muestran en su idioma original (inglés), tal como las publica la Fundación Nobel.")

        section("Buscador", "Encontrá a cualquier laureado", "Escribí un nombre, un apellido o una organización.")
        q = st.text_input("Buscar", placeholder="Ej.: Curie, Neruda, Red Cross…", label_visibility="collapsed")
        if q:
            hits = df[df["name"].map(norm).str.contains(norm(q), regex=False)]
            if hits.empty:
                st.caption("No hay coincidencias. Probá con el nombre en inglés (por ejemplo, «Red Cross»).")
            else:
                table = hits[["name", "cat", "year", "birth_country", "motivation"]].rename(columns={
                    "name": "Laureado", "cat": "Categoría", "year": "Año", "birth_country": "País de nacimiento", "motivation": "Motivación"})
                st.dataframe(table, hide_index=True)

# ── Footer ───────────────────────────────────────────────────────────────────
render(f"""
<div class="footer">
<b>Fuentes.</b> Datos de laureados: <a href="https://www.nobelprize.org/about/developer-zone-2/" target="_blank">API oficial de la Fundación Nobel</a> (nobelprize.org, v2.1), actualizados automáticamente cada 12 horas.
Imágenes: Wikipedia / Wikimedia Commons. Textos editoriales de elaboración propia.<br>
Proyecto de visualización de datos · {CURRENT_YEAR}
</div>
""")
