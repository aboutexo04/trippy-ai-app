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

# ==========================================
# 5. [기능] 사진 EXIF 메타데이터 추출
# ==========================================
def get_exif_data(image_file):
    """사진에서 EXIF 메타데이터(날짜, GPS 등)를 추출합니다."""
    try:
        img = Image.open(image_file)
        exif_data = img._getexif()
        
        result = {
            "datetime": None,
            "gps_lat": None,
            "gps_lon": None
        }
        
        if not exif_data:
            return result
        
        # EXIF 태그 번호
        # 36867: DateTimeOriginal, 34853: GPSInfo
        from PIL.ExifTags import TAGS, GPSTAGS
        
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            
            # 촬영 날짜/시간
            if tag == "DateTimeOriginal":
                result["datetime"] = value
            
            # GPS 정보
            if tag == "GPSInfo":
                gps_info = {}
                for gps_tag_id, gps_value in value.items():
                    gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                    gps_info[gps_tag] = gps_value
                
                # 위도 계산
                if "GPSLatitude" in gps_info and "GPSLatitudeRef" in gps_info:
                    lat = gps_info["GPSLatitude"]
                    lat_ref = gps_info["GPSLatitudeRef"]
                    lat_decimal = lat[0] + lat[1]/60 + lat[2]/3600
                    if lat_ref == "S":
                        lat_decimal = -lat_decimal
                    result["gps_lat"] = lat_decimal
                
                # 경도 계산
                if "GPSLongitude" in gps_info and "GPSLongitudeRef" in gps_info:
                    lon = gps_info["GPSLongitude"]
                    lon_ref = gps_info["GPSLongitudeRef"]
                    lon_decimal = lon[0] + lon[1]/60 + lon[2]/3600
                    if lon_ref == "W":
                        lon_decimal = -lon_decimal
                    result["gps_lon"] = lon_decimal
        
        return result
    except Exception as e:
        return {"datetime": None, "gps_lat": None, "gps_lon": None}

def get_location_name(lat, lon):
    """GPS 좌표를 장소명으로 변환합니다 (역지오코딩)."""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 18,
            "addressdetails": 1
        }
        headers = {"User-Agent": "TrippyAI/1.0"}
        
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        if "address" in data:
            addr = data["address"]
            # 장소명 조합
            parts = []
            for key in ["amenity", "shop", "tourism", "road", "neighbourhood", "suburb", "city", "country"]:
                if key in addr:
                    parts.append(addr[key])
                    if len(parts) >= 3:
                        break
            return ", ".join(parts) if parts else data.get("display_name", "알 수 없는 장소")
        
        return "알 수 없는 장소"
    except:
        return "장소 정보 없음"

def generate_photo_description(client, caption, datetime_str, location_name, user_location):
    """AI가 사진 설명을 풍부하게 만들어줍니다."""
    prompt = f"""다음 정보로 여행 사진에 대한 짧고 감성적인 설명을 한 문장으로 작성해줘:

여행지: {user_location}
촬영 시간: {datetime_str or "정보 없음"}
촬영 장소: {location_name or "정보 없음"}
사용자 메모: {caption or "없음"}

예시: "파리의 따스한 오후, 에펠탑 앞에서 커피 한 잔의 여유를 즐겼다."

한 문장으로만 답변해."""

    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-72B-Instruct-Turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,  # 창의성 낮춤
        max_tokens=100
    )
    return response.choices[0].message.content.strip()

def analyze_receipt_text(client, ocr_text):
    """AI가 OCR 텍스트에서 메뉴, 금액, 날짜, 시간을 추출합니다."""
    prompt = f"""다음은 영수증 OCR 결과야:

{ocr_text}

위 영수증에서 정보를 추출해줘.

중요:
- 메뉴/상품 이름을 그대로 적어줘 (여러 단어면 합쳐서)
- 총 금액은 "합계" 또는 "총액" 찾아
- 날짜는 YYYY-MM-DD 또는 YY.MM.DD 형식 찾아
- 시간은 HH:MM 형식 찾아

반드시 다음 형식으로만 답변해:
메뉴: [메뉴 이름]
금액: [총 금액]
날짜: [날짜 또는 "없음"]
시간: [시간 또는 "없음"]"""

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
    if "ocr_date" not in st.session_state:
        st.session_state.ocr_date = ""
    if "ocr_time" not in st.session_state:
        st.session_state.ocr_time = ""
    
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
                            elif "날짜:" in line or "날짜 :" in line:
                                date_val = line.split(":", 1)[-1].strip()
                                st.session_state.ocr_date = "" if date_val == "없음" else date_val
                            elif "시간:" in line or "시간 :" in line:
                                time_val = line.split(":", 1)[-1].strip()
                                st.session_state.ocr_time = "" if time_val == "없음" else time_val
                        
                        st.rerun()
                except Exception as e:
                    st.error(f"인식 실패: {e}")
    
    col_a, col_b = st.columns(2)
    with col_a:
        receipt_desc = st.text_input("메뉴/항목", value=st.session_state.ocr_menu, placeholder="예: 크루아상, 커피")
    with col_b:
        receipt_amount = st.text_input("금액", value=st.session_state.ocr_amount, placeholder="예: 15유로")
    
    col_c, col_d = st.columns(2)
    with col_c:
        receipt_date = st.text_input("📅 날짜", value=st.session_state.ocr_date, placeholder="예: 2024-12-15", key="receipt_date_input")
    with col_d:
        receipt_time = st.text_input("🕐 시간", value=st.session_state.ocr_time, placeholder="예: 저녁 7시", key="receipt_time_input")
    
    if st.button("➕ 영수증 추가", key="add_receipt"):
        if receipt_file and receipt_desc:
            st.session_state.receipts.append({
                "image": receipt_file,
                "text": receipt_desc,
                "amount": receipt_amount,
                "date": receipt_date,
                "time": receipt_time
            })
            # OCR 결과 초기화
            st.session_state.ocr_menu = ""
            st.session_state.ocr_amount = ""
            st.session_state.ocr_date = ""
            st.session_state.ocr_time = ""
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
                    if r.get('date') or r.get('time'):
                        st.caption(f"📅 {r.get('date', '')} {r.get('time', '')}")
                with col3:
                    if st.button("🗑️", key=f"del_receipt_{i}"):
                        st.session_state.receipts.pop(i)
                        st.rerun()

# ========== 탭2: 여행 사진 ==========
with tab2:
    st.subheader("여행 사진 추가")
    photo_file = st.file_uploader("여행 사진을 올려주세요", type=['png', 'jpg', 'jpeg'], key="photo")
    
    # EXIF 데이터 저장용
    if "photo_datetime" not in st.session_state:
        st.session_state.photo_datetime = ""
    if "photo_location" not in st.session_state:
        st.session_state.photo_location = ""
    if "photo_ai_caption" not in st.session_state:
        st.session_state.photo_ai_caption = ""
    
    if photo_file:
        st.image(photo_file, caption="업로드된 사진", width=300)
        
        # EXIF 자동 추출 버튼
        if st.button("🔍 사진 정보 자동 추출", key="extract_exif"):
            with st.spinner("사진 정보 분석 중..."):
                exif = get_exif_data(photo_file)
                
                # 날짜/시간
                if exif["datetime"]:
                    st.session_state.photo_datetime = exif["datetime"]
                    st.success(f"📅 촬영 시간: {exif['datetime']}")
                else:
                    st.session_state.photo_datetime = ""
                    st.info("📅 촬영 시간 정보가 없습니다.")
                
                # GPS → 장소명
                if exif["gps_lat"] and exif["gps_lon"]:
                    location_name = get_location_name(exif["gps_lat"], exif["gps_lon"])
                    st.session_state.photo_location = location_name
                    st.success(f"📍 촬영 장소: {location_name}")
                else:
                    st.session_state.photo_location = ""
                    st.info("📍 위치 정보가 없습니다. (위치 서비스 꺼진 상태로 촬영)")
    
    # 입력 필드
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        photo_datetime = st.text_input("📅 촬영 날짜/시간", value=st.session_state.photo_datetime, placeholder="예: 2024-12-16 14:30")
    with col_p2:
        photo_location_input = st.text_input("📍 촬영 장소", value=st.session_state.photo_location, placeholder="예: 에펠탑, 파리")
    
    photo_memo = st.text_input("✍️ 간단 메모 (선택)", placeholder="예: 점심 먹고 산책하다가")
    
    # AI 설명 생성
    if photo_file and st.button("✨ AI 설명 생성", key="generate_caption"):
        with st.spinner("AI가 설명 작성 중..."):
            ai_caption = generate_photo_description(
                client, 
                photo_memo, 
                photo_datetime, 
                photo_location_input, 
                location
            )
            st.session_state.photo_ai_caption = ai_caption
            st.success(f"**AI 설명:** {ai_caption}")
    
    # 최종 설명
    final_caption = st.text_area(
        "📝 최종 설명", 
        value=st.session_state.photo_ai_caption or photo_memo or "여행 사진",
        height=80
    )
    
    if st.button("➕ 사진 추가", key="add_photo"):
        if photo_file:
            st.session_state.photos.append({
                "image": photo_file,
                "caption": final_caption,
                "datetime": photo_datetime,
                "location": photo_location_input
            })
            # 초기화
            st.session_state.photo_datetime = ""
            st.session_state.photo_location = ""
            st.session_state.photo_ai_caption = ""
            st.success("✅ 사진이 추가되었습니다!")
            st.rerun()
    
    # 저장된 사진 목록
    if st.session_state.photos:
        st.markdown("---")
        st.subheader(f"📸 저장된 사진 ({len(st.session_state.photos)}장)")
        for i, p in enumerate(st.session_state.photos):
            with st.container():
                col_img, col_info = st.columns([1, 2])
                with col_img:
                    st.image(p["image"], use_container_width=True)
                with col_info:
                    st.write(f"**{p['caption']}**")
                    if p.get("datetime"):
                        st.caption(f"📅 {p['datetime']}")
                    if p.get("location"):
                        st.caption(f"📍 {p['location']}")
                    if st.button("🗑️ 삭제", key=f"del_photo_{i}"):
                        st.session_state.photos.pop(i)
                        st.rerun()
            st.markdown("---")

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
                # 데이터 정리 (날짜/장소 포함)
                photo_details = []
                for p in st.session_state.photos:
                    detail = f"- 설명: {p['caption']}"
                    if p.get('datetime'):
                        detail += f", 시간: {p['datetime']}"
                    if p.get('location'):
                        detail += f", 장소: {p['location']}"
                    photo_details.append(detail)
                
                # 영수증 정보 (날짜/시간 포함)
                receipt_details = []
                for r in st.session_state.receipts:
                    detail = f"- {r['text']}: {r['amount']}"
                    if r.get('date') or r.get('time'):
                        detail += f" ({r.get('date', '')} {r.get('time', '')})"
                    receipt_details.append(detail)
                
                final_prompt = f"""
                여행지: {location}
                
                여행 사진 기록들:
                {chr(10).join(photo_details) if photo_details else "없음"}
                
                지출 내역 (날짜/시간 포함):
                {chr(10).join(receipt_details) if receipt_details else "없음"}
                
                위 정보로 짧은 여행 일기를 작성해줘.
                - 3-5문장으로 간결하게
                - 시간/장소/지출을 자연스럽게 포함
                - 과장 없이 사실 위주로
                """
                
                response = client.chat.completions.create(
                    model="Qwen/Qwen2.5-72B-Instruct-Turbo",
                    messages=[{"role": "user", "content": final_prompt}],
                    temperature=0.5,  # 창의성 낮춤 (기본값 1.0)
                    max_tokens=300    # 길이 제한
                )
                
                # 결과 표시
                st.markdown("---")
                st.subheader("✨ 나의 여행 이야기")
                
                # 사진과 함께 여행기 표시
                for p in st.session_state.photos:
                    col_photo, col_desc = st.columns([1, 2])
                    with col_photo:
                        st.image(p["image"], use_container_width=True)
                    with col_desc:
                        st.write(f"**{p['caption']}**")
                        if p.get('datetime'):
                            st.caption(f"📅 {p['datetime']}")
                        if p.get('location'):
                            st.caption(f"📍 {p['location']}")
                    st.markdown("")
                
                st.markdown("---")
                st.markdown(response.choices[0].message.content)
                
                # 지출 요약
                if st.session_state.receipts:
                    st.markdown("---")
                    st.subheader("💰 지출 요약")
                    for r in st.session_state.receipts:
                        date_info = ""
                        if r.get('date') or r.get('time'):
                            date_info = f" ({r.get('date', '')} {r.get('time', '')})"
                        st.write(f"• {r['text']}: **{r['amount']}**{date_info}")
    
    # 초기화 버튼
    if st.session_state.photos or st.session_state.receipts:
        st.markdown("---")
        if st.button("🗑️ 모두 초기화", key="reset_all"):
            st.session_state.photos = []
            st.session_state.receipts = []
            st.rerun()
