from modules.video_preprocessor import normalize_video
from modules.video_converter import convert_to_h264
from modules.feature_extractor import extract_keypoints_from_video
from modules.dtw_compare import compare_dances
from modules.feedback import generate_feedback
from modules.visualisation import create_overlay_video
from modules.workspace import AnalysisWorkspace


def analyze_dance(pro_video, user_video, workspace: AnalysisWorkspace):

    # ------------------------------------
    # Normalize uploaded videos
    # ------------------------------------

    normalized_pro = normalize_video(
        pro_video,
        str(workspace.professional_normalized)
    )

    normalized_user = normalize_video(
        user_video,
        str(workspace.user_normalized)
    )

    # ------------------------------------
    # Generate skeleton videos
    # ------------------------------------

    extract_keypoints_from_video(
        normalized_pro,
        str(workspace.professional_keypoints),
        str(workspace.professional_skeleton_raw)
    )

    extract_keypoints_from_video(
        normalized_user,
        str(workspace.user_keypoints),
        str(workspace.user_skeleton_raw)
    )

    # ------------------------------------
    # Convert skeleton videos to H264
    # ------------------------------------

    convert_to_h264(
        str(workspace.professional_skeleton_raw),
        str(workspace.professional_skeleton)
    )

    convert_to_h264(
        str(workspace.user_skeleton_raw),
        str(workspace.user_skeleton)
    )

    # ------------------------------------
    # Create overlay video
    # ------------------------------------

    create_overlay_video(
        str(workspace.professional_skeleton),
        str(workspace.user_skeleton),
        str(workspace.overlay_raw)
    )

    convert_to_h264(
        str(workspace.overlay_raw),
        str(workspace.overlay)
    )

    # ------------------------------------
    # Compare dances
    # ------------------------------------

    distance = compare_dances(
        str(workspace.professional_keypoints),
        str(workspace.user_keypoints)
    )

    # ------------------------------------
    # Generate feedback
    # ------------------------------------

    feedback = generate_feedback(distance)

    # Convert list feedback to string
    if isinstance(feedback, list):
        feedback = "\n".join(feedback)

    return distance, feedback
