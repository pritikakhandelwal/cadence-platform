import os
import streamlit as st


def show_skeleton():

    st.title("🦴 Skeleton Studio")

    st.write(
        "Compare the professional skeleton, your skeleton, and the AI-generated overlay."
    )

    st.write("")

    # ==================================================
    # CHECK ANALYSIS
    # ==================================================

    if not st.session_state.get("analysis_complete", False):

        st.warning(
            "⚠ Please complete an analysis from the Dance Studio first."
        )

        return

    # ==================================================
    # FILE PATHS
    # ==================================================

    professional_video = st.session_state.get(
        "analysis_pro_skeleton",
        "output/professional_skeleton.mp4"
    )

    user_video = st.session_state.get(
        "analysis_user_skeleton",
        "output/user_skeleton.mp4"
    )

    overlay_video = st.session_state.get(
        "analysis_overlay",
        "output/overlay.mp4"
    )

    # ==================================================
    # SIDE BY SIDE
    # ==================================================

    left, right = st.columns(2)

    with left:

        st.subheader("🎬 Professional Skeleton")

        if os.path.exists(professional_video):

            st.video(professional_video)

        else:

            st.error("Professional skeleton video not found.")

    with right:

        st.subheader("💃 Your Skeleton")

        if os.path.exists(user_video):

            st.video(user_video)

        else:

            st.error("User skeleton video not found.")

    st.write("")
    st.divider()

    # ==================================================
    # OVERLAY
    # ==================================================

    st.subheader("🦴 Overlay Comparison")

    if os.path.exists(overlay_video):

        st.video(overlay_video)

    else:

        st.error("Overlay video not found.")

    st.write("")
    st.divider()

    # ==================================================
    # MOVEMENT SUMMARY
    # ==================================================

    similarity = max(
        0,
        min(
            100,
            100 - st.session_state["distance"] * 2
        )
    )

    st.subheader("📊 Movement Summary")

    if similarity >= 90:

        st.success("✅ Excellent pose alignment")

        st.success("✅ Excellent synchronization")

        st.success("✅ Stable body posture")

        st.success("✅ Accurate lower body movement")

        st.success("✅ Strong overall performance")

    elif similarity >= 80:

        st.info("✅ Good pose alignment")

        st.info("✅ Good synchronization")

        st.info("⚠ Improve arm extension")

        st.info("⚠ Improve transition smoothness")

        st.info("✅ Stable balance")

    else:

        st.warning("⚠ Practice posture")

        st.warning("⚠ Improve synchronization")

        st.warning("⚠ Improve body balance")

        st.warning("⚠ Work on timing")

        st.warning("⚠ Continue practicing")

    st.write("")
    st.divider()

    if st.button(
        "➡ Continue to Achievements",
        use_container_width=True,
        key="continue_to_achieve_btn"
    ):
        st.session_state.page = "Achievements"
        st.rerun()