import os
import cv2


def create_overlay_video(
    professional_video,
    user_video,
    output_video
):
    """
    Creates a synchronized side-by-side comparison video.
    """

    cap1 = cv2.VideoCapture(professional_video)
    cap2 = cv2.VideoCapture(user_video)

    if not cap1.isOpened():
        if cap2.isOpened():
            cap2.release()
        raise RuntimeError("Cannot open professional skeleton video.")

    if not cap2.isOpened():
        cap1.release()
        raise RuntimeError("Cannot open user skeleton video.")

    width1 = int(cap1.get(cv2.CAP_PROP_FRAME_WIDTH))
    height1 = int(cap1.get(cv2.CAP_PROP_FRAME_HEIGHT))

    width2 = int(cap2.get(cv2.CAP_PROP_FRAME_WIDTH))
    height2 = int(cap2.get(cv2.CAP_PROP_FRAME_HEIGHT))

    width = width1 + width2
    height = max(height1, height2)

    # Force overlay to 30 FPS
    fps = 30

    os.makedirs(os.path.dirname(output_video), exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    writer = cv2.VideoWriter(
        output_video,
        fourcc,
        fps,
        (width, height)
    )

    if not writer.isOpened():
        cap1.release()
        cap2.release()
        raise RuntimeError("Cannot create overlay video.")

    try:
        while True:

            ret1, frame1 = cap1.read()
            ret2, frame2 = cap2.read()

            if not ret1 or not ret2:
                break

            frame1 = cv2.resize(frame1, (width1, height))
            frame2 = cv2.resize(frame2, (width2, height))

            overlay = cv2.hconcat([frame1, frame2])

            writer.write(overlay)
    finally:
        cap1.release()
        cap2.release()
        writer.release()

    return output_video