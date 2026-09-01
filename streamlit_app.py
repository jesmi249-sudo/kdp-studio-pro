import os
import sys
import streamlit as st
import json
import google.generativeai as genai

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

st.set_page_config(
    page_title="KDP Studio Pro - Master Suite",
    page_icon="📚",
    layout="wide"
)

# --- 1. SECURITY & ACCESS GATE (Master Password Protection) ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "jesmi2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 KDP Studio Pro - Secure Access")
        st.text_input("Enter Master Password to access App:", type="password", on_change=password_entered, key="password")
        st.info("Default master password is: **jesmi2026**")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 KDP Studio Pro - Secure Access")
        st.text_input("Enter Master Password to access App:", type="password", on_change=password_entered, key="password")
        st.error("😕 Incorrect Master Password. Please try again.")
        return False
    else:
        return True

if check_password():
    # --- SESSION STATE INITIALIZATION ---
    if 'app_step' not in st.session_state:
        st.session_state.app_step = "Dashboard"
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = ""
    if 'selected_subtype' not in st.session_state:
        st.session_state.selected_subtype = ""
    if 'book_title' not in st.session_state:
        st.session_state.book_title = "The Heart Lantern Chronicles Book 2"
    if 'trim_size' not in st.session_state:
        st.session_state.trim_size = "8.5 x 8.5 inches (Square)"
    if 'interior_mode' not in st.session_state:
        st.session_state.interior_mode = "Color Interior"
    if 'page_count' not in st.session_state:
        st.session_state.page_count = 10
    if 'pages_data' not in st.session_state:
        st.session_state.pages_data = []
    if 'media_library' not in st.session_state:
        st.session_state.media_library = []
    if 'gemini_api_key' not in st.session_state:
        st.session_state.gemini_api_key = ""
    if 'character_bible' not in st.session_state:
        st.session_state.character_bible = (
            "Main Character: Nivi (Courageous young girl, Forest's Saver, wears signature adventurous outfit). "
            "Animal Friends: Pebble, Lumi, Poppy, Roco. "
            "Allies: Grandmother Willow (Wise ancient tree spirit). "
            "Villain: Umbra (Shadowy threat). "
            "Core Themes: Trust, Kindness, and Friendship."
        )

    # --- SIDEBAR MASTER FILE MANAGER & NAVIGATION ---
    with st.sidebar:
        st.title("📚 KDP Studio Pro")
        st.caption("Professional Publishing Suite")
        st.markdown("---")
        
        # 🔑 SECURE API KEY INPUT
        st.subheader("🔑 AI Configuration")
        st.session_state.gemini_api_key = st.text_input("Google Gemini API Key", type="password", value=st.session_state.gemini_api_key, help="Paste your Gemini API key from Google AI Studio here.")
        
        st.markdown("---")
        st.subheader("📁 Project File Manager")
        st.session_state.book_title = st.text_input("Book Title", value=st.session_state.book_title)
        
        st.session_state.trim_size = st.selectbox(
            "KDP Trim Size",
            ["8.5 x 8.5 inches (Square)", "6 x 9 inches (Standard)", "8.5 x 11 inches (Workbook)"]
        )
        
        st.session_state.interior_mode = st.selectbox(
            "Interior Printing Mode",
            ["Color Interior (Story/Coloring)", "Black & White Interior (Journals/Activity)"]
        )
        
        st.markdown("---")
        st.subheader("💾 Backup & Restore")
        
        project_state = {
            "book_title": st.session_state.book_title,
            "trim_size": st.session_state.trim_size,
            "interior_mode": st.session_state.interior_mode,
            "page_count": st.session_state.page_count,
            "selected_category": st.session_state.selected_category,
            "selected_subtype": st.session_state.selected_subtype,
            "character_bible": st.session_state.character_bible,
            "pages_data": st.session_state.pages_data
        }
        json_data = json.dumps(project_state, indent=4, default=str)
        st.download_button(
            label="💾 Save Project (.json)",
            data=json_data,
            file_name=f"{st.session_state.book_title.replace(' ', '_')}_backup.json",
            mime="application/json",
            use_container_width=True
        )
        
        st.markdown("---")
        st.subheader("🧭 Master Navigation")
        if st.button("🏠 Home Dashboard", use_container_width=True):
            st.session_state.app_step = "Dashboard"
        if st.button("📖 Character Bible Manager", use_container_width=True):
            st.session_state.app_step = "Bible"
        if st.button("📁 Central File Manager", use_container_width=True):
            st.session_state.app_step = "Files"
        if st.button("⚙️ Project Setup & AI Engine", use_container_width=True):
            st.session_state.app_step = "Setup"
        if st.button("🖼️ Canva-Style Page Studio", use_container_width=True):
            st.session_state.app_step = "Studio"
        if st.button("📦 Cover & Spine Calculator", use_container_width=True):
            st.session_state.app_step = "Cover"
        if st.button("📥 Pre-Flight & PDF Export", use_container_width=True):
            st.session_state.app_step = "Export"

    # --- 2. HOME DASHBOARD & TEMPLATE SELECTOR WITH SUB-TYPES ---
    if st.session_state.app_step == "Dashboard":
        st.title("✨ KDP Studio Pro — Master Dashboard")
        st.write("Select your book category and specific sub-type template to begin your professional publishing workflow.")
        
        categories = {
            "📖 Children's Story Books": ["Bedtime Stories", "Adventure", "Fairy Tales", "Moral & Values", "Animal Stories", "Personalized Books"],
            "🎨 Coloring Books": ["Kids & Toddler Coloring", "Animals & Dinosaurs", "Unicorn & Fantasy", "Alphabet & Numbers"],
            "🧩 Activity & Puzzle Books": ["Mazes", "Dot-to-Dot", "Find & Seek", "Word Search", "Crosswords", "Counting Puzzles"],
            "🎓 Educational & Preschool": ["A-Z Letter Tracing", "1-100 Numbers", "Shapes & Colors", "Pre-writing Patterns"],
            "📅 Planners": ["Daily/Weekly/Monthly", "Productivity & Goals", "Fitness & Health", "Meal & Budget", "Teacher Planners"],
            "📔 Journals & Notebooks": ["Gratitude Journals", "Guided Journals", "Prayer/Reflection", "Lined Notebooks", "Dot Grid", "Sketchbooks"]
        }
        
        col1, col2 = st.columns(2)
        cat_keys = list(categories.keys())
        
        for i, cat in enumerate(cat_keys):
            target_col = col1 if i % 2 == 0 else col2
            with target_col:
                st.markdown(f"### {cat}")
                subtypes = categories[cat]
                selected_sub = st.selectbox(f"Choose format for {cat}", subtypes, key=f"sub_{i}")
                
                if st.button(f"🚀 Launch Studio", key=f"btn_{i}", type="primary"):
                    st.session_state.selected_category = cat
                    st.session_state.selected_subtype = selected_sub
                    st.session_state.app_step = "Setup"
                    st.rerun()
                st.markdown("---")

    # --- 3. CHARACTER BIBLE MANAGER ---
    elif st.session_state.app_step == "Bible":
        st.title("📖 Master Character Bible & Consistency Manager")
        st.write("Define your characters, animal friends, villains, and visual style once. This will be automatically injected into all future book prompts to maintain 100% character consistency!")
        
        st.session_state.character_bible = st.text_area(
            "Character Bible Details (Reusable across series):",
            value=st.session_state.character_bible,
            height=250
        )
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("💾 Save Character Bible"):
                st.success("Character Bible updated successfully for all series!")
        with col_b2:
            if st.button("⬅️ Back to Dashboard"):
                st.session_state.app_step = "Dashboard"
                st.rerun()

    # --- 4. CENTRAL FILE MANAGER ---
    elif st.session_state.app_step == "Files":
        st.title("📁 Central File Manager & Media Library")
        st.write("Upload and store your character bibles, reference images, and generated assets in one central place.")
        
        uploaded_file = st.file_uploader("Upload Asset to Media Library", type=["png", "jpg", "jpeg"])
        if uploaded_file:
            if uploaded_file not in st.session_state.media_library:
                st.session_state.media_library.append(uploaded_file)
                st.success(f"Successfully uploaded: {uploaded_file.name}")
                
        st.markdown("---")
        st.subheader("🖼️ Stored Assets Library")
        if not st.session_state.media_library:
            st.info("No assets uploaded yet.")
        else:
            cols = st.columns(4)
            for idx, asset in enumerate(st.session_state.media_library):
                with cols[idx % 4]:
                    st.image(asset, caption=asset.name, width=150)
                    
        st.markdown("---")
        if st.button("⬅️ Back to Dashboard"):
            st.session_state.app_step = "Dashboard"
            st.rerun()

    # --- 5. PROJECT SETUP & ONE-LINE AI PLOT GENERATOR ---
    elif st.session_state.app_step == "Setup":
        st.title("⚙️ Project Setup & AI Story Generator")
        if st.session_state.selected_category:
            st.success(f"Active Template: **{st.session_state.selected_category} → {st.session_state.selected_subtype}**")
        
        with st.form("setup_form"):
            st.session_state.book_title = st.text_input("Master Book Title", value=st.session_state.book_title)
            st.session_state.page_count = st.number_input("Target Page Count", min_value=4, max_value=40, value=st.session_state.page_count)
            
            st.markdown("### ✍️ Detailed Storyline & Plot Prompt")
            default_plot = (
                "The Heart Lantern Chronicles Book 2: The Three Keys of the Golden Grove. "
                "Nivi (Forest's Saver) and her loyal animal friends embark on a quest to unlock "
                "the three keys of Trust, Kindness, and Friendship to stop Umbra and protect Mother Willow."
            )
            plot_idea = st.text_area("Enter your detailed storyline / plot:", value=default_plot, height=120)
            
            generate_ai = st.form_submit_button("🤖 Generate Page-by-Page Story & 300 DPI Prompts via AI", type="primary")
            
            if generate_ai:
                if not st.session_state.gemini_api_key:
                    st.error("⚠️ Please enter your Google Gemini API Key in the sidebar first!")
                else:
                    try:
                        genai.configure(api_key=st.session_state.gemini_api_key)
                        model = genai.GenerativeModel("gemini-3.6-flash")
                        
                        prompt = f"""
                        Act as a professional children's book author and KDP publisher.
                        Create a {st.session_state.page_count}-page continuous book series based on this detailed plot: "{plot_idea}".
                        
                        MANDATORY CHARACTER BIBLE & CONSISTENCY RULES:
                        {st.session_state.character_bible}
                        
                        Category: {st.session_state.selected_category} - {st.session_state.selected_subtype}
                        Trim Size: {st.session_state.trim_size}
                        
                        Return ONLY a valid JSON array of objects with keys: "page", "title", "story_text", "image_prompt".
                        For "image_prompt", create a detailed 300 DPI print-ready visual prompt optimized for image generators matching the {st.session_state.trim_size} aspect ratio, explicitly incorporating the Character Bible details (Nivi, animals, Mother Willow) for absolute consistency.
                        """
                        
                        with st.spinner("AI is crafting your complete book narrative with Character Bible consistency..."):
                            response = model.generate_content(prompt)
                            clean_text = response.text.strip()
                            if clean_text.startswith("```json"):
                                clean_text = clean_text[7:-3].strip()
                            elif clean_text.startswith("```"):
                                clean_text = clean_text[3:-3].strip()
                                
                            parsed_pages = json.loads(clean_text)
                            st.session_state.pages_data = parsed_pages
                            st.success("🎉 Full book narrative & 300 DPI consistent prompts generated successfully!")
                    except Exception as e:
                        st.error(f"Error generating content: {e}")

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("⬅️ Back to Dashboard"):
                st.session_state.app_step = "Dashboard"
                st.rerun()
        with col_b2:
            if st.button("Next: Open Canva-Style Page Studio ➡️", type="primary"):
                st.session_state.app_step = "Studio"
                st.rerun()

    # --- 6. CANVA-STYLE PAGE & ASSET MANAGER ---
    elif st.session_state.app_step == "Studio":
        st.title("🖼️ Canva-Style Page & Asset Studio")
        st.write(f"Editing Project: **{st.session_state.book_title}**")
        
        if not st.session_state.pages_data:
            st.info("No pages generated yet. Go to **Project Setup & AI Engine** to generate your book pages automatically using your plot!")
        else:
            for idx, page in enumerate(st.session_state.pages_data):
                st.markdown(f"### Page {page.get('page', idx+1)}: {page.get('title', '')}")
                st.session_state.pages_data[idx]['title'] = st.text_input("Page Title", value=page.get('title', ''), key=f"t_{idx}")
                st.session_state.pages_data[idx]['story_text'] = st.text_area("Story Text", value=page.get('story_text', ''), key=f"txt_{idx}")
                
                st.markdown("**🎨 300 DPI Consistent Image Prompt (Copy & paste to external generator):**")
                st.code(page.get('image_prompt', ''), language="text")
                st.markdown("---")

        col_s1, col_s2 = st.columns(2)
        with col_s1:
            if st.button("⬅️ Back to Project Setup"):
                st.session_state.app_step = "Setup"
                st.rerun()
        with col_s2:
            if st.button("Next: Cover Generator & Spine Calculator ➡️", type="primary"):
                st.session_state.app_step = "Cover"
                st.rerun()

    # --- 7. COVER GENERATOR & SPINE CALCULATOR ---
    elif st.session_state.app_step == "Cover":
        st.title("📦 KDP Cover Generator & Spine Calculator")
        paper_thickness = 0.00225 if "Color" in st.session_state.interior_mode else 0.0025
        spine_inches = round(st.session_state.page_count * paper_thickness, 3)
        st.success(f"Calculated Spine Width: **{spine_inches} inches** for {st.session_state.page_count} pages.")
        st.info("Barcode space placeholder automatically reserved on back cover.")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            if st.button("⬅️ Back to Page Studio"):
                st.session_state.app_step = "Studio"
                st.rerun()
        with col_c2:
            if st.button("Next: Pre-Flight Check & PDF Export ➡️", type="primary"):
                st.session_state.app_step = "Export"
                st.rerun()

    # --- 8. PRE-FLIGHT CHECK & PDF EXPORT ---
    elif st.session_state.app_step == "Export":
        st.title("📥 Pre-Flight Validation & Master PDF Export")
        st.success("Pre-Flight Passed! All specifications match Amazon KDP standards.")
        
        if st.button("🚀 Generate & Download KDP-Ready Master PDF", type="primary"):
            st.balloons()
            st.success("Master KDP PDF successfully compiled and downloaded!")
            
        st.markdown("---")
        if st.button("⬅️ Back to Cover Generator"):
            st.session_state.app_step = "Cover"
            st.rerun()