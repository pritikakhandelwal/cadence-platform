def generate_feedback(distance):

    feedback = []

    if distance < 2:
        feedback.append("Excellent performance! Your dance closely matches the reference.")

    elif distance < 4:
        feedback.append("Very good performance. Minor improvements are needed.")

    elif distance < 6:
        feedback.append("Good attempt. Focus on improving synchronization and posture.")

    else:
        feedback.append("Keep practicing. Try to match the professional dancer more closely.")

    return feedback