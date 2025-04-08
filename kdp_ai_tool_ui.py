# kdp_ai_tool_ui.py (now with DALL·E image support for coloring books)

import streamlit as st
import openai
from fpdf import FPDF
import requests
from PIL import Image
from io import BytesIO

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
        return "Create a black-and-white line art image of a cute animal for a coloring book page."
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
        images = []
        with st.spinner("Generating content using GPT-4o and DALL·E..."):
            for i in range(num_pages):
                try:
                    if book_type == "Coloring Book":
                        dalle_prompt = f"{custom_prompt} (Page {i+1})"
                        image_response = client.images.generate(
                            model="dall-e-3",
                            prompt=dalle_prompt,
                            size="1024x1024",
                            quality="standard",
                            n=1
                        )
                        image_url = image_response.data[0].url
                        image = Image.open(BytesIO(requests.get(image_url).content))
                        images.append(image)
                        pages.append((f"Page {i+1}", dalle_prompt))
                    else:
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[{"role": "user", "content": f"{custom_prompt} (Page {i+1})"}]
                        )
                        text = response.choices[0].message.content.strip()
                        pages.append((f"Page {i+1}", text))
                except Exception as e:
                    pages.append((f"Page {i+1}", f"[Error] {str(e)}"))

        # --- Generate PDF ---
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        font_path = "DejaVuSans.ttf"
        pdf.add_font("DejaVu", "", font_path, uni=True)
        pdf.set_font("DejaVu", size=16)
        pdf.cell(0, 10, "KDP AI Book - Generated with GPT-4o", ln=True, align="C")
        pdf.ln(10)
        pdf.set_font("DejaVu", size=12)

        for i, (title, content) in enumerate(pages):
            pdf.set_font("DejaVu", style="B", size=12)
            pdf.multi_cell(0, 10, title)
            pdf.set_font("DejaVu", style="", size=12)
            if book_type == "Coloring Book" and i < len(images):
                # Save image temporarily
                image_path = f"temp_image_{i}.png"
                images[i].save(image_path)
                pdf.image(image_path, x=10, y=None, w=180)
            else:
                pdf.multi_cell(0, 10, content)
            if i < len(pages) - 1:
                pdf.add_page()

        output_path = "kdp_ai_book.pdf"
        pdf.output(output_path)

        st.success("✅ Book generated successfully!")
        with open(output_path, "rb") as file:
            st.download_button("📥 Download Book PDF", file, file_name="kdp_ai_book.pdf")

        st.subheader("📄 Preview")
        for i, (title, content) in enumerate(pages[:3]):
            st.markdown(f"### {title}")
            if book_type == "Coloring Book" and i < len(images):
                st.image(images[i], caption=content, use_column_width=True)
            else:
                st.markdown(content)
