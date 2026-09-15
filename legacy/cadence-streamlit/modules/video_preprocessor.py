import os

from modules.ffmpeg_utils import run_ffmpeg


def normalize_video(input_video, output_video):

    """
    Converts any uploaded video into:
    - 30 FPS
    - 720x1280 resolution
    - H.264 codec
    - AAC audio
    """

    os.makedirs(os.path.dirname(output_video), exist_ok=True)

    command = [

        "ffmpeg",

        "-y",

        "-i", input_video,

        "-vf", "fps=30,scale=720:1280",

        "-c:v", "libx264",

        "-preset", "medium",

        "-pix_fmt", "yuv420p",

        "-c:a", "aac",

        output_video

    ]

    run_ffmpeg(command, "prepare this video")

    return output_video
