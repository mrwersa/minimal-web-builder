import os
from dotenv import load_dotenv
import streamlit as st
import streamlit.components.v1 as components

# Load .env file
load_dotenv()

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
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_app_code" not in st.session_state:
    st.session_state.last_app_code = None
if "is_generating" not in st.session_state:
    st.session_state.is_generating = False
if "show_preview" not in st.session_state:
    st.session_state.show_preview = True

# --- API CONFIGURATION ---
api_key = os.getenv("GEMINI_API_KEY", "")
model = "gemini-1.5-flash"
temperature = 0.2
max_output_tokens = 1500

if not api_key:
    st.warning("Please provide your Gemini API key in the .env file to start.")
    st.stop()

# Configure Gemini
genai.configure(api_key=api_key)
gemini_model = genai.GenerativeModel(model)

# --- HELPER FUNCTION ---
def call_gemini(messages):
    try:
        conversation = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
        prompt = (
            "You are an expert web app developer and UI designer specializing in minimalist, clean designs.\n"
            "Your task: Generate a beautiful, modern, and minimalistic single-page web app using only HTML, CSS, and minimal JavaScript.\n"
            "Requirements:\n"
            "- Create a MINIMALIST design with clean typography, ample whitespace, and subtle effects\n"
            "- Use best practices for accessibility, responsiveness, and performance\n"
            "- Focus on simplicity, readability and usability\n"
            "- Use modern CSS (Flexbox/Grid) but keep visual elements minimal\n"
            "- Avoid unnecessary frameworks, libraries, or decorative elements\n"
            "- Use a monochromatic or limited color palette\n"
            "- ALL images/icons must be inline SVG (no external images or links)\n"
            "- The HTML must be fully self-contained with NO external dependencies or CDN links\n"
            "- If you generate navigation or tabs, do NOT use anchor links or change the URL. Use JavaScript to show/hide content sections for tab navigation. All navigation must be fully client-side and must not reload or redirect the page.\n"
            "- Return ONLY the complete HTML/CSS/JS code block, no explanations\n"
            "- The code should be ready to copy-paste and run\n\n"
            f"Conversation:\n{conversation}"
        )
        response = gemini_model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            ),
        )
        return response.text
    except Exception as e:
        return f"API error: {e}"

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
.app-footer, .stChatInput {
}
.stChatInput {
    margin: 0 !important;
    padding: 0 !important;
    background: #f7f9fb !important;
    box-shadow: none !important;
    border-radius: 0 !important;
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
    transition: border 0.2s;
.stChatInput input:focus, .stChatInput textarea:focus {
    border: none !important;
    outline: none !important;
    background: #fff !important;
}
}
.stChatInput input::placeholder, .stChatInput textarea::placeholder {
    color: #78909c !important;
    opacity: 1 !important;
}
.stChatInput input:disabled, .stChatInput textarea:disabled {
    background: #f7f9fb !important;
    color: #b0b8c1 !important;
}
}
    position: fixed !important;
    left: 0;
    right: 0;
    bottom: 0;
    width: 100vw;
    z-index: 2000;
    background: white;
    border-top: 1px solid #e9ecef;
    margin: 0 !important;
    padding: 0 20px;
}
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
    preview_code = st.session_state.last_app_code
    if preview_code.strip().startswith("```html"):
        preview_code = preview_code.strip()[7:]
        if preview_code.endswith("```"):
            preview_code = preview_code[:-3]
    with tab1:
        container_class = "preview-container"
        if st.session_state.is_generating:
            container_class += " blur"
        st.markdown(f'<div class="{container_class}" style="position:relative;min-height:0;flex:1;">', unsafe_allow_html=True)
        components.html(preview_code, height=500, scrolling=False)
        if st.session_state.is_generating:
            st.markdown('''
<style>
.preview-loader-overlay {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(247,249,251,0.65);
    z-index: 10;
    backdrop-filter: blur(2.5px);
}
.preview-loader-spinner {
    width: 54px;
    height: 54px;
    margin-bottom: 18px;
    display: block;
}
.preview-loader-message {
    font-size: 1.13em;
    color: #1976d2 !important;
    font-weight: 500;
    letter-spacing: 0.01em;
    text-align: center;
    margin-top: 0;
    text-shadow: 0 1px 4px #fff, 0 0 2px #f7f9fb;
}
</style>
<div class="preview-loader-overlay">
    <svg class="preview-loader-spinner" viewBox="0 0 50 50">
        <circle cx="25" cy="25" r="20" fill="none" stroke="#1976d2" stroke-width="5" stroke-linecap="round" stroke-dasharray="31.4 31.4" stroke-dashoffset="0">
            <animateTransform attributeName="transform" type="rotate" from="0 25 25" to="360 25 25" dur="0.9s" repeatCount="indefinite"/>
        </circle>
        <circle cx="25" cy="25" r="12" fill="none" stroke="#90caf9" stroke-width="3" stroke-linecap="round" stroke-dasharray="18.8 18.8" stroke-dashoffset="0">
            <animateTransform attributeName="transform" type="rotate" from="360 25 25" to="0 25 25" dur="1.2s" repeatCount="indefinite"/>
        </circle>
    </svg>
    <div class="preview-loader-message">Generating your minimalist website...</div>
</div>
''', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with tab2:
        st.code(preview_code, language="html")
else:
    with tab1:
        st.markdown('''
<div style="height:500px;display:flex;flex-direction:column;align-items:center;justify-content:center;">
    <svg width="120" height="120" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="60" cy="60" r="56" fill="#E3F2FD" stroke="#90CAF9" stroke-width="4"/>
        <rect x="35" y="50" width="50" height="30" rx="6" fill="#fff" stroke="#90CAF9" stroke-width="2"/>
        <rect x="45" y="60" width="30" height="6" rx="3" fill="#BBDEFB"/>
        <circle cx="60" cy="65" r="2.5" fill="#90CAF9"/>
        <rect x="55" y="72" width="10" height="3" rx="1.5" fill="#E3F2FD"/>
        <ellipse cx="60" cy="95" rx="18" ry="4" fill="#E3F2FD"/>
    </svg>
    <div style="margin-top:18px;font-size:1.18em;color:#1976d2;font-weight:500;letter-spacing:0.01em;text-align:center;">
        <span style="font-size:1.5em;">Start your creative journey!</span><br/>
        <span style="color:#78909c;font-size:1em;">Describe your dream website below and watch it come to life.</span>
    </div>
</div>
''', unsafe_allow_html=True)
    with tab2:
        st.code("<!-- No code generated yet -->", language="html")
st.markdown('</div>', unsafe_allow_html=True)  # close tab-content-scroll
st.markdown('</div>', unsafe_allow_html=True)  # close main-scroll-area


# --- FOOTER WITH CHAT INPUT ---

# --- Chat input (always at the bottom) ---
if st.session_state.is_generating:
    # Disabled input look
    st.chat_input("Generating... Please wait.", disabled=True)
else:
    chat_input = st.chat_input("Describe the website you want to create...")
    if chat_input:
        st.session_state.messages.append({"role": "user", "content": chat_input})
        st.session_state.is_generating = True
        st.rerun()


# --- GENERATION STATUS INDICATOR ---


# --- PROCESS GENERATION (After UI is rendered) ---
if st.session_state.is_generating:
    # Token-efficient prompt: always include latest preview code and most recent user message
    messages = []
    # Add the latest preview code if it exists
    if st.session_state.last_app_code:
        messages.append({
            "role": "assistant",
            "content": f"Here is the current version of the website code:\n\n{st.session_state.last_app_code.strip()}"
        })
    # Add only the most recent user message
    if st.session_state.messages:
        # Find the last user message
        for m in reversed(st.session_state.messages):
            if m["role"] == "user":
                messages.append({"role": "user", "content": m["content"]})
                break
    output = call_gemini(messages)

    # Update session state with results
    st.session_state.messages.append({"role": "assistant", "content": "Your minimalist website has been generated!"})
    st.session_state.last_app_code = output
    st.session_state.is_generating = False

    # Refresh UI to show new content
    st.rerun()