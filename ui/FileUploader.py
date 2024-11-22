import io
import asyncio
import base64
from typing import Any, Dict, List
from models import Environ
from pdf2image import convert_from_bytes
import streamlit as st
from openai import AsyncClient
from PIL import Image

environ = Environ()
client = AsyncClient(api_key=environ.openai_api_key)

show_file = True


def file_upload_component():

    uploaded_files = st.file_uploader(
        "Choose a CSV file", accept_multiple_files=True
    )
    files_in_bytes: List[Dict[str, Any]] = []
    for uploaded_file in uploaded_files:
        name_of_file = uploaded_file.name
        bytes_data = uploaded_file.read()
        files_in_bytes.append({"name": name_of_file, "data": bytes_data})
        st.write("filename:", uploaded_file.name)

    st.button(label="Confirm", type="primary",
              on_click=lambda: upload_files(files=files_in_bytes))


@st.cache_data
def create_downloadable_md(md: str):
    # Create a downloadable markdown file
    return md.encode("utf-8")


def upload_files(files: List[Dict[str, Any]]):
    global show_file
    show_file = False
    files_data = [file["data"] for file in files]
    image_bytes = convert_pdf_into_image(files=files_data)
    for i, images in enumerate(image_bytes):
        st.progress(value=i//len(image_bytes), text="Processing Files...")
        mds = run_convert_all_images_into_md(image_bytes=images)
        md = "\n---\n".join(mds)
        files[i]["md"] = md
        del files[i]["data"]
    for file in files:
        name = file["name"]
        md = create_downloadable_md(file["md"])

        st.download_button(
            label=f"Download {name}.md",
            data=md,
            file_name=f"{name}.md",
            mime="text/markdown",
        )


def convert_pdf_into_image(files: List[bytes]) -> List[List[bytes]]:
    image_bytes: List[List[bytes]] = []
    for i, pdf_file_byte in enumerate(files):

        images: List[Image.Image] = convert_from_bytes(pdf_file=pdf_file_byte)
        image_byte: List[bytes] = []
        for image in images:
            with io.BytesIO() as output:
                image.save(output, format="JPEG")
                byte = output.getvalue()
                image_byte.append(byte)
        image_bytes.append(image_byte)
    return image_bytes


def run_convert_all_images_into_md(image_bytes: List[bytes]) -> List[str]:
    return asyncio.run(convert_all_images_into_md(image_bytes=image_bytes))


async def convert_all_images_into_md(image_bytes: List[bytes]) -> List[str]:
    b64s: List[str] = [convert_image_bytes_to_base64(
        image_byte) for image_byte in image_bytes]
    tasks = [convert_image_into_md(b64) for b64 in b64s]
    results = await asyncio.gather(*tasks)
    return results


def convert_image_bytes_to_base64(image_bytes: bytes) -> str:
    return base64.b64encode(image_bytes).decode('utf-8')


async def convert_image_into_md(image_b64: str) -> str:
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract the contents of this image, be as accurate as possible, word for word, no preamble. Ignore logos. If there are diagrams explain it",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url":  f"data:image/jpeg;base64,{image_b64}"
                        },
                    },
                ],
            }
        ],
    )
    return response.choices[0].message.content
