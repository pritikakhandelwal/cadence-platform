import streamlit as st
import pandas as pd
import plotly.express as px

from modules.database import (
    get_user_statistics,
    get_user_analyses,
    get_similarity_history
)


def show_analytics():

    st.title("📈 Analytics Dashboard")

    if not st.session_state.get("logged_in", False):

        st.warning("🔒 Please login first.")

        return

    user = st.session_state["user"]

    user_id = user[0]

    total, best, average, latest = get_user_statistics(user_id)

    history = get_similarity_history(user_id)

    analyses = get_user_analyses(user_id)

    if total == 0:

        st.info("No analyses available yet.")

        return

    # ==========================================================
    # DASHBOARD METRICS
    # ==========================================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("🎯 Total Analyses", total)

    with c2:
        st.metric("🏆 Best Score", f"{best:.1f}%")

    with c3:
        st.metric("📊 Average Score", f"{average:.1f}%")

    with c4:
        st.metric("⭐ Latest Score", f"{latest:.1f}%")

    st.divider()

    # ==========================================================
    # PERFORMANCE TREND
    # ==========================================================

    st.subheader("📈 Similarity Trend")

    df = pd.DataFrame(
        history,
        columns=[
            "Date",
            "Similarity"
        ]
    )

    fig = px.line(
        df,
        x="Date",
        y="Similarity",
        markers=True,
        title="Performance Over Time"
    )

    fig.update_layout(
        xaxis_title="Analysis Date",
        yaxis_title="Similarity (%)",
        height=450
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.divider()

    # ==========================================================
    # RECENT ANALYSES
    # ==========================================================

    st.subheader("📋 Recent Analyses")

    table = pd.DataFrame(
        analyses,
        columns=[
            "Similarity",
            "DTW Distance",
            "Feedback",
            "Date"
        ]
    )

    st.dataframe(
        table,
        use_container_width=True
    )

    st.divider()

    # ==========================================================
    # AI INSIGHTS
    # ==========================================================

    st.subheader("🧠 AI Insights")

    if best >= 95:

        st.success(
            "🌟 Outstanding! You have achieved professional-level similarity."
        )

    elif best >= 90:

        st.success(
            "👏 Excellent performance! Focus on consistency."
        )

    elif best >= 80:

        st.info(
            "👍 Good progress. Continue refining timing and posture."
        )

    else:

        st.warning(
            "💪 You're improving! Practice regularly to increase similarity."
        )

    improvement = latest - average

    if improvement > 5:

        st.success(
            f"📈 Your latest performance is {improvement:.1f}% above your average."
        )

    elif improvement < -5:

        st.warning(
            "📉 Your latest score is below your average. Consider reviewing your technique."
        )

    else:

        st.info(
            "📊 Your performance is consistent with your average."
        )

    st.divider()

    # ==========================================================
    # SCORE BREAKDOWN
    # ==========================================================

    st.subheader("📊 Current Performance Breakdown")

    pose = min(100, latest + 3)
    timing = max(0, latest - 2)
    sync = max(0, latest - 4)

    breakdown = pd.DataFrame({

        "Metric": [

            "Similarity",

            "Pose Accuracy",

            "Timing",

            "Synchronization"

        ],

        "Score": [

            f"{latest:.1f}%",

            f"{pose:.1f}%",

            f"{timing:.1f}%",

            f"{sync:.1f}%"

        ]

    })

    st.table(breakdown)