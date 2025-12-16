import streamlit as st
from openai import OpenAI
from duckduckgo_search import DDGS
import requests
import base64
from PIL import Image
import io
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
# 4. [기능] 영수증 OCR (OCR.space API)
# ==========================================
def compress_image(uploaded_file, max_size_kb=900):
    """이미지를 압축해서 최대 크기 이하로 만듭니다."""
    img = Image.open(uploaded_file)
    
    # RGBA를 RGB로 변환 (JPEG는 알파 채널 지원 안함)
    if img.mode == 'RGBA':
        img = img.convert('RGB')
    
    # 초기 품질
    quality = 85
    output = io.BytesIO()
    
    while quality > 10:
        output.seek(0)
        output.truncate()
        img.save(output, format='JPEG', quality=quality)
        size_kb = len(output.getvalue()) / 1024
        
        if size_kb <= max_size_kb:
            break
        
        # 이미지 크기도 줄이기
        if size_kb > max_size_kb * 2:
            img = img.resize((int(img.width * 0.7), int(img.height * 0.7)), Image.Resampling.LANCZOS)
        
        quality -= 10
    
    output.seek(0)
    return output.getvalue()

def image_to_base64(uploaded_file, compress=True):
    """업로드된 이미지를 base64로 변환합니다."""
    if compress:
        bytes_data = compress_image(uploaded_file)
    else:
        bytes_data = uploaded_file.getvalue()
    return base64.b64encode(bytes_data).decode("utf-8")

def extract_receipt_with_ocr(image_file):
    """OCR.space API를 사용해 영수증 텍스트를 추출합니다."""
    
    # OCR.space API 키 (secrets.toml에서 가져오기)
    try:
        ocr_api_key = st.secrets["OCR_API_KEY"]
    except:
        return None, "OCR API 키가 없습니다. secrets.toml에 OCR_API_KEY를 추가해주세요."
    
    base64_image = image_to_base64(image_file)
    
    # OCR.space API 호출
    url = "https://api.ocr.space/parse/image"
    payload = {
        "base64Image": f"data:image/jpeg;base64,{base64_image}",
        "language": "kor",  # 한국어
        "isOverlayRequired": False,
        "detectOrientation": True,
        "scale": True,
        "OCREngine": 2  # 더 정확한 엔진
    }
    headers = {
        "apikey": ocr_api_key
    }
    
    try:
        response = requests.post(url, data=payload, headers=headers)
        result = response.json()
        
        if result.get("IsErroredOnProcessing"):
            return None, result.get("ErrorMessage", "OCR 처리 실패")
        
        # 텍스트 추출
        parsed_results = result.get("ParsedResults", [])
        if parsed_results:
            ocr_text = parsed_results[0].get("ParsedText", "")
            return ocr_text, None
        
        return None, "텍스트를 인식하지 못했습니다."
    except Exception as e:
        return None, f"API 호출 실패: {e}"

def analyze_receipt_text(client, ocr_text):
    """AI가 OCR 텍스트에서 메뉴와 금액을 추출합니다."""
    prompt = f"""다음은 영수증 OCR 결과야:

{ocr_text}

위 영수증에서 주문한 음식/상품 이름과 총 금액을 찾아줘.

중요:
- 영수증에서 실제 주문한 메뉴/상품 이름을 그대로 적어줘
- 한 메뉴가 여러 단어로 되어있으면 그대로 합쳐서 적어 (예: "대우 해산물 볶음쌀국수"는 하나의 메뉴명)
- 수량, 가격이 아닌 메뉴 이름만 추출해
- 총 금액은 "합계" 또는 "총액" 옆의 숫자를 찾아

형식:
메뉴: [메뉴 이름]
금액: [총 금액]"""

    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-72B-Instruct-Turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
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
# 5. [기능] 영수증 & 여행 사진 & 종합 여행기 (탭 3개)
# ==========================================

# Session State 초기화 (데이터 저장용)
if "receipts" not in st.session_state:
    st.session_state.receipts = []  # [{image, text, amount}]
if "photos" not in st.session_state:
    st.session_state.photos = []    # [{image, caption}]

tab1, tab2, tab3 = st.tabs(["🧾 영수증 정리", "📸 여행 사진", "📖 종합 여행기"])

# ========== 탭1: 영수증 ==========
with tab1:
    st.subheader("영수증 추가")
    receipt_file = st.file_uploader("영수증 사진을 올려주세요", type=['png', 'jpg', 'jpeg'], key="receipt")
    
    # OCR 인식 결과 저장용
    if "ocr_menu" not in st.session_state:
        st.session_state.ocr_menu = ""
    if "ocr_amount" not in st.session_state:
        st.session_state.ocr_amount = ""
    
    # AI 인식 버튼
    if receipt_file:
        st.image(receipt_file, caption="업로드된 영수증", width=250)
        
        if st.button("🤖 AI로 자동 인식", key="ocr_receipt"):
            with st.spinner("영수증 분석 중..."):
                try:
                    # 1단계: OCR로 텍스트 추출
                    ocr_text, error = extract_receipt_with_ocr(receipt_file)
                    
                    if error:
                        st.error(f"OCR 실패: {error}")
                    elif ocr_text:
                        with st.expander("📝 OCR 원본 텍스트"):
                            st.text(ocr_text)
                        
                        # 2단계: AI로 메뉴/금액 추출
                        with st.spinner("AI 분석 중..."):
                            ai_result = analyze_receipt_text(client, ocr_text)
                            st.info(f"**인식 결과:**\n{ai_result}")
                        
                        # 결과 파싱
                        lines = ai_result.strip().split("\n")
                        for line in lines:
                            if "메뉴:" in line or "메뉴 :" in line:
                                st.session_state.ocr_menu = line.split(":", 1)[-1].strip()
                            elif "금액:" in line or "금액 :" in line:
                                st.session_state.ocr_amount = line.split(":", 1)[-1].strip()
                        
                        st.rerun()
                except Exception as e:
                    st.error(f"인식 실패: {e}")
    
    col_a, col_b = st.columns(2)
    with col_a:
        receipt_desc = st.text_input("메뉴/항목", value=st.session_state.ocr_menu, placeholder="예: 크루아상, 커피")
    with col_b:
        receipt_amount = st.text_input("금액", value=st.session_state.ocr_amount, placeholder="예: 15유로")
    
    if st.button("➕ 영수증 추가", key="add_receipt"):
        if receipt_file and receipt_desc:
            st.session_state.receipts.append({
                "image": receipt_file,
                "text": receipt_desc,
                "amount": receipt_amount
            })
            # OCR 결과 초기화
            st.session_state.ocr_menu = ""
            st.session_state.ocr_amount = ""
            st.success("✅ 영수증이 추가되었습니다!")
            st.rerun()
    
    # 저장된 영수증 목록
    if st.session_state.receipts:
        st.markdown("---")
        st.subheader(f"💰 저장된 영수증 ({len(st.session_state.receipts)}건)")
        for i, r in enumerate(st.session_state.receipts):
            with st.container():
                col1, col2, col3 = st.columns([1, 2, 1])
                with col1:
                    st.image(r["image"], width=80)
                with col2:
                    st.write(f"**{r['text']}**")
                    st.caption(f"💵 {r['amount']}")
                with col3:
                    if st.button("🗑️", key=f"del_receipt_{i}"):
                        st.session_state.receipts.pop(i)
                        st.rerun()

# ========== 탭2: 여행 사진 ==========
with tab2:
    st.subheader("여행 사진 추가")
    photo_file = st.file_uploader("여행 사진을 올려주세요", type=['png', 'jpg', 'jpeg'], key="photo")
    photo_caption = st.text_input("사진 설명", placeholder="예: 에펠탑 앞에서 인증샷!")
    
    if st.button("➕ 사진 추가", key="add_photo"):
        if photo_file:
            st.session_state.photos.append({
                "image": photo_file,
                "caption": photo_caption or "여행 사진"
            })
            st.success("✅ 사진이 추가되었습니다!")
            st.rerun()
    
    # 저장된 사진 목록
    if st.session_state.photos:
        st.markdown("---")
        st.subheader(f"📸 저장된 사진 ({len(st.session_state.photos)}장)")
        cols = st.columns(3)
        for i, p in enumerate(st.session_state.photos):
            with cols[i % 3]:
                st.image(p["image"], caption=p["caption"], use_container_width=True)
                if st.button("🗑️", key=f"del_photo_{i}"):
                    st.session_state.photos.pop(i)
                    st.rerun()

# ========== 탭3: 종합 여행기 ==========
with tab3:
    st.subheader("📖 나의 여행기")
    
    # 현재 저장된 데이터 요약
    st.info(f"📍 **{location}** | 📸 사진 {len(st.session_state.photos)}장 | 🧾 영수증 {len(st.session_state.receipts)}건")
    
    if st.button("✨ 종합 여행기 생성", key="generate_final", type="primary"):
        if not st.session_state.photos and not st.session_state.receipts:
            st.warning("사진이나 영수증을 먼저 추가해주세요!")
        else:
            with st.spinner("여행기 작성 중..."):
                # 데이터 정리
                photo_list = [f"- {p['caption']}" for p in st.session_state.photos]
                receipt_list = [f"- {r['text']}: {r['amount']}" for r in st.session_state.receipts]
                
                total_spending = ", ".join([f"{r['text']} {r['amount']}" for r in st.session_state.receipts])
                
                final_prompt = f"""
                여행지: {location}
                
                여행 사진들:
                {chr(10).join(photo_list) if photo_list else "없음"}
                
                지출 내역:
                {chr(10).join(receipt_list) if receipt_list else "없음"}
                
                위 정보를 바탕으로 감성적인 여행 일기를 작성해줘.
                각 사진에 대한 짧은 설명과 함께, 지출 내역도 자연스럽게 포함해줘.
                마지막에 총 지출 요약도 넣어줘.
                """
                
                response = client.chat.completions.create(
                    model="Qwen/Qwen2.5-72B-Instruct-Turbo",
                    messages=[{"role": "user", "content": final_prompt}]
                )
                
                # 결과 표시
                st.markdown("---")
                
                # 사진과 함께 여행기 표시
                for p in st.session_state.photos:
                    st.image(p["image"], caption=p["caption"], width=400)
                
                st.markdown(response.choices[0].message.content)
                
                # 지출 요약
                if st.session_state.receipts:
                    st.markdown("---")
                    st.subheader("💰 지출 요약")
                    for r in st.session_state.receipts:
                        st.write(f"• {r['text']}: **{r['amount']}**")
    
    # 초기화 버튼
    if st.session_state.photos or st.session_state.receipts:
        st.markdown("---")
        if st.button("🗑️ 모두 초기화", key="reset_all"):
            st.session_state.photos = []
            st.session_state.receipts = []
            st.rerun()
