from modules.feature_extractor import extract_keypoints_from_video

shape = extract_keypoints_from_video(
    "data/professional/professional_dance.mp4",
    "extracted_keypoints/professional.npy"
)

print("Professional Video Shape:", shape)

shape = extract_keypoints_from_video(
    "data/users/user_dance.mp4",
    "extracted_keypoints/user.npy"
)

print("User Video Shape:", shape)