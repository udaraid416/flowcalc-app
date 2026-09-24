import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from audio_recorder_streamlit import audio_recorder
from gtts import gTTS
import tempfile
import os
from PIL import Image

# ==========================================
# 1. PAGE CONFIGURATION & CSS LOADING
# ==========================================
st.set_page_config(page_title="Smart Agri Console", layout="wide", initial_sidebar_state="collapsed")

# Load Custom CSS (Animations, Light/Dark Adaptive Theme & Full Screen)
def local_css(file_name):
    try:
        with open(file_name, "r") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        pass 

local_css("assets/style.css")

# ==========================================
# 2. API KEY SETUP
# ==========================================
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except KeyError:
    st.warning("API Key not found! Please configure GEMINI_API_KEY in Streamlit Secrets.")

# ==========================================
# 3. DYNAMIC MODEL FETCHING (Error Fix)
# ==========================================
@st.cache_resource
def get_working_model_name():
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods and 'flash' in m.name.lower():
                return m.name
    except Exception as e:
        pass
    return "models/gemini-1.5-flash" 

# System Prompt - English language and concise answers
system_instruction = """
You are an experienced agricultural and farming expert. 
Provide accurate, clear, and friendly advice to farmers and researchers regarding their crops (especially hydroponics, lettuce, etc.).
You MUST provide all your answers and explanations entirely in English.
Provide clear, concise, and straight-to-the-point answers to keep the text-to-speech fast and efficient.
If you receive an image or an audio snippet, analyze it and suggest remedies in English.
"""

# ==========================================
# 4. READ HTML FOR FLOWCALC
# ==========================================
try:
    with open("index.html", "r", encoding="utf-8") as f:
        html_code = f.read()
except FileNotFoundError:
    html_code = "<h3>Error! index.html file not found. Ensure it is in the same directory as app.py.</h3>"

# ==========================================
# 5. TABS CREATION
# ==========================================
tab1, tab2 = st.tabs(["💧 FlowCalc Engine", "🤖 Agri-Assistant AI"])

# --- TAB 1: FlowCalc Engine ---
with tab1:
    components.html(html_code, height=950, scrolling=True)

# --- TAB 2: Agri-Assistant AI ---
with tab2:
    st.header("🌱 Agri-Assistant (AI Bot)")
    st.write("Do you have an issue with your crops? Upload a photo of a leaf, or ask your question via microphone.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📸 Provide an Image**")
        img_file_buffer = st.camera_input("Take a photo")
        uploaded_file = st.file_uploader("Or Upload an Image", type=["jpg", "jpeg", "png"])
        
        img_to_send = None
        if img_file_buffer is not None:
            img_to_send = Image.open(img_file_buffer)
        elif uploaded_file is not None:
            img_to_send = Image.open(uploaded_file)
            
        if img_to_send:
            st.image(img_to_send, caption="Uploaded Image", use_container_width=True)

    with col2:
        st.markdown("**🎤 Ask via Microphone**")
        audio_bytes = audio_recorder(text="Click to Record", recording_color="#e84118", neutral_color="#00a8ff")
        
    st.divider()
    
    # Render Chat History
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_query = st.chat_input("Type your question here...")
    
    audio_query = False
    if audio_bytes and "last_audio" not in st.session_state:
        st.session_state.last_audio = audio_bytes
        audio_query = True
    elif audio_bytes and st.session_state.last_audio != audio_bytes:
        st.session_state.last_audio = audio_bytes
        audio_query = True

    # Process Query
    if user_query or audio_query or img_to_send:
        prompt_text = user_query if user_query else "Please check this image or audio and advise me in English."
        
        st.session_state.chat_history.append({"role": "user", "content": prompt_text})
        with st.chat_message("user"):
            st.markdown(prompt_text)

        contents = [prompt_text]
        if img_to_send:
            contents.append(img_to_send)
        
        if audio_bytes and audio_query:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
                tmp_audio.write(audio_bytes)
                tmp_audio_path = tmp_audio.name
            try:
                audio_file = genai.upload_file(path=tmp_audio_path)
                contents.append(audio_file)
            except Exception as e:
                st.error("Audio upload error. Please type your question.")

        with st.chat_message("assistant"):
            with st.spinner("Analyzing... ⏳"):
                try:
                    # Initialize Model dynamically
                    model_name = get_working_model_name()
                    model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
                    
                    response = model.generate_content(contents)
                    bot_reply = response.text
                    st.markdown(bot_reply)
                    st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
                    
                    # Text to Speech (English - Fast Speed)
                    tts = gTTS(text=bot_reply, lang='en', slow=False)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mp3:
                        tts.save(tmp_mp3.name)
                        st.audio(tmp_mp3.name, format="audio/mp3", autoplay=True)
                        
                except Exception as e:
                    st.error(f"Sorry, an error occurred. System Error: {e}")

    # Report Download Option
    if len(st.session_state.chat_history) > 0:
        st.divider()
        report_text = "Agri-Assistant Daily Report\n================================================\n\n"
        for msg in st.session_state.chat_history:
            role = "You" if msg["role"] == "user" else "AI Expert"
            report_text += f"{role}: {msg['content']}\n\n"
            
        downloaded = st.download_button(
            label="📥 Download Daily Log",
            data=report_text,
            file_name="Agri_Report_Log.txt",
            mime="text/plain"
        )
        
        if downloaded:
            st.toast('Report Downloaded Successfully! 🌾', icon='✅')
