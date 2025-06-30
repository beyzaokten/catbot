import streamlit as st
import os
import base64
from datetime import datetime
import requests
import json
import threading
import time
import subprocess

# API URL configuration
API_URL = "http://127.0.0.1:8000"

try:
    import sys
    backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
    sys.path.append(backend_path)
    from llm_model import LLMModel
    DIRECT_LLM = True
    print("Using direct LLM connection (no backend API)")
except Exception as e:
    print(f"Direct LLM import failed: {e}")
    DIRECT_LLM = False
    print("Will try to use backend API")

print(f"Using API URL: {API_URL}")

def message_input_component(placeholder="Mesajınızı yazın...", key=None):
    # Create a unique key for this component
    component_key = f"msg_input_{key}" if key else "msg_input"
    
    #CSS for message input
    st.markdown("""
    <style>
        .message-input-container {
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            width: 90%;
            max-width: 800px;
            z-index: 1000;
        }
        
        .message-input-form {
            display: flex;
            align-items: flex-end;
            gap: 10px;
            background: linear-gradient(135deg, rgba(138, 43, 226, 0.3), rgba(168, 168, 168, 0.3));
            backdrop-filter: blur(15px);
            border-radius: 25px;
            padding: 15px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }
        
        /* Override Streamlit textarea styling */
        .stTextArea > div > div > textarea {
            background: linear-gradient(135deg, rgba(138, 43, 226, 0.2), rgba(168, 168, 168, 0.2)) !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            border-radius: 18px !important;
            padding: 12px 16px !important;
            color: white !important;
            font-size: 14px !important;
            backdrop-filter: blur(15px) !important;
            resize: none !important;
            outline: none !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1) !important;
        }
        
        .stTextArea > div > div > textarea::placeholder {
            color: rgba(255, 255, 255, 0.8) !important;
        }
        
        .stTextArea > div > div > textarea:focus {
            border: 1px solid rgba(138, 43, 226, 0.5) !important;
            box-shadow: 0 0 0 3px rgba(138, 43, 226, 0.2) !important;
        }
        
        /* Style the container around textarea */
        .stTextArea > div {
            background: transparent !important;
        }
        
        .stTextArea {
            background: transparent !important;
        }
        
        /* Style the submit button */
        .stFormSubmitButton > button {
            width: 45px !important;
            height: 45px !important;
            border-radius: 50% !important;
            background: linear-gradient(135deg, rgba(138, 43, 226, 0.8), rgba(168, 100, 226, 0.8)) !important;
            border: none !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            cursor: pointer !important;
            backdrop-filter: blur(10px) !important;
            box-shadow: 0 4px 15px rgba(138, 43, 226, 0.3) !important;
            transition: all 0.3s ease !important;
            color: white !important;
            font-size: 18px !important;
            font-weight: bold !important;
        }
        
        .stFormSubmitButton > button:hover {
            background: linear-gradient(135deg, rgba(138, 43, 226, 1), rgba(168, 100, 226, 1)) !important;
            transform: scale(1.05) !important;
            box-shadow: 0 6px 20px rgba(138, 43, 226, 0.4) !important;
        }
        
        .stFormSubmitButton > button:focus {
            box-shadow: 0 0 0 3px rgba(138, 43, 226, 0.3) !important;
        }
        
        .send-icon {
            color: white !important;
            font-size: 18px !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Form container styling
    st.markdown("""
    <style>
        /* Style the form container */
        .stForm {
            background: linear-gradient(135deg, rgba(138, 43, 226, 0.3), rgba(168, 168, 168, 0.3)) !important;
            backdrop-filter: blur(15px) !important;
            border-radius: 25px !important;
            padding: 15px !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15) !important;
            margin-top: 20px !important;
        }
        
        .stForm > div {
            background: transparent !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    with st.form(key=f"chat_form_{component_key}", clear_on_submit=True):
        # Create columns for input layout
        col1, col2 = st.columns([0.9, 0.1])
        
        with col1:
            # Message text area
            message = st.text_area(
                label="Mesaj",
                placeholder=placeholder,
                key=f"textarea_{component_key}",
                height=80,
                label_visibility="collapsed"
            )
        
        with col2:
            # Submit button 
            submitted = st.form_submit_button("➤", help="Mesajı gönder")
        
        # Process message if submitted
        if submitted and message and message.strip():
            if 'messages' not in st.session_state:
                st.session_state.messages = []
            
            st.session_state.messages.append({"role": "user", "content": message.strip()})
            st.session_state.current_screen = "chat"
            # Force immediate rerun to show chat screen
            st.rerun()
    
    return None

def check_api_connection():
    try:
        print("Checking API connection...")
        response = requests.get(f"{API_URL}/models", timeout=2)
        if response.status_code == 200:
            print("API connection successful")
            return True
        else:
            print(f"API connection failed with status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"API connection error: {str(e)}")
        return False

st.set_page_config(
    page_title="CatBot - Kişisel AI Asistanı",
    page_icon="🐱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar
st.markdown("""
<style>
    [data-testid="collapsedControl"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# CSS stilleri
def local_css():
    st.markdown("""
    <style>
        /* Ana tema renkleri */
        :root {
            --primary-color: #8a2be2;
            --secondary-color: #a29bfe;
            --background-color: #f8f9fa;
            --text-color: #2d3436;
            --sidebar-color: #1a1a1a;
            --card-bg-color: #ffffff;
        }
        
        /* Sayfa arka planı */
        section.main {
            background: radial-gradient(circle at center, rgba(164, 138, 212, 0.3) 0%, rgba(255, 255, 255, 1) 70%) !important;
            background-attachment: fixed !important;
        }
        
        /* Genel stil */
        .main {
            color: var(--text-color);
            padding: 0 !important;
            position: relative;
        }
        
        /* Sidebar stili */
        .css-1d391kg, [data-testid="stSidebar"], .stSidebar {
            background: radial-gradient(circle at 80% 70%, rgba(138, 43, 226, 0.4) 0%, rgba(26, 26, 26, 1) 70%) !important;
            background-attachment: fixed !important;
            color: white !important;
        }
        
        /* Sidebar başlık */
        .sidebar-title {
            color: white;
            font-size: 1.2em;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .sidebar-logo {
            width: 40px;
            height: 40px;
            margin-right: 10px;
        }
        
        /* Yeni sohbet butonu */
        .new-chat-btn {
            background-color: rgba(51, 51, 51, 0.4);
            color: white;
            border: 1px solid rgba(68, 68, 68, 0.3);
            border-radius: 8px;
            padding: 8px;
            text-align: center;
            cursor: pointer;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            backdrop-filter: blur(5px);
        }
        
        /* Arama kutusu */
        .search-box-container {
            display: flex;
            align-items: center;
            background-color: rgba(51, 51, 51, 0.4);
            border-radius: 8px;
            padding: 6px 10px;
            margin-bottom: 15px;
            backdrop-filter: blur(5px);
        }
        
        .search-box {
            background-color: transparent;
            border: none;
            padding: 6px 10px;
            width: 100%;
            color: white;
            outline: none;
        }
        
        /* Geçmiş konuşmalar */
        .chat-history-title {
            color: #aaa;
            font-size: 0.9em;
            margin-bottom: 10px;
            text-transform: uppercase;
        }
        
        /* Konuşmaların konteyneri */
        .chat-history-container {
            background-color: rgba(51, 51, 51, 0.3);
            border-radius: 8px;
            padding: 8px;
            backdrop-filter: blur(10px);
        }
        
        /* Konuşma öğesi */
        .chat-item {
            padding: 8px;
            border-radius: 5px;
            margin-bottom: 6px;
            cursor: pointer;
            color: #ddd;
            display: flex;
            align-items: center;
            justify-content: space-between;
            background-color: rgba(51, 51, 51, 0.5);
        }
        
        .chat-item:hover {
            background-color: rgba(68, 68, 68, 0.7);
        }
        
        .chat-icon {
            margin-right: 8px;
            color: #aaa;
        }
        
        .chat-options {
            color: #aaa;
            font-size: 16px;
        }
        
        /* Ana içerik */
        .main-content {
            display: flex;
            flex-direction: column;
            height: 100vh;
            padding: 10px;
            position: relative;
            z-index: 1;
        }
        
        /* Model seçim alanı */
        .model-selector {
            background-color: #eee;
            border-radius: 20px;
            padding: 6px 12px;
            font-size: 0.9em;
            margin: 5px auto 15px auto;
            display: inline-block;
        }
        
        /* Logo ve karşılama mesajı */
        .welcome-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
            position: relative;
            z-index: 2;
        }
        
        .cat-logo {
            width: 80px;
            height: auto;
            margin-bottom: 15px;
            object-fit: contain;
            image-rendering: auto;
            display: block;
        }
        
        .welcome-text {
            font-size: 1.6em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .welcome-text span {
            color: #8a2be2;
        }
        
        .welcome-subtext {
            color: #666;
            font-size: 0.9em;
            text-align: center;
            max-width: 600px;
            margin-bottom: 15px;
        }
        
        /* Mesaj giriş alanı */
        .message-input-container {
            position: fixed;
            bottom: 20px;
            left: calc(50% + 125px); /* Sidebar genişliğinin yarısı kadar sağa kaydır */
            transform: translateX(-50%);
            width: 70%;
            max-width: 700px;
            background-color: #e0e0e0;
            border-radius: 24px;
            padding: 10px 20px;
            display: flex;
            align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 10;
        }
        
        /* Hide the hidden widget columns */
        [data-testid="column"]:has(button:contains("Send")) {
            display: none !important;
            width: 0 !important;
            min-width: 0 !important;
            position: absolute !important;
            left: -9999px !important;
        }
        
        /* Hide columns with very small widths */
        [data-testid="column"][style*="width: 0.001%"] {
            display: none !important;
            position: absolute !important;
            left: -9999px !important;
        }
        
        /* Hide hidden inputs and buttons */
        input[aria-label="Hidden"], 
        button[data-testid*="hidden_btn_"],
        button:contains("Send") {
            display: none !important;
            visibility: hidden !important;
            position: absolute !important;
            left: -9999px !important;
            opacity: 0 !important;
            height: 0 !important;
            width: 0 !important;
        }
        
        /* Force hide all elements in the hidden column */
        [data-testid="column"][style*="width: 0.001%"] {
            display: none !important;
            visibility: hidden !important;
            position: absolute !important;
            left: -10000px !important;
            opacity: 0 !important;
            height: 0 !important;
            width: 0 !important;
            overflow: hidden !important;
        }
        
        [data-testid="column"][style*="width: 0.001%"] * {
            display: none !important;
        }
        
        .message-input {
            flex-grow: 1;
            border: none;
            background-color: transparent;
            padding: 12px;
            font-size: 1em;
            outline: none;
            text-align: center;
        }
        
        .input-button {
            background: none;
            border: none;
            color: #666;
            font-size: 1.2em;
            cursor: pointer;
            margin: 0 5px;
            padding: 3px;
            min-width: 24px;
        }
        
        .input-button:hover {
            color: var(--primary-color);
        }
        
        .send-button {
            background-color: var(--primary-color);
            color: white;
            border: none;
            border-radius: 50%;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            margin-left: 8px;
        }
        
        .send-button:hover {
            background-color: #7126b5;
        }
        
        /* Web search button */
        .web-search-btn {
            background-color: rgba(138, 43, 226, 0.1);
            color: #8a2be2;
            border: 1px solid rgba(138, 43, 226, 0.2);
            padding: 4px 10px;
            border-radius: 16px;
            font-size: 0.8em;
            cursor: pointer;
            margin: 0 8px;
            display: flex;
            align-items: center;
            white-space: nowrap;
        }
        
        /* Mesaj konteyneri */
        .messages-container {
            display: flex;
            flex-direction: column;
            padding: 15px;
            overflow-y: auto;
            flex-grow: 1;
            position: relative;
            z-index: 2;
            margin-bottom: 80px;
        }
        
        /* Mesaj balonu stilleri */
        .message-container {
            display: flex;
            margin-bottom: 12px;
        }
        
        .user-message {
            background-color: var(--primary-color);
            color: white;
            border-radius: 18px 18px 0 18px;
            padding: 10px 14px;
            max-width: 70%;
            margin-left: auto;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        
        .bot-message {
            background-color: white;
            color: #333;
            border-radius: 18px 18px 18px 0;
            padding: 10px 14px;
            max-width: 70%;
            margin-right: auto;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        
        /* Kategori kartları */
        .category-cards {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 15px;
            margin: 0 auto;
            max-width: 900px;
            position: relative;
            z-index: 2;
        }
        
        .category-card {
            background-color: white;
            border-radius: 10px;
            padding: 12px;
            width: 180px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            cursor: pointer;
            transition: transform 0.2s;
            text-align: center;
        }
        
        .category-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .category-title {
            font-weight: bold;
            margin: 8px 0;
            color: #333;
            font-size: 0.95em;
        }
        
        .category-description {
            font-size: 0.8em;
            color: #666;
        }
        
        .info-icon {
            color: #aaa;
            font-size: 1.2em;
            margin-left: 5px;
            vertical-align: middle;
        }

        /* Düşünme animasyonu */
        .thinking-dots {
            display: inline-block;
        }
        
        .thinking-dots span {
            animation: thinking 1.4s infinite;
            animation-fill-mode: both;
        }
        
        .thinking-dots span:nth-child(2) {
            animation-delay: 0.2s;
        }
        
        .thinking-dots span:nth-child(3) {
            animation-delay: 0.4s;
        }
        
        @keyframes thinking {
            0%, 80%, 100% { opacity: 0; }
            40% { opacity: 1; }
        }
        
        /* Streamlit'in varsayılan öğelerini gizleme */
        .stTextInput {
            position: absolute;
            left: -9999px;
        }
        
        /* Gizli butonları tamamen gizle */
        .hidden-element {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            width: 0 !important;
            position: absolute !important;
            left: -9999px !important;
            top: -9999px !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
        
        /* Streamlit Değişkenleri Sıfırlama */
        div[data-testid="stDecoration"] {
            display: none;
        }
        
        footer {
            display: none;
        }

        header {
            display: none;
        }
    </style>
    """, unsafe_allow_html=True)

def get_image_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# API fonksiyonları
def get_models():
    try:
        response = requests.get(f"{API_URL}/models")
        if response.status_code == 200:
            return response.json()["models"]
        return ["llama3"]
    except:
        return ["llama3"]

def send_message(message, history=None, model_name=None):
    
    # Global LLM instance
    if 'llm_instance' not in st.session_state and DIRECT_LLM:
        try:
            print("Initializing direct LLM connection...")
            st.session_state.llm_instance = LLMModel(model_name=model_name or "llama3")
            print("Direct LLM initialized successfully")
        except Exception as e:
            print(f"Failed to initialize direct LLM: {e}")
            st.session_state.llm_instance = None
    
    if DIRECT_LLM and st.session_state.get('llm_instance'):
        try:
            print(f"Using direct LLM for message: {message}")
            response = st.session_state.llm_instance.get_response(message)
            print(f"Direct LLM response received: {response[:100]}...")
            return response
        except Exception as e:
            print(f"Direct LLM failed: {e}")
            # Fall back to API
    
    if not check_api_connection():
        print("API connection failed")
        if DIRECT_LLM:
            return "Hem direkt LLM hem de Backend API bağlantısı başarısız. Lütfen Ollama'nın çalıştığından emin olun."
        else:
            return "Backend API'ye bağlanılamadı. Lütfen API'nin çalıştığından emin olun."
        
    try:
        print(f"Sending message to API: {message}")
        data = {
            "message": message,
            "history": history,
            "model_name": model_name
        }
        
        print(f"Using model: {model_name}")
        response = requests.post(f"{API_URL}/chat", json=data)
        
        print(f"API response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()["response"]
            print(f"API response content: {result[:100]}...") 
            return result
        else:
            error_msg = f"API'den yanıt alınamadı. Hata kodu: {response.status_code}"
            print(error_msg)
            if response.text:
                print(f"Response text: {response.text}")
            return error_msg
    except Exception as e:
        error_msg = f"Hata oluştu: {str(e)}"
        print(f"Exception in send_message: {error_msg}")
        return error_msg

def clear_chat_history():
    try:
        requests.post(f"{API_URL}/clear_history")
    except:
        pass



def process_message(user_input):
    """Process user message and get response from the model"""
    if not user_input:
        return
        
        print(f"Processing message: {user_input}")
    
    try:
        response = send_message(
            message=user_input,
            model_name=st.session_state.get('current_model', 'llama3')
        )
        
        # Add assistant response to chat
        st.session_state.messages.append({"role": "assistant", "content": response})
        print(f"Response added: {response}")
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"Error in process_message: {error_msg}")
        
        # Add error message
        st.session_state.messages.append({"role": "assistant", "content": f"❌ {error_msg}"})

def main():
    local_css()
    
    logo_path = os.path.join("..", "assets", "cat_logo.png")  
    
    if not os.path.exists(logo_path):
        logo_path = os.path.join("assets", "cat_logo.png")  
        
    if not os.path.exists(logo_path) and "CATBOT_ROOT" in os.environ:
        logo_path = os.path.join(os.environ["CATBOT_ROOT"], "assets", "cat_logo.png")
    
    logo_base64 = ""
    
    if os.path.exists(logo_path):
        try:
            logo_base64 = get_image_base64(logo_path)
        except Exception as e:
            st.error(f"Logo yüklenirken hata oluştu: {e}")
    
    st.markdown("""
        <style>
            body {
                background: radial-gradient(circle at center, rgba(164, 138, 212, 0.3) 0%, rgba(255, 255, 255, 1) 70%);
            }
            .stApp {
                background: radial-gradient(circle at center, rgba(164, 138, 212, 0.3) 0%, rgba(255, 255, 255, 1) 70%) !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    api_status = check_api_connection()
    if not api_status and not DIRECT_LLM:
        st.warning("Backend API'ye bağlanılamadı. Lütfen API'nin çalıştığından emin olun.")
    
    # Session state initialization
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'current_model' not in st.session_state:
        st.session_state.current_model = "llama3"
    
    if 'model_options' not in st.session_state:
        st.session_state.model_options = ["llama3"]
        
        def update_models():
            time.sleep(2)  # Wait for API to start
            models = get_models()
            if models:
                st.session_state.model_options = models
                
        threading.Thread(target=update_models).start()
    
    # Initialize thinking state
    if 'thinking' not in st.session_state:
        st.session_state.thinking = False
    
    # Initialize user input
    if 'user_input' not in st.session_state:
        st.session_state.user_input = ""
    
    # Sidebar
    with st.sidebar:
        if logo_base64:
            st.markdown(f"""
            <div class="sidebar-title">
                <img src="data:image/png;base64,{logo_base64}" class="sidebar-logo">
                <span>CatBot</span>
                <span>⋯</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="sidebar-title">
                <span style="font-size: 24px; margin-right: 10px;">🐱</span>
                <span>CatBot</span>
                <span>⋯</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="new-chat-btn">
            <span>Begin a New Chat</span>
            <span>+</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Arama kutusu
        st.markdown("""
        <div class="search-box-container">
            <span style="color:#aaa;margin-right:5px;">🔍</span>
            <input type="text" placeholder="Search" class="search-box">
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="chat-history-title">Recent Chats</div>', unsafe_allow_html=True)
        
        # Geçmiş konuşmalar konteynerı
        st.markdown("""
        <div class="chat-history-container">
            <div class="chat-item">
                <div>
                    <span class="chat-icon">💬</span>
                    <span>How can I increase the number...</span>
                </div>
                <span class="chat-options">⋯</span>
            </div>
            <div class="chat-item">
                <div>
                    <span class="chat-icon">💬</span>
                    <span>What's the best approach to...</span>
                </div>
                <span class="chat-options">⋯</span>
            </div>
            <div class="chat-item">
                <div>
                    <span class="chat-icon">💬</span>
                    <span>What's the best approach to...</span>
                </div>
                <span class="chat-options">⋯</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Ana içerik
    if len(st.session_state.messages) == 0:
        # Karşılama ekranını göster
        welcome_screen(logo_base64)
    else:
        # Mesajları göster
        chat_screen()

def welcome_screen(logo_base64=""):
    # Model seçimi
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        st.selectbox("Model", st.session_state.model_options, key="model_selector", 
                     index=st.session_state.model_options.index(st.session_state.current_model) 
                     if st.session_state.current_model in st.session_state.model_options else 0,
                     label_visibility="collapsed")
        
    if st.session_state.current_model != st.session_state.model_selector:
        st.session_state.current_model = st.session_state.model_selector
    
    if logo_base64:
        st.markdown(f"""
        <div class="welcome-container" style="margin-left: auto; margin-right: auto; max-width: 900px;">
            <img src="data:image/png;base64,{logo_base64}" class="cat-logo">
            <div class="welcome-text">
                <span style="color: #000;">How can we</span> 
                <span>assist</span> 
                <span style="color: #000;">you today?</span>
            </div>
            <div class="welcome-subtext">
                Hi there! I'm your friendly AI companion ready to purr-vide some paw-some help! 
                Whether you need insights on sales strategies, negotiation advice, or just a friendly chat, 
                I'm here to make your day a little brighter. What can I help you with today?
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="welcome-container" style="margin-left: auto; margin-right: auto; max-width: 900px;">
            <div style="font-size: 60px;">🐱</div>
            <div class="welcome-text">
                <span style="color: #000;">How can we</span> 
                <span>assist</span> 
                <span style="color: #000;">you today?</span>
            </div>
            <div class="welcome-subtext">
                Hi there! I'm your friendly AI companion ready to purr-vide some paw-some help! 
                Whether you need insights on sales strategies, negotiation advice, or just a friendly chat, 
                I'm here to make your day a little brighter. What can I help you with today?
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Kategori kartları
    st.markdown("""
    <div class="category-cards">

    <div class="category-card">
        <div class="category-title">📈 Purr-fect Sales Strategies <span class="info-icon">ⓘ</span></div>
        <div class="category-description">Try asking: "How can I boost sales during slow seasons?" or "What kind of offers attract serious buyers?"</div>
    </div>

    <div class="category-card">
        <div class="category-title">🧠 Smart Negotiation Tactics <span class="info-icon">ⓘ</span></div>
        <div class="category-description">Try asking: "How can I stay firm on price without scaring off buyers?" or "Tips for winning a bidding war like a pro?"</div>
    </div>

    <div class="category-card">
        <div class="category-title">📣 Marketing with Cat-titude <span class="info-icon">ⓘ</span></div>
        <div class="category-description">Try asking: "What Instagram strategies work best for real estate?" or "How do I write a scroll-stopping ad headline?"</div>
    </div>

    <div class="category-card">
        <div class="category-title">🛠️ General Support & Advice <span class="info-icon">ⓘ</span></div>
        <div class="category-description">Try asking: "Can you help me write a snappy listing for a studio apartment?" or "How do I follow up with a cold lead?"</div>
    </div>

    </div>
    """, unsafe_allow_html=True)
    
    user_message = message_input_component(placeholder="type your prompt here", key="welcome")
    if user_message:
        process_message(user_message)

def chat_screen():
    """Display chat messages and input area"""
    # Initialize messages if not exists
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Model selection at the top - no extra spacing
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        st.selectbox(
            "Model",
            st.session_state.model_options,
            key="model_selector",
            index=st.session_state.model_options.index(st.session_state.current_model)
            if st.session_state.current_model in st.session_state.model_options else 0,
            label_visibility="collapsed"
        )
    
    if st.session_state.current_model != st.session_state.model_selector:
        st.session_state.current_model = st.session_state.model_selector
    
    try:
        with open("assets/cat_logo.png", "rb") as f:
            cat_logo_bytes = f.read()
        cat_logo_base64 = base64.b64encode(cat_logo_bytes).decode()
    except:
        cat_logo_base64 = None
    
    st.markdown("""
    <style>
        /* Remove any extra spacing from Streamlit elements */
        .stSelectbox {
            margin-bottom: 10px !important;
        }
        
        /* Chat messages container */
        .main .block-container {
            padding-top: 1rem !important;
            padding-bottom: 120px !important;
        }
        
        .thinking-animation {
            display: inline-block;
            font-size: 14px;
            color: #ccc;
        }
        
        .thinking-dots {
            display: inline-block;
            width: 20px;
            text-align: left;
        }
        
        .thinking-dots::after {
            content: '.';
            animation: dots 2s infinite;
        }
        
        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60%, 100% { content: '...'; }
        }
    </style>
    """, unsafe_allow_html=True)
    
    for i, message in enumerate(st.session_state.messages):
        if message["role"] == "assistant":
            # Assistant message - left side with logo
            content_length = len(message["content"])
            if content_length < 50:
                width_style = "max-width: 300px;"
            elif content_length < 100:
                width_style = "max-width: 500px;"
            else:
                width_style = "max-width: 70%;"
            
            logo_html = ""
            if cat_logo_base64:
                logo_html = f'<img src="data:image/png;base64,{cat_logo_base64}" style="width: 40px; height: 40px; border-radius: 50%; margin-right: 12px; vertical-align: top;">'
            else:
                logo_html = '<span style="font-size: 40px; margin-right: 12px; vertical-align: top;">🐱</span>'
            
            st.markdown(f"""
            <div style="
                display: flex; 
                align-items: flex-start; 
                margin-bottom: 15px;
                padding-left: 10px;
            ">
                {logo_html}
                <div style="
                    background: rgba(64, 64, 64, 0.5);
                    backdrop-filter: blur(10px);
                    border-radius: 18px 18px 18px 4px;
                    padding: 12px 16px;
                    color: white;
                    font-size: 14px;
                    line-height: 1.4;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                    {width_style}
                ">
                    {message["content"]}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # User message - right side
            st.markdown(f"""
            <div style="
                display: flex;
                justify-content: flex-end;
                margin-bottom: 15px;
                padding-right: 10px;
            ">
                <div style="
                    background: rgba(138, 43, 226, 0.4);
                    backdrop-filter: blur(10px);
                    border-radius: 18px 18px 4px 18px;
                    padding: 12px 16px;
                    color: white;
                    font-size: 14px;
                    line-height: 1.4;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                    max-width: 70%;
                    word-wrap: break-word;
                    text-align: left;
                ">
                    {message["content"]}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Check if we need to process the last user message
    if (st.session_state.messages and 
        st.session_state.messages[-1]["role"] == "user"):
        # Count user vs assistant messages to see if we need a response
        user_count = len([msg for msg in st.session_state.messages if msg["role"] == "user"])
        assistant_count = len([msg for msg in st.session_state.messages if msg["role"] == "assistant"])
        
        # If user has more messages than assistant responses, we need to process
        if user_count > assistant_count:
            # Show thinking animation
            st.markdown(f"""
            <div style="
                display: flex;
                align-items: flex-start;
                margin-bottom: 15px;
                padding-left: 10px;
            ">
                {'<img src="data:image/png;base64,' + cat_logo_base64 + '" style="width: 40px; height: 40px; border-radius: 50%; margin-right: 12px; vertical-align: top;">' if cat_logo_base64 else '<span style="font-size: 40px; margin-right: 12px; vertical-align: top;">🐱</span>'}
                <div style="
                    background: rgba(64, 64, 64, 0.5);
                    backdrop-filter: blur(10px);
                    border-radius: 18px 18px 18px 4px;
                    padding: 12px 16px;
                    color: white;
                    font-size: 14px;
                    line-height: 1.4;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                    max-width: 300px;
                ">
                    <span class="thinking-animation">Thinking<span class="thinking-dots"></span></span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            last_user_message = st.session_state.messages[-1]["content"]
            process_message(last_user_message)
            st.rerun()
    
    # Message input area at the bottom
    user_message = message_input_component(
        placeholder="Mesajınızı yazın...",
        key="chat"
    )
    
    # Process message if entered
    if user_message:
        process_message(user_message)

if __name__ == "__main__":
    main() 