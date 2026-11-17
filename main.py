"""LAIKA letter studio, protected by the configured MyKey access key."""

import hashlib
import hmac

import streamlit as st

from configuration import read_setting
from studio import render_studio


def configured_key() -> str | None:
    """Support Streamlit Cloud Secrets and local configuration without caching keys."""
    return read_setting("MyKey")


def clear_result() -> None:
    st.session_state.pop("validation_result", None)


def validate_key() -> None:
    expected = configured_key()
    entered = st.session_state.get("key_input", "")
    if not expected:
        result = "unconfigured"
    elif not entered:
        result = "empty"
    elif hmac.compare_digest(entered.encode("utf-8"), expected.encode("utf-8")):
        result = "valid"
        st.session_state.auth_proof = hashlib.sha256(expected.encode("utf-8")).hexdigest()
        st.session_state.key_input = ""
    else:
        result = "invalid"
    st.session_state.validation_result = result


def authenticated() -> bool:
    expected = configured_key()
    proof = st.session_state.get("auth_proof", "")
    if not expected or not proof:
        return False
    return hmac.compare_digest(proof, hashlib.sha256(expected.encode("utf-8")).hexdigest())


def logout() -> None:
    for key in list(st.session_state):
        del st.session_state[key]


def clear_input() -> None:
    st.session_state.key_input = ""
    clear_result()


st.set_page_config(
    page_title="Laika · Letter studio",
    page_icon="✳",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;450;500;550;600;650;700&family=Manrope:wght@400;500;600;650;700;750;800&display=swap');
    :root { --ink: #192d2a; --muted: #687872; --green: #18634d; }
    .stApp { background: #f7f9f7; color: var(--ink); }
    html, body, [class*="css"], .stApp, .stButton button, .stTextArea textarea {
        font-family: 'DM Sans', sans-serif;
    }
    [data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 1190px; padding: 2.4rem 2.5rem 2rem; }
    .brand { display: flex; align-items: center; gap: 11px; font-family: 'Manrope', sans-serif;
        font-size: 25px; font-weight: 800; letter-spacing: -1px; }
    .brand-mark { display: inline-flex; align-items: center; justify-content: center;
        width: 38px; height: 38px; background: #1b604d; border-radius: 12px;
        color: #e2f6c8; font-size: 30px; font-weight: 500; }
    .top-status { display: flex; justify-content: flex-end; align-items: center; gap: 8px;
        color: #697a73; font-size: 12px; padding-top: 12px; }
    .status-dot { height: 7px; width: 7px; border-radius: 50%; background: #45876b; }
    .page-rule { border-top: 1px solid #e0e7e1; margin: 25px 0 72px; }
    .eyebrow { color: #427460; font-size: 11px; font-weight: 700;
        letter-spacing: 2px; text-transform: uppercase; margin-bottom: 19px; }
    .hero-title { font-family: 'Manrope', sans-serif; font-size: clamp(38px, 4.6vw, 57px);
        font-weight: 750; line-height: 1.12; letter-spacing: -2.8px; margin: 0 0 22px;
        color: #1d332c; }
    .hero-title span { color: #448468; }
    .hero-copy { font-size: 16px; line-height: 1.8; color: #6b7972; max-width: 370px; }
    .illustration { position: relative; width: 180px; height: 139px; margin: 31px 0 15px;
        display: flex; align-items: center; justify-content: center; }
    .illustration:before { content: ''; width: 123px; height: 123px; border-radius: 50%;
        background: #e8efe5; position: absolute; }
    .illustration svg { position: relative; transform: rotate(-12deg); }
    .small-note { color: #7a877f; font-size: 12px; line-height: 1.7; }
    .st-key-verification_panel { background: #fff; border: 1px solid #e0e7df !important;
        border-radius: 20px !important; padding: 31px !important;
        box-shadow: 0 12px 38px #233e2e06; }
    .panel-heading { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }
    .panel-icon { display: flex; align-items: center; justify-content: center; width: 39px;
        height: 39px; border: 1px solid #e1e9df; border-radius: 11px; background: #f7faf5; }
    .panel-heading h2 { font-family: 'Manrope', sans-serif; font-size: 20px;
        font-weight: 750; letter-spacing: -.6px; margin: 0; padding: 0; color: #20382e; }
    .panel-copy { color: #78847d; font-size: 13px; line-height: 1.7; margin: -7px 0 20px; }
    .stTextArea label p { color: #34483d; font-weight: 600; font-size: 13px; }
    .stTextArea textarea { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 13px; line-height: 1.65; background: #fbfcfa; border-radius: 10px;
        caret-color: #18634d; }
    [data-testid="stTextArea"] > div { border-radius: 10px; }
    .stButton button[kind="primary"] { background: #20634e; border: 1px solid #20634e;
        border-radius: 10px; min-height: 47px; font-weight: 600; transition: background .15s; }
    .stButton button[kind="primary"]:hover { background: #174b3b; border-color: #174b3b; }
    .stButton button[kind="secondary"] { border-radius: 9px; color: #66786e;
        border-color: #e3e9e0; font-size: 12px; }
    .stButton button:focus-visible { outline: 3px solid #8cbd97; outline-offset: 3px; }
    .input-hint { font-size: 11px; color: #89938d; margin: -3px 0 16px; line-height: 1.6; }
    .privacy-note { border-top: 1px solid #edf0ea; margin-top: 20px; padding-top: 18px;
        font-size: 11px; color: #859087; display: flex; gap: 8px; align-items: center; }
    .how-heading { font-size: 11px; letter-spacing: 1.7px; font-weight: 650;
        color: #78867e; margin: 64px 0 22px; }
    .steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 28px;
        padding-bottom: 38px; border-bottom: 1px solid #e0e7e1; }
    .step { display: flex; gap: 13px; }
    .step-number { color: #61816e; border: 1px solid #dce5da; border-radius: 50%;
        width: 28px; height: 28px; flex-shrink: 0; display: flex; align-items: center;
        justify-content: center; font-size: 11px; }
    .step h3 { font-size: 13px; margin: 3px 0 5px; padding: 0; font-weight: 600; }
    .step p { font-size: 12px; color: #829087; line-height: 1.7; margin: 0; }
    .footer { display: flex; justify-content: space-between; color: #8b968d;
        font-size: 11px; padding-top: 22px; }
    @media (max-width: 740px) {
        .block-container { padding: 1.3rem 1.2rem 2rem; }
        .page-rule { margin-bottom: 35px; }
        .hero-title { font-size: 42px; letter-spacing: -2px; }
        .illustration { display: none; }
        .small-note { margin-bottom: 24px; }
        .st-key-verification_panel { padding: 23px !important; }
        .steps { grid-template-columns: 1fr; gap: 23px; }
        .how-heading { margin-top: 40px; }
        .footer { gap: 20px; }
    }
    @media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
    </style>
    """,
    unsafe_allow_html=True,
)

ready = bool(configured_key())
unlocked = authenticated()
if st.session_state.get("auth_proof") and not unlocked:
    logout()
brand, status = st.columns([1, 1])
with brand:
    st.markdown('<div class="brand"><span class="brand-mark">✳</span> laika<span style="color:#70917b">.</span></div>', unsafe_allow_html=True)
with status:
    st.markdown(
        f'<div class="top-status"><span class="status-dot"></span>{"Letter studio · Unlocked" if unlocked else "Private workspace" if ready else "Configuration needed"}</div>',
        unsafe_allow_html=True,
    )
st.markdown('<div class="page-rule"></div>', unsafe_allow_html=True)

if unlocked:
    render_studio(authenticated, logout)
    st.stop()

intro, form = st.columns([1.05, 1], gap="large")
with intro:
    st.markdown(
        """
        <div class="eyebrow">LAIKA · YOUR PRIVATE LETTER STUDIO</div>
        <h1 class="hero-title">Thoughtful words.<br><span>Meaningful support.</span></h1>
        <p class="hero-copy">A space to write for the work that matters.<br>Enter your access key to create a new letter,<br>inspired by LAIKA’s story and your own words.</p>
        <div class="illustration" aria-hidden="true">
          <svg width="147" height="113" viewBox="0 0 147 113" fill="none">
            <rect x="23" y="21" width="107" height="73" rx="14" fill="#FDFEFB" stroke="#B6CBB3" stroke-width="1.5"/>
            <rect x="32" y="30" width="89" height="55" rx="8" stroke="#E0E9DC"/>
            <circle cx="63" cy="57" r="13" fill="#E3EDDC" stroke="#679374" stroke-width="2"/>
            <circle cx="63" cy="57" r="4" fill="#FDFEFB" stroke="#679374" stroke-width="1.5"/>
            <path d="M76 57h29m-7 0v9m-9-9v6" stroke="#679374" stroke-width="3" stroke-linecap="round"/>
            <circle cx="124" cy="22" r="15" fill="#28684F"/>
            <path d="m118 22 4 4 8-9" stroke="#F5FAEC" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="m13 34 2-5 2 5 5 2-5 2-2 5-2-5-5-2 5-2Z" fill="#A1B99A"/>
          </svg>
        </div>
        <div class="small-note">For LAIKA – Trost auf vier Pfoten e.V.</div>
        """,
        unsafe_allow_html=True,
    )

with form:
    with st.container(border=True, key="verification_panel"):
        st.markdown(
            """
            <div class="panel-heading"><span class="panel-icon" aria-hidden="true">
            <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="#48735A" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="10" width="14" height="11" rx="3"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/></svg>
            </span><h2>Welcome to your studio</h2></div>
            <p class="panel-copy">Validate your access key to start writing.</p>
            """,
            unsafe_allow_html=True,
        )
        st.text_area(
            "Your key",
            key="key_input",
            placeholder="Paste or type your key here…",
            height=135,
            on_change=clear_result,
            help="Keys are case-sensitive. Spaces and line breaks must match exactly.",
        )
        st.markdown('<div class="input-hint">Case-sensitive · Check for extra spaces or line breaks.</div>', unsafe_allow_html=True)
        st.button(
            "Validate key  →",
            type="primary",
            use_container_width=True,
            disabled=not ready,
            on_click=validate_key,
            key="validate_button",
        )

        result = st.session_state.get("validation_result")
        if not ready or result == "unconfigured":
            st.error("Key verification is unavailable. Set MyKey in Streamlit Settings → Secrets, an environment variable, or the local .env file.")
        elif result == "valid":
            st.success("Key verified. Your key matches successfully.", icon="✅")
        elif result == "invalid":
            st.error("This key doesn't match. Check your key and try again.", icon="❌")
        elif result == "empty":
            st.warning("Enter your key before validating.", icon="✏️")

        if st.session_state.get("key_input"):
            st.button("Clear input", on_click=clear_input, use_container_width=True)

        st.markdown(
            '<div class="privacy-note"><span aria-hidden="true">◇</span> Your key is never included in validation results.</div>',
            unsafe_allow_html=True,
        )

st.markdown(
    """
    <div class="how-heading">THREE STEPS. THAT’S ALL.</div>
    <div class="steps">
      <div class="step"><span class="step-number">01</span><div><h3>Unlock your workspace</h3><p>Validate your personal access key.</p></div></div>
      <div class="step"><span class="step-number">02</span><div><h3>Find the right words</h3><p>Create a letter from your full reference library.</p></div></div>
      <div class="step"><span class="step-number">03</span><div><h3>Make it your own</h3><p>Review, edit, and download your new letter.</p></div></div>
    </div>
    <div class="footer"><span>laika. &nbsp; Words that make a difference.</span><span>Trost auf vier Pfoten e.V.</span></div>
    """,
    unsafe_allow_html=True,
)
