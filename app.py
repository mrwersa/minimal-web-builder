import streamlit as st
import streamlit.components.v1 as components

from src.a11y import audit_generated_html
from src.config import load_config
from src.generation import (
    call_gemini,
    call_gemini_for_section,
    strip_html_code_fence,
)
from src.rendering import (
    EMPTY_STATE_HTML,
    NO_CODE_PLACEHOLDER,
    PREVIEW_LOADER_OVERLAY_HTML,
    build_app_styles,
    build_sandboxed_preview_html,
    preview_container_class,
)
from src.safety import apply_output_safety_policy
from src.sections import (
    extract_first_top_level,
    extract_sections,
    replace_section,
)
from src.state import (
    add_user_message_and_start_generation,
    apply_generation_error,
    apply_generation_result,
    apply_section_regeneration_error,
    apply_section_regeneration_result,
    build_generation_messages,
    init_session_state,
    last_user_message,
    request_section_regeneration,
)
from src.theme import (
    COMPLEXITY_BY_KEY,
    TONE_PRESETS_BY_KEY,
    complexity_options,
    tone_options,
)
from src.validation import validate_user_prompt

try:
    import google.generativeai as genai
except ModuleNotFoundError:
    st.error(
        "Module 'google.generativeai' not installed. Run `pip install google-generativeai`."
    )
    st.stop()

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Minimal Web Builder",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={},
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
    st.session_state.generation_complexity = complexity_options()[
        st.session_state.generation_complexity_slider - 1
    ]
    st.toggle("Strict minimal mode", key="strict_minimal_mode")
    st.caption(
        "Strict minimal mode restricts output to flat, monochrome, decoration-free designs."
    )

    st.markdown("#### Refine")
    if (
        st.session_state.last_app_code
        and not st.session_state.is_generating
        and not st.session_state.is_regenerating_section
    ):
        sections = extract_sections(
            strip_html_code_fence(st.session_state.last_app_code)
        )
        if sections:
            section_labels = [
                f"{s.index + 1}. <{s.tag}> — {s.snippet}"
                if s.snippet
                else f"{s.index + 1}. <{s.tag}>"
                for s in sections
            ]
            st.selectbox(
                "Regenerate section",
                options=range(len(sections)),
                format_func=lambda i: section_labels[i],
                key="section_choice",
            )
            if st.button("Regenerate section"):
                request_section_regeneration(
                    st.session_state,
                    st.session_state.section_choice,
                )
                st.rerun()
        else:
            st.caption("No sections detected in the current page.")
    else:
        st.caption("Generate a website first, then refine individual sections.")

# --- APP STYLES (token-driven, from src/theme) ---
st.markdown(build_app_styles(), unsafe_allow_html=True)

# --- START APP LAYOUT ---


# CONTENT AREA - Either empty state or generated preview

# --- TABS: Preview | Code ---

# --- Custom layout for sticky tabs and fixed chat input ---
tab_labels = ["Preview", "Code"]
tab1, tab2 = st.tabs(tab_labels)
st.markdown('<div class="main-scroll-area">', unsafe_allow_html=True)
st.markdown('<div class="sticky-tabs">', unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
st.markdown('<div class="tab-content-scroll">', unsafe_allow_html=True)
if st.session_state.last_app_code:
    preview_code = strip_html_code_fence(st.session_state.last_app_code)
    sandboxed_preview_html = build_sandboxed_preview_html(preview_code)
    with tab1:
        container_class = preview_container_class(st.session_state.is_generating)
        st.markdown(
            f'<div class="{container_class}" style="position:relative;min-height:0;flex:1;">',
            unsafe_allow_html=True,
        )
        components.html(sandboxed_preview_html, height=500, scrolling=False)
        if st.session_state.is_generating or st.session_state.is_regenerating_section:
            st.markdown(PREVIEW_LOADER_OVERLAY_HTML, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with tab2:
        st.code(preview_code, language="html")
else:
    with tab1:
        st.markdown(EMPTY_STATE_HTML, unsafe_allow_html=True)
    with tab2:
        st.code(NO_CODE_PLACEHOLDER, language="html")
st.markdown("</div>", unsafe_allow_html=True)  # close tab-content-scroll
st.markdown("</div>", unsafe_allow_html=True)  # close main-scroll-area


# --- FOOTER WITH CHAT INPUT ---

# --- Chat input (always at the bottom) ---
if st.session_state.is_generating or st.session_state.is_regenerating_section:
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


# --- PROCESS SECTION REGENERATION (After UI is rendered) ---
if st.session_state.is_regenerating_section:
    current_code = strip_html_code_fence(st.session_state.last_app_code)
    sections = extract_sections(current_code)
    section_index = st.session_state.pending_section_index
    if section_index is None or section_index >= len(sections):
        st.error("The selected section is no longer available. Please try again.")
        apply_section_regeneration_error(st.session_state)
        st.rerun()

    section = sections[section_index]
    output = call_gemini_for_section(
        model=gemini_model,
        genai=genai,
        current_code=current_code,
        section=section,
        instructions=last_user_message(st.session_state),
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        tone_key=st.session_state.generation_tone,
        strict_minimal=st.session_state.strict_minimal_mode,
        complexity_key=st.session_state.generation_complexity,
    )

    if output.startswith("API error:"):
        st.error("Section regeneration failed due to an API error. Please try again.")
        apply_section_regeneration_error(st.session_state)
        st.rerun()

    sanitized_output, safety_alerts = apply_output_safety_policy(output)
    if safety_alerts:
        st.warning("Safety policy applied: " + " ".join(safety_alerts))

    replacement = extract_first_top_level(strip_html_code_fence(sanitized_output))
    if not replacement:
        st.error("Could not parse the regenerated section. Please try again.")
        apply_section_regeneration_error(st.session_state)
        st.rerun()

    updated_code = replace_section(current_code, section, replacement)
    a11y_notes = audit_generated_html(updated_code)
    if a11y_notes:
        st.info("Accessibility notes: " + " ".join(a11y_notes))

    apply_section_regeneration_result(st.session_state, updated_code)
    st.rerun()


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
