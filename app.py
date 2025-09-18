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
/* GLOBAL SETTINGS */
html, body {
    margin: 0;
    padding: 0;
    height: 100vh;
    overflow: hidden;
}

/* BASE LAYOUT STRUCTURE - THREE PARTS */
.app-frame {
    position: fixed !important;
    top: 0;
    left: 0;
    width: 100%;
    height: 100vh;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

/* 1. HEADER - Fixed at top */
.app-header {
    flex: 0 0 60px;
    background: linear-gradient(to right, #2196F3, #1976D2);
    color: white;
    display: flex;
    align-items: center;
    padding: 0 20px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    z-index: 1000;
}

.logo {
    display: flex;
    align-items: center;
}

.logo img {
    height: 32px;
    margin-right: 10px;
}

.app-title {
    font-size: 20px;
    font-weight: 600;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* 2. MAIN CONTENT - Fill available space */
.app-content {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    overflow: hidden;
}

/* 3. FOOTER - Fixed at bottom */
.app-footer {
    flex: 0 0 60px;
    border-top: 1px solid #e9ecef;
    padding: 0 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: white;
    z-index: 1000;
}

/* Empty state mockup */
.browser-mockup {
    width: 380px;
    height: 280px;
    border: 2px dashed #dee2e6;
    border-radius: 8px;
    background: white;
    overflow: hidden;
    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
}

.browser-bar {
    height: 28px;
    background: #f0f2f5;
    display: flex;
    align-items: center;
    padding-left: 10px;
    border-radius: 6px 6px 0 0;
}

.browser-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
}

.red-dot {background: #ff6b6b;}
.yellow-dot {background: #ffd43b;}
.green-dot {background: #69db7c;}

.browser-content {
    height: calc(100% - 28px);
    padding: 20px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
}

.content-line {
    height: 6px;
    border-radius: 3px;
    background: #f0f2f5;
}

.empty-state-message {
    margin-top: 15px;
    font-size: 14px;
    color: #6c757d;
    text-align: center;
}

/* Generated site preview */
.preview-container {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
}

.preview-header {
    display: flex;
    justify-content: flex-end;
    padding: 10px;
}

.preview-content {
    flex: 1;
    overflow: hidden;
}

/* Status indicator */
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

/* Override for Streamlit elements */
.stButton, .stDownloadButton {
    margin: 0 !important;
}

.stChatInput {
    margin-bottom: 0 !important;
}

.stApp {
    overflow: hidden !important;
}

/* Fix iframe sizing */
iframe {
    width: 100% !important;
    height: 100% !important;
    border: none !important;
}

/* No scrollbars anywhere */
* {
    scrollbar-width: none !important;
    -ms-overflow-style: none !important;
}
*::-webkit-scrollbar {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# --- START APP LAYOUT ---
st.markdown("""
<div class="app-frame">
    <!-- HEADER -->
    <div class="app-header">
        <div class="logo">
            <img src="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAxMjAgMTIwIiB3aWR0aD0iMzAiIGhlaWdodD0iMzAiPjxjaXJjbGUgY3g9IjYwIiBjeT0iNjAiIHI9IjU4IiBmaWxsPSIjMjE5NkYzIiBzdHJva2U9IiMxOTc2RDIiIHN0cm9rZS13aWR0aD0iNCIgLz48cmVjdCB4PSIzNSIgeT0iNDAiIHdpZHRoPSI1MCIgaGVpZ2h0PSIzMCIgcng9IjUiIGZpbGw9IiNGRkZGRkYiIHN0cm9rZT0iI0JCREVGQiIgc3Ryb2tlLXdpZHRoPSIyIiAvPjxjaXJjbGUgY3g9IjQyIiBjeT0iNDUiIHI9IjIiIGZpbGw9IiNGRjUyNTIiIC8+PGNpcmNsZSBjeD0iNDgiIGN5PSI0NSIgcj0iMiIgZmlsbD0iI0ZGRUIzQiIgLz48Y2lyY2xlIGN4PSI1NCIgY3k9IjQ1IiByPSIyIiBmaWxsPSIjNENBRjUwIiAvPjxwYXRoIGQ9Ik01MCA2MCBMNzAgNjAgTDYwIDc1IFoiIGZpbGw9IiM2NEI1RjYiIC8+PHRleHQgeD0iNjAiIHk9Ijg1IiBmb250LXNpemU9IjkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGZpbGw9IiNGRkZGRkYiIGZvbnQtZmFtaWx5PSJWZXJkYW5hLCBzYW5zLXNlcmlmIiBmb250LXdlaWdodD0iYm9sZCI+TUlOSU1BTCBCVUlMREVSPC90ZXh0Pjwvc3ZnPg==" alt="Logo">
            <span class="app-title">Minimal Web Builder</span>
        </div>
    </div>

    <!-- MAIN CONTENT -->
    <div class="app-content">
""", unsafe_allow_html=True)

# CONTENT AREA - Either empty state or generated preview
if not st.session_state.last_app_code:
    # Empty state mockup
    st.markdown("""
    <div style="text-align: center;">
        <div class="browser-mockup">
            <div class="browser-bar">
                <span class="browser-dot red-dot"></span>
                <span class="browser-dot yellow-dot"></span>
                <span class="browser-dot green-dot"></span>
            </div>
            <div class="browser-content">
                <div class="content-line" style="width: 70%;"></div>
                <div class="content-line" style="width: 40%;"></div>
                <div class="content-line" style="width: 80%;"></div>
                <div class="content-line" style="width: 55%;"></div>
                <div class="content-line" style="width: 30%;"></div>
            </div>
        </div>
        <p class="empty-state-message">Describe your website idea in the chat below</p>
    </div>
    """, unsafe_allow_html=True)
else:
    # Show generated website
    if st.session_state.show_preview:
        # Clean up code if needed (remove markdown formatting)
        preview_code = st.session_state.last_app_code
        if preview_code.strip().startswith("```html"):
            preview_code = preview_code.strip()[7:]  # Remove leading ```html
            if preview_code.endswith("```"):
                preview_code = preview_code[:-3]  # Remove trailing ```

        # Preview container with button
        st.markdown('<div class="preview-container">', unsafe_allow_html=True)

        # Control buttons at top
        col1, col2, col3 = st.columns([1, 1, 8])
        with col1:
            if st.button("View Code"):
                st.session_state.show_preview = False
                st.rerun()
        with col2:
            st.download_button(
                label="Download HTML",
                data=preview_code,
                file_name="minimal_website.html",
                mime="text/html"
            )

        # Actual preview iframe - fixed height
        components.html(preview_code, height=500, scrolling=False)
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Code view
        code = st.session_state.last_app_code
        if code.strip().startswith("```html"):
            code = code.strip()[7:]  # Remove leading ```html
            if code.endswith("```"):
                code = code[:-3]  # Remove trailing ```

        st.code(code, language="html")

        if st.button("Back to Preview"):
            st.session_state.show_preview = True
            st.rerun()

# Close content div
st.markdown('</div>', unsafe_allow_html=True)

# --- FOOTER WITH CHAT INPUT ---
st.markdown('<div class="app-footer">', unsafe_allow_html=True)
chat_input = st.chat_input("Describe the website you want to create...")
if chat_input:
    st.session_state.messages.append({"role": "user", "content": chat_input})
    st.session_state.is_generating = True
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# --- GENERATION STATUS INDICATOR ---
if st.session_state.is_generating:
    st.markdown("""
    <div class="status-indicator">
        <span>✨ Generating your website...</span>
    </div>
    """, unsafe_allow_html=True)

# Close app frame
st.markdown('</div>', unsafe_allow_html=True)

# --- PROCESS GENERATION (After UI is rendered) ---
if st.session_state.is_generating:
    # Prepare and make API call
    messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    output = call_gemini(messages)

    # Update session state with results
    st.session_state.messages.append({"role": "assistant", "content": "Your minimalist website has been generated!"})
    st.session_state.last_app_code = output
    st.session_state.is_generating = False

    # Refresh UI to show new content
    st.rerun()