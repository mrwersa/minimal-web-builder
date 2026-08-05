import streamlit as st
import streamlit.components.v1 as components
from src.config import load_config
from src.generation import call_gemini, strip_html_code_fence
from src.a11y import audit_generated_html
from src.theme import (
    COMPLEXITY_BY_KEY,
    TONE_PRESETS_BY_KEY,
    complexity_options,
    tone_options,
)
from src.rendering import (
    build_sandboxed_preview_html,
    EMPTY_STATE_HTML,
    NO_CODE_PLACEHOLDER,
    PREVIEW_LOADER_OVERLAY_HTML,
    preview_container_class,
)
from src.state import (
    add_user_message_and_start_generation,
    apply_generation_error,
    apply_generation_result,
    build_generation_messages,
    init_session_state,
)
from src.safety import apply_output_safety_policy
from src.validation import validate_user_prompt

try:
    import google.generativeai as genai
except ModuleNotFoundError:
    st.error("Module 'google.generativeai' not installed. Run `pip install google-generativeai`.")
    st.stop()

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Minimal Web Builder",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={}
)

# --- SESSION STATE ---
init_session_state(st.session_state)

# --- API CONFIGURATION ---
config = load_config()
api_key = config.api_key
model = config.model
temperature = config.temperature
max_output_tokens = config.max_output_tokens
max_prompt_chars = config.max_prompt_chars

if not api_key:
    st.warning("Please provide your Gemini API key in the .env file to start.")
    st.stop()

# Configure Gemini
genai.configure(api_key=api_key)
gemini_model = genai.GenerativeModel(model)

# --- GENERATION OPTIONS (SIDEBAR) ---
with st.sidebar:
    st.markdown("#### Generation options")
    st.selectbox(
        "Tone",
        options=tone_options(),
        format_func=lambda key: TONE_PRESETS_BY_KEY[key].label,
        key="generation_tone",
    )
    st.select_slider(
        "Complexity",
        options=[1, 2, 3],
        format_func=lambda n: COMPLEXITY_BY_KEY[complexity_options()[n - 1]].label,
        value=complexity_options().index(st.session_state.generation_complexity) + 1,
        key="generation_complexity_slider",
        help="How much the generated page should include. Compact = minimal; Detailed = richer.",
    )
    st.session_state.generation_complexity = complexity_options()[st.session_state.generation_complexity_slider - 1]
    st.toggle("Strict minimal mode", key="strict_minimal_mode")
    st.caption("Strict minimal mode restricts output to flat, monochrome, decoration-free designs.")

# --- FIRST REMOVE STREAMLIT DEFAULTS ---
# This must come first to properly hide the default components
st.markdown("""
<style>
/* Complete hiding of default Streamlit elements */
#MainMenu, header, footer {display: none !important;}
.stDeployButton {display: none !important;}
[data-testid="stToolbar"] {display: none !important;}
.viewerBadge_container__1QSob {display: none !important;}

/* Remove ALL padding and margins */
.block-container {
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
}

/* Fix gaps */
div[data-testid="stVerticalBlock"] {
    gap: 0 !important;
}

/* Remove padding from every element */
section.main, .element-container {
    padding: 0 !important;
    margin: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# --- LAYOUT CSS (SEPARATE FROM STREAMLIT DEFAULTS) ---
st.markdown("""
<style>
html, body, .stApp {
    margin: 0;
    padding: 0;
    height: 100vh;
    overflow-x: hidden;
    background: #f7f9fb;
}
.app-frame {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}
.main-scroll-area {
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    justify-content: flex-start;
    padding: 0;
    margin: 0;
    overflow: hidden;
    position: relative;
    min-height: 0;
}
.sticky-tabs {
    position: sticky !important;
    top: 0 !important;
    z-index: 1002 !important;
    background: #f7f9fb !important;
}
.tab-content-scroll {
    flex: 1 1 auto;
    overflow-y: auto;
    min-height: 0;
    position: relative;
    padding-bottom: 24px;
}
.stChatInput {
    position: fixed !important;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100vw;
    z-index: 2000;
    background: #f7f9fb !important;
    border-top: 1px solid #e9ecef;
    margin: 0 !important;
    padding: 0 20px;
}
.stChatInput > div {
    margin: 0 !important;
    padding: 0 !important;
    background: #f7f9fb !important;
    box-shadow: none !important;
    border-radius: 0 !important;
}
.stChatInput input, .stChatInput textarea {
    color: #222 !important;
    caret-color: #1976d2 !important;
    padding: 12px 16px !important;
    font-size: 1.08em !important;
    background: #fff !important;
    border: 1.5px solid #e3e8ee !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    outline: none !important;
    transition: border-color 0.2s;
}
.stChatInput input:focus, .stChatInput textarea:focus {
    border: 1.5px solid #1976d2 !important;
    outline: none !important;
    background: #fff !important;
}
.stChatInput input::placeholder, .stChatInput textarea::placeholder {
    color: #78909c !important;
    opacity: 1 !important;
}
.stChatInput input:disabled, .stChatInput textarea:disabled {
    background: #f7f9fb !important;
    color: #b0b8c1 !important;
}
.preview-container {
    width: 100%;
    flex: 1 1 auto;
    min-height: 0;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    justify-content: flex-start;
}
.status-indicator {
    position: absolute;
    left: 50%;
    bottom: 80px;
    transform: translateX(-50%);
    background: rgba(255,255,255,0.95);
    padding: 8px 16px;
    border-radius: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    font-size: 14px;
    z-index: 1001;
}
.stButton, .stDownloadButton {
    margin: 0 !important;
}
iframe {
    width: 100vw !important;
    max-width: 100% !important;
    height: 100% !important;
    min-height: 0 !important;
    border: none !important;
    display: block;
    overflow: auto !important;
}
.stTabs [data-baseweb="tab-list"] {
    background: #fff;
    border-radius: 10px 10px 0 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    border-bottom: 1.5px solid #e3e8ee;
    padding-left: 12px;
}
.stTabs [data-baseweb="tab"] {
    font-size: 1.08em;
    font-weight: 500;
    color: #1976d2;
    padding: 12px 24px 10px 24px;
    margin-right: 2px;
    border-radius: 10px 10px 0 0;
    background: #f7f9fb;
    transition: background 0.2s, color 0.2s;
}
.stTabs [aria-selected="true"] {
    background: #1976d2 !important;
    color: #fff !important;
    box-shadow: 0 2px 8px rgba(25,118,210,0.08);
}
.stTabs [data-baseweb="tab-panel"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}
</style>
""", unsafe_allow_html=True)

# --- START APP LAYOUT ---


# CONTENT AREA - Either empty state or generated preview

# --- TABS: Preview | Code ---

# --- Custom layout for sticky tabs and fixed chat input ---
tab_labels = ["Preview", "Code"]
tab1, tab2 = st.tabs(tab_labels)
st.markdown('<div class="main-scroll-area">', unsafe_allow_html=True)
st.markdown('<div class="sticky-tabs">', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="tab-content-scroll">', unsafe_allow_html=True)
if st.session_state.last_app_code:
    preview_code = strip_html_code_fence(st.session_state.last_app_code)
    sandboxed_preview_html = build_sandboxed_preview_html(preview_code)
    with tab1:
        container_class = preview_container_class(st.session_state.is_generating)
        st.markdown(f'<div class="{container_class}" style="position:relative;min-height:0;flex:1;">', unsafe_allow_html=True)
        components.html(sandboxed_preview_html, height=500, scrolling=False)
        if st.session_state.is_generating:
            st.markdown(PREVIEW_LOADER_OVERLAY_HTML, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with tab2:
        st.code(preview_code, language="html")
else:
    with tab1:
        st.markdown(EMPTY_STATE_HTML, unsafe_allow_html=True)
    with tab2:
        st.code(NO_CODE_PLACEHOLDER, language="html")
st.markdown('</div>', unsafe_allow_html=True)  # close tab-content-scroll
st.markdown('</div>', unsafe_allow_html=True)  # close main-scroll-area


# --- FOOTER WITH CHAT INPUT ---

# --- Chat input (always at the bottom) ---
if st.session_state.is_generating:
    # Disabled input look
    st.chat_input("Generating... Please wait.", disabled=True)
else:
    chat_input = st.chat_input("Describe the website you want to create...")
    if chat_input is not None:
        validated_prompt, validation_error = validate_user_prompt(
            chat_input,
            max_prompt_chars=max_prompt_chars,
        )
        if validation_error:
            st.warning(validation_error)
        else:
            add_user_message_and_start_generation(st.session_state, validated_prompt)
            st.rerun()


# --- GENERATION STATUS INDICATOR ---


# --- PROCESS GENERATION (After UI is rendered) ---
if st.session_state.is_generating:
    messages = build_generation_messages(st.session_state)
    output = call_gemini(
        model=gemini_model,
        genai=genai,
        messages=messages,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        tone_key=st.session_state.generation_tone,
        strict_minimal=st.session_state.strict_minimal_mode,
        complexity_key=st.session_state.generation_complexity,
    )

    if output.startswith("API error:"):
        st.error("Generation failed due to an API error. Please try again.")
        apply_generation_error(st.session_state, output)
        st.rerun()

    sanitized_output, safety_alerts = apply_output_safety_policy(output)
    if safety_alerts:
        st.warning("Safety policy applied: " + " ".join(safety_alerts))

    a11y_notes = audit_generated_html(strip_html_code_fence(sanitized_output))
    if a11y_notes:
        st.info("Accessibility notes: " + " ".join(a11y_notes))

    # Update session state with results
    apply_generation_result(st.session_state, sanitized_output)

    # Refresh UI to show new content
    st.rerun()