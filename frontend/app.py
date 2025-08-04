import streamlit as st
import os
import base64
from datetime import datetime
import requests
import json
import threading
import time
import subprocess
import html
from typing import Optional, List

class APIService:    
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self._connection_verified = False
    
    def verify_connection(self, max_retries: int = 3) -> bool:
        for attempt in range(max_retries):
            try:
                timeout = 3 + (attempt * 2)
                response = requests.get(f"{self.base_url}/health", timeout=timeout)
                if response.status_code == 200:
                    self._connection_verified = True
                    return True
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(1)
                continue
        return False
    
    def is_connected(self) -> bool:
        """Check if connection is verified"""
        return self._connection_verified or self.verify_connection(max_retries=1)
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        return requests.get(f"{self.base_url}{endpoint}", **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        return requests.post(f"{self.base_url}{endpoint}", **kwargs)
    
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        return requests.delete(f"{self.base_url}{endpoint}", **kwargs)
    
    def put(self, endpoint: str, **kwargs) -> requests.Response:
        return requests.put(f"{self.base_url}{endpoint}", **kwargs)

api_service = APIService()

try:
    import sys
    backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
    sys.path.append(backend_path)
    from llm_model import LLMModel
    DIRECT_LLM = True
except Exception as e:
    DIRECT_LLM = False

def upload_file_to_backend(uploaded_file, conversation_id: Optional[int] = None):
    """Upload file to backend API"""
    try:
        files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        data = {}
        
        if conversation_id is not None:
            data['conversation_id'] = conversation_id
        
        response = api_service.post("/upload", files=files, data=data, timeout=30)
        
        if response.status_code == 200:
            return response.json()
        else:
            error_text = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get('detail', error_text)
            except:
                error_detail = error_text
            
            return {
                "success": False,
                "message": f"HTTP {response.status_code}: {error_detail}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection error: {str(e)}"
        }

def get_conversation_files(conversation_id: int):
    """Get files for a conversation"""
    try:
        response = api_service.get(f"/conversations/{conversation_id}/files", timeout=10)
        if response.status_code == 200:
            return response.json().get("files", [])
        return []
    except Exception:
        return []

def delete_file_from_backend(file_id: int):
    try:
        response = api_service.delete(f"/files/{file_id}", timeout=10)
        return response.status_code == 200
    except Exception:
        return False

def get_supported_file_types():
    try:
        response = api_service.get("/supported-file-types", timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("supported_types", []), data.get("max_file_size_mb", 10)
        return [], 10
    except Exception:
        return [], 10

def process_file_with_rag(file_id: int):
    try:
        response = api_service.post(f"/files/{file_id}/process", timeout=30)
        if response.status_code == 200:
            return response.json()
        return {"status": "error", "message": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def get_rag_stats():
    try:
        response = api_service.get("/rag/stats", timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def message_input_component(placeholder="Mesajınızı yazın...", key=None):
    component_key = f"msg_input_{key}" if key else "msg_input"
    
    attach_logo_base64 = ""
    try:
        attach_logo_path = os.path.join("..", "assets", "attach_logo.png")
        if not os.path.exists(attach_logo_path):
            attach_logo_path = os.path.join("assets", "attach_logo.png")
        if os.path.exists(attach_logo_path):
            with open(attach_logo_path, "rb") as f:
                attach_logo_base64 = base64.b64encode(f.read()).decode()
    except Exception as e:
        pass
    
    css_content = f"""
    <style>
        .stFileUploader {{
            width: 45px !important;
            height: 45px !important;
            min-width: 45px !important;
            max-width: 45px !important;
            min-height: 45px !important;
            max-height: 45px !important;
            border-radius: 50% !important;
            position: relative !important;
            overflow: hidden !important;
            background-image: url('data:image/png;base64,{attach_logo_base64}') !important;
            background-size: cover !important;
            background-repeat: no-repeat !important;
            background-position: center !important;
            background-color: transparent !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
            cursor: pointer !important;
            transition: all 0.3s ease !important;
            z-index: 1 !important;
        }}
        
        .stFileUploader::before {{
            content: '' !important;
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            background-image: url('data:image/png;base64,{attach_logo_base64}') !important;
            background-size: cover !important;
            background-repeat: no-repeat !important;
            background-position: center !important;
            border-radius: 50% !important;
            z-index: 2 !important;
            pointer-events: none !important;
        }}
        
        .stFileUploader:hover {{
            transform: scale(1.1) !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3) !important;
            filter: brightness(1.1) !important;
        }}
        
        .stFileUploader > div,
        .stFileUploader > div > div,
        .stFileUploader > div > div > div,
        .stFileUploader > div > div > div > div,
        .stFileUploader [data-testid="stFileUploadDropzone"],
        .stFileUploader div,
        .stFileUploader span,
        .stFileUploader p,
        .stFileUploader button,
        .stFileUploader label {{
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
            position: absolute !important;
            left: -9999px !important;
            opacity: 0 !important;
        }}
        
        .stFileUploader input[type="file"] {{
            width: 45px !important;
            height: 45px !important;
            opacity: 0 !important;
            cursor: pointer !important;
            border-radius: 50% !important;
            position: absolute !important;
            top: 0 !important;
            left: 0 !important;
            right: 0 !important;
            bottom: 0 !important;
            z-index: 3 !important;
            margin: 0 !important;
            padding: 0 !important;
            background: transparent !important;
            border: none !important;
        }}
        
        .stForm .stHorizontalBlock > div:first-child {{
            width: 55px !important;
            min-width: 55px !important;
            max-width: 55px !important;
            flex: 0 0 55px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }}
        
        .message-input-container {{
            position: fixed;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            width: 90%;
            max-width: 800px;
            z-index: 1000;
        }}
        
        .message-input-form {{
            display: flex;
            align-items: flex-end;
            gap: 10px;
            background: linear-gradient(135deg, rgba(138, 43, 226, 0.3), rgba(168, 168, 168, 0.3));
            backdrop-filter: blur(15px);
            border-radius: 25px;
            padding: 15px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
        }}
        
        .stTextArea > div > div > textarea {{
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
        }}
        
        .stTextArea > div > div > textarea::placeholder {{
            color: rgba(255, 255, 255, 0.8) !important;
        }}
        
        .stTextArea > div > div > textarea:focus {{
            border: 1px solid rgba(138, 43, 226, 0.5) !important;
            box-shadow: 0 0 0 3px rgba(138, 43, 226, 0.2) !important;
        }}
        
        .stTextArea > div {{
            background: transparent !important;
        }}
        
        .stTextArea {{
            background: transparent !important;
        }}
        
        .stFormSubmitButton > button {{
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
        }}
        
        .stFormSubmitButton > button:hover {{
            background: linear-gradient(135deg, rgba(138, 43, 226, 1), rgba(168, 100, 226, 1)) !important;
            transform: scale(1.05) !important;
            box-shadow: 0 6px 20px rgba(138, 43, 226, 0.4) !important;
        }}
        
        .stFormSubmitButton > button:focus {{
            box-shadow: 0 0 0 3px rgba(138, 43, 226, 0.3) !important;
        }}
        
        .uploaded-files-compact {{
            background: rgba(138, 43, 226, 0.1);
            border-radius: 8px;
            padding: 8px 12px;
            margin-bottom: 10px;
            border: 1px solid rgba(138, 43, 226, 0.3);
        }}
        
        .file-item-compact {{
            display: flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.1);
            padding: 6px 10px;
            margin: 2px 0;
            border-radius: 6px;
            font-size: 11px;
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .file-icon {{
            margin-right: 6px;
            font-size: 12px;
        }}
        
        .file-name {{
            flex: 1;
            margin-right: 8px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-weight: 500;
        }}
        
        .file-size {{
            color: rgba(255, 255, 255, 0.6);
            font-size: 10px;
            margin-left: auto;
        }}
        
        .send-icon {{
            color: white !important;
            font-size: 18px !important;
        }}
        
        .stButton > button[title="Tüm dosyaları temizle"] {{
            background: rgba(231, 76, 60, 0.7) !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 4px 8px !important;
            font-size: 11px !important;
            color: white !important;
            transition: all 0.3s ease !important;
        }}
        
        .stButton > button[title="Tüm dosyaları temizle"]:hover {{
            background: rgba(231, 76, 60, 0.9) !important;
        }}
    </style>
    
    <script>
        function forceFileUploaderStyle() {{
            const uploaders = document.querySelectorAll('.stFileUploader');
            uploaders.forEach(uploader => {{
                uploader.style.cssText = `
                    width: 45px !important;
                    height: 45px !important;
                    min-width: 45px !important;
                    max-width: 45px !important;
                    min-height: 45px !important;
                    max-height: 45px !important;
                    border-radius: 50% !important;
                    overflow: hidden !important;
                    background-image: url('data:image/png;base64,{attach_logo_base64}') !important;
                    background-size: cover !important;
                    background-repeat: no-repeat !important;
                    background-position: center !important;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
                    cursor: pointer !important;
                    transition: all 0.3s ease !important;
                `;
                
                const allElements = uploader.querySelectorAll('div, span, p, button, label');
                allElements.forEach(el => {{
                    el.style.display = 'none';
                    el.style.visibility = 'hidden';
                    el.style.position = 'absolute';
                    el.style.left = '-9999px';
                    el.style.opacity = '0';
                    el.style.width = '0';
                    el.style.height = '0';
                }});
                
                const fileInput = uploader.querySelector('input[type="file"]');
                if (fileInput) {{
                    fileInput.style.width = '45px';
                    fileInput.style.height = '45px';
                    fileInput.style.opacity = '0';
                    fileInput.style.cursor = 'pointer';
                    fileInput.style.position = 'absolute';
                    fileInput.style.top = '0';
                    fileInput.style.left = '0';
                    fileInput.style.right = '0';
                    fileInput.style.bottom = '0';
                    fileInput.style.zIndex = '3';
                    fileInput.style.pointerEvents = 'auto';
                    fileInput.style.margin = '0';
                    fileInput.style.padding = '0';
                    fileInput.style.background = 'transparent';
                    fileInput.style.border = 'none';
                }}
            }});
        }}
        
        // Apply styles immediately and on any changes
        forceFileUploaderStyle();
        setInterval(forceFileUploaderStyle, 100);
        
        // Also apply on DOM changes
        const observer = new MutationObserver(forceFileUploaderStyle);
        observer.observe(document.body, {{ childList: true, subtree: true }});
    </script>
    """
    
    st.markdown(css_content, unsafe_allow_html=True)
    
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
    
    # Initialize file upload state
    if f'uploaded_files_{component_key}' not in st.session_state:
        st.session_state[f'uploaded_files_{component_key}'] = []
    
    # Get current conversation ID
    current_conversation_id = getattr(st.session_state, 'current_conversation_id', None)
    
    # Show upload success messages
    if f'upload_success_{component_key}' in st.session_state:
        st.success(st.session_state[f'upload_success_{component_key}'])
        del st.session_state[f'upload_success_{component_key}']
    
    if f'rag_success_{component_key}' in st.session_state:
        st.success(st.session_state[f'rag_success_{component_key}'])
        del st.session_state[f'rag_success_{component_key}']
    
    if f'rag_error_{component_key}' in st.session_state:
        st.warning(st.session_state[f'rag_error_{component_key}'])
        del st.session_state[f'rag_error_{component_key}']

    if st.session_state[f'uploaded_files_{component_key}']:
        st.markdown('''
        <div class="uploaded-files-compact">
            <div style="color: rgba(255,255,255,0.9); font-size: 12px; margin-bottom: 8px;">
                📎 Ekli Dosyalar:
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        for idx, file_info in enumerate(st.session_state[f'uploaded_files_{component_key}']):
            file_size_str = format_file_size(file_info['size'])
            
            col1, col2 = st.columns([0.9, 0.1])
            with col1:
                st.markdown(
                    f'<div class="file-item-compact">'
                    f'<span class="file-icon">📄</span>'
                    f'<span class="file-name" title="{file_info["name"]}">{file_info["name"]}</span>'
                    f'<span class="file-size">({file_size_str})</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
            with col2:
                if st.button("❌", key=f"remove_file_{component_key}_{idx}", help=f"Remove {file_info['name']}"):
                    delete_file_from_backend(file_info['id'])
                    st.session_state[f'uploaded_files_{component_key}'].pop(idx)
                    processed_files_key = f'processed_files_{component_key}'
                    if processed_files_key in st.session_state:
                        file_key = f"{file_info['name']}_{file_info['size']}"
                        st.session_state[processed_files_key].discard(file_key)
                    st.rerun()

    with st.form(key=f"chat_form_{component_key}", clear_on_submit=True):
        col1, col2, col3 = st.columns([0.1, 0.8, 0.1])
        
        with col1:
            uploaded_file = st.file_uploader(
                "",
                type=['pdf', 'txt', 'md', 'docx', 'doc', 'html', 'rtf', 'csv', 'json', 'xml'],
                help="Dosya ekle",
                key=f"file_uploader_{component_key}",
                label_visibility="hidden"
            )
        
        with col2:
            message = st.text_area(
                label="Mesaj",
                placeholder=placeholder,
                key=f"textarea_{component_key}",
                height=80,
                label_visibility="collapsed"
            )
        
        with col3:
            submitted = st.form_submit_button("➤", help="Mesajı gönder")
        
        if uploaded_file is not None:
            # Check if this file was already uploaded
            file_key = f"{uploaded_file.name}_{uploaded_file.size}"
            processed_files_key = f'processed_files_{component_key}'
            
            if processed_files_key not in st.session_state:
                st.session_state[processed_files_key] = set()
            
            if file_key not in st.session_state[processed_files_key]:
                # Mark as being processed
                st.session_state[processed_files_key].add(file_key)
                
                with st.spinner("Dosya yükleniyor..."):
                    try:
                        upload_result = upload_file_to_backend(uploaded_file, current_conversation_id)
                        
                        if upload_result.get("success"):
                            file_info = upload_result.get("file", {})
                            file_id = file_info.get('id')
                            st.session_state[f'uploaded_files_{component_key}'].append({
                                'id': file_id,
                                'name': file_info.get('filename'),
                                'size': file_info.get('file_size'),
                                'type': file_info.get('mime_type')
                            })
                            
                            # Store success message in session state
                            st.session_state[f'upload_success_{component_key}'] = f"✅ {uploaded_file.name} başarıyla yüklendi!"
                            
                            # Process file through RAG pipeline
                            with st.spinner("📚 Dosya AI sistemi için işleniyor..."):
                                rag_result = process_file_with_rag(file_id)
                                if rag_result.get("status") == "success":
                                    chunks_added = rag_result.get("chunks_added", 0)
                                    st.session_state[f'rag_success_{component_key}'] = f"🧠 Dosya AI sistemi tarafından işlendi! ({chunks_added} parça oluşturuldu)"
                                else:
                                    st.session_state[f'rag_error_{component_key}'] = f"⚠️ AI işleme hatası: {rag_result.get('message', 'Bilinmeyen hata')}"
                        else:
                            error_msg = upload_result.get('message', 'Bilinmeyen hata')
                            st.error(f"❌ Yükleme hatası: {error_msg}")
                            st.session_state[processed_files_key].discard(file_key)
                    except Exception as e:
                        st.error(f"❌ Yükleme hatası: {str(e)}")
                        st.session_state[processed_files_key].discard(file_key)
        
        # Process message if submitted
        if submitted and message and message.strip():
            if 'messages' not in st.session_state:
                st.session_state.messages = []
            
            clean_user_message = message.strip()
            
            llm_message = clean_user_message
            
            if st.session_state[f'uploaded_files_{component_key}']:
                attachment_info = []
                for file_info in st.session_state[f'uploaded_files_{component_key}']:
                    attachment_info.append(f"📎 {file_info['name']} ({format_file_size(file_info['size'])})")
                
                # Simple message indicating files were attached
                if attachment_info:
                    file_context = f"\n\n=== ATTACHED FILES ===\n"
                    file_context += "\n".join(attachment_info)
                    file_context += f"\n\nUser message: {clean_user_message}"
                    file_context += f"\n\nNote: The attached files have been processed by the RAG system. Please provide a response based on the file contents and the user's question."
                    llm_message = file_context
            
            # Add message to UI history with file attachment info
            message_data = {
                "role": "user", 
                "content": clean_user_message,
                "attachments": []
            }
            
            # Add file attachment info if any
            if st.session_state[f'uploaded_files_{component_key}']:
                for file_info in st.session_state[f'uploaded_files_{component_key}']:
                    message_data["attachments"].append({
                        'name': file_info['name'],
                        'size': file_info['size'],
                        'type': file_info['type']
                    })
            
            st.session_state.messages.append(message_data)
            
            st.session_state.last_llm_message = llm_message
            
            st.session_state.current_screen = "chat"
            
            st.session_state[f'uploaded_files_{component_key}'] = []
            
            st.rerun()
    
    return None



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
        response = api_service.get("/models")
        if response.status_code == 200:
            return response.json()["models"]
        return ["llama3"]
    except:
        return ["llama3"]

def get_conversations():
    try:
        response = api_service.get("/conversations")
        if response.status_code == 200:
            return response.json()["conversations"]
        return []
    except Exception:
        return []

def get_conversation_messages(conversation_id):
    """Get messages for a specific conversation"""
    try:
        response = api_service.get(f"/conversations/{conversation_id}")
        if response.status_code == 200:
            return response.json()["messages"]
        return []
    except Exception:
        return []

def create_conversation(title="New Conversation"):
    try:
        response = api_service.post("/conversations", params={"title": title})
        if response.status_code == 200:
            return response.json()
        return None
    except Exception:
        return None

def send_message(message, history=None, model_name=None):
    
    # Global LLM instance
    if 'llm_instance' not in st.session_state and DIRECT_LLM:
        try:
            st.session_state.llm_instance = LLMModel(model_name=model_name or "llama3")
        except Exception as e:
            st.session_state.llm_instance = None
    
    if DIRECT_LLM and st.session_state.get('llm_instance'):
        try:
            response = st.session_state.llm_instance.get_response(message)
            return response
        except Exception as e:
            pass  # Fall back to API
    
    if not api_service.is_connected():
        if DIRECT_LLM:
            return "Both direct LLM and Backend API connection failed. Please ensure Ollama is running."
        else:
            return "Backend API connection failed. Please ensure the API is running."
        
    try:
        data = {
            "message": message,
            "conversation_id": st.session_state.get('current_conversation_id'),
            "history": history,
            "model_name": model_name
        }
        
        response = api_service.post("/chat", json=data)
        
        if response.status_code == 200:
            response_data = response.json()
            result = response_data["response"]
            
            if "conversation_id" in response_data:
                st.session_state.current_conversation_id = response_data["conversation_id"]
            
            return result
        else:
            error_msg = f"API'den yanıt alınamadı. Hata kodu: {response.status_code}"
            return error_msg
    except Exception as e:
        error_msg = f"Hata oluştu: {str(e)}"
        return error_msg

def clear_chat_history():
    try:
        api_service.post("/clear_history")
    except:
        pass

def load_conversations():
    """Load conversations from API"""
    conversations = get_conversations()
    st.session_state.conversations = conversations
    st.session_state.conversations_loaded = True

def load_conversation_messages(conversation_id):
    """Load messages for a specific conversation"""
    messages = get_conversation_messages(conversation_id)
    
    # Convert API format to frontend format
    formatted_messages = []
    for msg in messages:
        message_data = {
            "role": msg["role"],
            "content": msg["content"],
            "attachments": []  
        }
        formatted_messages.append(message_data)
    
    st.session_state.messages = formatted_messages
    st.session_state.current_conversation_id = conversation_id

def start_new_conversation():
    """Start a new conversation"""
    st.session_state.messages = []
    st.session_state.current_conversation_id = None

def process_message(user_input):
    """Process user message and get response from the model"""
    if not user_input:
        return
    
    message_to_llm = st.session_state.get('last_llm_message', user_input)
    
    # Clear the stored LLM message after use
    if 'last_llm_message' in st.session_state:
        del st.session_state.last_llm_message
    
    try:
        response = send_message(
            message=message_to_llm,
            model_name=st.session_state.get('current_model', 'llama3')
        )
        
        st.session_state.messages.append({"role": "assistant", "content": response, "attachments": []})
        
        try:
            load_conversations()
        except Exception as refresh_error:
            pass  
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        st.session_state.messages.append({"role": "assistant", "content": f"❌ {error_msg}", "attachments": []})

def read_file_content(file_id: int):
    """Read file content from backend"""
    try:
        response = api_service.get(f"/files/{file_id}/download", timeout=15)
        if response.status_code == 200:
            return response.content
        return None
    except Exception:
        return None

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
    
    # Session state initialization
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'current_conversation_id' not in st.session_state:
        st.session_state.current_conversation_id = None
    
    if 'conversations' not in st.session_state:
        st.session_state.conversations = []
    
    if 'current_model' not in st.session_state:
        st.session_state.current_model = "llama3"
    
    if 'model_options' not in st.session_state:
        st.session_state.model_options = ["llama3"]
        
        def update_models():
            time.sleep(2)  
            models = get_models()
            if models:
                st.session_state.model_options = models
                
        threading.Thread(target=update_models).start()
    
    if len(st.session_state.conversations) == 0:
        current_time = time.time()
        last_attempt = st.session_state.get('last_conversation_load_attempt', 0)
        
        if current_time - last_attempt > 5:
            st.session_state.last_conversation_load_attempt = current_time
            try:
                conversations = get_conversations()
                if conversations:
                    st.session_state.conversations = conversations
            except Exception:
                pass
    
    if 'thinking' not in st.session_state:
        st.session_state.thinking = False
    
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
        
        # Begin New Chat button
        if st.button("Begin a New Chat", key="new_chat_btn", use_container_width=True):
            start_new_conversation()
            st.rerun()
        
        # Arama kutusu
        st.markdown("""
        <div class="search-box-container">
            <span style="color:#aaa;margin-right:5px;">🔍</span>
            <input type="text" placeholder="Search" class="search-box">
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="chat-history-title">Recent Chats</div>', unsafe_allow_html=True)
        
        # Real conversations from database
        if st.session_state.conversations:
            for conv in st.session_state.conversations:
                # Truncate title for display
                display_title = conv['title']
                if len(display_title) > 30:
                    display_title = display_title[:30] + "..."
                
                # Check if this is the current conversation
                is_current = st.session_state.current_conversation_id == conv['id']
                button_style = "🟢 " if is_current else "💬 "
                
                if st.button(f"{button_style}{display_title}", key=f"conv_{conv['id']}", use_container_width=True):
                    load_conversation_messages(conv['id'])
                    st.rerun()
        else:
            st.markdown('<div style="color: #888; padding: 10px; font-size: 12px;">No conversations yet</div>', unsafe_allow_html=True)
            if st.button("🔄 Load Conversations", key="load_conversations_manual"):
                st.session_state.last_conversation_load_attempt = 0
                st.session_state.conversations = []
                st.rerun()
        
        # RAG System Status
        st.markdown('<div class="chat-history-title" style="margin-top: 20px;">🧠 RAG System</div>', unsafe_allow_html=True)
        
        rag_stats = get_rag_stats()
        if rag_stats and rag_stats.get('is_initialized'):
            vector_stats = rag_stats.get('vector_store', {})
            doc_count = vector_stats.get('document_count', 0)
            chunk_count = vector_stats.get('total_chunks', 0)
            
            st.markdown(f'''
            <div style="background-color: rgba(51, 51, 51, 0.3); border-radius: 8px; padding: 8px; backdrop-filter: blur(10px); font-size: 12px; color: #ddd;">
                <div>📚 Documents: {doc_count}</div>
                <div>🧩 Chunks: {chunk_count}</div>
                <div>🎯 Model: {rag_stats.get('embedding_service', {}).get('model_name', 'Unknown')}</div>
                <div style="color: #4CAF50;">✅ Active</div>
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown('''
            <div style="background-color: rgba(51, 51, 51, 0.3); border-radius: 8px; padding: 8px; backdrop-filter: blur(10px); font-size: 12px; color: #888;">
                <div style="color: #FFA726;">⚠️ Not initialized</div>
            </div>
            ''', unsafe_allow_html=True)
    
    # Ana içerik
    if len(st.session_state.messages) == 0:
        welcome_screen(logo_base64)
    else:
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
            # Assistant message 
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
                    {html.escape(message["content"])}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # User message - check if has attachments
            has_attachments = message.get("attachments") and len(message["attachments"]) > 0
            
            if has_attachments:
                # User message WITH attachments
                attachments_html = '<div style="margin-top: 8px; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 8px;">'
                for attachment in message["attachments"]:
                    file_size_str = format_file_size(attachment['size'])
                    attachments_html += f'''
                    <div style="
                        display: flex; 
                        align-items: center; 
                        margin-bottom: 4px;
                        background: rgba(255,255,255,0.1);
                        border-radius: 8px;
                        padding: 4px 8px;
                        font-size: 12px;
                    ">
                        <span style="margin-right: 6px;">📄</span>
                        <span style="flex: 1; color: rgba(255,255,255,0.9);">{html.escape(attachment["name"])}</span>
                        <span style="color: rgba(255,255,255,0.6); font-size: 10px;">{file_size_str}</span>
                    </div>
                    '''
                attachments_html += '</div>'
                
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
                        {html.escape(message["content"])}
                        {attachments_html}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                # User message WITHOUT attachments
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
                        {html.escape(message["content"])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Check if AI is thinking
    user_count = len([msg for msg in st.session_state.messages if msg["role"] == "user"])
    assistant_count = len([msg for msg in st.session_state.messages if msg["role"] == "assistant"])
    is_thinking = user_count > assistant_count
    
    # Debug info for thinking state
    print(f"DEBUG: user_count={user_count}, assistant_count={assistant_count}, is_thinking={is_thinking}")
    if st.session_state.messages:
        print(f"DEBUG: last_message_role={st.session_state.messages[-1]['role']}")

    # If AI is thinking, show thinking animation and process message
    if is_thinking and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        print("DEBUG: Showing thinking animation - hiding message input")
        
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
        
        # Completely hide any potential input elements during thinking
        st.markdown("""
        <style>
            /* Hide all input elements during thinking */
            .stFileUploader,
            .stTextInput,
            .stTextArea,
            .stButton,
            div[data-testid="stTextInput"],
            div[data-testid="stFileUploader"],
            div[data-testid="stTextArea"] {
                display: none !important;
                visibility: hidden !important;
                opacity: 0 !important;
                position: absolute !important;
                left: -9999px !important;
            }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="
            position: fixed;
            bottom: 20px;
            left: calc(50% + 125px);
            transform: translateX(-50%);
            width: 70%;
            max-width: 700px;
            z-index: 1000;
            background: linear-gradient(135deg, rgba(138, 43, 226, 0.3), rgba(168, 168, 168, 0.3));
            backdrop-filter: blur(15px);
            border-radius: 25px;
            padding: 15px;
            border: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            text-align: center;
            color: white;
            font-size: 14px;
        ">
             AI is thinking... Please wait
        </div>
        """, unsafe_allow_html=True)
        
        last_user_message = st.session_state.messages[-1]["content"]
        process_message(last_user_message)
        st.rerun()
    else:
        print("DEBUG: Showing message input - not thinking")
        # Show message input only when NOT thinking
        user_message = message_input_component(
            placeholder="Mesajınızı yazın...",
            key="chat"
        )
        
        if user_message:
            process_message(user_message)

if __name__ == "__main__":
    main() 