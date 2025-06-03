import streamlit as st
import os
import base64
from datetime import datetime


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
            margin-bottom: 30px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .sidebar-logo {
            width: 50px;
            height: 50px;
            margin-right: 10px;
        }
        
        /* Yeni sohbet butonu */
        .new-chat-btn {
            background-color: rgba(51, 51, 51, 0.4);
            color: white;
            border: 1px solid rgba(68, 68, 68, 0.3);
            border-radius: 8px;
            padding: 12px;
            text-align: center;
            cursor: pointer;
            margin-bottom: 20px;
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
            padding: 8px 12px;
            margin-bottom: 20px;
            backdrop-filter: blur(5px);
        }
        
        .search-box {
            background-color: transparent;
            border: none;
            padding: 8px 12px;
            width: 100%;
            color: white;
            outline: none;
        }
        
        /* Geçmiş konuşmalar */
        .chat-history-title {
            color: #aaa;
            font-size: 0.9em;
            margin-bottom: 15px;
            text-transform: uppercase;
        }
        
        /* Konuşmaların konteyneri */
        .chat-history-container {
            background-color: rgba(51, 51, 51, 0.3);
            border-radius: 8px;
            padding: 10px;
            backdrop-filter: blur(10px);
        }
        
        /* Konuşma öğesi */
        .chat-item {
            padding: 12px;
            border-radius: 5px;
            margin-bottom: 8px;
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
            margin-right: 10px;
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
            padding: 20px;
            position: relative;
            z-index: 1;
        }
        
        /* Model seçim alanı */
        .model-selector {
            background-color: #eee;
            border-radius: 20px;
            padding: 8px 15px;
            font-size: 0.9em;
            margin: 10px auto 30px auto;
            display: inline-block;
        }
        
        /* Logo ve karşılama mesajı */
        .welcome-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            flex-grow: 1;
            margin-bottom: 100px;
            position: relative;
            z-index: 2;
        }
        
        .cat-logo {
            width: 120px;
            height: auto;
            margin-bottom: 30px;
            object-fit: contain;
            image-rendering: auto;
            display: block;
        }
        
        .welcome-text {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .welcome-text span {
            color: #8a2be2;
        }
        
        .welcome-subtext {
            color: #666;
            font-size: 1.2em;
            text-align: center;
            max-width: 600px;
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
            padding: 5px;
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
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            margin-left: 10px;
        }
        
        .send-button:hover {
            background-color: #7126b5;
        }
        
        /* Web search button */
        .web-search-btn {
            background-color: #4285f4;
            color: white;
            border: none;
            padding: 5px 15px;
            border-radius: 16px;
            font-size: 0.8em;
            cursor: pointer;
            margin: 0 10px;
            display: flex;
            align-items: center;
            white-space: nowrap;
        }
        
        .web-search-btn:hover {
            background-color: #3b78e7;
        }
        
        /* Mesaj konteyneri */
        .messages-container {
            display: flex;
            flex-direction: column;
            padding: 20px;
            overflow-y: auto;
            flex-grow: 1;
            position: relative;
            z-index: 2;
        }
        
        /* Mesaj balonu stilleri */
        .message-container {
            display: flex;
            margin-bottom: 15px;
        }
        
        .user-message {
            background-color: var(--primary-color);
            color: white;
            border-radius: 18px 18px 0 18px;
            padding: 12px 16px;
            max-width: 70%;
            margin-left: auto;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        
        .bot-message {
            background-color: white;
            color: #333;
            border-radius: 18px 18px 18px 0;
            padding: 12px 16px;
            max-width: 70%;
            margin-right: auto;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        
        /* Kategori kartları */
        .category-cards {
            display: flex;
            justify-content: center;
            flex-wrap: wrap;
            gap: 20px;
            margin: 20px auto;
            max-width: 900px;
            position: relative;
            z-index: 2;
        }
        
        .category-card {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            width: 200px;
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
            margin: 10px 0;
            color: #333;
        }
        
        .category-description {
            font-size: 0.9em;
            color: #666;
        }
        
        .info-icon {
            color: #aaa;
            font-size: 1.2em;
            margin-left: 5px;
            vertical-align: middle;
        }
        
        /* Streamlit'in varsayılan öğelerini gizleme */
        .stTextInput {
            position: absolute;
            left: -9999px;
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

        /* Arka plan ayarları */
        .stApp {
            background: radial-gradient(circle at center, rgba(164, 138, 212, 0.3) 0%, rgba(255, 255, 255, 1) 70%) !important;
        }
    </style>
    """, unsafe_allow_html=True)

def get_image_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

# Uygulama başlangıcı
def main():
    local_css()
    
    logo_path = os.path.join("..", "assets", "cat_logo.png")
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
        
        # Yeni konuşma butonu
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
        
        # Geçmiş konuşmalar başlığı
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
    if 'messages' not in st.session_state:
        st.session_state.messages = []
        # Karşılama ekranını göster
        welcome_screen(logo_base64)
    else:
        if len(st.session_state.messages) == 0:
            welcome_screen(logo_base64)
        else:
            # Mesajları göster
            chat_screen()

def welcome_screen(logo_base64=""):
    st.markdown("""
    <div style="text-align:center;margin-top:20px;">
        <div class="model-selector">
            llama 3.2
        </div>
    </div>
    """, unsafe_allow_html=True)
    
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
            <div class="category-title">Sales Strategies <span class="info-icon">ⓘ</span></div>
            <div class="category-description">Try asking: "What are effective ways to increase my property sales in a slow market?"</div>
        </div>
        <div class="category-card">
            <div class="category-title">Negotiation Tactics <span class="info-icon">ⓘ</span></div>
            <div class="category-description">Try asking: "How can I negotiate better terms with difficult clients without damaging relationships?"</div>
        </div>
        <div class="category-card">
            <div class="category-title">Marketing Insights <span class="info-icon">ⓘ</span></div>
            <div class="category-description">Try asking: "What digital marketing strategies work best for luxury properties in 2023?"</div>
        </div>
        <div class="category-card">
            <div class="category-title">General Support <span class="info-icon">ⓘ</span></div>
            <div class="category-description">Try asking: "Can you help me draft a compelling property description for a beachfront villa?"</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Mesaj giriş alanı 
    st.markdown("""
    <div class="message-input-container">
        <button class="input-button">📎</button>
        <input type="text" placeholder="type your prompt here" class="message-input">
        <button class="web-search-btn">🌐 Web Search</button>
        <button class="input-button">🎤</button>
        <button class="send-button">➤</button>
    </div>
    """, unsafe_allow_html=True)
    
    user_input = st.text_input("", key="user_input", label_visibility="collapsed")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": "Merhaba! Size nasıl yardımcı olabilirim?"})
        st.experimental_rerun()

def chat_screen():
    # Model seçici
    st.markdown("""
    <div style="text-align:center;margin-top:20px;">
        <div class="model-selector">
            llama 3.2
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Mesajları göster
    st.markdown('<div class="messages-container">', unsafe_allow_html=True)
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f"""
            <div class="message-container">
                <div class="user-message">
                    {message["content"]}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="message-container">
                <div class="bot-message">
                    {message["content"]}
                </div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Mesaj giriş alanı 
    st.markdown("""
    <div class="message-input-container">
        <button class="input-button">📎</button>
        <input type="text" placeholder="type your prompt here" class="message-input">
        <button class="web-search-btn">🌐 Web Search</button>
        <button class="input-button">🎤</button>
        <button class="send-button">➤</button>
    </div>
    """, unsafe_allow_html=True)
    
    user_input = st.text_input("", key="user_input", label_visibility="collapsed")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": "Bu bir örnek yanıttır. Gerçek uygulamada burada AI modeli yanıt üretecektir."})
        st.experimental_rerun()

if __name__ == "__main__":
    main() 