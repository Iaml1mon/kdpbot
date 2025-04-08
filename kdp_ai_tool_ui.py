# kdp_ai_tool_ui.py (uses local DejaVuSans.ttf font for Unicode PDF)

import streamlit as st
import openai
from fpdf import FPDF

# --- Streamlit UI ---
st.set_page_config(page_title="KDP AI Book Creator", layout="centered")
st.title("📘 KDP AI Book Creator")

# --- Sidebar Settings ---
st.sidebar.header("🔐 API Key Setup")
api_key = st.sidebar.text_input("Enter your OpenAI API key", type="password")

# --- Book Type Dropdown ---
st.sidebar.header("📚 Book Settings")
book_type = st.sidebar.selectbox("Choose Book Type", [
    "Coloring Book",
    "Planner",
    "Storybook",
    "Journal",
    "Quote Book"
])

num_pages = st.sidebar.slider("Number of Pages", min_value=5, max_value=50, value=10)

# --- Prompt Suggestions ---
def get_prompt_template(book_type):
    if book_type == "Coloring Book":
        return "Generate a black-and-white coloring page idea for kids with cute animals."
    elif book_type == "Planner":
        return "Generate a daily planner layout idea with motivational elements."
    elif book_type == "Storybook":
        return "Write a short bedtime story for children under 100 words."
    elif book_type == "Journal":
        return "Generate a journal prompt with space to write reflections."
    elif book_type == "Quote Book":
        return "Provide an inspirational quote with author's name."
    return ""

prompt_template = get_prompt_template(book_type)
custom_prompt = st.text_area("Customize the AI prompt:", prompt_template)

if st.button("🚀 Generate Book"):
    if not api_key:
        st.warning("Please enter your OpenAI API key in the sidebar.")
    else:
        client = openai.OpenAI(api_key=api_key)

        pages = []
        with st.spinner("Generating content using GPT-4o..."):
            for i in range(num_pages):
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": f"{custom_prompt} (Page {i+1})"}]
                    )
                    text = response.choices[0].message.content.strip()
                    pages.append(f"Page {i+1}:\n{text}\n")
                except Exception as e:
                    pages.append(f"Page {i+1}: [Error] {str(e)}\n")

        # --- Generate PDF ---
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # Use a local Unicode-safe font
        font_path = "DejaVuSans.ttf"  # Make sure this file is in the same directory
        pdf.add_font("DejaVu", "", font_path, uni=True)
        pdf.set_font("DejaVu", size=12)

        for page in pages:
            pdf.multi_cell(0, 10, page)
            pdf.add_page()

        output_path = "kdp_ai_book.pdf"
        pdf.output(output_path)

        st.success("✅ Book generated successfully!")
        with open(output_path, "rb") as file:
            st.download_button("📥 Download Book PDF", file, file_name="kdp_ai_book.pdf")

        st.subheader("📄 Preview")
        for page in pages[:3]:
            st.text(page)
