import streamlit as st
import base64
import os

# Checklists KYC por tipo de cliente
DOCS_NATURAL = [
    "Cédula de Identidad vigente",
    "RIF personal",
    "Comprobante de domicilio (menos de 3 meses)",
    "Constancia de ingresos / Declaración de ISLR",
    "Estado de cuenta bancario (últimos 3 meses)",
    "Referencias bancarias",
    "Declaración jurada de origen de fondos",
]
DOCS_JURIDICA = [
    "RIF de la empresa",
    "Acta Constitutiva y Estatutos Sociales",
    "Última Acta de Asamblea",
    "Poderes notariados del Representante Legal",
    "Cédula de Identidad del Representante Legal",
    "RIF del Representante Legal",
    "Estados financieros auditados (últimos 2 años)",
    "Referencias bancarias",
    "Comprobante de domicilio fiscal (menos de 3 meses)",
    "Declaración jurada de origen de fondos",
]

@st.cache_data
def get_base64_image(image_path):
    if not os.path.exists(image_path):
        return ""
    with open(image_path, "rb") as img_file:
        return f"data:image/png;base64,{base64.b64encode(img_file.read()).decode()}"



# ── Diccionario de Iconos SVG (Versión Blanca para Headers) ──
APP_ICONS = {
    "dashboard": """<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'><path fill='white' d='m16 8.41l-4.5-4.5L4.41 11H6v8h3v-6h5v6h3v-8h1.59L17 9.41V6h-1zM2 12l9.5-9.5L15 6V5h3v4l3 3h-3v8h-5v-6h-3v6H5v-8z'/></svg>""",
    "compliance": """<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 2048 2048'><path fill='white' d='M1033 1280q-14 30-21 62t-13 66H384v-128zm-649 384v-128h613q5 33 14 65t23 63zm-128 256h1349l127 128H128V0h1115l549 549v568q-29-26-61-47t-67-37V640h-512V128H256zM1280 219v293h293zm24 805q-109 41-187 128H384v-128zM384 512h640v128H384zm1152 256v128H384V768zm512 1216q0 26-19 45t-45 19t-45-19l-291-290q-39 26-84 39t-92 14q-66 0-124-25t-102-68t-69-102t-25-125t25-124t68-101t102-69t125-26t124 25t101 69t69 102t26 124q0 47-13 92t-40 84l290 291q19 19 19 45m-768-512q0 40 15 75t41 61t61 41t75 15t75-15t61-41t41-61t15-75t-15-75t-41-61t-61-41t-75-15t-75 15t-61 41t-41 61t-15 75'/></svg>""",
    "legal": """<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 50 50'><path fill='white' d='M.3 27.58a6.457 6.457 0 0 0 12.81 0H.31zm34.89 13c0 .55-.45 1-1 1H15.53c-.55 0-1-.45-1-1s.45-.99 1-.99h18.66c.55 0 1 .44 1 .99m-20.54 1.51h20.44v2.89H14.65zm22.26-14.51a6.46 6.46 0 0 0 6.4 5.63a6.45 6.45 0 0 0 6.4-5.63zm12.45-2.01l-5.24-7.22h2.8c.68 0 1.23-.56 1.23-1.25c0-.68-.55-1.24-1.23-1.24H32.07a7.33 7.33 0 0 0-5.63-4.73v-3.9c0-.69-.56-1.25-1.25-1.25l-.12.01l-.12-.01c-.69 0-1.24.55-1.24 1.25v3.9a7.35 7.35 0 0 0-5.63 4.73H3.23c-.68 0-1.23.55-1.23 1.24s.55 1.25 1.23 1.25h2.68L.67 25.57H.02v1.33h13.4v-1.33h-.66l-5.24-7.22h12.17c0-.28.03-.56.07-.82c.04-.12.07-.25.07-.38a5.32 5.32 0 0 1 3.9-3.93v13.7h-.05c-.11 5.15-2.56 9.65-6.19 12.17H32.7c-3.64-2.52-6.09-7.02-6.2-12.17h-.05v-13.7c1.93.47 3.44 2 3.89 3.93c0 .13.03.26.08.38c.04.27.07.54.07.82h12.04l-5.24 7.22h-.65v1.33h13.39v-1.33h-.65zm-43.18 0H2l4.18-5.76v5.77zm1.07 0v-5.76l4.18 5.77H7.25zm35.53 0h-4.19l4.19-5.76v5.77zm1.07 0v-5.76l4.19 5.77h-4.19zM7.96 14.12c0 .68-.56 1.24-1.24 1.24c-.69 0-1.25-.56-1.25-1.24c0-.69.56-1.25 1.25-1.25c.68 0 1.24.56 1.24 1.25m36.6-.07c0 .69-.56 1.24-1.24 1.24c-.69 0-1.24-.55-1.24-1.24s.55-1.25 1.24-1.25s1.24.56 1.24 1.25'/></svg>""",
    "risk": """<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'><path fill='white' d='m16 11.78l4.24-7.33l1.73 1l-5.23 9.05l-6.51-3.75L5.46 19H22v2H2V3h2v14.54L9.5 8z'/></svg>""",
    "comite": """<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 2048 2048'><path fill='white' d='M1792 768v768q0 1 9 27t22 67t30 89t30 90t24 73t13 38H0q2-7 12-37t25-73t30-91t29-88t23-67t9-28V768H0V640l960-480l960 480v128zM286 640h1348L960 303zm1250 128v768h128V768zm-256 0v768h128V768zm-256 0v768h128V768zm-256 0v768h128V768zm-256 0v768h128V768zm-256 768h128V768H256zm1486 256l-42-128H220l-42 128z'/></svg>""",
    "collections": """<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'><g fill='none' stroke='white' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5'><path d='M11 9.5h1.5A1.5 1.5 0 0 1 14 11m-3-1.5H9.5A1.5 1.5 0 0 0 8 11v.5A1.5 1.5 0 0 0 9.5 13h3a1.5 1.5 0 0 1 1.5 1.5v.5a1.5 1.5 0 0 1-1.5 1.5H11m0-7V8m0 8.5H9.5A1.5 1.5 0 0 1 8 15m3 1.5V18'/><path d='M12 4.055A9 9 0 1 0 19.945 12M18.5 2v7M22 5.5h-7'/></g></svg>""",
    "portfolio": """<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 256 256'><path fill='white' d='M216 66H56a10 10 0 0 1 0-20h136a6 6 0 0 0 0-12H56a22 22 0 0 0-22 22v128a22 22 0 0 0 22 22h160a14 14 0 0 0 14-14V80a14 14 0 0 0-14-14m2 126a2 2 0 0 1-2 2H56a10 10 0 0 1-10-10V75.59A21.84 21.84 0 0 0 56 78h160a2 2 0 0 1 2 2Zm-28-60a10 10 0 1 1-10-10a10 10 0 0 1 10 10'/></svg>""",
    "onboarding": """<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'><path fill='white' fill-rule='evenodd' d='M9 6.25a2.75 2.75 0 1 0 0 5.5a2.75 2.75 0 0 0 0-5.5M7.75 9a1.25 1.25 0 1 1 2.5 0a1.25 1.25 0 0 1-2.5 0M9 12.25c-1.196 0-2.315.24-3.164.665c-.803.402-1.586 1.096-1.586 2.085v.063c-.002.51-.004 1.37.81 1.959c.378.273.877.448 1.495.559c.623.112 1.422.169 2.445.169s1.822-.057 2.445-.169c.618-.111 1.117-.286 1.495-.56c.814-.589.812-1.448.81-1.959V15c0-.99-.783-1.683-1.586-2.085c-.849-.424-1.968-.665-3.164-.665M5.75 15c0-.115.113-.421.757-.743c.6-.3 1.48-.507 2.493-.507s1.894.207 2.493.507c.644.322.757.628.757.743c0 .604-.039.697-.19.807c-.122.088-.373.206-.88.298c-.502.09-1.203.145-2.18.145s-1.678-.055-2.18-.145c-.507-.092-.758-.21-.88-.298c-.152-.11-.19-.203-.19-.807' clip-rule='evenodd' /><path fill='white' d='M19 12.75a.75.75 0 0 0 0-1.5h-4a.75.75 0 0 0 0 1.5zM19.75 9a.75.75 0 0 1-.75.75h-5a.75.75 0 0 1 0-1.5h5a.75.75 0 0 1 .75.75M19 15.75a.75.75 0 0 0 0-1.5h-3a.75.75 0 0 0 0 1.5z' /><path fill='white' fill-rule='evenodd' d='M9.944 3.25h4.112c1.838 0 3.294 0 4.433.153c1.172.158 2.121.49 2.87 1.238c.748.749 1.08 1.698 1.238 2.87c.153 1.14.153 2.595.153 4.433v.112c0 1.838 0 3.294-.153 4.433c-.158 1.172-.49 2.121-1.238 2.87c-.749.748-1.698 1.08-2.87 1.238c-1.14.153-2.595.153-4.433.153H9.945c-1.838 0-3.294 0-4.433-.153c-1.172-.158-2.121-.49-2.87-1.238c-.748-.749-1.08-1.698-1.238-2.87c-.153-1.14-.153-2.595-.153-4.433v-.112c0-1.838 0-3.294.153-4.433c.158-1.172.49-2.121 1.238-2.87c.749-.748 1.698-1.08 2.87-1.238c1.14-.153 2.595-.153 4.433-.153M5.71 4.89c-1.006.135-1.586.389-2.01.812c-.422.423-.676 1.003-.811 2.009c-.138 1.028-.14 2.382-.14 4.289s.002 3.262.14 4.29c.135 1.005.389 1.585.812 2.008s1.003.677 2.009.812c1.028.138 2.382.14 4.289.14h4c1.907 0 3.262-.002 4.29-.14c1.005-.135 1.585-.389 2.008-.812s.677-1.003.812-2.009c.138-1.028.14-2.382.14-4.289s-.002-3.261-.14-4.29c-.135-1.005-.389-1.585-.812-2.008s-1.003-.677-2.009-.812c-1.027-.138-2.382-.14-4.289-.14h-4c-1.907 0-3.261.002-4.29.14' clip-rule='evenodd' /></svg>""",
    "parameters": """<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 512 512'><path fill='white' fill-rule='evenodd' d='m234.67 85.33l-.004 213.338h-21.333v42.666h21.333l.005 85.33h42.666l-.004-85.33h21.333v-42.666h-21.333l.004-213.338zm-128.006 0v85.355H85.331v42.645h21.333v213.333h42.667V213.33h21.333v-42.645h-21.333V85.33zm255.981.004v128h-21.333l.013 42.663h21.333v170.666h42.688V255.997h21.333l-.013-42.663h-21.333l.013-128.004z'/></svg>""",
    "users": """<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 256 256'><path fill='white' d='M243.6 148.8a6 6 0 0 1-8.4-1.2A53.58 53.58 0 0 0 192 126a6 6 0 0 1 0-12a26 26 0 1 0-25.18-32.5a6 6 0 0 1-11.62-3a38 38 0 1 1 59.91 39.63a65.7 65.7 0 0 1 29.69 22.27a6 6 0 0 1-1.2 8.4M189.19 213a6 6 0 0 1-2.19 8.2a5.9 5.9 0 0 1-3 .81a6 6 0 0 1-5.2-3a59 59 0 0 0-101.62 0a6 6 0 1 1-10.38-6a70.1 70.1 0 0 1 36.2-30.46a46 46 0 1 1 50.1 0A70.1 70.1 0 0 1 189.19 213M128 178a34 34 0 1 0-34-34a34 34 0 0 0 34 34m-58-58a6 6 0 0 0-6-6a26 26 0 1 1 25.18-32.51a6 6 0 1 0 11.62-3a38 38 0 1 0-59.91 39.63A65.7 65.7 0 0 0 11.2 140.4a6 6 0 1 0 9.6 7.2A53.58 53.58 0 0 1 64 126a6 6 0 0 0 6-6'/></svg>""",
    "profile": """<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'><g fill='none' stroke='white' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5'><path d='M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10s10-4.477 10-10S17.523 2 12 2'/><path d='M4.271 18.346S6.5 15.5 12 15.5s7.73 2.846 7.73 2.846M12 12a3 3 0 1 0 0-6a3 3 0 0 0 0 6'/></g></svg>""",
    "function": """<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 16 16'><path d='M0 0h16v16H0z' fill='none' /><g fill='white'><path d='M8.33 1.225A2.5 2.5 0 0 0 4.81 3.34L4.698 5H3.5a.5.5 0 0 0 0 1h1.132l-.44 6.595a1.5 1.5 0 0 1-2.112 1.268l-.375-.169a.5.5 0 0 0-.41.912l.375.17a2.5 2.5 0 0 0 3.52-2.114L5.634 6H7.5a.5.5 0 1 0 0-1H5.7l.107-1.595A1.5 1.5 0 0 1 7.92 2.137l.376.17a.5.5 0 1 0 .41-.913z' /><path d='M8.16 8.048a.25.25 0 0 1 .393.053l1.323 2.316l-2.73 2.73a.5.5 0 1 0 .708.707l2.537-2.537l1.188 2.079a1.25 1.25 0 0 0 1.969.263l.306-.305a.5.5 0 0 0-.708-.707l-.305.305a.25.25 0 0 1-.394-.052l-1.323-2.316l2.73-2.73a.5.5 0 1 0-.707-.707l-2.538 2.537l-1.188-2.08a1.25 1.25 0 0 0-1.969-.263l-.306.306a.5.5 0 1 0 .708.707z' /></g></svg>""",
    "automotriz": """<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'><path fill='currentColor' d='M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.21.42-1.42.99L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99ZM6.5 16c-.83 0-1.5-.67-1.5-1.5S5.67 13 6.5 13s1.5.67 1.5 1.5S7.33 16 6.5 16Zm11 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5s1.5.67 1.5 1.5s-.67 1.5-1.5 1.5ZM5 11l1.27-3.61c.11-.34.42-.39.73-.39h10c.31 0 .62.05.73.39L19 11H5Z'/></svg>""",
    "corporativo": """<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'><path fill='currentColor' d='M12 7V3H2v18h20V7H12zM6 19H4v-2h2v2zm0-4H4v-2h2v2zm0-4H4V9h2v2zm0-4H4V5h2v2zm4 12H8v-2h2v2zm0-4H8v-2h2v2zm0-4H8V9h2v2zm0-4H8V5h2v2zm10 12h-8v-2h2v-2h-2v-2h2v-2h-2V9h8v10zm-2-8h-2v2h2v-2zm0 4h-2v2h2v-2z'/></svg>""",
    "alerta": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path fill="currentColor" d="M13 17.5a1 1 0 1 1-2 0a1 1 0 0 1 2 0m-.25-8.25a.75.75 0 0 0-1.5 0v4.5a.75.75 0 0 0 1.5 0z" /><path fill="currentColor" d="M9.836 3.244c.963-1.665 3.365-1.665 4.328 0l8.967 15.504c.963 1.667-.24 3.752-2.165 3.752H3.034c-1.926 0-3.128-2.085-2.165-3.752Zm3.03.751a1.002 1.002 0 0 0-1.732 0L2.168 19.499A1.002 1.002 0 0 0 3.034 21h17.932a1.002 1.002 0 0 0 .866-1.5L12.866 3.994Z" /></svg>""",
    "campana": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 16 16"><path fill="#183177" d="M.584 2.223a.5.5 0 0 1 .693-.14l1.5 1.001a.5.5 0 0 1-.554.832l-1.5-1a.5.5 0 0 1-.139-.693M8 2a4.5 4.5 0 0 0-4.5 4.5v2.401l-.964 2.413A.5.5 0 0 0 3 12h10a.5.5 0 0 0 .464-.685L12.5 8.9V6.5A4.5 4.5 0 0 0 8 2m0 12.5A2 2 0 0 1 6.063 13h3.874A2 2 0 0 1 8 14.5m6.723-12.416a.5.5 0 0 1 .554.832l-1.5 1a.5.5 0 0 1-.554-.832zM0 6.5A.5.5 0 0 1 .5 6H2a.5.5 0 0 1 0 1H.5a.5.5 0 0 1-.5-.5M15.5 6a.5.5 0 0 1 0 1H14a.5.5 0 0 1 0-1z" /></svg>""",
    "reloj": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path fill="#183177" d="M9.367 2.25h5.266c1.092 0 1.958 0 2.655.057c.714.058 1.317.18 1.869.46a4.75 4.75 0 0 1 2.075 2.077c.281.55.403 1.154.461 1.868c.057.697.057 1.563.057 2.655v5.266c0 1.092 0 1.958-.057 2.655c-.058.714-.18 1.317-.46 1.869a4.75 4.75 0 0 1-2.076 2.075c-.552.281-1.155.403-1.869.461c-.697.057-1.563.057-2.655.057H9.367c-1.092 0-1.958 0-2.655-.057c-.714-.058-1.317-.18-1.868-.46a4.75 4.75 0 0 1-2.076-2.076c-.281-.552-.403-1.155-.461-1.869c-.057-.697-.057-1.563-.057-2.655V9.367c0-1.092 0-1.958.057-2.655c.058-.714.18-1.317.46-1.868a4.75 4.75 0 0 1 2.077-2.076c.55-.281 1.154-.403 1.868-.461c.697-.057 1.563-.057 2.655-.057M12.75 6a.75.75 0 0 0-1.5 0v6c0 .284.16.544.415.67l4 2a.75.75 0 1 0 .67-1.34l-3.585-1.793z" /></svg>""",
    "cartera": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 512 512"><path fill="#183177" d="M47.5 104H432V51.52a16 16 0 0 0-19.14-15.69l-368 60.48a16 16 0 0 0-12 10.47A39.7 39.7 0 0 1 47.5 104m416 24h-416a16 16 0 0 0-16 16v288a16 16 0 0 0 16 16h416a16 16 0 0 0 16-16V144a16 16 0 0 0-16-16M368 320a32 32 0 1 1 32-32a32 32 0 0 1-32 32" /><path fill="#183177" d="M31.33 259.5V116c0-12.33 5.72-18.48 15.42-20c35.2-5.53 108.58-8.5 108.58-8.5s-8.33 16-27.33 16V128c18.5 0 31.33 23.5 31.33 23.5L84.83 236Z" /></svg>""",
}

@st.cache_data
def inyectar_css_kfg():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Global ── */
.stApp {
    background-color: #F0F2F5 !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
html, body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    color: #1E293B;
}
.main .block-container { padding: 1.5rem 2rem 2rem; max-width: 1400px !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] > div:first-child {
    background: #183177 !important;
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] a,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stCaption { color: #FFFFFF !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #FFFFFF !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15) !important; }
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.10) !important;
    
    border: 1px solid rgba(255,255,255,0.18) !important;
    border-radius: 8px !important; width: 100%; transition: all 0.2s;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.20) !important;
}
/* Sidebar radio as nav rows */
[data-testid="stSidebar"] .stRadio > div { display:flex; flex-direction:column; gap:2px; }
[data-testid="stSidebar"] .stRadio label {
    display:flex !important; align-items:center !important;
    padding:9px 14px !important; border-radius:8px !important;
    cursor:pointer !important; transition:background 0.15s !important;
    font-size:0.88em !important; font-weight:500 !important;
    color:#CBD5E1 !important;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background:rgba(255,255,255,0.10) !important;
    color:#FFFFFF !important;
}
[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p { }

/* ── Badges de Contador en Enlaces (Superíndice de Notificación) ── */
[data-testid="stSidebar"] a strong,
[data-testid="stSidebar"] a p strong {
    background: linear-gradient(135deg, #FF416C, #FF4B2B) !important;
    color: white !important; /* Vuelve a mostrar el número */
    border-radius: 10px !important;
    padding: 0 4px !important;
    font-size: 0.65em !important; 
    font-weight: 800 !important;
    
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    min-width: 16px !important;
    height: 16px !important;
    line-height: 1 !important;
    box-shadow: 0 2px 4px rgba(255, 65, 108, 0.4) !important;
    border: 1px solid rgba(255, 255, 255, 0.3) !important;
    transform: translateY(-6px) !important; /* Lo mueve arriba del texto (efecto superíndice) */
}
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stNumberInput input {
    background: rgba(255,255,255,0.12) !important;
    border-color: rgba(255,255,255,0.25) !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] .stTextInput input::placeholder,
[data-testid="stSidebar"] .stNumberInput input::placeholder {
    color: rgba(255,255,255,0.45) !important;
    -webkit-text-fill-color: rgba(255,255,255,0.45) !important;
}
[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
    background: rgba(255,255,255,0.12) !important;
    border-color: rgba(255,255,255,0.25) !important; color: #FFFFFF !important;
}

/* ── Forzar Opacidad en Carga (Evitar que se ponga opaco/transparente) ── */
[data-testid="stSidebar"] {
    opacity: 1 !important;
}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {
    opacity: 1 !important;
    filter: none !important;
}
/* Anular el efecto de "stale" (procesando) de Streamlit */
[data-testid="stSidebar"] [data-stale="true"] {
    opacity: 1 !important;
    filter: none !important;
}
/* Asegurar que los enlaces y botones no se atenúen */
[data-testid="stSidebar"] a, 
[data-testid="stSidebar"] button, 
[data-testid="stSidebar"] .stPageLink {
    opacity: 1 !important;
}

/* ── Tabs — flat underline style ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0; background: transparent;
    padding: 0; border-radius: 0;
    border-bottom: 2px solid #E2E8F0 !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 0; padding: 10px 20px;
    font-weight: 500; font-size: 0.88em;
    color: #64748B !important; background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -2px; transition: color 0.15s, border-color 0.15s;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #1E3A8A !important; background: transparent !important;
    border-bottom-color: #BFDBFE !important;
}
.stTabs [aria-selected="true"] {
    background: transparent !important; color: #1E3A8A !important;
    font-weight: 700 !important; box-shadow: none !important;
    border-bottom: 2px solid #1E3A8A !important;
}


/* ── Expanders como cards ── */
.stExpander {
    background: white !important; border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 8px rgba(11,29,78,0.06) !important;
    margin-bottom: 10px !important; overflow: hidden !important;
    transition: box-shadow 0.2s !important;
}
.stExpander:hover {
    box-shadow: 0 4px 16px rgba(11,29,78,0.10) !important;
}

/* ── Loaders & Skeletons ── */
@keyframes shimmer {
    0% { background-position: -468px 0; }
    100% { background-position: 468px 0; }
}
.skeleton {
    height: 20px;
    background: #f6f7f8;
    background-image: linear-gradient(to right, #f6f7f8 0%, #edeef1 20%, #f6f7f8 40%, #f6f7f8 100%);
    background-repeat: no-repeat;
    background-size: 800px 104px;
    display: inline-block;
    position: relative;
    animation: shimmer 1.2s linear infinite forwards;
    border-radius: 4px;
}

/* Estilo para el Spinner de Streamlit */
/* Estilo para el Spinner de Streamlit */
div[data-testid="stSpinner"] > div {
    border-top-color: #183177 !important;
}
div[data-testid="stSpinner"] p {
    color: #183177 !important;
    font-weight: 500 !important;
}
.stExpander > details > summary {
    padding: 14px 20px !important; font-weight: 600 !important;
    color: #0B1D4E !important; font-size: 0.92em !important;
}
.stExpander > details > summary:hover { background: #F8FAFC !important; }
.stExpander > details[open] > summary {
    border-bottom: 1px solid #E2E8F0 !important; background: #F8FAFC !important;
    border-left: 3px solid #1E3A8A !important; padding-left: 17px !important;
}
.stExpander > details > div { padding: 16px 20px !important; }
/* Texto dentro de expanders siempre oscuro */
.stExpander p, .stExpander span:not([style]),
.stExpander label, .stExpander li,
.stExpander [data-testid="stMarkdownContainer"] p { color: #1E293B !important; }
.stExpander [data-testid="stWidgetLabel"] p { color: #374151 !important; }

/* ── Containers con borde (ej. Comité) ── */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: white !important; border-radius: 12px !important;
    border-color: #E2E8F0 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important; padding: 4px !important;
}
/* Todo el texto dentro de containers con borde oscuro */
[data-testid="stVerticalBlockBorderWrapper"] p,
[data-testid="stVerticalBlockBorderWrapper"] span:not([style]),
[data-testid="stVerticalBlockBorderWrapper"] label,
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stMarkdownContainer"] p,
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stWidgetLabel"] p { color: #1E293B !important; }

/* ── Métricas ── */
[data-testid="metric-container"] {
    background: white; border: 1px solid #E2E8F0;
    border-left: 4px solid #1E3A8A;
    border-radius: 12px; padding: 20px 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    transition: box-shadow 0.2s, transform 0.2s;
}
[data-testid="metric-container"]:hover {
    box-shadow: 0 6px 20px rgba(11,29,78,0.10);
    transform: translateY(-1px);
}
[data-testid="stMetricValue"] {
    color: #0B1D4E !important; font-weight: 800 !important;
    font-size: 2em !important; line-height: 1.1 !important;
    letter-spacing: -0.02em !important;
}
[data-testid="stMetricLabel"] {
    color: #64748B !important; font-weight: 600 !important;
    font-size: 0.78em !important; text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
[data-testid="stMetricDelta"] { font-size: 0.82em !important; font-weight: 600 !important; }

/* ── Botones ── */
.stButton > button {
    border-radius: 8px !important; font-weight: 600 !important;
    font-size: 0.88em !important; transition: all 0.18s ease !important;
    letter-spacing: 0.01em !important;
}
.stButton > button:hover { transform: translateY(-1px) !important; }

[data-testid="stFormSubmitButton"] > button,
button[data-testid="baseButton-primary"] {
    background: #0B1D4E !important;
    color: white !important; border: none !important;
    border-radius: 8px !important; width: 100%; padding: 12px !important;
    font-weight: 700 !important; font-size: 0.92em !important;
    letter-spacing: 0.03em !important;
    box-shadow: 0 2px 10px rgba(11,29,78,0.25) !important;
    transition: all 0.18s !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    text-align: center !important;
    margin: auto;
}

/* Forzar color blanco para el texto y todos los elementos internos de los botones */
[data-testid="stFormSubmitButton"] button *,
[data-testid="stFormSubmitButton"] button p,
button[data-testid="baseButton-primary"] *,
button[data-testid="baseButton-primary"] p,
button[kind="primary"] *,
button[kind="primary"] p {
    color: white !important;
    -webkit-text-fill-color: white !important;
}

[data-testid="stFormSubmitButton"] > button:hover,
button[data-testid="baseButton-primary"]:hover {
    background: #1E3A8A !important;
    box-shadow: 0 4px 18px rgba(30,58,138,0.35) !important;
    transform: translateY(-1px) !important;
}
[data-testid="stDownloadButton"] > button {
    background: #059669 !important; color: white !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(5,150,105,0.2) !important;
}
[data-testid="stDownloadButton"] > button p {
    color: white !important;
}
[data-testid="stDownloadButton"] > button:hover {
    background: #047857 !important; box-shadow: 0 4px 14px rgba(5,150,105,0.35) !important;
}

/* ── Inputs — texto oscuro obligatorio ── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius: 8px !important;
    border: 1px solid #D1D5DB !important;
    font-size: 0.9em !important;
    color: #111827 !important;
    background: #FFFFFF !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
    -webkit-text-fill-color: #111827 !important;
}
.stTextInput > div > div > input::placeholder,
.stNumberInput > div > div > input::placeholder,
.stTextArea > div > div > textarea::placeholder {
    color: #9CA3AF !important;
    -webkit-text-fill-color: #9CA3AF !important;
}
/* Forzar bordes visibles en todos los inputs */
div[data-baseweb="input"] {
    border: 1px solid #94A3B8 !important;
    border-radius: 8px !important;
}
div[data-baseweb="input"]:focus-within {
    border-color: #1E3A8A !important;
    box-shadow: 0 0 0 3px rgba(30,58,138,0.15) !important;
}
.stTextInput input, .stNumberInput input, .stTextArea textarea {
    border: none !important; /* El borde lo da el contenedor baseweb anterior */
}

/* ── Labels de widgets — todos oscuros ── */
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] span,
[data-testid="stWidgetLabel"] label,
.stTextInput label,
.stNumberInput label,
.stSelectbox label,
.stMultiSelect label,
.stTextArea label,
.stSlider label,
.stCheckbox label,
.stRadio label,
.stDateInput label,
.stTimeInput label {
    color: #374151 !important;
    font-weight: 500 !important;
}
/* ── Labels con color KFG para formularios principales ── */
div[data-testid="stMarkdownContainer"] p { color: #1E293B; }
.stTextInput label, .stNumberInput label, .stSelectbox label {
    color: #0B1D4E !important;
    font-weight: 600 !important;
}
/* Login y formularios de entrada — labels siempre visibles */
[data-testid="stForm"] .stTextInput label,
[data-testid="stForm"] .stNumberInput label,
[data-testid="stForm"] .stSelectbox label,
[data-testid="stForm"] .stTextArea label,
[data-testid="stForm"] .stDateInput label,
[data-testid="stForm"] [data-testid="stWidgetLabel"] p {
    color: #0B1D4E !important;
    font-weight: 600 !important;
}
/* Anular solo dentro de sidebar */
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] span,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stCheckbox label {
    color: #003144 !important;
}
.st-key-submit_button{
    margin: auto;
    width: 100%;
}

/* ── Select boxes — texto oscuro ── */
div[data-baseweb="select"] > div {
    border-radius: 8px !important;
    border: 1px solid #D1D5DB !important;
    background: #FFFFFF !important;
    font-size: 0.9em !important;
    color: #111827 !important;
}
[data-baseweb="select"] span,
[data-baseweb="select"] input,
[data-baseweb="select"] div[role="option"],
[data-baseweb="menu"] li,
[data-baseweb="menu"] [role="option"] {
    color: #111827 !important;
}
/* Dropdown option list */
[data-baseweb="popover"] li,
[data-baseweb="popover"] [role="option"] {
    color: #111827 !important;
    background: #FFFFFF !important;
}

/* ── Sliders — texto y valores oscuros ── */
[data-testid="stSlider"] p,
[data-testid="stSlider"] span,
[data-testid="stSlider"] [data-testid="stMarkdownContainer"] p { color: #374151 !important; }

/* ── LaTeX / KaTeX — texto oscuro ── */
.katex { color: #1E293B !important; }
.katex * { color: inherit !important; }
.katex-html { color: #1E293B !important; }
[data-testid="stText"] { color: #1E293B !important; }

/* ── Markdown general en contenido principal eliminada por conflictos con botones ── */

/* ── Números en st.number_input ── */
.stNumberInput [data-testid="stNumberInput-StepUp"],
.stNumberInput [data-testid="stNumberInput-StepDown"],
.stNumberInput button svg { color: #374151 !important; fill: #374151 !important; }

/* ── Texto caption / st.caption ── */
.main [data-testid="stCaptionContainer"] p { color: #6B7280 !important; }

/* ── Forms ── */
[data-testid="stForm"] {
    background: white; border-radius: 14px;
    padding: 24px; border: 1px solid #E2E8F0;
    box-shadow: 0 2px 10px rgba(11,29,78,0.06);
}

/* ── Alerts nativos ── */
.stAlert { border-radius: 10px !important; font-size: 0.9em !important; }
/* Estilo específico para st.info sin afectar otros widgets */
[data-testid="stNotification"] {
    background-color: #a9c1d3 !important;
    border: 1px solid rgba(0,0,0,0.05) !important;
}
[data-testid="stNotification"] p {
    color: #0B1D4E !important;
    font-weight: 500 !important;
}

/* ── Botones de Descarga (st.download_button) ── */
div[data-testid="stDownloadButton"] button {
    background-color: #312E81 !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1rem !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 4px 12px rgba(49, 46, 129, 0.2) !important;
}
div[data-testid="stDownloadButton"] button:hover {
    background-color: #1E1B4B !important;
    box-shadow: 0 6px 16px rgba(49, 46, 129, 0.3) !important;
    transform: translateY(-1px) !important;
}
div[data-testid="stDownloadButton"] button:active {
    transform: translateY(0px) !important;
}

/* ── Dividers ── */
hr { border-color: #E2E8F0 !important; margin: 1.2rem 0 !important; }

/* ── DataFrames ── */
[data-testid="stDataFrame"] {
    border-radius: 10px !important; overflow: hidden !important;
    border: 1px solid #E2E8F0 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
}

/* ── Progress bar ── */
[data-testid="stProgress"] > div > div {
    background: #E2E8F0 !important; border-radius: 6px !important; height: 8px !important;
}
[data-testid="stProgress"] > div > div > div > div {
    background: linear-gradient(90deg, #1E3A8A, #3B82F6) !important;
    border-radius: 6px !important;
}

/* ── Headers de sección ── */
.stMarkdown h1 {
    color: #0B1D4E !important; font-size: 1.55em !important;
    font-weight: 800 !important; letter-spacing: -0.02em !important;
    margin-bottom: 4px !important;
}
.stMarkdown h2 {
    color: #1E3A8A !important; font-size: 1.12em !important;
    font-weight: 700 !important; padding-bottom: 10px !important;
    border-bottom: 2px solid #DBEAFE !important;
    margin-top: 1.2em !important; margin-bottom: 0.8em !important;
}
.stMarkdown h3 {
    color: #1E293B !important; font-size: 0.88em !important;
    font-weight: 700 !important; text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

/* ── Subheaders nativos ── */
[data-testid="stHeadingWithActionElements"] h2,
[data-testid="stHeadingWithActionElements"] h3 {
    color: #0B1D4E !important; font-weight: 700 !important;
}

/* ── Tables ── */
table { border-collapse: collapse !important; width: 100% !important; }
th {
    background: #F8FAFC !important; color: #64748B !important;
    font-size: 0.76em !important; font-weight: 700 !important;
    text-transform: uppercase !important; letter-spacing: 0.06em !important;
    padding: 10px 14px !important; border-bottom: 2px solid #E2E8F0 !important;
    white-space: nowrap !important;
}
td {
    padding: 10px 14px !important; font-size: 0.87em !important;
    border-bottom: 1px solid #F1F5F9 !important; color: #1E293B !important;
    vertical-align: middle !important;
}
tr:hover td { background: #F8FAFC !important; }

/* ── Checkbox ── */
[data-testid="stCheckbox"] label { font-size: 0.9em !important; color: #334155 !important; }

/* ── Slider track ── */
[data-testid="stSlider"] > div > div > div > div {
    background: #1E3A8A !important;
}

/* ── Botones Personalizados ── */
.submit_button {
    background: #0B1D4E !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 12px !important;
    font-weight: 700 !important;
    font-size: 0.92em !important;
    width: 100% !important;
    text-align: center !important;
    box-shadow: 0 2px 10px rgba(11,29,78,0.25) !important;
    transition: all 0.18s !important;
    cursor: pointer !important;
    display: inline-block !important;
}
.submit_button:hover {
    background: #1E3A8A !important;
    box-shadow: 0 4px 18px rgba(30,58,138,0.35) !important;
    transform: translateY(-1px) !important;
}

/* ══════════════════════════════════════════════════
   RED DE SEGURIDAD: texto oscuro en área principal
   Aplica a cualquier elemento que no sea sidebar,
   no tenga style inline ni sea un badge/span con color.
   ══════════════════════════════════════════════════ */
.main p, .main li, .main strong, .main em,
.main [class*="streamlit"] p,
.main [class*="streamlit"] li { color: #1E293B; }

/* Tabs inner text */
.stTabs [data-baseweb="tab-panel"] p,
.stTabs [data-baseweb="tab-panel"] li,
.stTabs [data-baseweb="tab-panel"] label {  }

/* st.write / st.text output */
[data-testid="stText"] p,
[data-testid="stText"] span { color: #1E293B !important; }

/* Forms — todos los textos dentro */
[data-testid="stForm"] p,
[data-testid="stForm"] li,
[data-testid="stForm"] label,
[data-testid="stForm"] [data-testid="stMarkdownContainer"] p {}

/* st.write tables */
[data-testid="stTable"] td,
[data-testid="stTable"] th { color: #1E293B !important; }

/* ── SVG Offline Hacks para Sidebar ── */
[data-testid="stSidebar"] a[href*="show_dashboard"]::before,
[data-testid="stSidebar"] a[href$="/"]::before,
[data-testid="stSidebar"] a[href=""]::before,
[data-testid="stSidebar"] a[href="."]::before,
[data-testid="stSidebar"] a[href="./"]::before {
    content: ""; display: inline-block; width: 18px; height: 18px; margin-right: 12px;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'%3E%3Cpath fill='%23a9c1d3' d='m16 8.41l-4.5-4.5L4.41 11H6v8h3v-6h5v6h3v-8h1.59L17 9.41V6h-1zM2 12l9.5-9.5L15 6V5h3v4l3 3h-3v8h-5v-6h-3v6H5v-8z'/%3E%3C/svg%3E") no-repeat center;
    background-size: contain;
}
[data-testid="stSidebar"] a[href*="show_compliance"]::before {
    content: ""; display: inline-block; width: 18px; height: 18px; margin-right: 12px;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='2048' height='2048' viewBox='0 0 2048 2048'%3E%3Cpath fill='%23a9c1d3' d='M1033 1280q-14 30-21 62t-13 66H384v-128zm-649 384v-128h613q5 33 14 65t23 63zm-128 256h1349l127 128H128V0h1115l549 549v568q-29-26-61-47t-67-37V640h-512V128H256zM1280 219v293h293zm24 805q-109 41-187 128H384v-128zM384 512h640v128H384zm1152 256v128H384V768zm512 1216q0 26-19 45t-45 19t-45-19l-291-290q-39 26-84 39t-92 14q-66 0-124-25t-102-68t-69-102t-25-125t25-124t68-101t102-69t125-26t124 25t101 69t69 102t26 124q0 47-13 92t-40 84l290 291q19 19 19 45m-768-512q0 40 15 75t41 61t61 41t75 15t75-15t61-41t41-61t15-75t-15-75t-41-61t-61-41t-75-15t-75 15t-61 41t-41 61t-15 75' /%3E%3C/svg%3E") no-repeat center;
    background-size: contain;
}
[data-testid="stSidebar"] a[href*="show_legal"]::before {
    content: ""; display: inline-block; width: 18px; height: 18px; margin-right: 12px;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='50' height='50' viewBox='0 0 50 50'%3E%3Cpath fill='%23a9c1d3' d='M.3 27.58a6.457 6.457 0 0 0 12.81 0H.31zm34.89 13c0 .55-.45 1-1 1H15.53c-.55 0-1-.45-1-1s.45-.99 1-.99h18.66c.55 0 1 .44 1 .99m-20.54 1.51h20.44v2.89H14.65zm22.26-14.51a6.46 6.46 0 0 0 6.4 5.63a6.45 6.45 0 0 0 6.4-5.63zm12.45-2.01l-5.24-7.22h2.8c.68 0 1.23-.56 1.23-1.25c0-.68-.55-1.24-1.23-1.24H32.07a7.33 7.33 0 0 0-5.63-4.73v-3.9c0-.69-.56-1.25-1.25-1.25l-.12.01l-.12-.01c-.69 0-1.24.55-1.24 1.25v3.9a7.35 7.35 0 0 0-5.63 4.73H3.23c-.68 0-1.23.55-1.23 1.24s.55 1.25 1.23 1.25h2.68L.67 25.57H.02v1.33h13.4v-1.33h-.66l-5.24-7.22h12.17c0-.28.03-.56.07-.82c.04-.12.07-.25.07-.38a5.32 5.32 0 0 1 3.9-3.93v13.7h-.05c-.11 5.15-2.56 9.65-6.19 12.17H32.7c-3.64-2.52-6.09-7.02-6.2-12.17h-.05v-13.7c1.93.47 3.44 2 3.89 3.93c0 .13.03.26.08.38c.04.27.07.54.07.82h12.04l-5.24 7.22h-.65v1.33h13.39v-1.33h-.65zm-43.18 0H2l4.18-5.76v5.77zm1.07 0v-5.76l4.18 5.77H7.25zm35.53 0h-4.19l4.19-5.76v5.77zm1.07 0v-5.76l4.19 5.77h-4.19zM7.96 14.12c0 .68-.56 1.24-1.24 1.24c-.69 0-1.25-.56-1.25-1.24c0-.69.56-1.25 1.25-1.25c.68 0 1.24.56 1.24 1.25m36.6-.07c0 .69-.56 1.24-1.24 1.24c-.69 0-1.24-.55-1.24-1.24s.55-1.25 1.24-1.25s1.24.56 1.24 1.25' /%3E%3C/svg%3E") no-repeat center;
    background-size: contain;
}
[data-testid="stSidebar"] a[href*="show_risk"]::before {
    content: ""; display: inline-block; width: 18px; height: 18px; margin-right: 12px;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'%3E%3Cpath fill='%23a9c1d3' d='m16 11.78l4.24-7.33l1.73 1l-5.23 9.05l-6.51-3.75L5.46 19H22v2H2V3h2v14.54L9.5 8z' /%3E%3C/svg%3E") no-repeat center;
    background-size: contain;
}
[data-testid="stSidebar"] a[href*="show_evaluations"]::before {
    content: ""; display: inline-block; width: 18px; height: 18px; margin-right: 12px;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='2048' height='2048' viewBox='0 0 2048 2048'%3E%3Cpath fill='%23a9c1d3' d='M1792 768v768q0 1 9 27t22 67t30 89t30 90t24 73t13 38H0q2-7 12-37t25-73t30-91t29-88t23-67t9-28V768H0V640l960-480l960 480v128zM286 640h1348L960 303zm1250 128v768h128V768zm-256 0v768h128V768zm-256 0v768h128V768zm-256 0v768h128V768zm-256 0v768h128V768zm-256 768h128V768H256zm1486 256l-42-128H220l-42 128z' /%3E%3C/svg%3E") no-repeat center;
    background-size: contain;
}
[data-testid="stSidebar"] a[href*="show_collections"]::before,
[data-testid="stSidebar"] a[href*="collections"]::before,
[data-testid="stSidebar"] a[href*="Cobranzas"]::before,
[data-testid="stSidebar"] a[href*="cobranzas"]::before {
    content: ""; display: inline-block; width: 18px; height: 18px; margin-right: 12px;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'%3E%3Cg fill='none' stroke='%23a9c1d3' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5'%3E%3Cpath d='M11 9.5h1.5A1.5 1.5 0 0 1 14 11m-3-1.5H9.5A1.5 1.5 0 0 0 8 11v.5A1.5 1.5 0 0 0 9.5 13h3a1.5 1.5 0 0 1 1.5 1.5v.5a1.5 1.5 0 0 1-1.5 1.5H11m0-7V8m0 8.5H9.5A1.5 1.5 0 0 1 8 15m3 1.5V18' /%3E%3Cpath d='M12 4.055A9 9 0 1 0 19.945 12M18.5 2v7M22 5.5h-7' /%3E%3C/g%3E%3C/svg%3E") no-repeat center;
    background-size: contain;
}
[data-testid="stSidebar"] a[href*="show_general_report"]::before,
[data-testid="stSidebar"] a[href*="show_portfolio"]::before {
    content: ""; display: inline-block; width: 18px; height: 18px; margin-right: 12px;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='256' height='256' viewBox='0 0 256 256'%3E%3Cpath fill='%23a9c1d3' d='M216 66H56a10 10 0 0 1 0-20h136a6 6 0 0 0 0-12H56a22 22 0 0 0-22 22v128a22 22 0 0 0 22 22h160a14 14 0 0 0 14-14V80a14 14 0 0 0-14-14m2 126a2 2 0 0 1-2 2H56a10 10 0 0 1-10-10V75.59A21.84 21.84 0 0 0 56 78h160a2 2 0 0 1 2 2Zm-28-60a10 10 0 1 1-10-10a10 10 0 0 1 10 10' /%3E%3C/svg%3E") no-repeat center;
    background-size: contain;
}
[data-testid="stSidebar"] a[href*="show_client_registration"]::before,
[data-testid="stSidebar"] a[href*="show_client_list"]::before {
    content: ""; display: inline-block; width: 18px; height: 18px; margin-right: 12px;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'%3E%3Cpath fill='%23a9c1d3' fill-rule='evenodd' d='M9 6.25a2.75 2.75 0 1 0 0 5.5a2.75 2.75 0 0 0 0-5.5M7.75 9a1.25 1.25 0 1 1 2.5 0a1.25 1.25 0 0 1-2.5 0M9 12.25c-1.196 0-2.315.24-3.164.665c-.803.402-1.586 1.096-1.586 2.085v.063c-.002.51-.004 1.37.81 1.959c.378.273.877.448 1.495.559c.623.112 1.422.169 2.445.169s1.822-.057 2.445-.169c.618-.111 1.117-.286 1.495-.56c.814-.589.812-1.448.81-1.959V15c0-.99-.783-1.683-1.586-2.085c-.849-.424-1.968-.665-3.164-.665M5.75 15c0-.115.113-.421.757-.743c.6-.3 1.48-.507 2.493-.507s1.894.207 2.493.507c.644.322.757.628.757.743c0 .604-.039.697-.19.807c-.122.088-.373.206-.88.298c-.502.09-1.203.145-2.18.145s-1.678-.055-2.18-.145c-.507-.092-.758-.21-.88-.298c-.152-.11-.19-.203-.19-.807' clip-rule='evenodd' /%3E%3Cpath fill='%23a9c1d3' d='M19 12.75a.75.75 0 0 0 0-1.5h-4a.75.75 0 0 0 0 1.5zM19.75 9a.75.75 0 0 1-.75.75h-5a.75.75 0 0 1 0-1.5h5a.75.75 0 0 1 .75.75M19 15.75a.75.75 0 0 0 0-1.5h-3a.75.75 0 0 0 0 1.5z' /%3E%3Cpath fill='%23a9c1d3' fill-rule='evenodd' d='M9.944 3.25h4.112c1.838 0 3.294 0 4.433.153c1.172.158 2.121.49 2.87 1.238c.748.749 1.08 1.698 1.238 2.87c.153 1.14.153 2.595.153 4.433v.112c0 1.838 0 3.294-.153 4.433c-.158 1.172-.49 2.121-1.238 2.87c-.749.748-1.698 1.08-2.87 1.238c-1.14.153-2.595.153-4.433.153H9.945c-1.838 0-3.294 0-4.433-.153c-1.172-.158-2.121-.49-2.87-1.238c-.748-.749-1.08-1.698-1.238-2.87c-.153-1.14-.153-2.595-.153-4.433v-.112c0-1.838 0-3.294.153-4.433c.158-1.172.49-2.121 1.238-2.87c.749-.748 1.698-1.08 2.87-1.238c1.14-.153 2.595-.153 4.433-.153M5.71 4.89c-1.006.135-1.586.389-2.01.812c-.422.423-.676 1.003-.811 2.009c-.138 1.028-.14 2.382-.14 4.289s.002 3.262.14 4.29c.135 1.005.389 1.585.812 2.008s1.003.677 2.009.812c1.028.138 2.382.14 4.289.14h4c1.907 0 3.262-.002 4.29-.14c1.005-.135 1.585-.389 2.008-.812s.677-1.003.812-2.009c.138-1.028.14-2.382.14-4.289s-.002-3.261-.14-4.29c-.135-1.005-.389-1.585-.812-2.008s-1.003-.677-2.009-.812c-1.027-.138-2.382-.14-4.289-.14h-4c-1.907 0-3.261.002-4.29.14' clip-rule='evenodd' /%3E%3C/svg%3E") no-repeat center;
    background-size: contain;
}
[data-testid="stSidebar"] a[href*="show_parameters"]::before {
    content: ""; display: inline-block; width: 18px; height: 18px; margin-right: 12px;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='512' height='512' viewBox='0 0 512 512'%3E%3Cpath fill='%23a9c1d3' fill-rule='evenodd' d='m234.67 85.33l-.004 213.338h-21.333v42.666h21.333l.005 85.33h42.666l-.004-85.33h21.333v-42.666h-21.333l.004-213.338zm-128.006 0v85.355H85.331v42.645h21.333v213.333h42.667V213.33h21.333v-42.645h-21.333V85.33zm255.981.004v128h-21.333l.013 42.663h21.333v170.666h42.688V255.997h21.333l-.013-42.663h-21.333l.013-128.004z' /%3E%3C/svg%3E") no-repeat center;
    background-size: contain;
}
[data-testid="stSidebar"] a[href*="show_users"]::before {
    content: ""; display: inline-block; width: 18px; height: 18px; margin-right: 12px;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='256' height='256' viewBox='0 0 256 256'%3E%3Cpath fill='%23a9c1d3' d='M243.6 148.8a6 6 0 0 1-8.4-1.2A53.58 53.58 0 0 0 192 126a6 6 0 0 1 0-12a26 26 0 1 0-25.18-32.5a6 6 0 0 1-11.62-3a38 38 0 1 1 59.91 39.63a65.7 65.7 0 0 1 29.69 22.27a6 6 0 0 1-1.2 8.4M189.19 213a6 6 0 0 1-2.19 8.2a5.9 5.9 0 0 1-3 .81a6 6 0 0 1-5.2-3a59 59 0 0 0-101.62 0a6 6 0 1 1-10.38-6a70.1 70.1 0 0 1 36.2-30.46a46 46 0 1 1 50.1 0A70.1 70.1 0 0 1 189.19 213M128 178a34 34 0 1 0-34-34a34 34 0 0 0 34 34m-58-58a6 6 0 0 0-6-6a26 26 0 1 1 25.18-32.51a6 6 0 1 0 11.62-3a38 38 0 1 0-59.91 39.63A65.7 65.7 0 0 0 11.2 140.4a6 6 0 1 0 9.6 7.2A53.58 53.58 0 0 1 64 126a6 6 0 0 0 6-6' /%3E%3C/svg%3E") no-repeat center;
    background-size: contain;
}
[data-testid="stSidebar"] a[href*="show_profile"]::before {
    content: ""; display: inline-block; width: 18px; height: 18px; margin-right: 12px;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'%3E%3Cg fill='none' stroke='%23a9c1d3' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5'%3E%3Cpath d='M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10s10-4.477 10-10S17.523 2 12 2' /%3E%3Cpath d='M4.271 18.346S6.5 15.5 12 15.5s7.73 2.846 7.73 2.846M12 12a3 3 0 1 0 0-6a3 3 0 0 0 0 6' /%3E%3C/g%3E%3C/svg%3E") no-repeat center;
    background-size: contain;
}
[data-testid="stSidebar"] a[href*="show_formulas_info"]::before {
    content: ""; display: inline-block; width: 18px; height: 18px; margin-right: 12px;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 16 16'%3E%3Cpath d='M0 0h16v16H0z' fill='none' /%3E%3Cg fill='%23a9c1d3'%3E%3Cpath d='M8.33 1.225A2.5 2.5 0 0 0 4.81 3.34L4.698 5H3.5a.5.5 0 0 0 0 1h1.132l-.44 6.595a1.5 1.5 0 0 1-2.112 1.268l-.375-.169a.5.5 0 0 0-.41.912l.375.17a2.5 2.5 0 0 0 3.52-2.114L5.634 6H7.5a.5.5 0 1 0 0-1H5.7l.107-1.595A1.5 1.5 0 0 1 7.92 2.137l.376.17a.5.5 0 1 0 .41-.913z' /%3E%3Cpath d='M8.16 8.048a.25.25 0 0 1 .393.053l1.323 2.316l-2.73 2.73a.5.5 0 1 0 .708.707l2.537-2.537l1.188 2.079a1.25 1.25 0 0 0 1.969.263l.306-.305a.5.5 0 0 0-.708-.707l-.305.305a.25.25 0 0 1-.394-.052l-1.323-2.316l2.73-2.73a.5.5 0 1 0-.707-.707l-2.538 2.537l-1.188-2.08a1.25 1.25 0 0 0-1.969-.263l-.306.306a.5.5 0 1 0 .708.707z' /%3E%3C/g%3E%3C/svg%3E") no-repeat center;
    background-size: contain;
}

/* Botón Nueva Solicitud */
.element-container:has(.btn-solicitud-hook) + .element-container button p::before {
    content: ""; display: inline-block; width: 18px; height: 18px; margin-right: 8px; vertical-align: middle;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24'%3E%3Cpath fill='%23a9c1d3' d='M5 21q-.825 0-1.412-.587T3 19V5q0-.825.588-1.412T5 3h8q.425 0 .713.288T14 4t-.288.713T13 5H5v14h14v-8q0-.425.288-.712T20 10t.713.288T21 11v8q0 .825-.587 1.413T19 21zm4-4q-.425 0-.712-.288T8 16t.288-.712T9 15h6q.425 0 .713.288T16 16t-.288.713T15 17zm0-3q-.425 0-.712-.288T8 13t.288-.712T9 12h6q.425 0 .713.288T16 13t-.288.713T15 14zm0-3q-.425 0-.712-.288T8 10t.288-.712T9 9h6q.425 0 .713.288T16 10t-.288.713T15 11zm8.288-2.287Q17 8.425 17 8V7h-1q-.425 0-.712-.288T15 6t.288-.712T16 5h1V4q0-.425.288-.712T18 3t.713.288T19 4v1h1q.425 0 .713.288T21 6t-.288.713T20 7h-1v1q0 .425-.288.713T18 9t-.712-.288' /%3E%3C/svg%3E") no-repeat center;
    background-size: contain;
}
</style>
""", unsafe_allow_html=True)
    


# ═══════════════════════════════════════════════════════════════
#  2. HELPERS UI
# ═══════════════════════════════════════════════════════════════
def _dot_badge(text, bg, fg, dot):
    return (f'<span style="display:inline-flex;align-items:center;gap:5px;background:{bg};'
            f'color:{fg};padding:3px 11px;border-radius:20px;font-size:0.75em;font-weight:700;'
            f'letter-spacing:0.3px;white-space:nowrap">'
            f'<span style="width:6px;height:6px;border-radius:50%;background:{dot};'
            f'display:inline-block;flex-shrink:0"></span>{text}</span>')

def badge(status):
    cfg = {
        'PENDIENTE': ('#FEF3C7','#92400E','#F59E0B'),
        'APROBADO':  ('#D1FAE5','#065F46','#10B981'),
        'RECHAZADO': ('#FEE2E2','#991B1B','#EF4444'),
        'EN MORA':   ('#FFEDD5','#9A3412','#F97316'),
        'AL DÍA':    ('#D1FAE5','#065F46','#10B981'),
    }
    bg, fg, dot = cfg.get(status, ('#F1F5F9','#475569','#94A3B8'))
    return _dot_badge(status, bg, fg, dot)

def aml_badge(nivel):
    cfg = {
        'Bajo':  ('#D1FAE5','#065F46','#10B981'),
        'Medio': ('#FEF3C7','#92400E','#F59E0B'),
        'Alto':  ('#FEE2E2','#991B1B','#EF4444'),
    }
    bg, fg, dot = cfg.get(nivel, ('#F1F5F9','#475569','#94A3B8'))
    return _dot_badge(nivel, bg, fg, dot)

def card_header(icon, title, subtitle=""):
    sub = f'<p style="margin:4px 0 0;color:#64748B;font-size:0.88em">{subtitle}</p>' if subtitle else ""
    return (f'<div style="display:flex;align-items:center;gap:14px;margin-bottom:18px;'
            f'padding-bottom:14px;border-bottom:1px solid #F1F5F9">'
            f'<div style="width:42px;height:42px;background:linear-gradient(135deg,#0B1D4E,#1E3A8A);'
            f'border-radius:10px;display:flex;align-items:center;justify-content:center;'
            f'font-size:1.3em;flex-shrink:0">{icon}</div>'
            f'<div><h3 style="margin:0;color:#0B1D4E;font-size:1.05em;font-weight:700">{title}</h3>{sub}</div>'
            f'</div>')

def kyc_badge(status):
    cfg = {
        'Prospecto':     ('#F1F5F9','#475569','#94A3B8'),
        'KYC Pendiente': ('#FEF3C7','#92400E','#F59E0B'),
        'KYC Aprobado':  ('#D1FAE5','#065F46','#10B981'),
        'Activo':        ('#DBEAFE','#1E40AF','#3B82F6'),
    }
    bg, fg, dot = cfg.get(status, ('#F1F5F9','#475569','#94A3B8'))
    return _dot_badge(status, bg, fg, dot)

def sig_badge(signed):
    if signed:
        return ('<span style="color:#059669;font-weight:800;font-size:1.05em;'
                'background:#D1FAE5;padding:1px 7px;border-radius:6px">✓</span>')
    return ('<span style="color:#DC2626;font-weight:800;font-size:1.05em;'
            'background:#FEE2E2;padding:1px 7px;border-radius:6px">✗</span>')

def page_header(icon, title, subtitle="", breadcrumb=""):
    """Encabezado de página estilo mockup con ícono, título y subtítulo opcional."""
    bc = (f'<div style="font-size:0.75em;color:#94A3B8;font-weight:500;'
          f'letter-spacing:0.04em;margin-bottom:6px">{breadcrumb}</div>') if breadcrumb else ""
    sub = (f'<p style="color:#64748B;font-size:0.9em;margin:4px 0 0;font-weight:400">{subtitle}</p>') if subtitle else ""
    
    # Soporte para iconos del diccionario APP_ICONS
    icon_content = APP_ICONS.get(icon, icon)
    
    st.markdown(
        f'{bc}<div style="display:flex;align-items:center;gap:14px;margin-bottom:20px;'
        f'padding-bottom:16px;border-bottom:2px solid #E2E8F0">'
        f'<div style="width:44px;height:44px;background:linear-gradient(135deg,#0B1D4E,#1E3A8A);'
        f'border-radius:8px;display:flex;align-items:center;justify-content:center;'
        f'font-size:1.4em;flex-shrink:0;box-shadow:0 4px 12px rgba(11,29,78,0.20)">{icon_content}</div>'
        f'<div><h1 style="margin:0;color:#0B1D4E;font-size:1.45em;font-weight:800;'
        f'letter-spacing:-0.02em;border:none!important;padding:0!important">{title}</h1>{sub}</div>'
        f'</div>',
        unsafe_allow_html=True)

def section_divider(label=""):
    """Separador de sección con etiqueta opcional."""
    if label:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;margin:20px 0 14px">'
            f'<div style="height:1px;flex:1;background:#E2E8F0"></div>'
            f'<span style="font-size:0.76em;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:0.08em;color:#94A3B8">{label}</span>'
            f'<div style="height:1px;flex:1;background:#E2E8F0"></div>'
            f'</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="height:1px;background:#E2E8F0;margin:16px 0"></div>',
                    unsafe_allow_html=True)

# Checklists KYC por tipo de cliente
DOCS_NATURAL = [
    "Cédula de Identidad vigente",
    "RIF personal",
    "Comprobante de domicilio (menos de 3 meses)",
    "Constancia de ingresos / Declaración de ISLR",
    "Estado de cuenta bancario (últimos 3 meses)",
    "Referencias bancarias",
    "Declaración jurada de origen de fondos",
]
DOCS_JURIDICA = [
    "RIF de la empresa",
    "Acta Constitutiva y Estatutos Sociales",
    "Última Acta de Asamblea",
    "Poderes notariados del Representante Legal",
    "Cédula de Identidad del Representante Legal",
    "RIF del Representante Legal",
    "Estados financieros auditados (últimos 2 años)",
    "Referencias bancarias",
    "Comprobante de domicilio fiscal (menos de 3 meses)",
    "Declaración jurada de origen de fondos",
]

def paginate_controls(total_items: int, page_size: int = 10, key_prefix: str = "pag") -> int:
    """
    Renderiza los controles de paginación (Anterior / Siguiente) y retorna
    el número de página actual (1-indexed). Utilizar junto con consultas SQL
    paginadas (LIMIT/OFFSET) en los DAOs para paginación real.

    Uso típico:
        total = MyDAO.count(filters)
        page  = paginate_controls(total, page_size=10, key_prefix="my_view")
        df    = MyDAO.get_paginated(page=page, page_size=10, filters=filters)
    """
    import math

    page_key = f"{key_prefix}_current_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1

    total_pages = max(math.ceil(total_items / page_size), 1)

    # Corregir si el dataset se redujo (p.ej. al aplicar un filtro)
    if st.session_state[page_key] > total_pages:
        st.session_state[page_key] = 1

    page = st.session_state[page_key]
    start = (page - 1) * page_size + 1
    end   = min(page * page_size, total_items)

    if total_items == 0:
        st.caption("Sin registros para mostrar.")
        return 1

    # ── Barra de paginación ────────────────────────────
    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
    _, c_prev, c_info, c_next, _ = st.columns([1.5, 1.5, 2, 1.5, 1.5])

    with c_prev:
        if st.button("← Anterior", key=f"{key_prefix}_prev",
                     use_container_width=True, disabled=(page <= 1)):
            st.session_state[page_key] -= 1
            st.rerun()

    with c_info:
        st.markdown(
            f"<div style='text-align:center;padding-top:8px;color:#64748B;"
            f"font-size:0.88em'>"
            f"<strong>{start} – {end}</strong> de <strong>{total_items}</strong> "
            f"&nbsp;·&nbsp; Pág <strong>{page}</strong> / {total_pages}</div>",
            unsafe_allow_html=True)

    with c_next:
        if st.button("Siguiente →", key=f"{key_prefix}_next",
                     use_container_width=True, disabled=(page >= total_pages)):
            st.session_state[page_key] += 1
            st.rerun()

    return page


def paginate_dataframe(df, page_size: int = 10, key_prefix: str = "pag"):
    """
    Wrapper de compatibilidad: pagina un DataFrame ya cargado en memoria.
    Para nuevas vistas, usar paginate_controls() + DAOs paginados en su lugar.
    """
    import math
    total_items = len(df)
    if total_items == 0:
        return df

    page = paginate_controls(total_items, page_size=page_size, key_prefix=key_prefix)
    start_idx = (page - 1) * page_size
    end_idx   = start_idx + page_size
    return df.iloc[start_idx:end_idx] if hasattr(df, 'iloc') else df[start_idx:end_idx]


