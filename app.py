import os
from datetime import datetime

import requests
import streamlit as st


# Config / constants

DEFAULT_API_BASE = os.getenv("API_BASE", "https://movie-recommender-0yao.onrender.com" or "http://127.0.0.1:8000")
POSTER_BASE = "https://image.tmdb.org/t/p/w500"
BACKDROP_BASE = "https://image.tmdb.org/t/p/original"

CATEGORY_LABELS = {
    "trending": "🔥 Trending Today",
    "popular": "⭐ Popular Right Now",
    "top_rated": "🏆 Top Rated",
    "upcoming": "🎬 Coming Soon",
    "now_playing": "🎟️ Now Playing",
}

st.set_page_config(page_title="CineMatch", page_icon="🎬", layout="wide")


# Session state

defaults = {
    "view": "home",
    "selected_query": None,
    "search_box": "",
    "api_base": DEFAULT_API_BASE,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# Theme

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp { background:#141414; color:#e5e5e5; }
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1400px; }
footer, #MainMenu { visibility:hidden; }

section[data-testid="stSidebar"] { background:#000000; border-right:1px solid #262626; }
section[data-testid="stSidebar"] * { color:#e5e5e5 !important; }

.brand { font-family:'Bebas Neue', sans-serif; color:#E50914; font-size:2.4rem;
         letter-spacing:2px; margin:0; line-height:1; }
.tagline { color:#8c8c8c; font-size:.82rem; margin:0 0 1rem 0; }

.section-title { color:#fff; font-size:1.25rem; font-weight:700; margin:1.8rem 0 .9rem 0;
                  border-left:4px solid #E50914; padding-left:10px; }
.muted-note { color:#8c8c8c; font-size:.88rem; margin:.2rem 0 1rem 0; }

.poster-wrap { position:relative; border-radius:6px; overflow:hidden; aspect-ratio:2/3;
               background:#222; box-shadow:0 4px 14px rgba(0,0,0,.5);
               transition:transform .2s ease, box-shadow .2s ease; }
.poster-wrap:hover { transform:scale(1.04); box-shadow:0 10px 26px rgba(0,0,0,.75); }
.poster-wrap img { width:100%; height:100%; object-fit:cover; display:block; }
.poster-placeholder { display:flex; align-items:center; justify-content:center;
                       width:100%; height:100%; background:#262626; color:#555; font-size:2.2rem; }

.rating-badge { position:absolute; top:6px; right:6px; background:rgba(0,0,0,.78);
                 color:#f5c518; font-size:.7rem; font-weight:700; padding:2px 6px; border-radius:4px; }
.match-badge { position:absolute; top:6px; left:6px; font-size:.7rem; font-weight:800;
                padding:2px 6px; border-radius:4px; background:rgba(0,0,0,.78); }

.card-title { color:#e5e5e5; font-size:.84rem; font-weight:600; margin:.5rem 0 0 0;
              line-height:1.2; height:2.3em; overflow:hidden; }
.card-year { color:#8c8c8c; font-size:.74rem; margin-bottom:.35rem; }

.stButton>button { background:#E50914 !important; color:#fff !important; border:none !important;
                    border-radius:4px !important; font-weight:600 !important;
                    padding:.32rem .8rem !important; transition:background .15s ease; }
.stButton>button:hover { background:#f6121d !important; }

.hero { border-radius:10px; padding:2.6rem 2.4rem 1.8rem; margin-bottom:.4rem; min-height:380px;
        display:flex; flex-direction:column; justify-content:flex-end;
        background-size:cover; background-position:center top; }
.hero-title { font-family:'Bebas Neue', sans-serif; font-size:3rem; color:#fff;
              letter-spacing:1px; margin:0; }
.hero-meta { color:#d2d2d2; font-size:.95rem; margin:.5rem 0 1rem 0; }
.hero-overview { color:#dadada; max-width:680px; line-height:1.55; font-size:.95rem; }
.pill { display:inline-block; border:1px solid #555; color:#ccc; border-radius:20px;
        padding:2px 12px; font-size:.74rem; margin:0 6px 6px 0; }

div[data-testid="stTextInput"] input { background:#222 !important; color:#eee !important;
                                        border:1px solid #3a3a3a !important; }
div[data-testid="stSelectbox"] div, .stSlider label, .stSlider span { color:#e5e5e5 !important; }

::-webkit-scrollbar { width:10px; }
::-webkit-scrollbar-track { background:#141414; }
::-webkit-scrollbar-thumb { background:#3a3a3a; border-radius:5px; }
</style>
""",
    unsafe_allow_html=True,
)


# API helpers

def _get(path: str, params: dict | None = None):
    base = st.session_state.api_base.rstrip("/")
    try:
        r = requests.get(f"{base}{path}", params=params or {}, timeout=20)
    except requests.exceptions.ConnectionError:
        st.error(f"Can't reach the API at `{base}`. Is the FastAPI backend running?")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Request to the API failed: {e}")
        return None

    if r.status_code != 200:
        detail = r.text
        try:
            detail = r.json().get("detail", detail)
        except Exception:
            pass
        st.warning(
            "Movie service is temporarily unavailable. "
            "Please try again."
        )
        return None

    try:
        return r.json()
    except Exception:
        st.error("Backend returned a response that wasn't valid JSON.")
        return None


@st.cache_data(ttl=600, show_spinner=False)
def fetch_home(api_base: str, category: str, limit: int):
    return _get("/home", {"category": category, "limit": limit})


@st.cache_data(ttl=300, show_spinner=False)
def fetch_search(api_base: str, query: str, page: int = 1):
    return _get("/tmdb/search", {"query": query, "page": page})


@st.cache_data(ttl=300, show_spinner=False)
def fetch_bundle(api_base: str, query: str, tfidf_top_n: int = 10, genre_limit: int = 12):
    return _get(
        "/movie/search",
        {"query": query, "tfidf_top_n": tfidf_top_n, "genre_limit": genre_limit},
    )


# Wrappers that key the cache on the current backend URL automatically
def get_home(category, limit):
    return fetch_home(st.session_state.api_base, category, limit)


def get_search(query, page=1):
    return fetch_search(st.session_state.api_base, query, page)


def get_bundle(query):
    return fetch_bundle(st.session_state.api_base, query)



# Render helpers

def match_color(pct: float) -> str:
    if pct >= 70:
        return "#46d369"
    if pct >= 40:
        return "#e0a72f"
    return "#888888"


def poster_block(poster_url, rating=None, match_pct=None):
    if poster_url:
        inner = f'<img src="{poster_url}" alt="poster" />'
    else:
        inner = '<div class="poster-placeholder">🎬</div>'

    badges = ""
    if rating is not None:
        badges += f'<div class="rating-badge">★ {rating:.1f}</div>'
    if match_pct is not None:
        badges += f'<div class="match-badge" style="color:{match_color(match_pct)}">{match_pct:.0f}% Match</div>'

    return f'<div class="poster-wrap">{inner}{badges}</div>'


def render_card(col, title, year, poster_url, rating=None, match_pct=None, key=""):
    with col:
        st.markdown(poster_block(poster_url, rating, match_pct), unsafe_allow_html=True)
        st.markdown(f'<div class="card-title">{title}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-year">{year or "—"}</div>', unsafe_allow_html=True)
        st.button("▶  Details", key=key, use_container_width=True, on_click=go_to_details, args=(title,))


def render_grid(items, columns, key_prefix):
    if not items:
        st.markdown('<p class="muted-note">Nothing to show here yet.</p>', unsafe_allow_html=True)
        return
    cols = st.columns(columns)
    for i, item in enumerate(items):
        render_card(
            cols[i % columns],
            title=item["title"],
            year=(item.get("release_date") or "")[:4],
            poster_url=item.get("poster_url"),
            rating=item.get("vote_average"),
            key=f"{key_prefix}_{i}_{item.get('tmdb_id', item['title'])}",
        )


def go_to_details(title: str):
    print("CLICKED:", title)
    st.session_state.view = "details"
    st.session_state.selected_query = title


def go_home():
    st.session_state.view = "home"



# Sidebar

with st.sidebar:
    st.markdown('<p class="brand">🎬 CINEMATCH</p>', unsafe_allow_html=True)
    st.markdown('<p class="tagline">Find your next watch</p>', unsafe_allow_html=True)

    st.button("🏠 Home", use_container_width=True, on_click=go_home)

    st.markdown("---")
    st.markdown("**Browse**")
    category = st.selectbox(
        "Category",
        options=list(CATEGORY_LABELS.keys()),
        format_func=lambda c: CATEGORY_LABELS[c],
        index=0,
    )
    columns = st.slider("Grid columns", min_value=4, max_value=8, value=6)

    with st.expander("⚙️ Settings"):
        st.session_state.api_base = st.text_input("Backend URL", value=st.session_state.api_base)
        st.caption("Point this at wherever `uvicorn main:app` is running.")


# Top bar — search

st.markdown('<p class="brand">🎬 CINEMATCH</p>', unsafe_allow_html=True)
st.markdown('<p class="tagline">Type a title to search, or browse what\'s trending below.</p>', unsafe_allow_html=True)

if st.session_state.view != "details":

    query_input = st.text_input(
        "Search",
        value=st.session_state.search_box,
        placeholder="Search for a movie… e.g. avenger, batman, love",
        label_visibility="collapsed",
        key="search_box",
    )

    if query_input.strip():
        st.session_state.view = "search"

    elif st.session_state.view == "search":
        st.session_state.view = "home"


# Views
#

if st.session_state.view == "home":
    st.markdown(f'<p class="section-title">{CATEGORY_LABELS[category]}</p>', unsafe_allow_html=True)
    with st.spinner("Loading titles…"):
        items = get_home(category, 30)
    render_grid(items, columns, key_prefix="home")

elif st.session_state.view == "search":
    q = query_input.strip()
    st.markdown(f'<p class="section-title">Results for “{q}”</p>', unsafe_allow_html=True)
    with st.spinner("Searching…"):
        data = get_search(q)

    results = (data or {}).get("results", [])
    if not results:
        st.markdown('<p class="muted-note">No matches. Try a different title.</p>', unsafe_allow_html=True)
    else:
        mapped = [
            {
                "tmdb_id": m.get("id"),
                "title": m.get("title") or m.get("name") or "Untitled",
                "poster_url": f"{POSTER_BASE}{m['poster_path']}" if m.get("poster_path") else None,
                "release_date": m.get("release_date"),
                "vote_average": m.get("vote_average"),
            }
            for m in results
        ]
        render_grid(mapped, columns, key_prefix="search")

elif st.session_state.view == "details":
    st.button("←  Back to Browse", on_click=go_home)

    q = st.session_state.selected_query
    with st.spinner(f"Loading “{q}”…"):
        bundle = get_bundle(q)

    if not bundle:
        st.markdown(
            '<p class="muted-note">Couldn\'t load this title right now. '
            "It may not have returned a match, or the backend hit an error — check the server logs.</p>",
            unsafe_allow_html=True,
        )
    else:
        details = bundle["movie_details"]
        year = (details.get("release_date") or "")[:4]
        genres = details.get("genres") or []
        genre_pills = "".join(f'<span class="pill">{g["name"]}</span>' for g in genres)
        backdrop = details.get("backdrop_url") or details.get("poster_url")

        bg_style = (
            f"background-image: linear-gradient(180deg, rgba(20,20,20,0) 35%, rgba(20,20,20,1) 96%), url('{backdrop}');"
            if backdrop
            else "background:#1c1c1c;"
        )

        st.markdown(
            f"""
            <div class="hero" style="{bg_style}">
                <h1 class="hero-title">{details['title']}</h1>
                <div class="hero-meta">{year or "—"} &nbsp;•&nbsp; ★ {details.get('vote_average', '—') if details.get('vote_average') else '—'}</div>
                <div style="margin-bottom:.8rem;">{genre_pills}</div>
                <p class="hero-overview">{details.get('overview') or 'No overview available.'}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # --- TF-IDF recommendations ---
        st.markdown('<p class="section-title">More Like This</p>', unsafe_allow_html=True)
        tfidf_items = bundle.get("tfidf_recommendations") or []
        if not tfidf_items:
            st.markdown(
                '<p class="muted-note">This title isn\'t in the curated dataset yet, '
                "so no similarity-based picks are available — see the genre row below instead.</p>",
                unsafe_allow_html=True,
            )
        else:
            cols = st.columns(columns)
            for i, rec in enumerate(tfidf_items):
                tmdb_card = rec.get("tmdb") or {}
                render_card(
                    cols[i % columns],
                    title=rec["title"],
                    year=(tmdb_card.get("release_date") or "")[:4],
                    poster_url=tmdb_card.get("poster_url"),
                    rating=tmdb_card.get("vote_average"),
                    match_pct=rec.get("score", 0) * 100,
                    key=f"tfidf_{i}_{rec['title']}",
                )

        # --- Genre recommendations ---
        label = f"Because You Like {genres[0]['name']}" if genres else "You Might Also Like"
        st.markdown(f'<p class="section-title">{label}</p>', unsafe_allow_html=True)
        render_grid(bundle.get("genre_recommendation") or [], columns, key_prefix="genre")