from modules.dtw_compare import compare_dances

similarity = compare_dances(
    "extracted_keypoints/professional.npy",
    "extracted_keypoints/user.npy"
)

print("Dance Similarity:", similarity, "%")