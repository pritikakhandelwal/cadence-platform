import os
import time
from pathlib import Path
import streamlit as st

from components.ui.video_panel import video_panel
from modules.dance_analyzer import analyze_dance
from modules.database import save_analysis
from modules.ffmpeg_utils import FFmpegError
from modules.video_validation import VideoValidationError, validate_saved_video, validate_uploaded_video
from modules.workspace import AnalysisWorkspace, create_analysis_workspace, remove_analysis_workspace


def save_uploaded_video(uploaded_file, save_path, workspace: AnalysisWorkspace | None = None) -> str:
    """
    Save an uploaded Streamlit video to disk within an isolated workspace.
    """
    target = Path(save_path).resolve()
    if workspace is not None:
        workspace_root = workspace.root.resolve()
        if workspace_root not in target.parents:
            raise VideoValidationError("Invalid upload destination.")

    os.makedirs(target.parent, exist_ok=True)

    with open(target, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return str(target)


def show_dance_studio():

    st.title("🎥 Dance Studio")

    st.write(
        "Upload a professional reference video and your own dance video to begin AI analysis."
    )

    st.write("")

    # ==========================================================
    # LOGIN CHECK
    # ==========================================================

    if not st.session_state.get("logged_in", False):

        st.warning("🔒 Please login from the Profile page before starting an analysis.")

        return

    left, right = st.columns(2)

    with left:

        professional_video = video_panel(
            "Professional Dance",
            "professional_video"
        )

    with right:

        user_video = video_panel(
            "Your Dance",
            "user_video"
        )

    st.write("")
    st.divider()

    if professional_video and user_video:

        if st.button(
            "🔥 START AI ANALYSIS",
            use_container_width=True
        ):

            # ==========================================
            # SAVE UPLOADED VIDEOS
            # ==========================================

            workspace = None

            try:
                validate_uploaded_video(professional_video)
                validate_uploaded_video(user_video)
                workspace = create_analysis_workspace()

                pro_path = save_uploaded_video(
                    professional_video,
                    str(workspace.professional_upload),
                    workspace
                )
                user_path = save_uploaded_video(
                    user_video,
                    str(workspace.user_upload),
                    workspace
                )
                validate_saved_video(pro_path)
                validate_saved_video(user_path)

                st.success("✅ Videos validated successfully!")
                st.write("")
                st.subheader("🧠 AI Processing")

                progress = st.progress(0)
                status = st.empty()
                console = st.empty()
                logs = []
                steps = [
                    ("🎥 Reading Professional Video...", 15),
                    ("🎥 Reading User Video...", 30),
                    ("🦴 Detecting Human Pose...", 45),
                    ("📌 Extracting Body Keypoints...", 60),
                    ("📊 Comparing Dance Motion...", 80),
                ]

                for message, value in steps:
                    progress.progress(value)
                    status.info(message)
                    logs.append(f"✔ {message}")
                    console.code("\n".join(logs))
                    time.sleep(0.6)

                distance, feedback = analyze_dance(pro_path, user_path, workspace)

            except (VideoValidationError, FFmpegError, ValueError) as error:
                if workspace is not None:
                    remove_analysis_workspace(workspace)
                st.error(str(error))
                return
            except Exception:
                if workspace is not None:
                    remove_analysis_workspace(workspace)
                st.error("Analysis could not be completed. Please try different MP4 videos.")
                return

            progress.progress(100)

            logs.append("✔ 🤖 AI Feedback Generated")
            logs.append("✔ ✅ Analysis Complete")

            console.code("\n".join(logs))

            status.success("Analysis Completed Successfully!")

            # ==========================================
            # CALCULATE SIMILARITY
            # ==========================================

            similarity = max(
                0,
                min(
                    100,
                    100 - distance * 2
                )
            )

            # ==========================================
            # SAVE RESULTS TO SESSION
            # ==========================================

            st.session_state["distance"] = distance
            st.session_state["feedback"] = feedback
            st.session_state["analysis_complete"] = True
            st.session_state["analysis_run_id"] = workspace.run_id
            st.session_state["analysis_overlay"] = str(workspace.overlay)
            st.session_state["analysis_pro_skeleton"] = str(workspace.professional_skeleton)
            st.session_state["analysis_user_skeleton"] = str(workspace.user_skeleton)

            # ==========================================
            # SAVE RESULTS TO DATABASE
            # ==========================================

            try:

                user = st.session_state["user"]

                save_analysis(
                    user[0],
                    similarity,
                    distance,
                    feedback
                )

                st.success("✅ Analysis saved to database!")

            except Exception as e:

                st.error(f"❌ Database Error: {e}")

            # ==========================================
            # DISPLAY RESULTS
            # ==========================================

            st.success("🎉 AI Analysis Completed Successfully!")

            st.metric(
                "Similarity Score",
                f"{similarity:.1f}%"
            )

            st.metric(
                "DTW Distance",
                f"{distance:.2f}"
            )

            st.info(feedback)

            if st.button(
                "➡ View AI Analysis",
                use_container_width=True,
                key="view_ai_analysis_btn"
            ):
                st.session_state.page = "AI Analysis"
                st.rerun()
