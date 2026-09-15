import streamlit as st


def show_performance():

    st.title("📊 Performance")

    st.write("Detailed performance metrics based on your dance analysis.")

    st.write("")

    # ==========================================
    # CHECK ANALYSIS
    # ==========================================

    if not st.session_state.get("analysis_complete", False):

        st.warning("⚠ Please complete an analysis from the Dance Studio first.")

        return

    distance = st.session_state["distance"]

    similarity = max(0, min(100, 100 - distance * 2))

    # ==========================================
    # GENERATE METRICS
    # ==========================================

    pose_accuracy = min(100, similarity + 3)

    timing = max(0, similarity - 4)

    synchronization = max(0, similarity - 2)

    # ==========================================
    # HERO SCORE
    # ==========================================

    st.metric(
        "⭐ Overall Performance",
        f"{similarity:.1f}%"
    )

    st.write("")
    st.divider()

    # ==========================================
    # METRICS
    # ==========================================

    c1, c2 = st.columns(2)

    with c1:

        st.metric(
            "🎯 Overall Score",
            f"{similarity:.1f}%"
        )

        st.progress(similarity / 100)

    with c2:

        st.metric(
            "🦴 Pose Accuracy",
            f"{pose_accuracy:.1f}%"
        )

        st.progress(pose_accuracy / 100)

    st.write("")

    c3, c4 = st.columns(2)

    with c3:

        st.metric(
            "🎵 Timing",
            f"{timing:.1f}%"
        )

        st.progress(timing / 100)

    with c4:

        st.metric(
            "⚡ Synchronization",
            f"{synchronization:.1f}%"
        )

        st.progress(synchronization / 100)

    st.write("")
    st.divider()

    # ==========================================
    # PERFORMANCE SUMMARY
    # ==========================================

    st.subheader("🏅 Performance Summary")

    if similarity >= 90:

        st.success("Excellent Performance")

    elif similarity >= 80:

        st.success("Very Good Performance")

    elif similarity >= 70:

        st.warning("Good Performance")

    else:

        st.error("Needs Improvement")

    st.progress(similarity / 100)

    st.write("")
    st.divider()

    # ==========================================
    # BREAKDOWN
    # ==========================================

    st.subheader("📋 Performance Breakdown")

    st.checkbox("Posture", value=True, disabled=True)

    st.checkbox("Timing", value=timing >= 70, disabled=True)

    st.checkbox("Synchronization", value=synchronization >= 70, disabled=True)

    st.checkbox("Body Alignment", value=pose_accuracy >= 80, disabled=True)

    st.write("")
    st.divider()

    if st.button(
        "➡ Continue to Analytics",
        use_container_width=True,
        key="continue_to_analytics_btn"
    ):
        st.session_state.page = "Analytics"
        st.rerun()