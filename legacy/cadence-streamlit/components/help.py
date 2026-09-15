import streamlit as st


def show_help():

    # ==========================================================
    # HEADER
    # ==========================================================

    st.markdown(
        """
<div class="help-title">

❓ Help Center

</div>

<div class="help-subtitle">

Everything you need to get started with Cadence AI

</div>
""",
        unsafe_allow_html=True
    )

    st.divider()

    # ==========================================================
    # GETTING STARTED
    # ==========================================================

    st.markdown(
        """
<h3 class="help-heading">

🚀 Getting Started

</h3>
""",
        unsafe_allow_html=True
    )

    steps = [

        "Upload a professional reference dance video.",

        "Upload your own dance performance.",

        "Run AI Analysis to compare both performances.",

        "View similarity scores, analytics and AI-generated reports.",

        "Track your achievements and improve over time."

    ]

    for i, step in enumerate(steps, start=1):

        st.markdown(
            f"""
<div class="help-step">

<b>Step {i}</b><br>

{step}

</div>
""",
            unsafe_allow_html=True
        )

    st.divider()

        # ==========================================================
    # SUPPORTED VIDEO FORMATS
    # ==========================================================

    st.markdown(
        """
<h3 class="help-heading">

🎥 Supported Video Formats

</h3>
""",
        unsafe_allow_html=True
    )

    formats = [
        "MP4 (.mp4)",
        "AVI (.avi)",
        "MOV (.mov)"
    ]

    for fmt in formats:

        st.markdown(
            f"""
<div class="help-item">

✓ {fmt}

</div>
""",
            unsafe_allow_html=True
        )

    st.divider()

    # ==========================================================
    # HOW CADENCE WORKS
    # ==========================================================

    st.markdown(
        """
<h3 class="help-heading">

🧠 How Cadence Works

</h3>
""",
        unsafe_allow_html=True
    )

    workflow = [

        (
            "🎥 Video Processing",
            "Cadence extracts every frame from both the reference and performance videos."
        ),

        (
            "🦴 Pose Detection",
            "MediaPipe Pose detects 33 body landmarks from each frame."
        ),

        (
            "📐 Movement Comparison",
            "Dynamic Time Warping (DTW) aligns and compares the dancer's movements with the reference."
        ),

        (
            "📊 AI Evaluation",
            "Similarity scores, analytics and detailed reports are generated automatically."
        )

    ]

    for title, desc in workflow:

        st.markdown(
            f"""
<div class="help-item">

<b>{title}</b><br>

{desc}

</div>
""",
            unsafe_allow_html=True
        )

    st.divider()

    # ==========================================================
    # SIMILARITY SCORE GUIDE
    # ==========================================================

    st.markdown(
        """
<h3 class="help-heading">

📊 Understanding Similarity Scores

</h3>
""",
        unsafe_allow_html=True
    )

    score_table = [
        ("🟢", "90–100%", "Excellent"),
        ("🟡", "75–89%", "Very Good"),
        ("🟠", "60–74%", "Good"),
        ("🔴", "Below 60%", "Needs Improvement")
    ]

    for color, score, remark in score_table:

        st.markdown(
            f"""
<div class="score-guide">

<span class="score-icon">{color}</span>

<div>

<b>{score}</b><br>

{remark}

</div>

</div>
""",
            unsafe_allow_html=True
        )

    st.divider()

        # ==========================================================
    # FREQUENTLY ASKED QUESTIONS
    # ==========================================================

    st.markdown(
        """
<h3 class="help-heading">

❓ Frequently Asked Questions

</h3>
""",
        unsafe_allow_html=True
    )

    faqs = [

        (
            "How accurate is Cadence AI?",
            "Cadence compares body landmarks using MediaPipe Pose and Dynamic Time Warping (DTW), providing a reliable similarity score based on movement patterns."
        ),

        (
            "Which video formats are supported?",
            "Cadence currently supports MP4, AVI and MOV video formats."
        ),

        (
            "Why is my similarity score low?",
            "Low scores can result from differences in timing, body posture, camera angle, lighting conditions or incomplete visibility of body landmarks."
        ),

        (
            "Do both videos need the same duration?",
            "No. Dynamic Time Warping (DTW) automatically aligns dance sequences of different lengths before comparison."
        ),

        (
            "Does Cadence store my videos?",
            "No. Cadence processes videos locally. Videos are not uploaded or stored unless you explicitly choose to save generated reports or overlays."
        )

    ]

    for question, answer in faqs:

        with st.expander(question):

            st.write(answer)

    st.divider()

    # ==========================================================
    # CONTACT & SUPPORT
    # ==========================================================

    st.markdown(
        """
<h3 class="help-heading">

💬 Contact & Support

</h3>
""",
        unsafe_allow_html=True
    )

    st.markdown(
        """
<div class="help-contact">

If you experience any issues while using Cadence or have suggestions for future improvements, feel free to contact the developer.

<br><br>

<b>Developer:</b> Pritika Khandelwal

<br>

<b>Contact:</b> +91 9930840862

<br>

<b>Version:</b> Cadence AI v1.0

</div>
""",
        unsafe_allow_html=True
    )

    st.divider()

    # ==========================================================
    # FOOTER
    # ==========================================================

    st.markdown(
        """
<div class="help-footer">

Cadence AI • AI-Powered Dance Performance Evaluation System

<br><br>

Built with ❤️ using Python • Streamlit • OpenCV • MediaPipe

</div>
""",
        unsafe_allow_html=True
    )