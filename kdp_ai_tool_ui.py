# kdp_ai_tool_ui.py (Improved tool with SD connection check)

import streamlit as st
import openai
from fpdf import FPDF
import requests
from PIL import Image
from io import BytesIO
import os
import base64
import pandas as pd

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
generate_cover = st.sidebar.checkbox("Generate DALL·E 3 Cover", value=True)
cover_title = st.sidebar.text_input("Cover Title", value="A Bedtime Story")
use_local_sd = st.sidebar.checkbox("🖥️ Use Local Stable Diffusion (for pages)", value=True)

# --- Check Local SD Availability ---
def check_sd_connection():
    try:
        r = requests.get("http://127.0.0.1:7860/sdapi/v1/sd-models", timeout=5)
        if r.status_code == 200:
            return True
    except:
        pass
    return False

sd_available = check_sd_connection()
if use_local_sd:
    if sd_available:
        st.sidebar.success("✅ Stable Diffusion API connected")
    else:
        st.sidebar.error("❌ Can't connect to SD at 127.0.0.1:7861")

# --- Prompt Suggestions ---
def get_prompt_template(book_type):
    if book_type == "Coloring Book":
        return "A cute unicorn with rainbow mane, magical lighting, soft pastel clouds, dreamy fantasy storybook style"
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

uploaded_images = []
if book_type == "Coloring Book":
    st.markdown("### 📥 Upload Coloring Pages (Optional)")
    uploaded_images = st.file_uploader("Upload coloring page images to convert to fantasy style", accept_multiple_files=True, type=["png", "jpg", "jpeg"])

editable_pages = []
metadata_records = []

# Local SD generator

def generate_with_local_sd(image, prompt):
    try:
        api_url = "http://127.0.0.1:7861/sdapi/v1/img2img"
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        b64_img = base64.b64encode(buffered.getvalue()).decode()

        payload = {
            "init_images": [b64_img],
            "prompt": prompt,
            "sampler_name": "Euler a",
            "cfg_scale": 7,
            "steps": 30,
            "denoising_strength": 0.6,
            "width": 512,
            "height": 512
        }

        response = requests.post(api_url, json=payload).json()
        result_b64 = response["images"][0]
        result_bytes = BytesIO(base64.b64decode(result_b64))
        return Image.open(result_bytes)
    except Exception as e:
        st.error(f"Local SD failed: {e}")
        return image

# Generate book content
if st.button("🚀 Generate Book"):
    if not api_key:
        st.warning("Please enter your OpenAI API key in the sidebar.")
    else:
        client = openai.OpenAI(api_key=api_key)

        pages = []
        images = []
        with st.spinner("Generating content using GPT-4o and DALL·E / Local SD..."):
            for i in range(num_pages):
                try:
                    title = f"Page {i+1}"
                    prompt = f"{custom_prompt} (Page {i+1})"
                    if book_type == "Coloring Book" and i < len(uploaded_images):
                        uploaded_file = uploaded_images[i]
                        original_img = Image.open(uploaded_file).convert("RGB")
                        if use_local_sd and sd_available:
                            image = generate_with_local_sd(original_img, custom_prompt)
                        else:
                            image_response = client.images.generate(
                                model="dall-e-3",
                                prompt=custom_prompt,
                                size="1024x1024",
                                quality="standard",
                                n=1
                            )
                            image_url = image_response.data[0].url
                            image = Image.open(BytesIO(requests.get(image_url).content))
                        pages.append((title, prompt))
                        images.append(image)
                        metadata_records.append({"Title": title, "Prompt": prompt, "Type": book_type})
                    else:
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[{"role": "user", "content": prompt}]
                        )
                        text = response.choices[0].message.content.strip()
                        editable_text = st.text_area(f"📝 Edit {title}", text)
                        pages.append((title, editable_text))
                        metadata_records.append({"Title": title, "Prompt": editable_text, "Type": book_type})
                except Exception as e:
                    pages.append((f"Page {i+1}", f"[Error] {str(e)}"))

        # --- Optional Cover Generation ---
        cover_image = None
        if generate_cover:
            try:
                cover_response = client.images.generate(
                    model="dall-e-3",
                    prompt=f"a magical unicorn standing in a sunny fantasy meadow, children's book cover, soft dreamy pastel colors, title: {cover_title}",
                    size="1024x1024",
                    quality="hd",
                    n=1
                )
                cover_url = cover_response.data[0].url
                cover_image = Image.open(BytesIO(requests.get(cover_url).content))
            except Exception as e:
                st.error(f"Cover generation failed: {e}")

        # --- Generate PDF ---
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)

        font_path = "DejaVuSans.ttf"
        pdf.add_font("DejaVu", "", font_path, uni=True)
        pdf.set_font("DejaVu", size=16)

        if cover_image:
            pdf.add_page()
            cover_image_path = "cover_temp.png"
            cover_image.save(cover_image_path)
            pdf.image(cover_image_path, x=10, y=10, w=180)
            pdf.ln(120)
            pdf.set_font("DejaVu", size=20)
            pdf.cell(0, 10, cover_title, ln=True, align="C")

        for i, (title, content) in enumerate(pages):
            pdf.add_page()
            pdf.set_font("DejaVu", size=12)
            pdf.multi_cell(0, 10, title)
            if book_type == "Coloring Book" and i < len(images):
                image_path = f"temp_image_{i}.png"
                images[i].save(image_path)
                pdf.image(image_path, x=10, y=None, w=180)
            else:
                pdf.multi_cell(0, 10, content)

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

        if cover_image:
            st.subheader("🖼️ Generated Cover")
            st.image(cover_image, caption=cover_title, use_column_width=True)

        # --- Export Metadata CSV ---
        st.subheader("📄 Book Metadata")
        metadata_df = pd.DataFrame(metadata_records)
        st.dataframe(metadata_df)
        st.download_button("📥 Download CSV Metadata", metadata_df.to_csv(index=False).encode(), "kdp_book_metadata.csv")
