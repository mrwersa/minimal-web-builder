from pathlib import Path

import streamlit as st

from src.a11y import audit_generated_html
from src.config import OPENROUTER_PROVIDER, load_config
from src.constraints import (
    COLOR_LIMITS,
    COLOR_LIMITS_BY_KEY,
    SECTION_OPTIONS,
    SECTION_OPTIONS_BY_KEY,
    build_constraints_prompt,
)
from src.export import split_document
from src.generation import (
    call_gemini,
    call_gemini_for_section,
    strip_html_code_fence,
)
from src.js_analysis import audit_inline_scripts
from src.layout_dna import (
    combine_guidance,
    extract_layout_dna,
    grammar_signature,
    list_saved_dnas,
    save_dna,
    to_guidance,
)
from src.profiles import (
    CUSTOM_PROFILE_ID,
    get_profile,
    load_profiles,
    profile_options,
)
from src.rendering import (
    EMPTY_STATE_HTML,
    NO_CODE_PLACEHOLDER,
    PREVIEW_LOADER_OVERLAY_HTML,
    build_app_styles,
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
    seed_from_template,
)
from src.templates import (
    delete_template,
    list_templates,
    load_template,
    save_template,
)
from src.theme import (
    COMPLEXITY_BY_KEY,
    REFINE_ASPECTS,
    REFINE_ASPECTS_BY_KEY,
    TONE_PRESETS_BY_KEY,
    complexity_options,
    tone_options,
)
from src.validation import validate_user_prompt
from src.wysiwyg import (
    build_editable_preview_document,
    consume_edit_message,
    register_component,
    wysiwyg_preview,
)

# Register the WYSIWYG preview component with Streamlit's server at startup.
register_component()

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
temperature = config.temperature
max_output_tokens = config.max_output_tokens
max_prompt_chars = config.max_prompt_chars

if config.provider == OPENROUTER_PROVIDER:
    if not config.openrouter_api_key:
        st.warning("Please provide your OpenRouter API key in the .env file to start.")
        st.stop()
    genai = None
    gemini_model = config.openrouter_model
else:
    try:
        import google.generativeai as genai
    except ModuleNotFoundError:
        st.error(
            "Module 'google.generativeai' not installed. Run `pip install google-generativeai`."
        )
        st.stop()
    if not config.api_key:
        st.warning("Please provide your Gemini API key in the .env file to start.")
        st.stop()

    # Configure Gemini
    genai.configure(api_key=config.api_key)
    gemini_model = genai.GenerativeModel(config.model)

# --- GENERATION PROFILES ---
PROFILES_DIR = Path(__file__).resolve().parent / "profiles"
try:
    PROFILES = load_profiles(PROFILES_DIR)
except (ValueError, TypeError) as exc:
    st.error(f"Failed to load generation profiles: {exc}")
    PROFILES = []

# --- TEMPLATE MEMORY ---
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
LAYOUT_DNA_DIR = Path(__file__).resolve().parent / "layout_dna"

# --- GENERATION OPTIONS (SIDEBAR) ---
with st.sidebar:
    st.markdown("#### Generation options")
    profile_key = st.selectbox(
        "Profile",
        options=profile_options(PROFILES),
        format_func=lambda key: (
            "Custom (manual controls)"
            if key == CUSTOM_PROFILE_ID
            else get_profile(PROFILES, key).label
        ),
        key="generation_profile",
    )
    active_profile = get_profile(PROFILES, profile_key)
    profile_active = active_profile is not None
    if profile_active:
        st.caption(active_profile.description)

    st.selectbox(
        "Tone",
        options=tone_options(),
        format_func=lambda key: TONE_PRESETS_BY_KEY[key].label,
        key="generation_tone",
        disabled=profile_active,
    )
    st.select_slider(
        "Complexity",
        options=[1, 2, 3],
        format_func=lambda n: COMPLEXITY_BY_KEY[complexity_options()[n - 1]].label,
        value=complexity_options().index(st.session_state.generation_complexity) + 1,
        key="generation_complexity_slider",
        help="How much the generated page should include. Compact = minimal; Detailed = richer.",
        disabled=profile_active,
    )
    st.session_state.generation_complexity = complexity_options()[
        st.session_state.generation_complexity_slider - 1
    ]
    st.toggle("Strict minimal mode", key="strict_minimal_mode", disabled=profile_active)
    st.caption(
        "Strict minimal mode restricts output to flat, monochrome, decoration-free designs."
    )

    with st.expander("Constraint-first generation"):
        st.checkbox(
            "Generate from constraints",
            key="constraint_mode",
            help="Build the page from selected sections and limits; the model fills in the details.",
        )
        if st.session_state.constraint_mode:
            st.multiselect(
                "Sections",
                options=[s.key for s in SECTION_OPTIONS],
                format_func=lambda key: SECTION_OPTIONS_BY_KEY[key].label,
                default=["hero", "features", "footer"],
                key="constraint_sections",
            )
            st.selectbox(
                "Color limit",
                options=[c.key for c in COLOR_LIMITS],
                format_func=lambda key: COLOR_LIMITS_BY_KEY[key].label,
                key="constraint_color",
            )
            st.selectbox(
                "Density",
                options=complexity_options(),
                format_func=lambda key: COMPLEXITY_BY_KEY[key].label,
                key="constraint_density",
            )
            if st.button(
                "Generate from constraints",
                disabled=st.session_state.is_generating,
                help="Sends the constraints as the generation prompt.",
            ):
                prompt = build_constraints_prompt(
                    st.session_state.constraint_sections,
                    st.session_state.constraint_color,
                    st.session_state.constraint_density,
                )
                add_user_message_and_start_generation(st.session_state, prompt)
                st.rerun()

    if profile_active:
        effective_tone = active_profile.tone_key
        effective_complexity = active_profile.complexity_key
        effective_strict = active_profile.strict_minimal
        effective_guidance = active_profile.extra_guidance
    else:
        effective_tone = st.session_state.generation_tone
        effective_complexity = st.session_state.generation_complexity
        effective_strict = st.session_state.strict_minimal_mode
        effective_guidance = ""

    st.markdown("#### Refine")
    if (
        st.session_state.last_app_code
        and not st.session_state.is_generating
        and not st.session_state.is_regenerating_section
    ):
        st.toggle(
            "WYSIWYG editing",
            key="wysiwyg_editing",
            help="Turn on click-to-edit in the preview: select an element, edit text,"
            " restyle it, then Apply to sync changes into the page.",
        )
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
                options=list(range(len(sections))),
                format_func=lambda i: section_labels[i],
                key="section_choice",
            )
            st.selectbox(
                "Refine focus",
                options=[a.key for a in REFINE_ASPECTS],
                format_func=lambda key: REFINE_ASPECTS_BY_KEY[key].label,
                key="refine_aspect",
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

    st.markdown("#### Layout DNA")
    if (
        st.session_state.last_app_code
        and not st.session_state.is_generating
        and not st.session_state.is_regenerating_section
    ):
        current_dna = extract_layout_dna(
            strip_html_code_fence(st.session_state.last_app_code)
        )
        st.caption(
            f"Grammar: **{grammar_signature(current_dna)}** · "
            f"{current_dna.script_statement_count} JS statement(s)"
        )
        if st.button("Save this layout as DNA"):
            saved = save_dna(LAYOUT_DNA_DIR, current_dna)
            st.success(f"Saved layout DNA '{saved.stem}'.")
            st.rerun()
        saved_dnas = list_saved_dnas(LAYOUT_DNA_DIR)
        if saved_dnas:
            dna_labels = [
                f"{name}: {grammar_signature(dna)}" for name, dna in saved_dnas
            ]
            st.selectbox(
                "Apply a saved layout",
                options=list(range(len(saved_dnas))),
                format_func=lambda i: dna_labels[i],
                key="layout_dna_choice",
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Use layout"):
                    st.session_state.layout_dna_guidance = to_guidance(
                        saved_dnas[st.session_state.layout_dna_choice][1]
                    )
                    st.rerun()
            with col2:
                if st.button("Clear layout"):
                    st.session_state.layout_dna_guidance = ""
                    st.rerun()
        if st.session_state.layout_dna_guidance:
            st.caption("Layout guidance will be applied to the next generation.")
    else:
        st.caption("Generate a website first to inspect its layout DNA.")

# --- APP STYLES (token-driven, from src/theme) ---
st.markdown(build_app_styles(), unsafe_allow_html=True)

# --- START APP LAYOUT ---


# CONTENT AREA - Either empty state or generated preview

# --- TABS: Preview | Code ---
tab_labels = ["Preview", "Code"]
tab1, tab2 = st.tabs(tab_labels)
if st.session_state.last_app_code:
    preview_code = strip_html_code_fence(st.session_state.last_app_code)
    with tab1:
        container_class = preview_container_class(st.session_state.is_generating)
        st.markdown(
            f'<div class="{container_class}" style="position:relative;">',
            unsafe_allow_html=True,
        )
        editing = bool(st.session_state.wysiwyg_editing) and not (
            st.session_state.is_generating or st.session_state.is_regenerating_section
        )
        preview_document = build_editable_preview_document(
            preview_code, editing=editing
        )
        edit_message = wysiwyg_preview(
            html=preview_document,
            editing=editing,
            height=800,
            key="wysiwyg_preview",
        )
        if edit_message and consume_edit_message(st.session_state, edit_message):
            st.toast("WYSIWYG edits applied")
            st.rerun()
        if st.session_state.is_generating or st.session_state.is_regenerating_section:
            st.markdown(PREVIEW_LOADER_OVERLAY_HTML, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with tab2:
        export_mode = st.radio(
            "Export format",
            options=["Single HTML", "Split (index.html + styles.css + app.js)"],
            horizontal=True,
            key="export_format",
        )
        if export_mode == "Single HTML":
            st.download_button(
                "Download HTML",
                data=preview_code,
                file_name="index.html",
                mime="text/html",
            )
        else:
            split = split_document(preview_code)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.download_button(
                    "index.html",
                    data=split.index_html,
                    file_name="index.html",
                    mime="text/html",
                )
            with col2:
                if split.styles_css:
                    st.download_button(
                        "styles.css",
                        data=split.styles_css,
                        file_name="styles.css",
                        mime="text/css",
                    )
                else:
                    st.caption("No CSS to export")
            with col3:
                if split.app_js:
                    st.download_button(
                        "app.js",
                        data=split.app_js,
                        file_name="app.js",
                        mime="text/javascript",
                    )
                else:
                    st.caption("No JS to export")

        st.markdown("#### Templates")
        template_name = st.text_input(
            "Save current page as a template",
            placeholder="my-page",
            key="template_name_input",
        )
        if st.button("Save template"):
            if template_name.strip():
                try:
                    saved = save_template(TEMPLATES_DIR, template_name, preview_code)
                    st.success(f"Saved template '{saved.stem}'.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
            else:
                st.warning("Enter a template name first.")

        available = list_templates(TEMPLATES_DIR)
        if available:
            template_choice = st.selectbox(
                "Start from a saved template",
                options=available,
                key="template_choice",
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Use template"):
                    try:
                        seed_from_template(
                            st.session_state,
                            load_template(TEMPLATES_DIR, template_choice),
                        )
                        st.rerun()
                    except FileNotFoundError:
                        st.error("Template no longer exists.")
            with col2:
                if st.button("Delete template"):
                    delete_template(TEMPLATES_DIR, template_choice)
                    st.rerun()
        else:
            st.caption("No saved templates yet.")

        st.code(preview_code, language="html")
else:
    with tab1:
        st.markdown(EMPTY_STATE_HTML, unsafe_allow_html=True)
    with tab2:
        st.code(NO_CODE_PLACEHOLDER, language="html")


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
        tone_key=effective_tone,
        strict_minimal=effective_strict,
        complexity_key=effective_complexity,
        extra_guidance=combine_guidance(
            effective_guidance,
            st.session_state.get("layout_dna_guidance"),
        ),
        analytics_file=config.analytics_file,
        refine_aspect_key=st.session_state.get("refine_aspect"),
        provider=config.provider,
        api_key=config.openrouter_api_key or "",
        base_url=config.openrouter_base_url,
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
    js_notes = audit_inline_scripts(updated_code)
    if js_notes:
        st.info("JavaScript notes: " + " ".join(js_notes))

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
        tone_key=effective_tone,
        strict_minimal=effective_strict,
        complexity_key=effective_complexity,
        extra_guidance=combine_guidance(
            effective_guidance,
            st.session_state.get("layout_dna_guidance"),
        ),
        analytics_file=config.analytics_file,
        provider=config.provider,
        api_key=config.openrouter_api_key or "",
        base_url=config.openrouter_base_url,
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
    js_notes = audit_inline_scripts(strip_html_code_fence(sanitized_output))
    if js_notes:
        st.info("JavaScript notes: " + " ".join(js_notes))

    # Update session state with results
    apply_generation_result(st.session_state, sanitized_output)

    # Refresh UI to show new content
    st.rerun()
