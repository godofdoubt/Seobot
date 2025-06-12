import streamlit as st
import requests
import os
import base64
from dotenv import load_dotenv

# --- Load Environment Variables ---
# Call this function at the beginning of your script to load variables from the .env file
load_dotenv() 

# --- Page Configuration ---
st.set_page_config(
    page_title="Image Creator",
    page_icon="🎨",
    layout="centered"
)

# --- Main Application ---

def image_creator_page():
    """
    Defines the layout and functionality of the Streamlit image generator page.
    """

    # --- State Management ---
    # Initialize session state variables, similar to React's useState
    if "prompt" not in st.session_state:
        st.session_state.prompt = (
            "A vibrant, engaging image for a tech blog post about AI in content creation. "
            "The image should feature abstract digital patterns, neural network motifs, or a "
            "stylized brain icon intertwined with flowing text or data streams. Use a modern, "
            "clean aesthetic with a color palette of deep blues, teals, and accents of bright "
            "orange or electric green. Focus on conveying innovation, intelligence, and "
            "seamless automation."
        )
    if "image_url" not in st.session_state:
        st.session_state.image_url = ""
    if "is_loading" not in st.session_state:
        st.session_state.is_loading = False
    if "error" not in st.session_state:
        st.session_state.error = ""

    # --- UI Components ---
    st.title("🎨 Ricas.com Website Image Generator")
    st.markdown(
        "Generate custom images for your website product and blog pages by refining the prompt below."
    )

    # --- API Key Handling ---
    # The 'load_dotenv()' call above makes the .env variables available via os.environ
    api_key = os.environ.get("IMAGEN_API_KEY")

    if not api_key:
        # Added a fallback to st.secrets for when you deploy the app
        try:
            api_key = st.secrets["IMAGEN_API_KEY"]
        except (FileNotFoundError, KeyError):
            st.warning(
                "**API key not found.** Please create a `.env` file with `IMAGEN_API_KEY='your_key'` for local development, "
                "or set it in Streamlit Secrets for deployment.",
                icon="⚠️"
            )
            st.stop()

    # --- Image Generation Prompt ---
    st.session_state.prompt = st.text_area(
        label="**Image Generation Prompt:**",
        value=st.session_state.prompt,
        height=160,
        placeholder="Describe the image you want to generate for your website or blog...",
        help="The more descriptive your prompt, the better the result will be."
    )

    # --- Generate Image Button ---
    if st.button("Generate Image", type="primary", use_container_width=True, disabled=(not api_key)):
        st.session_state.is_loading = True
        st.session_state.error = ""
        st.session_state.image_url = ""
        
        # --- API Call Logic ---
        with st.spinner("Please wait, your image is being generated..."):
            try:
                # Construct the payload and API URL
                payload = {
                    "instances": [{"prompt": st.session_state.prompt}],
                    "parameters": {"sampleCount": 1}
                }
                api_url = f"https://generativelanguage.googleapis.com/v1beta/models/imagen-3.0-generate-002:predict?key={api_key}"

                # Make the fetch call to the Imagen API
                response = requests.post(
                    api_url,
                    headers={'Content-Type': 'application/json'},
                    json=payload,
                    timeout=120  # Set a timeout for the request
                )
                
                response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

                result = response.json()

                # Process the API response
                if (result.get("predictions") and
                    isinstance(result["predictions"], list) and
                    len(result["predictions"]) > 0 and
                    result["predictions"][0].get("bytesBase64Encoded")):
                    
                    base64_image = result["predictions"][0]["bytesBase64Encoded"]
                    st.session_state.image_url = f"data:image/png;base64,{base64_image}"
                else:
                    st.session_state.error = "Failed to generate image. The API response did not contain valid image data."

            except requests.exceptions.HTTPError as http_err:
                st.session_state.error = f"HTTP error occurred: {http_err} - {response.text}"
            except Exception as err:
                st.session_state.error = f"An error occurred: {err}"
            finally:
                st.session_state.is_loading = False

    st.divider()

    # --- Display Area ---
    if st.session_state.error:
        st.error(f"**Error generating image:**\n\n{st.session_state.error}")
    
    if st.session_state.image_url:
        st.subheader("Your Generated Image:")
        st.image(
            st.session_state.image_url,
            caption="Right-click or long-press to save the image.",
            use_column_width=True
        )
        
        try:
            image_bytes = base64.b64decode(st.session_state.image_url.split(",")[1])
            st.download_button(
                label="Download Image",
                data=image_bytes,
                file_name="generated_image.png",
                mime="image/png",
                use_container_width=True
            )
        except Exception as e:
            st.warning(f"Could not prepare image for download. Error: {e}")

    elif not st.session_state.is_loading:
        st.info("Enter a prompt and click 'Generate Image' to create your design!")

# --- Run the main function ---
if __name__ == "__main__":
    image_creator_page()