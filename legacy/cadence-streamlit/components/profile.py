import streamlit as st

from modules.auth import register_user, login_user, PASSWORD_MINIMUM_LENGTH
from modules.database import get_user_analyses
from modules.input_validation import validate_registration_fields
from modules.session_security import stamp_session


def show_profile():

    st.title("👤 Profile")

    # =====================================
    # Session Check
    # =====================================

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if "user" not in st.session_state:
        st.session_state.user = None

    # =====================================
    # Logged In Screen
    # =====================================

    if st.session_state.logged_in:

        user = st.session_state.user

        st.success("✅ Logged in successfully!")

        st.subheader(f"Welcome, {user[1]} 👋")

        st.write(f"**📧 Email:** {user[2]}")
        st.write(f"**📅 Joined:** {user[3]}")

        analyses = get_user_analyses(user[0])

        total = len(analyses)

        if total > 0:

            similarities = [row[0] for row in analyses]

            best_score = max(similarities)

            avg_score = sum(similarities) / total

        else:

            best_score = 0

            avg_score = 0

        st.divider()

        st.subheader("📊 Statistics")

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Dance Analyses",
                total
            )

        with c2:
            st.metric(
                "Best Score",
                f"{best_score:.1f}%"
            )

        with c3:
            st.metric(
                "Average Accuracy",
                f"{avg_score:.1f}%"
            )

        if total > 0:

            st.divider()

            st.subheader("📜 Recent Analyses")

            for similarity, distance, feedback, date in analyses:

                with st.expander(
                    f"{date}   •   {similarity:.1f}%"
                ):

                    st.write(f"**Similarity:** {similarity:.1f}%")

                    st.write(f"**DTW Distance:** {distance:.2f}")

                    st.write("**Feedback:**")

                    st.write(feedback)

        st.divider()

        if st.button(
            "🚪 Logout",
            use_container_width=True
        ):

            st.session_state.logged_in = False
            st.session_state.user = None
            stamp_session()

            st.rerun()

        return

    # =====================================
    # Login / Signup Tabs
    # =====================================

    login_tab, signup_tab = st.tabs(
        [
            "🔑 Login",
            "📝 Sign Up"
        ]
    )

    # =====================================
    # LOGIN
    # =====================================

    with login_tab:

        st.subheader("Login")

        email = st.text_input(
            "Email",
            key="login_email"
        )

        password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button(
            "Login",
            use_container_width=True
        ):

            login_result = login_user(
                email,
                password
            )

            if login_result.user:

                st.session_state.logged_in = True
                st.session_state.user = login_result.user
                stamp_session()

                st.rerun()

            else:

                st.error(login_result.error or "Invalid email or password.")

    # =====================================
    # SIGNUP
    # =====================================

    with signup_tab:

        st.subheader("Create Account")

        name = st.text_input(
            "Full Name"
        )

        email = st.text_input(
            "Email Address"
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        confirm = st.text_input(
            "Confirm Password",
            type="password"
        )

        if st.button(
            "Create Account",
            use_container_width=True
        ):

            result = validate_registration_fields(
                name,
                email,
                password,
                confirm,
                password_minimum=PASSWORD_MINIMUM_LENGTH,
            )

            if not result.ok:
                st.error(result.error)

            else:

                success = register_user(
                    name,
                    email,
                    password
                )

                if success:

                    st.success(
                        "🎉 Account created successfully! You can now log in."
                    )

                else:

                    st.error(
                        "Email already exists."
                    )
