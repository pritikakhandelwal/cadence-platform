import numpy as np
from dtaidistance import dtw

def compare_dances(professional_file, user_file):

    professional = np.load(professional_file)
    user = np.load(user_file)

    min_frames = min(len(professional), len(user))

    if min_frames == 0:
        raise ValueError(
            "No reliable pose landmarks were detected in one or both videos. "
            "Use a well-lit, full-body video and try again."
        )

    total_distance = 0

    for i in range(min_frames):
        total_distance += dtw.distance(
            professional[i],
            user[i]
        )

    average_distance = total_distance / min_frames

    print("Average DTW Distance:", average_distance)

    return average_distance
