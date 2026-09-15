import streamlit as st

from modules.database import get_achievement_data
from modules.html_safety import escape_html


def show_achievements():

    st.title("🏆 Achievements")

    # ==========================================================
    # LOGIN CHECK
    # ==========================================================

    if not st.session_state.get("logged_in", False):

        st.warning(
            "🔒 Please login from the Profile page first."
        )

        return

    # ==========================================================
    # USER DATA
    # ==========================================================

    user = st.session_state["user"]
    display_name = escape_html(user[1])

    total, best, average = get_achievement_data(
        user[0]
    )

    # ==========================================================
    # XP SYSTEM
    # ==========================================================

    xp = int(

        total * 100 +

        best * 10

    )

    max_xp = 2500

    xp = min(xp, max_xp)

    progress = int(

        xp / max_xp * 100

    )

    # ==========================================================
    # RANK SYSTEM
    # ==========================================================

    if xp >= 2200:

        rank = "👑 Diamond Dancer"

        next_rank = "Maximum Rank"

    elif xp >= 1700:

        rank = "💎 Platinum Dancer"

        next_rank = "👑 Diamond Dancer"

    elif xp >= 1200:

        rank = "🥇 Gold Dancer"

        next_rank = "💎 Platinum Dancer"

    elif xp >= 700:

        rank = "🥈 Silver Dancer"

        next_rank = "🥇 Gold Dancer"

    else:

        rank = "🥉 Bronze Dancer"

        next_rank = "🥈 Silver Dancer"

    # ==========================================================
    # HERO CARD
    # ==========================================================

    st.markdown(

        f"""

<div class="rank-card">

<h2>

🏆 {rank}

</h2>

<h4>

{display_name}

</h4>

<p>

Current XP

</p>

<h2 style="color:#22c55e;">

{xp} / {max_xp}

</h2>

<p>

{progress}% Completed

</p>

</div>

""",

        unsafe_allow_html=True

    )

    # ==========================================================
    # XP BAR
    # ==========================================================

    st.subheader("⭐ XP Progress")

    st.markdown(

        f"""

<div class="xp-container">

<div
class="xp-fill"
style="width:{progress}%;">
</div>

</div>

<div class="xp-text">

{progress}% Complete

</div>

""",

        unsafe_allow_html=True,

    )

    st.divider()
        # ==========================================================
    # NEXT GOAL
    # ==========================================================

    st.subheader("🎯 Next Goal")

    remaining_analyses = max(
        0,
        20 - total
    )

    remaining_similarity = max(
        0,
        90 - best
    )

    col1, col2 = st.columns(2)

    with col1:

        st.metric(
            "🏆 Current Rank",
            rank
        )

    with col2:

        st.metric(
            "🚀 Next Rank",
            next_rank
        )

    st.info(
        f"""
To unlock your next rank, you need:

• {remaining_analyses} more completed analyses

• {remaining_similarity:.1f}% more best similarity
"""
    )

    st.divider()

    # ==========================================================
    # ACHIEVEMENTS
    # ==========================================================

    st.subheader("🏅 Achievement Collection")

    achievements = [

        (
            "🎉 First Steps",
            "Complete your first dance analysis.",
            total >= 1
        ),

        (
            "🥉 Beginner Dancer",
            "Complete 5 dance analyses.",
            total >= 5
        ),

        (
            "🥈 Consistent Performer",
            "Complete 10 dance analyses.",
            total >= 10
        ),

        (
            "🥇 Dance Master",
            "Complete 20 dance analyses.",
            total >= 20
        ),

        (
            "⭐ Rising Star",
            "Reach 80% similarity.",
            best >= 80
        ),

        (
            "💎 Elite Performer",
            "Reach 90% similarity.",
            best >= 90
        ),

        (
            "👑 Perfect Performer",
            "Reach 95% similarity.",
            best >= 95
        )

    ]

    unlocked = 0

    cols = st.columns(2)

    for index, (title, description, earned) in enumerate(achievements):

        with cols[index % 2]:

            if earned:

                unlocked += 1

                st.markdown(
                    f"""
<div class="badge-card">

<div class="badge-title">
{title}
</div>

<div class="badge-desc">
{description}
</div>

<div class="badge-unlocked">
✅ Unlocked
</div>

</div>
""",
                    unsafe_allow_html=True,
                )

            else:

                st.markdown(
                    f"""
<div class="badge-card">

<div class="badge-title">
{title}
</div>

<div class="badge-desc">
{description}
</div>

<div class="badge-locked">
🔒 Locked
</div>

</div>
""",
                    unsafe_allow_html=True,
                )

    st.divider()
        # ==========================================================
    # OVERALL PROGRESS
    # ==========================================================

    st.subheader("📈 Overall Progress")

    completion = int(

        unlocked / len(achievements) * 100

    )

    st.progress(

        completion / 100

    )

    st.write(

        f"### {unlocked} / {len(achievements)} Achievements Unlocked"

    )

    st.write(

        f"Overall Completion: **{completion}%**"

    )

    st.divider()

    # ==========================================================
    # PLAYER STATISTICS
    # ==========================================================

    st.subheader("📊 Your Journey")

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(

            "Dance Analyses",

            total

        )

    with col2:

        st.metric(

            "Best Similarity",

            f"{best:.1f}%"

        )

    with col3:

        st.metric(

            "Average Similarity",

            f"{average:.1f}%"

        )

    st.divider()

    # ==========================================================
    # MOTIVATION
    # ==========================================================

    st.subheader("💬 Motivation")

    if completion == 100:

        st.success(

            """
🏆 Incredible!

You've unlocked every achievement in Cadence.

Keep practicing and maintain your incredible consistency!
"""

        )

    elif completion >= 80:

        st.success(

            """
🔥 Amazing work!

You're only a few achievements away from becoming a complete Dance Master.
"""

        )

    elif completion >= 50:

        st.info(

            """
⭐ Excellent progress!

Every practice session is making your movements cleaner and more synchronized.
"""

        )

    elif completion >= 25:

        st.info(

            """
💪 Nice progress!

Keep analysing your dances and you'll unlock achievements much faster.
"""

        )

    else:

        st.warning(

            """
🚀 Your journey has just begun!

Complete more analyses to earn XP, unlock badges and climb the ranks.
"""

        )

    st.divider()

    # ==========================================================
    # FOOTER
    # ==========================================================

    st.caption(

        "Practice consistently • Improve your timing • Master every routine 💃"

    )

    if st.button(
        "➡ Continue to Reports",
        use_container_width=True,
        key="continue_to_reports_btn"
    ):
        st.session_state.page = "Reports"
        st.rerun()
