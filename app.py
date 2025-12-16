import streamlit as st
from openai import OpenAI
from duckduckgo_search import DDGS
import requests

# ==========================================
# 1. 설정 및 API 연결 (st.set_page_config는 반드시 첫 번째!)
# ==========================================
st.set_page_config(page_title="TrippyAI", page_icon="✈️")
st.title("✈️ TrippyAI: 안전한 여행의 기록")

# API 키 불러오기 (secrets.toml에서)
try:
    together_api_key = st.secrets["TOGETHER_API_KEY"]
    weather_api_key = st.secrets["OPENWEATHER_API_KEY"]
except Exception as e:
    st.error(f"⚠️ `.streamlit/secrets.toml` 파일을 확인해주세요: {e}")
    st.code('TOGETHER_API_KEY = "your-api-key-here"\nOPENWEATHER_API_KEY = "your-key"', language="toml")
    st.stop()

# 클라이언트 설정
client = OpenAI(api_key=together_api_key, base_url="https://api.together.xyz/v1")

# ==========================================
# 2. [기능] 날씨 API
# ==========================================
def get_weather_from_api(city, weather_key):
    """OpenWeatherMap API를 통해 정확한 날씨를 가져옵니다."""
    if not weather_key:
        return "날씨 API 키가 없습니다."
    
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": weather_key,
        "units": "metric",
        "lang": "kr"
    }
    
    try:
        response = requests.get(base_url, params=params)
        data = response.json()
        
        if response.status_code == 200:
            temp = data['main']['temp']
            desc = data['weather'][0]['description']
            hum = data['main']['humidity']
            return f"{temp}°C, {desc} (습도 {hum}%)"
        else:
            return f"에러: {data.get('message', '알 수 없는 오류')}"
            
    except Exception as e:
        return f"통신 에러: {e}"

# ==========================================
# 3. [기능] 안전 정보 검색 (뉴스 기반)
# ==========================================
def get_safety_news(location):
    """실시간 뉴스를 검색해서 안전 정보를 가져옵니다."""
    try:
        with DDGS() as ddgs:
            keywords = f"{location} travel safety"
            # 뉴스 전용 검색 (최근 1개월 이내만)
            results = list(ddgs.news(keywords, max_results=5, timelimit="m"))
            return results if results else []
    except:
        return []

def analyze_safety_with_ai(client, location, news_results):
    """AI가 뉴스 기반 안전 분석을 제공합니다."""
    news_titles = " | ".join([r.get('title', '') for r in news_results]) if news_results else "관련 뉴스 없음"
    
    prompt = f"""
    여행지: {location}
    최근 뉴스: {news_titles}
    
    위 뉴스를 보고 여행자에게 2-3문장으로 간단히 안전 상황을 알려줘.
    위험하면 주의사항도 짧게 추가해.
    """
    
    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-72B-Instruct-Turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ==========================================
# 4. 화면 UI 구성
# ==========================================
col1, col2 = st.columns(2)

with col1:
    location = st.text_input("📍 현재 위치", "Paris, France")
    if st.button("🌦️ 날씨 확인"):
        with st.spinner("날씨 정보 가져오는 중..."):
            weather_info = get_weather_from_api(location, weather_api_key)
            st.info(f"☁️ {weather_info}")

with col2:
    st.write("🛡️ **안전 모니터링**")
    if st.button("🚨 안전 이슈 확인"):
        with st.spinner("관련 뉴스 검색 중..."):
            # 실시간 뉴스 검색
            news_results = get_safety_news(location)
            
            # AI 분석
            ai_analysis = analyze_safety_with_ai(client, location, news_results)
        
        # 결과 표시
        st.subheader("📋 안전 브리핑")
        
        # AI 분석 결과
        st.success(f"**🤖 AI 안전 분석**\n\n{ai_analysis}")
        
        # 뉴스 링크
        if news_results:
            with st.expander("📰 관련 뉴스 보기"):
                for news in news_results[:5]:
                    title = news.get('title', 'No title')
                    url = news.get('url', '#')
                    date = news.get('date', '')
                    source = news.get('source', '')
                    st.markdown(f"- [{title}]({url})")
                    if date or source:
                        st.caption(f"   {source} • {date[:10] if date else ''}")
        else:
            st.info("관련 뉴스를 찾지 못했습니다.")

st.markdown("---")

# ==========================================
# 5. [기능] 영수증 인식 (Vision AI)
# ==========================================
st.header("🧾 영수증 정리 & 여행기 작성")

uploaded_file = st.file_uploader("영수증이나 여행 사진을 올려주세요", type=['png', 'jpg', 'jpeg'])
receipt_text = ""

if uploaded_file is not None:
    st.image(uploaded_file, caption="업로드된 사진", width=200)
    st.success("📸 사진 인식 완료! (Vision 모델 연결 대기 중)")
    receipt_text = "크루아상 2개 10유로, 커피 5유로"  # 가짜 데이터

# ==========================================
# 6. 여행기 생성
# ==========================================
if st.button("📝 여행기 자동 생성"):
    with st.spinner("여행기 작성 중..."):
        # 뉴스 정보 가져오기
        news_results = get_safety_news(location)
        news_summary = " | ".join([r.get('title', '') for r in news_results[:3]]) if news_results else "특별한 이슈 없음"
        
        final_prompt = f"""
        위치: {location}
        현지 뉴스: {news_summary}
        영수증 내역: {receipt_text}
        
        위 정보를 바탕으로 감성적인 여행 일기를 써줘.
        특히 안전 이슈에 대해 여행자가 안심할 수 있는 멘트를 포함해줘.
        """
        
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct-Turbo",
            messages=[{"role": "user", "content": final_prompt}]
        )
        st.markdown(response.choices[0].message.content)
