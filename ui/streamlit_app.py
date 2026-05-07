from __future__ import annotations

import os

import streamlit as st
import httpx

PUBLIC_API_URL = os.getenv("PUBLIC_API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Rozgaar AI", layout="wide")

st.title("Rozgaar AI Job Agent")

if st.button("Check API health"):
    try:
        response = httpx.get(f"{PUBLIC_API_URL}/health", timeout=5)
        st.success(response.json())
    except Exception as exc:
        st.error(str(exc))

st.subheader("Pipeline")
with st.form("pipeline_start"):
    query = st.text_input("Target role", value="Data Scientist")
    location = st.text_input("Location", value="Remote")
    submitted = st.form_submit_button("Start discovery")

if submitted:
    st.info(
        "Use the FastAPI docs at "
        f"{PUBLIC_API_URL}/docs to authenticate, then call /api/v1/pipeline/start."
    )
