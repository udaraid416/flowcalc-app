import streamlit as st
import streamlit.components.v1 as components

# Page configurations
st.set_page_config(page_title="FlowCalc Console", layout="wide", initial_sidebar_state="collapsed")

# Read the HTML file
with open("index.html", "r", encoding="utf-8") as f:
    html_code = f.read()

# Render HTML in Streamlit
components.html(html_code, height=950, scrolling=True)