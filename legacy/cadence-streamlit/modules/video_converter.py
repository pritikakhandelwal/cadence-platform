import os

from modules.ffmpeg_utils import run_ffmpeg


def convert_to_h264(input_video, output_video):

    os.makedirs(os.path.dirname(output_video), exist_ok=True)

    command = [

        "ffmpeg",

        "-y",

        "-i", input_video,

        "-c:v", "libx264",

        "-preset", "fast",

        "-pix_fmt", "yuv420p",

        "-movflags", "+faststart",

        "-c:a", "aac",

        output_video

    ]

    run_ffmpeg(command, "convert this video")

    return output_video
