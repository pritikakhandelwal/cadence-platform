import os

import streamlit as st

from modules.database import create_tables
from modules.html_safety import escape_html
from modules.session_security import enforce_session_integrity, stamp_session

# ==========================================================
# PAGE CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="Cadence",
    page_icon="💃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# LOAD CSS
# ==========================================================

def load_css():

    css_files = [

        "assets/css/style.css",

        "assets/css/home.css",

        "assets/css/cards.css",

        "assets/css/buttons.css",

        "assets/css/sidebar.css",

        "assets/css/animations.css",

        "assets/css/achievements.css",

        "assets/css/about.css",

        "assets/css/reports.css",

        "assets/css/help.css"

    ]

    for css in css_files:

        try:

            with open(css) as f:

                st.markdown(
                    f"<style>{f.read()}</style>",
                    unsafe_allow_html=True
                )

        except FileNotFoundError:
            pass

    st.markdown(
"""
<link rel="stylesheet"
href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,500,1,0">
""",
    unsafe_allow_html=True
)


# ==========================================================
# INITIALIZE APP
# ==========================================================

load_css()

create_tables()

# Detect and clear any corrupted session state before rendering.
enforce_session_integrity()

# ==========================================================
# IMPORT PAGES
# ==========================================================

from components.home import show_home
from components.dance_studio import show_dance_studio
from components.analysis import show_analysis
from components.performance import show_performance
from components.analytics import show_analytics
from components.skeleton import show_skeleton
from components.achievements import show_achievements
from components.reports import show_reports
from components.profile import show_profile
from components.about import show_about
from components.help import show_help

# ==========================================================
# SIDEBAR INITIALIZATION
# ==========================================================

from modules.database import get_achievement_data

if "page" not in st.session_state:

    st.session_state.page = "Home"

# ==========================================================
# USER INFORMATION
# ==========================================================

logged_in = st.session_state.get("logged_in", False)

if logged_in:

    user = st.session_state["user"]

    total, best, average = get_achievement_data(user[0])

    xp = min(int(total * 100 + best * 10), 2500)

    if xp >= 2200:

        rank = "👑 Diamond Dancer"

    elif xp >= 1700:

        rank = "💎 Platinum Dancer"

    elif xp >= 1200:

        rank = "🥇 Gold Dancer"

    elif xp >= 700:

        rank = "🥈 Silver Dancer"

    else:

        rank = "🥉 Bronze Dancer"

else:

    user = [0, "Guest"]

    xp = 0

    rank = "Not Logged In"

display_name = escape_html(user[1])

# ==========================================================
# SIDEBAR HEADER
# ==========================================================

with st.sidebar:

    st.markdown(
        f"""
<div class="sidebar-header">

<div class="sidebar-logo">

CADENCE 

</div>

</div>

<div class="sidebar-user-card">

<div class="sidebar-user-name">

👤 {display_name}

</div>

<div class="sidebar-user-rank">

{rank}

</div>

<div class="sidebar-user-xp">

⭐ {xp} XP

</div>

</div>

<hr>
""",
        unsafe_allow_html=True,
    )
    # ==========================================================
# SIDEBAR NAVIGATION
# ==========================================================

with st.sidebar:

    navigation_pages = [

        "Home",

        "Dance Analysis",

        "AI Analysis",

        "Performance",

        "Analytics",

        "Skeleton Studio",

        "Achievements",

        "Reports",

        "Profile",

        "About"

    ]

    for item in navigation_pages:

        active = item == st.session_state.page

        button_type = "primary" if active else "secondary"

        if st.button(

            item,

            key=f"nav_{item}",

            use_container_width=True,

            type=button_type

        ):

            st.session_state.page = item

            st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

# ==========================================================
# PAGE ROUTER
# ==========================================================

page = st.session_state.page

if page == "Home":

    show_home()

elif page == "Dance Analysis":

    show_dance_studio()

elif page == "AI Analysis":

    show_analysis()

elif page == "Performance":

    show_performance()

elif page == "Analytics":

    show_analytics()

elif page == "Skeleton Studio":

    show_skeleton()

elif page == "Achievements":

    show_achievements()

elif page == "Reports":

    show_reports()

elif page == "Profile":

    show_profile()

elif page == "About":

    show_about()

elif page == "❓ Help":

    show_help()

    # ==========================================================
# SIDEBAR UTILITIES
# ==========================================================

with st.sidebar:

    st.markdown("<hr>", unsafe_allow_html=True)

    if st.button(
    "❓ Help",
    use_container_width=True,
    key="help_shortcut"
):
        st.session_state.page = "❓ Help"
        st.rerun()

    if st.button(

        "🚪 Logout",

        use_container_width=True,

        key="logout"

    ):

        st.session_state.clear()
        stamp_session()

        st.rerun()

    st.markdown("<hr>", unsafe_allow_html=True)

    st.markdown(
        """
<div class="sidebar-footer">

Cadence AI v1.0

<br>

Built with ❤️

<br>

OpenCV • MediaPipe

</div>
""",
        unsafe_allow_html=True,
    )
