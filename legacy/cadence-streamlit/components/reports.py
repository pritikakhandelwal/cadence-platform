import streamlit as st

from datetime import datetime

from modules.database import get_achievement_data
from modules.html_safety import escape_html


def show_reports():

    # ==========================================================
    # LOGIN CHECK
    # ==========================================================

    if not st.session_state.get(
        "logged_in",
        False
    ):

        st.warning(
            "🔒 Please login first."
        )

        return

    # ==========================================================
    # ANALYSIS CHECK
    # ==========================================================

    if not st.session_state.get(
        "analysis_complete",
        False
    ):

        st.warning(
            "⚠ Please complete a dance analysis first."
        )

        return

    # ==========================================================
    # USER DATA
    # ==========================================================

    user = st.session_state["user"]
    display_name = escape_html(user[1])
    display_email = escape_html(user[2])

    total, best, average = get_achievement_data(
        user[0]
    )

    distance = st.session_state["distance"]

    feedback = st.session_state["feedback"]
    display_feedback = escape_html(feedback)

    similarity = max(
        0,
        min(
            100,
            100 - distance * 2
        )
    )

    pose_accuracy = min(
        100,
        similarity + 3
    )

    timing = max(
        0,
        similarity - 4
    )

    synchronization = max(
        0,
        similarity - 2
    )

    xp = min(
        int(
            total * 100 +
            best * 10
        ),
        2500
    )

    # ==========================================================
    # RANK
    # ==========================================================

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

    report_date = datetime.now().strftime(
        "%d %B %Y"
    )

    # ==========================================================
    # REPORT HEADER
    # ==========================================================

    st.markdown(

        f"""

<div class="report-cover">

<div class="cover-logo">

💃 CADENCE AI

</div>

<div class="cover-title">

Dance Performance Evaluation

</div>

<div class="cover-subtitle">

Powered by OpenCV • MediaPipe • Dynamic Time Warping

</div>

<hr>

<div class="cover-user">

<div>

👤 {display_name}

</div>

<div>

📧 {display_email}

</div>

<div>

📅 {report_date}

</div>

</div>

</div>

""",

        unsafe_allow_html=True

    )

    st.divider()
        # ==========================================================
    # AI EVALUATION REPORT
    # ==========================================================

    st.subheader("📋 AI Evaluation Report")

    st.markdown(
        f"""
<div class="report-summary">

<h2>Dance Performance Evaluation</h2>

<hr>

<h3>📊 Performance Overview</h3>

<ul>

<li><b>Similarity Score</b> : {similarity:.1f}%</li>

<li><b>DTW Distance</b> : {distance:.2f}</li>

<li><b>Current Rank</b> : {rank}</li>

<li><b>XP Earned</b> : {xp}</li>

</ul>

<h3>🦴 Technical Analysis</h3>

<ul>

<li><b>Pose Accuracy</b> : {pose_accuracy:.1f}%</li>

<li><b>Timing Accuracy</b> : {timing:.1f}%</li>

<li><b>Synchronization</b> : {synchronization:.1f}%</li>

</ul>

<h3>📈 Performance Statistics</h3>

<ul>

<li><b>Total Analyses</b> : {total}</li>

<li><b>Best Similarity</b> : {best:.1f}%</li>

<li><b>Average Similarity</b> : {average:.1f}%</li>

</ul>

<h3>🤖 AI Coach Remarks</h3>

<p>

{display_feedback}

</p>

</div>
""",
        unsafe_allow_html=True
    )

    st.divider()
        # ==========================================================
    # OVERALL GRADE
    # ==========================================================

    st.subheader("🎓 Overall Grade")

    if similarity >= 95:

        grade = "A+"

        remark = "Outstanding Performance"

    elif similarity >= 90:

        grade = "A"

        remark = "Excellent Performance"

    elif similarity >= 80:

        grade = "B+"

        remark = "Very Good Performance"

    elif similarity >= 70:

        grade = "B"

        remark = "Good Performance"

    elif similarity >= 60:

        grade = "C"

        remark = "Average Performance"

    else:

        grade = "Needs Practice"

        remark = "Keep Practicing!"

    st.markdown(
    f"""
<div class="grade-card">

<h1>{grade}</h1>

<h3>{remark}</h3>

<p>

Overall Similarity

<br>

<b>{similarity:.1f}%</b>

</p>

</div>
""",
    unsafe_allow_html=True
)

    st.divider()

    # ==========================================================
    # AI RECOMMENDATIONS
    # ==========================================================

    st.subheader("🎯 AI Recommendations")

    recommendations = []

    if similarity >= 95:

        recommendations = [

            "Outstanding performance! Maintain your consistency.",

            "Experiment with more advanced choreography.",

            "Keep practicing to preserve your precision."

        ]

    elif similarity >= 85:

        recommendations = [

            "Excellent performance with only minor improvements needed.",

            "Focus on smoother transitions between dance moves.",

            "Continue refining your synchronization."

        ]

    elif similarity >= 70:

        recommendations = [

            "Practice the routine a few more times.",

            "Improve body alignment during transitions.",

            "Work on maintaining consistent rhythm."

        ]

    else:

        recommendations = [

            "Break the choreography into smaller sections.",

            "Practice in front of a mirror.",

            "Repeat difficult sequences before attempting the full routine."

        ]

    for rec in recommendations:

        st.markdown(
            f"""
<div class="recommendation-card">

✅ {rec}

</div>
""",
            unsafe_allow_html=True
        )

    st.divider()
        # ==========================================================
    # DOWNLOADABLE REPORT
    # ==========================================================

    report = f"""
====================================================
                CADENCE AI REPORT
====================================================

Dance Performance Evaluation

----------------------------------------------------

Name                : {user[1]}
Email               : {user[2]}
Report Date         : {report_date}

----------------------------------------------------
PERFORMANCE OVERVIEW
----------------------------------------------------

Similarity Score    : {similarity:.1f}%
DTW Distance        : {distance:.2f}

Current Rank        : {rank}
XP Earned           : {xp}

----------------------------------------------------
TECHNICAL ANALYSIS
----------------------------------------------------

Pose Accuracy       : {pose_accuracy:.1f}%
Timing Accuracy     : {timing:.1f}%
Synchronization     : {synchronization:.1f}%

----------------------------------------------------
PERFORMANCE STATISTICS
----------------------------------------------------

Total Analyses      : {total}
Best Similarity     : {best:.1f}%
Average Similarity  : {average:.1f}%

----------------------------------------------------
OVERALL GRADE
----------------------------------------------------

{grade}

{remark}

----------------------------------------------------
AI COACH REMARKS
----------------------------------------------------

{feedback}

----------------------------------------------------
AI RECOMMENDATIONS
----------------------------------------------------

"""

    for recommendation in recommendations:

        report += f"• {recommendation}\n"

    report += """

----------------------------------------------------

Generated by CADENCE AI
AI Powered Dance Performance Evaluation

====================================================
"""

    st.download_button(

        "📥 Download AI Evaluation Report",

        data=report,

        file_name="Cadence_AI_Report.txt",

        mime="text/plain",

        use_container_width=True

    )

    st.divider()

    st.success(

        "✅ Dance Performance Evaluation generated successfully."

    )

    st.caption(

        "Cadence AI • Built with OpenCV, MediaPipe & Dynamic Time Warping"

    )
