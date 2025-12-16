import streamlit as st
from openai import OpenAI
from duckduckgo_search import DDGS # pip install duckduckgo-search 필요
import base64

# ==========================================
# 1. 설정 및 API 연결
# ==========================================
st.set_page_config(page_title="TrippyAI", page_icon="✈️")
st.title("✈️ TrippyAI: 안전한 여행의 기록")

api_key = st.sidebar.text_input("Together AI API Key", type="password")

if not api_key:
    st.info("API 키를 입력하면 모든 기능이 활성화됩니다.")
    st.stop()

client = OpenAI(api_key=api_key, base_url="https://api.together.xyz/v1")

# ==========================================
# 2. [기능] 안전 정보 검색 (AI Agent)
# ==========================================
def get_safety_alert(location):
    """실시간 뉴스를 검색해서 안전 정보를 가져옵니다."""
    try:
        with DDGS() as ddgs:
            # 영어로 검색해야 정보가 더 많음
            keywords = f"{location} travel safety news"
            results = list(ddgs.text(keywords, max_results=3))
            if results:
                summary = " | ".join([r['title'] for r in results])
                return summary
            return "특별한 뉴스 없음"
    except:
        return "검색 연결 실패"

# ==========================================
# 3. 화면 UI 구성
# ==========================================
col1, col2 = st.columns(2)

with col1:
    location = st.text_input("📍 현재 위치", "Paris, France")
    # 날씨는 API 키가 필요해서 일단 임시 버튼으로 대체
    if st.button("🌦️ 날씨 확인"):
        st.info("☁️ 18°C, 흐림 (OpenWeatherMap 연동 예정)")

with col2:
    st.write("🛡️ **안전 모니터링**")
    safety_status = st.empty() # 빈 공간 확보
    if st.button("🚨 주변 위험요소 스캔"):
        with st.spinner("현지 뉴스 검색 중..."):
            news_summary = get_safety_alert(location)
            # LLM에게 판단 시키기
            prompt = f"다음 뉴스 제목들을 보고 여행자에게 위험한 상황인지 한 문장으로 요약해: {news_summary}"
            response = client.chat.completions.create(
                model="Qwen/Qwen2.5-72B-Instruct-Turbo",
                messages=[{"role": "user", "content": prompt}]
            )
            st.warning(f"AI 분석 결과: {response.choices[0].message.content}")

st.markdown("---")

# ==========================================
# 4. [기능] 영수증 인식 (Vision AI)
# ==========================================
st.header("🧾 영수증 정리 & 여행기 작성")

uploaded_file = st.file_uploader("영수증이나 여행 사진을 올려주세요", type=['png', 'jpg', 'jpeg'])
receipt_text = ""

if uploaded_file is not None:
    st.image(uploaded_file, caption="업로드된 사진", width=200)
    # 실제로는 여기서 이미지를 base64로 변환해서 Vision 모델에 보내야 함
    # 지금은 텍스트 입력으로 대체 (Vision 코드 추가 가능)
    st.success("📸 사진 인식 완료! (Vision 모델 연결 대기 중)")
    receipt_text = "크루아상 2개 10유로, 커피 5유로" # 가짜 데이터

# ==========================================
# 5. 여행기 생성
# ==========================================
if st.button("📝 여행기 자동 생성"):
    final_prompt = f"""
    위치: {location}
    안전이슈: {get_safety_alert(location)}
    영수증 내역: {receipt_text}
    
    위 정보를 바탕으로 감성적인 여행 일기를 써줘.
    특히 안전 이슈에 대해 여행자가 안심할 수 있는 멘트를 포함해줘.
    """
    
    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-72B-Instruct-Turbo",
        messages=[{"role": "user", "content": final_prompt}]
    )
    st.markdown(response.choices[0].message.content)
