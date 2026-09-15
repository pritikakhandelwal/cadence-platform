import streamlit as st


def show_analysis():

    st.title("🤖 AI Analysis")

    st.write("Your AI-generated dance performance analysis.")

    st.write("")

    # ==========================================
    # CHECK IF ANALYSIS HAS BEEN RUN
    # ==========================================

    if not st.session_state.get("analysis_complete", False):

        st.warning("⚠ Please complete an analysis from the Dance Studio first.")

        return

    # ==========================================
    # GET RESULTS
    # ==========================================

    distance = st.session_state["distance"]
    feedback = st.session_state["feedback"]

    # ==========================================
    # CONVERT DTW DISTANCE TO SCORE
    # ==========================================

    similarity = max(0, min(100, 100 - distance * 2))

    # ==========================================
    # PERFORMANCE LABEL
    # ==========================================

    if similarity >= 90:
        rating = "🌟 Excellent"

    elif similarity >= 80:
        rating = "✅ Very Good"

    elif similarity >= 70:
        rating = "👍 Good"

    elif similarity >= 60:
        rating = "🙂 Average"

    else:
        rating = "💪 Needs Improvement"

    # ==========================================
    # HERO SCORE
    # ==========================================

    st.metric(
        "⭐ Similarity Score",
        f"{similarity:.1f}%"
    )

    st.success(rating)

    st.write("")

    # ==========================================
    # SUMMARY
    # ==========================================

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric(
            "📏 DTW Distance",
            f"{distance:.2f}"
        )

    with c2:
        st.metric(
            "🏅 Rating",
            rating
        )

    with c3:
        st.metric(
            "🤖 AI Confidence",
            "95%"
        )

    st.write("")
    st.divider()

    # ==========================================
    # FEEDBACK
    # ==========================================

    st.subheader("🤖 AI Feedback")

    st.info(feedback)

    st.write("")
    st.divider()

    # ==========================================
    # RECOMMENDATION
    # ==========================================

    st.subheader("💡 Recommendation")

    if similarity >= 90:

        st.success(
            "Excellent performance! Focus on maintaining consistency and refining finer movements."
        )

    elif similarity >= 80:

        st.success(
            "Very good performance! Small improvements in synchronization will further enhance your dance."
        )

    elif similarity >= 70:

        st.warning(
            "Good progress. Continue practicing timing and posture to improve overall similarity."
        )

    else:

        st.error(
            "Keep practicing the routine. Focus on posture, balance and synchronization with the reference video."
        )

    st.write("")
    st.divider()

    # ==========================================
    # NEXT PAGE
    # ==========================================

    if st.button(
        "➡ Continue to Performance Dashboard",
        use_container_width=True,
        key="continue_to_perf_btn"
    ):
        st.session_state.page = "Performance"
        st.rerun()