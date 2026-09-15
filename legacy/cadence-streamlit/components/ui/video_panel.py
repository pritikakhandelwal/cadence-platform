import streamlit as st


def video_panel(title, key_name):

    st.markdown(f"### {title}")

    uploaded_video = st.file_uploader(
        "Upload MP4 video",
        type=["mp4"],
        key=key_name,
        label_visibility="collapsed",
        help="MP4 only, up to 250 MB and five minutes long.",
    )

    if uploaded_video is not None:

        st.success("Video selected successfully.")

        st.video(uploaded_video)

        st.caption(f"📄 {uploaded_video.name}")

    return uploaded_video
