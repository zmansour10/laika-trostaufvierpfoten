"""The authenticated Streamlit letter-writing workspace."""

from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import streamlit as st

from generate_letter import (
    GenerationError,
    LetterBrief,
    MODELS,
    berlin_today,
    generate_letter,
    load_sources,
    model_option,
    provider_key,
)
from letter_storage import LetterSaveError, save_letter
from letter_purposes import PURPOSE_LABELS, purpose_guide


STUDIO_CSS = """
<style>
.page-rule { margin-bottom: 36px; }
.studio-hero { background: #eaf0e6; border: 1px solid #dce5d6; border-radius: 20px;
    padding: 30px 35px; margin-bottom: 26px; position: relative; overflow: hidden; }
.studio-hero .eyebrow { margin-bottom: 12px; font-size: 10px; }
.studio-hero h1 { font-family: 'Manrope', sans-serif; font-weight: 750; font-size: 36px;
    line-height: 1.2; letter-spacing: -1.5px; color: #294934; padding: 0; margin: 0 0 12px; }
.studio-hero p { color: #6b7d6c; line-height: 1.8; font-size: 13px; max-width: 580px; margin: 0; }
.hero-flower { position: absolute; right: 35px; top: 5px; color: #c5d5bd; font-size: 155px;
    line-height: 1.3; transform: rotate(15deg); }
.library-strip { display: flex; flex-wrap: wrap; gap: 12px 28px; font-size: 12px; color: #74816e;
    margin: 0 0 30px; padding: 0 3px; }
.library-strip strong { color: #39583f; font-size: 15px; margin-right: 5px; }
.studio-section { font-size: 10px; font-weight: 700; letter-spacing: 1.4px; color: #7a8c78;
    margin: 2px 0 15px; text-transform: uppercase; }
.st-key-brief_panel, .st-key-output_panel { background: #fff; border: 1px solid #e0e7df !important;
    border-radius: 17px !important; padding: 24px !important; }
.st-key-brief_panel h2, .st-key-output_panel h2 { font-family: 'Manrope', sans-serif;
    font-size: 21px; font-weight: 750; letter-spacing: -.7px; margin: 0; padding: 0 0 7px; }
.studio-subtitle { font-size: 12px; color: #7b887c; line-height: 1.7; margin: 0 0 18px; }
.st-key-brief_panel label p, .st-key-brief_panel label span { font-size: 12px; }
.st-key-brief_panel textarea, .st-key-draft_text textarea { font-family: 'DM Sans', sans-serif; font-size: 13px; }
.empty-preview { min-height: 475px; display: flex; flex-direction: column; align-items: center;
    justify-content: center; text-align: center; padding: 35px 18px;
    border: 1px dashed #dbe4d6; background: #fafbf8; border-radius: 12px; }
.paper-icon { height: 78px; width: 63px; background: #fff; border: 1px solid #d9e3d3;
    border-radius: 5px; box-shadow: 7px 7px 0 #ecf0e6; margin-bottom: 29px;
    display: flex; flex-direction: column; justify-content: center; padding: 13px; gap: 7px;
    transform: rotate(-6deg); }
.paper-icon i { display: block; height: 2px; background: #c2d2b7; width: 100%; }
.paper-icon i:last-child { width: 65%; }
.empty-preview h3 { font-family: 'Manrope', sans-serif; font-size: 19px; font-weight: 700;
    letter-spacing: -.6px; color: #40573c; margin: 0 0 10px; padding: 0; }
.empty-preview p { font-size: 12px; color: #8a9582; line-height: 1.9; max-width: 270px; }
.preview-tag { border: 1px solid #e0e7d9; border-radius: 20px; font-size: 10px;
    color: #7f9173; padding: 5px 12px; margin-top: 15px; }
.letter-sheet { background: #fdfdfb; border: 1px solid #e6e9e0; border-radius: 8px;
    padding: 32px; margin: 9px 0 17px; }
.letter-letterhead { color: #48704e; font-size: 9px; font-weight: 700; letter-spacing: 1.4px;
    border-bottom: 1px solid #e2e8db; padding-bottom: 14px; margin-bottom: 22px; }
.letter-content { white-space: pre-wrap; overflow-wrap: anywhere; font-family: Georgia, serif;
    color: #354231; font-size: 14px; line-height: 1.95; }
.st-key-output_panel [data-testid="stTabs"] button { font-size: 12px; }
.studio-footnote { font-size: 11px; color: #8b9685; line-height: 1.8; padding-top: 5px; }
.workspace-footer { display: flex; justify-content: space-between; gap: 20px; border-top: 1px solid #dfe6dc;
    margin-top: 35px; padding-top: 20px; color: #8b9685; font-size: 10px; }
@media(max-width:740px) {
    .studio-hero { padding: 24px; }
    .studio-hero h1 { font-size: 29px; }
    .hero-flower { display: none; }
    .st-key-brief_panel, .st-key-output_panel { padding: 20px !important; }
    .letter-sheet { padding: 20px; }
    .empty-preview { min-height: 300px; }
}
</style>
"""


def clear_prepared_download() -> None:
    st.session_state.pop("prepared_download", None)


def update_purpose_recipient() -> None:
    previous_default = st.session_state.get("recipient_default", purpose_guide(PURPOSE_LABELS[0]).recipient)
    next_default = purpose_guide(st.session_state.brief_purpose).recipient
    current = st.session_state.get("brief_recipient", "")
    if not current.strip() or current == previous_default:
        st.session_state.brief_recipient = next_default
    st.session_state.recipient_default = next_default


def render_studio(authenticated: Callable[[], bool], logout: Callable[[], None]) -> None:
    """Require the gate before reading source files, rendering drafts, or making calls."""
    if not authenticated():
        st.stop()
    st.markdown(STUDIO_CSS, unsafe_allow_html=True)
    st.markdown(
        """<div class="studio-hero">
        <div class="hero-flower" aria-hidden="true">✳</div>
        <div class="eyebrow">LAIKA · LETTER STUDIO</div>
        <h1>Good words. A little more hope.</h1>
        <p>Turn years of heartfelt letters into your next thoughtful message.<br>
        Grounded in your association. Written with care. Shaped by you.</p></div>""",
        unsafe_allow_html=True,
    )

    try:
        sources = load_sources()
    except GenerationError as exc:
        st.error(str(exc))
        st.button("Lock workspace", on_click=logout, key="lock_button")
        return

    st.markdown(
        f'<div class="library-strip"><span><strong>{len(sources.letters):02}</strong> previous letters</span>'
        f'<span><strong>{len(sources.association):02}</strong> association reference{("s" if len(sources.association) != 1 else "")}</span>'
        '<span>✧ &nbsp; Your full library, included in every request</span></div>',
        unsafe_allow_html=True,
    )

    brief_column, output_column = st.columns([0.85, 1.3], gap="large")
    with brief_column:
        st.markdown('<div class="studio-section">01 / Shape your letter</div>', unsafe_allow_html=True)
        with st.container(border=True, key="brief_panel"):
            st.markdown("## A few thoughtful details")
            st.markdown('<p class="studio-subtitle">Start with a purpose. We’ll bring your references.</p>', unsafe_allow_html=True)
            purpose = st.selectbox(
                "Purpose",
                PURPOSE_LABELS,
                key="brief_purpose",
                on_change=update_purpose_recipient,
            )
            if "recipient_default" not in st.session_state:
                # Migrate the fixed judicial default used by older sessions.
                st.session_state.recipient_default = purpose_guide(PURPOSE_LABELS[0]).recipient
                update_purpose_recipient()
            if "brief_recipient" not in st.session_state:
                st.session_state.brief_recipient = purpose_guide(purpose).recipient
            recipient = st.text_input(
                "Recipient / audience", key="brief_recipient", max_chars=500,
                help="Suggested for the selected purpose. Your own audience is preserved when you switch purposes.",
            )
            instructions = st.text_area(
                "What should this letter focus on?",
                placeholder="For example: Focus on immediate support for bereaved children and the importance of reliable funding…",
                height=135,
                max_chars=12_000,
                key="brief_instructions",
                help="Optional. Add verified updates, a specific request, or details to emphasize. The complete reference library is always included.",
            )
            selected_id = st.selectbox(
                "AI model",
                [model.id for model in MODELS],
                format_func=lambda model_id: (
                    f"{model_option(model_id).label} · {model_option(model_id).rpm} RPM"
                    if model_option(model_id).rpm else f"{model_option(model_id).label} · OpenAI"
                ),
                key="brief_model",
            )
            model = model_option(selected_id)
            has_key = bool(provider_key(model.provider))
            if not has_key:
                variable = "GEMINI_API_KEY" if model.provider == "Gemini" else "OPENAI_API_KEY"
                st.info(f"Add {variable} to the server’s .env file to enable {model.provider} generation.")
            else:
                st.caption(f"{model.provider} connected · No web search or external tools")
            if model.rpm:
                st.caption(f"App limit: {model.rpm} requests/minute. Provider token and daily quotas also apply.")

            with st.expander("Fine-tune your letter"):
                tone = st.selectbox("Tone", ["Warm, professional, and persuasive", "Formal and factual", "Personal and heartfelt"], key="brief_tone")
                length = st.selectbox("Length", ["Standard: approximately 400–550 words", "Concise: approximately 250–350 words", "Detailed: approximately 600–750 words"], key="brief_length")
                language = st.selectbox("Letter language", ["German", "English"], key="brief_language")
                signatory = st.text_input("Signatory (optional)", placeholder="Leave blank to sign on behalf of LAIKA", key="brief_signatory", max_chars=300)
                letter_date = st.date_input("Letter date", value=berlin_today(), key="brief_date")

            generate = st.button(
                "Generate a letter  →" if not st.session_state.get("draft_text") else "Generate a new version  →",
                type="primary", use_container_width=True, disabled=not has_key, key="generate_button",
            )
            st.markdown('<p class="studio-footnote">Your brief and reference texts are sent to the selected AI provider when you generate.</p>', unsafe_allow_html=True)

        with st.expander("Your reference library"):
            st.caption("All populated .txt files are included in full. Changes to the folders are picked up on the next run.")
            for heading, documents in (("Previous letters", sources.letters), ("Association information", sources.association)):
                st.markdown(f"**{heading}**")
                for document in documents:
                    with st.expander(document.name):
                        st.text(document.text)
            if sources.empty_files:
                st.caption("Empty files skipped: " + ", ".join(sources.empty_files))

    brief = LetterBrief(purpose, recipient, instructions, tone, length, language, signatory, letter_date)
    current_settings = asdict(brief)
    current_settings["letter_date"] = letter_date.isoformat()
    current_settings["model_id"] = selected_id
    if generate:
        # Repeat the authorization check immediately before a provider request.
        if not authenticated():
            logout()
            st.rerun()
        try:
            with st.spinner("Finding the right words from your reference library…"):
                result = generate_letter(brief, selected_id, sources=sources)
            if not authenticated():
                logout()
                st.rerun()
            st.session_state.draft_text = result.text
            clear_prepared_download()
            st.session_state.draft_metadata = {
                "model": result.model_label,
                "provider": result.provider,
                "letters": result.letter_count,
                "association": result.association_count,
                "created": datetime.now(ZoneInfo("Europe/Berlin")).strftime("%d %b %Y · %H:%M"),
                "date": letter_date.isoformat(),
                "purpose": purpose,
                "settings": current_settings,
            }
        except GenerationError as exc:
            with output_column:
                st.error(str(exc))
                if st.session_state.get("draft_text"):
                    st.caption("Your previous draft is still available below.")

    with output_column:
        st.markdown('<div class="studio-section">02 / Make it your own</div>', unsafe_allow_html=True)
        with st.container(border=True, key="output_panel"):
            st.markdown("## Your next letter")
            draft = st.session_state.get("draft_text", "")
            if not draft:
                st.markdown('<p class="studio-subtitle">A fresh page for an important message.</p>', unsafe_allow_html=True)
                st.markdown(
                    """<div class="empty-preview"><div class="paper-icon" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
                    <h3>A little inspiration starts here.</h3>
                    <p>Choose your focus and generate a letter.<br>Your draft will appear here, ready for your personal touch.</p>
                    <span class="preview-tag">Your voice. A fresh beginning.</span></div>""",
                    unsafe_allow_html=True,
                )
            else:
                meta = st.session_state.draft_metadata
                st.caption(f"{meta['model']} · {meta['created']}")
                if meta.get("purpose"):
                    st.caption(f"Written for: {meta['purpose']}")
                if meta.get("settings") != current_settings:
                    st.info("Your letter settings have changed. Generate a new version to apply them; the draft below is the previous version.")
                preview, edit = st.tabs(["Letter preview", "Edit your draft"])
                with edit:
                    st.text_area("Letter text", key="draft_text", height=560, label_visibility="collapsed", on_change=clear_prepared_download)
                    st.caption("Save & prepare download captures your latest edits. Generating a new version replaces this draft.")
                with preview:
                    # Model output and user edits are always escaped before HTML rendering.
                    st.markdown(
                        '<div class="letter-sheet"><div class="letter-letterhead">LAIKA · TROST AUF VIER PFOTEN E.V.</div>'
                        f'<div class="letter-content">{escape(st.session_state.draft_text)}</div></div>',
                        unsafe_allow_html=True,
                    )
                count = len(st.session_state.draft_text.split())
                st.caption(f"{count} words · Based on {meta['letters']} letters and {meta['association']} association reference(s)")
                if st.button(
                    "Save & prepare download", key="save_letter_button",
                    use_container_width=True, disabled=not st.session_state.draft_text.strip(),
                ):
                    if not authenticated():
                        logout()
                        st.rerun()
                    try:
                        text = st.session_state.draft_text
                        path = save_letter(text)
                        st.session_state.prepared_download = {
                            "text": text,
                            "path": f"data/letters/{path.name}",
                            "filename": f"laika_letter_{meta['date']}.txt",
                        }
                        # Refresh the library so this reviewed letter is immediately visible.
                        st.rerun()
                    except LetterSaveError as exc:
                        st.error(str(exc))
                prepared = st.session_state.get("prepared_download")
                if prepared and prepared["text"] == st.session_state.draft_text:
                    st.success("Saved to your letter library. This version will be included in future generations.")
                    st.caption(prepared["path"])
                    st.download_button(
                        "Download saved letter (.txt)  ↓",
                        data=prepared["text"],
                        file_name=prepared["filename"],
                        mime="text/plain; charset=utf-8",
                        key="download_saved_letter",
                        on_click="ignore",
                        use_container_width=True,
                    )
                st.markdown('<p class="studio-footnote">Review names, dates, and facts before saving. Saved letters stay in your reference library; further edits need to be saved again.</p>', unsafe_allow_html=True)

    footer, lock = st.columns([4, 1])
    with footer:
        st.markdown('<div class="workspace-footer"><span>LAIKA · Trost auf vier Pfoten e.V.</span><span>Written with care. Reviewed by you.</span></div>', unsafe_allow_html=True)
    with lock:
        st.button("Lock workspace", on_click=logout, use_container_width=True, key="lock_button")
