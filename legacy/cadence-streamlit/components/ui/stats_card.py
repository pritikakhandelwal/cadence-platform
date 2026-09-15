import streamlit as st

from modules.html_safety import escape_html


def stats_card(icon, value, title):

    _icon = escape_html(icon)
    _value = escape_html(value)
    _title = escape_html(title)

    html = f"""
<div style="
background:#151B2D;
padding:20px;
border-radius:18px;
border:2px solid #00CFFF;
text-align:center;
margin-bottom:20px;
">

<div style="font-size:36px;">
{_icon}
</div>

<div style="
font-size:34px;
font-weight:bold;
color:#00CFFF;
">
{_value}
</div>

<div style="
font-size:18px;
color:white;
">
{_title}
</div>

</div>
"""

    st.markdown(html, unsafe_allow_html=True)