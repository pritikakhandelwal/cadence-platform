from modules.dance_analyzer import analyze_dance

distance, feedback = analyze_dance(
    "data/professional/professional_dance.mp4",
    "data/users/user_dance.mp4"
)

print("\n========== AI Dance Analysis ==========\n")

print("Average DTW Distance:", round(distance, 2))

print("\nFeedback:")

for line in feedback:
    print("-", line)