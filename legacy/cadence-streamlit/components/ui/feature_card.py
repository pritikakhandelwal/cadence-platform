import streamlit as st

from modules.html_safety import escape_html


def feature_card(icon, title, description):

    _icon = escape_html(icon)
    _title = escape_html(title)
    _description = escape_html(description)

    html = f"""
<div style="
background:#151B2D;
padding:30px;
border-radius:20px;
border:2px solid #00CFFF;
text-align:center;
margin-bottom:20px;
">
    <h1>{_icon}</h1>
    <h2>{_title}</h2>
    <p>{_description}</p>
</div>
"""

    st.markdown(html, unsafe_allow_html=True)