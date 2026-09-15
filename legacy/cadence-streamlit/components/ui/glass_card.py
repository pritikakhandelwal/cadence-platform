import streamlit as st

from modules.html_safety import escape_html


def glass_card(title, content):

    _title = escape_html(title)
    _content = escape_html(content)

    st.markdown(
        f"""
        <div class="summary-card">

            <div class="summary-title">
                {_title}
            </div>

            <div class="summary-text">
                {_content}
            </div>

        </div>
        """,
        unsafe_allow_html=True
    )