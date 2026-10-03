# -*- coding: utf-8 -*-
import streamlit as st
import sys
import os

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

st.set_page_config(
    page_title="شركة مهاره للتحصيل - stc #1",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 DESIGN SYSTEM & LIGHT THEME STYLES (RTL - CAIRO)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;800;900&display=swap');
    
    html, body, [class*="css"], .stApp {
        font-family: 'Cairo', sans-serif !important;
        direction: RTL;
        background-color: #f4f6fb !important;
        color: #1e293b !important;
    }
    
    .stApp {
        background: radial-gradient(circle at 10% 10%, rgba(37, 99, 235, 0.05) 0%, transparent 40%),
                    radial-gradient(circle at 90% 90%, rgba(14, 165, 233, 0.06) 0%, transparent 40%),
                    #f8fafc !important;
    }
    
    /* Global Sidebar Light Styling */
    [data-testid="stSidebar"] {
        background: #ffffff !important;
        border-left: 1px solid #e2e8f0 !important;
        box-shadow: -4px 0 20px rgba(0, 0, 0, 0.02) !important;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] span {
        color: #334155 !important;
    }
    
    .login-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        padding-top: 35px;
        padding-bottom: 25px;
    }
    
    .login-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 24px;
        padding: 45px 40px;
        max-width: 480px;
        width: 100%;
        text-align: center;
        box-shadow: 0 15px 35px -5px rgba(15, 23, 42, 0.08), 0 0 0 1px rgba(0, 0, 0, 0.02);
    }
    
    .brand-badge {
        display: inline-block;
        background: linear-gradient(135deg, #eff6ff, #dbeafe);
        border: 1px solid #bfdbfe;
        color: #1d4ed8;
        padding: 6px 18px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 800;
        margin-bottom: 14px;
        letter-spacing: 0.5px;
    }
    
    .logo-text {
        font-size: 40px;
        font-weight: 900;
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 60%, #0284c7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.2;
        margin-bottom: 4px;
    }
    
    .subtitle {
        color: #475569;
        font-size: 20px;
        font-weight: 800;
        margin-top: 2px;
        margin-bottom: 6px;
    }
    
    .sub-tagline {
        color: #0284c7;
        font-size: 15px;
        font-weight: 700;
        margin-bottom: 18px;
        background: #f0f9ff;
        display: inline-block;
        padding: 3px 14px;
        border-radius: 12px;
        border: 1px solid #bae6fd;
    }
    
    .light-divider {
        height: 2px;
        background: linear-gradient(90deg, transparent, #2563eb, #38bdf8, transparent);
        border-radius: 2px;
        margin: 20px 0;
    }
    
    .sector-chips {
        display: flex;
        justify-content: center;
        gap: 12px;
        margin-bottom: 24px;
    }
    
    .chip {
        background: #f1f5f9;
        border: 1px solid #cbd5e1;
        padding: 7px 16px;
        border-radius: 12px;
        font-size: 13px;
        font-weight: 700;
        color: #334155;
    }
    
    .sidebar-logo-card {
        background: linear-gradient(135deg, #f8fafc, #f1f5f9);
        border: 1px solid #cbd5e1;
        border-radius: 16px;
        padding: 18px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    .sidebar-logo-title {
        font-size: 22px;
        font-weight: 900;
        color: #1e3a8a;
        margin-bottom: 2px;
    }
    
    .sidebar-logo-sub {
        font-size: 13px;
        font-weight: 700;
        color: #0284c7;
    }
    
    .footer {
        color: #64748b;
        font-size: 13px;
        margin-top: 24px;
        font-weight: 600;
    }
    
    /* Input & Button Styling for Light Theme */
    .stTextInput > div > div > input {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #1e293b !important;
        border-radius: 12px !important;
        padding: 10px 16px !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15) !important;
    }
    .stButton > button {
        border-radius: 12px !important;
        font-weight: 700 !important;
    }
    </style>
""", unsafe_allow_html=True)

# 🔐 AUTHENTICATION GATE
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "sector" not in st.session_state:
    st.session_state.sector = None

if not st.session_state.authenticated:
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("""
            <div class="login-wrapper">
                <div class="login-card">
                    <div class="brand-badge">⭐ PLATFORM 2026</div>
                    <div class="logo-text">شركة مهاره للتحصيل</div>
                    <div class="subtitle">stc #1</div>
                    <div class="light-divider"></div>
                    <div class="sector-chips">
                        <div class="chip">👥 قطاع الأفراد</div>
                        <div class="chip">🏢 قطاع الأعمال</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        pwd = st.text_input("كلمة المرور", type="password", label_visibility="collapsed", placeholder="أدخل كلمة المرور لدخول المنصة...")
        if st.button("🔓 دخول المنصة", use_container_width=True, type="primary"):
            if pwd in ("333", "افراد", "1234"):
                st.session_state.authenticated = True
                st.session_state.sector = "افراد"
                st.session_state.sector_display = "قطاع الأفراد"
                st.rerun()
            elif pwd in ("444", "اعمال"):
                st.session_state.authenticated = True
                st.session_state.sector = "اعمال"
                st.session_state.sector_display = "قطاع الأعمال"
                st.rerun()
            else:
                st.error("❌ كلمة المرور غير صحيحة. حاول مرة أخرى.")
        
        st.markdown('<div class="footer" style="text-align:center;">شركة مهاره للتحصيل © 2026 جميع الحقوق محفوظة</div>', unsafe_allow_html=True)
    st.stop()

# 🚀 LOGGED IN - SIDEBAR & SYSTEM ROUTING
with st.sidebar:
    st.markdown(f"""
        <div class="sidebar-logo-card">
            <div class="sidebar-logo-title">شركة مهاره للتحصيل</div>
            <div class="sidebar-logo-sub">stc #1</div>
            <div style="margin-top:10px;">
                <span class="chip">{'👥 ' if st.session_state.sector == 'افراد' else '🏢 '}{st.session_state.get('sector_display', 'النظام')}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.sector = None
        st.rerun()

# Run the selected sector app
if st.session_state.sector == "افراد":
    import افراد_app
    افراد_app.run_afrad_app()
elif st.session_state.sector == "اعمال":
    import اعمال_app
    اعمال_app.run_aamal_app()

