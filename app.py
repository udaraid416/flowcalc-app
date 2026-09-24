import streamlit as st
import streamlit.components.v1 as components
import google.generativeai as genai
from PIL import Image

# ==========================================
# 1. PAGE CONFIGURATION & CSS LOADING
# ==========================================
st.set_page_config(page_title="Smart Agri Console", layout="wide", initial_sidebar_state="collapsed")

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
# 3. DYNAMIC MODEL FETCHING & HELPERS
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

system_instruction = """
You are an experienced agricultural and farming expert. 
Provide accurate, clear, and friendly advice to farmers and researchers regarding their crops.
CRITICAL RULE: You MUST reply to the user in the EXACT SAME LANGUAGE they used to ask the question.
- If they ask in English, reply in English.
- If they ask in Sinhala, reply in Sinhala.
- If they ask in Singlish, reply in Singlish or standard Sinhala.
Keep your answers clear, concise, and straight-to-the-point.
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
    components.html(html_code, height=1000, scrolling=True)

# --- TAB 2: Agri-Assistant AI ---
with tab2:
    st.write("Do you have an issue with your crops? Ask a question or share a photo.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
        
    with st.expander("📸 Open Camera / Image Upload", expanded=False):
        img_file_buffer = st.camera_input("Take a photo")
        uploaded_file = st.file_uploader("Or Upload an Image", type=["jpg", "jpeg", "png"])
            
    img_to_send = None
    if img_file_buffer is not None:
        img_to_send = Image.open(img_file_buffer)
    elif uploaded_file is not None:
        img_to_send = Image.open(uploaded_file)
        
    if img_to_send:
        st.image(img_to_send, caption="Image ready to be sent", use_container_width=True)
        
    st.divider()
    
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_query = st.chat_input("Type your question here...")

    if user_query or (img_to_send and user_query):
        prompt_text = user_query if user_query else "Please analyze this image and advise me."
        
        st.session_state.chat_history.append({"role": "user", "content": prompt_text})
        with st.chat_message("user"):
            st.markdown(prompt_text)

        contents = [prompt_text]
        if img_to_send:
            contents.append(img_to_send)

        with st.chat_message("assistant"):
            with st.spinner("Thinking... ⏳"):
                try:
                    model_name = get_working_model_name()
                    model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
                    
                    response = model.generate_content(contents)
                    bot_reply = response.text
                    st.markdown(bot_reply)
                    st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
                        
                except Exception as e:
                    st.error(f"Sorry, an error occurred. System Error: {e}")

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
