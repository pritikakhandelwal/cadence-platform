from modules.dtw_compare import compare_dances
from modules.feedback import generate_feedback

distance = compare_dances(
    "extracted_keypoints/professional.npy",
    "extracted_keypoints/user.npy"
)

print("Average DTW Distance:", distance)

feedback = generate_feedback(distance)

print("\nFeedback:")

for line in feedback:
    print("-", line)