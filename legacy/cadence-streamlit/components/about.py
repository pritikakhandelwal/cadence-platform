import streamlit as st


def show_about():

    # ==========================================================
    # HEADER
    # ==========================================================

    st.markdown(
        """
<div class="about-title">

CADENCE AI

</div>

<div class="about-subtitle">

AI-Powered Dance Performance Evaluation System

</div>
""",
        unsafe_allow_html=True
    )

    st.divider()

    # ==========================================================
    # VERSION
    # ==========================================================

    st.markdown(
        """
<h3 class="about-heading">

Version

</h3>

<p class="about-text">

v1.0

</p>
""",
        unsafe_allow_html=True
    )

    # ==========================================================
    # DEVELOPER
    # ==========================================================

    st.markdown(
        """
<h3 class="about-heading">

Developed By

</h3>

<p class="about-text">

Pritika Khandelwal

</p>
""",
        unsafe_allow_html=True
    )

    st.divider()

    # ==========================================================
    # TECHNOLOGY STACK
    # ==========================================================

    st.markdown(
        """
<h3 class="about-heading">

Technology Stack

</h3>
""",
        unsafe_allow_html=True
    )

    technologies = [

        "Python",

        "Streamlit",

        "OpenCV",

        "MediaPipe",

        "Dynamic Time Warping (DTW)",

        "NumPy",

        "SQLite"

    ]

    for tech in technologies:
        st.markdown(
        f"""
<div class="about-text">

• {tech}

</div>
""",
        unsafe_allow_html=True
    )

    st.divider()
        # ==========================================================
    # CORE FEATURES
    # ==========================================================

    st.markdown(
        """
<h3 class="about-heading">

Core Features

</h3>
""",
        unsafe_allow_html=True
    )

    features = [

        "AI Dance Performance Analysis",

        "Pose Detection & Skeleton Tracking",

        "Dynamic Time Warping Similarity",

        "Performance Analytics Dashboard",

        "Achievement & XP System",

        "AI Evaluation Reports",

        "User Profiles"

    ]

    for feature in features:
        st.markdown(
        f"""
<div class="about-text">

✔ {feature}

</div>
""",
        unsafe_allow_html=True
    )

    st.divider()

    # ==========================================================
    # PROJECT DESCRIPTION
    # ==========================================================

    st.markdown(
        """
<h3 class="about-heading">

Project Description

</h3>
""",
        unsafe_allow_html=True
    )

    st.markdown(
        """
<p class="about-description">

Cadence AI is an intelligent dance performance evaluation platform
designed to analyze and compare a dancer's performance against a
reference choreography using advanced computer vision techniques.

The system utilizes MediaPipe Pose for human pose estimation and
Dynamic Time Warping (DTW) to evaluate movement similarity.
It generates detailed performance analytics, tracks achievements
and XP progression, and produces AI-powered evaluation reports
that provide meaningful insights to help users improve their
dance performance.

</p>
""",
        unsafe_allow_html=True
    )

    st.divider()

    st.markdown(
    """
<div class="about-footer">

Cadence AI • AI-Powered Dance Performance Evaluation System

</div>
""",
    unsafe_allow_html=True
)