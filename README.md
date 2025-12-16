# ✈️ TrippyAI - 안전한 여행의 기록

> AI 기반 스마트 여행 기록 앱 - 영수증 OCR, 사진 메타데이터 추출, 안전 정보 분석까지

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

<img width="741" height="436" alt="image" src="https://github.com/user-attachments/assets/5d642701-3c93-4026-9ced-54f3e392f0f1" />

## 📋 프로젝트 소개

TrippyAI는 여행자를 위한 올인원 AI 어시스턴트입니다. 여행 중 영수증을 촬영하면 자동으로 지출을 정리하고, 사진의 시간/장소 정보를 추출하여 감성적인 여행기를 자동 생성합니다.

### ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 🧾 **영수증 OCR** | 영수증 사진에서 메뉴, 금액, 날짜/시간 자동 인식 |
| 📸 **사진 메타데이터 추출** | EXIF에서 촬영 날짜/시간, GPS 좌표 자동 추출 |
| 📍 **역지오코딩** | GPS 좌표를 실제 장소명으로 변환 |
| 🛡️ **안전 정보 분석** | 실시간 뉴스 기반 여행지 안전 분석 |
| 🌦️ **날씨 정보** | 현재 위치의 실시간 날씨 제공 |
| 📖 **AI 여행기 생성** | 사진과 영수증을 종합하여 여행 일기 자동 작성 |

## 🛠️ 기술 스택

- **Frontend**: Streamlit
- **AI/LLM**: Together AI (Qwen2.5-72B)
- **OCR**: OCR.space API
- **날씨**: OpenWeatherMap API
- **뉴스 검색**: DuckDuckGo Search
- **이미지 처리**: Pillow

## 🚀 설치 및 실행

### 1. 저장소 클론

```bash
git clone https://github.com/yourusername/trippy-ai-app.git
cd trippy-ai-app
```

### 2. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. API 키 설정

`.streamlit/secrets.toml` 파일을 생성하고 다음 내용을 추가하세요:

```toml
TOGETHER_API_KEY = "your-together-ai-key"
OPENWEATHER_API_KEY = "your-openweather-key"
OCR_API_KEY = "your-ocr-space-key"
```

**API 키 발급:**
- [Together AI](https://api.together.xyz/) - LLM 모델 사용
- [OpenWeatherMap](https://openweathermap.org/api) - 날씨 정보
- [OCR.space](https://ocr.space/ocrapi/freekey) - 영수증 OCR (무료)

### 5. 앱 실행

```bash
streamlit run app.py
```

## 📱 사용 방법

### 1️⃣ 안전 정보 확인
- 여행지 입력 후 "안전 이슈 확인" 클릭
- 실시간 뉴스 기반 AI 안전 분석 제공

### 2️⃣ 영수증 등록
- 영수증 사진 업로드
- "AI로 자동 인식" 클릭
- 메뉴, 금액, 날짜/시간 자동 추출

### 3️⃣ 여행 사진 등록
- 사진 업로드
- "사진 정보 자동 추출" 클릭 (EXIF 메타데이터)
- "AI 설명 생성"으로 감성적인 설명 작성

### 4️⃣ 종합 여행기 생성
- 사진과 영수증 정보를 종합
- AI가 시간순으로 여행 일기 작성

## 📁 프로젝트 구조

```
trippy-ai-app/
├── app.py                 # 메인 애플리케이션
├── requirements.txt       # 패키지 의존성
├── README.md             # 프로젝트 문서
├── LICENSE               # MIT 라이선스
├── .gitignore            # Git 제외 파일
└── .streamlit/
    └── secrets.toml      # API 키 설정 (git 제외)
```

## 🔒 보안 주의사항

- `secrets.toml` 파일은 절대 GitHub에 업로드하지 마세요
- `.gitignore`에 이미 포함되어 있습니다
- API 키가 노출되었다면 즉시 재발급 받으세요

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 📞 문의

프로젝트에 대한 문의사항이 있으시면 Issue를 등록해주세요.

---

<p align="center">
  Made with ❤️ for travelers
</p>

