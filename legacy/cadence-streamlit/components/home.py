import streamlit as st
from components.ui.hero import hero

def show_home():

    # =====================================================
    # HERO
    # =====================================================

    hero()

    st.markdown(
        """
<div class="home-tagline">

Inspired by Movement. Powered by Intelligence.

</div>
""",
        unsafe_allow_html=True
    )

    st.write("")
    # =====================================================
    # WHY CHOOSE CADENCE
    # =====================================================

    features = [
        (
            "psychology",
            "AI-Powered Analysis",
            "Analyze dance performances using OpenCV, MediaPipe Pose and Dynamic Time Warping to deliver intelligent movement comparison and precise similarity evaluation."
        ),
        (
            "accessibility_new",
            "Skeleton Tracking",
            "Track and visualize 33 body landmarks in real time to understand posture, body alignment and movement accuracy."
        ),
        (
            "monitoring",
            "Performance Insights",
            "Receive detailed similarity scores, movement analytics and AI-generated feedback to continuously improve your dance performance."
        ),
        (
            "emoji_events",
            "Achievements & Progress",
            "Earn XP, unlock ranks and achievements, and monitor your improvement throughout your dance journey."
        )
    ]

    for icon, title, description in features:
        st.markdown(
            f"""
<div class="home-feature">
<div class="feature-icon-circle">
<span class="material-symbols-rounded">
{icon}
</span>
</div>
<div class="home-feature-content">
<div class="home-feature-title">
{title}
</div>
<div class="home-feature-description">
{description}
</div>
</div>
</div>
<div class="feature-divider"></div>
""",
            unsafe_allow_html=True
        )

    st.write("")
    st.divider()
    st.write("")
    st.divider()


    # =====================================================
    # ABOUT
    # =====================================================

    st.markdown(
        """
<div class="about-home-title">
✨ About Cadence
</div>
""",
        unsafe_allow_html=True
    )

    st.markdown(
        """
<div class="about-home-text">
Cadence is an AI-powered dance performance evaluation platform that compares a user's dance performance with a professional reference using computer vision and pose estimation.

By combining MediaPipe Pose and Dynamic Time Warping (DTW), the system analyzes movement similarity, generates detailed performance insights, tracks achievements and XP progression, and produces comprehensive AI-powered evaluation reports to help dancers continuously improve their skills.
</div>
""",
        unsafe_allow_html=True
    )

    st.write("")
    st.write("")

    if st.button(
        "🚀 START DANCE ANALYSIS",
        use_container_width=True,
        key="start_dance_analysis_bottom"
    ):
        st.session_state.page = "Dance Analysis"
        st.rerun()