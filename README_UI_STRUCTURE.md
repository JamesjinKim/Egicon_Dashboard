# EZ-Dash UI 구조 및 확장 가이드

## 📁 폴더 구조

```
📁 최종 정리된 프로젝트 구조

  egdash/
  ├── 📱 메인 애플리케이션
  │   ├── sensor_api_simple.py      # Flask 웹 서버
  │   └── sensor_manager.py         # 센서 관리자 (리팩토링됨)
  │
  ├── 🔧 센서 클래스들 (모듈화)
  │   ├── bme688_sensor.py          # BME688 환경센서
  │   ├── sht40_sensor.py           # SHT40 온습도센서  
  │   ├── bh1750_sensor.py          # BH1750 조도센서
  │   ├── sdp810_sensor.py          # SDP810 차압센서
  │   └── sps30_sensor.py           # SPS30 미세먼지센서
  │
  ├── 🛠️ 지원 모듈들
  │   ├── constants.py              # BME688 상수
  │   ├── database.py               # 센서 DB 관리
  │   └── i2c_scanner.py            # I2C 스캐너
  │
  ├── 🌐 웹 인터페이스
  │   ├── templates/                # HTML 템플릿
  │   └── static/                   # CSS, JS 파일
  │
  ├── 📚 문서들
  │   ├── README.md
  │   ├── INSTALLATION_GUIDE.md
  │   └── README_UI_STRUCTURE.md
  │
  └── 🗂️ 백업
      └── backup_deprecated/        # 사용하지 않는 파일들
```

## 🚀 새로운 UI 페이지 추가하기

### 1. 새 페이지 템플릿 생성
`templates/pages/` 폴더에 새 HTML 파일을 생성합니다:

```html
<!-- templates/pages/settings.html -->
{% extends "base.html" %}

{% block title %}설정 - 센서 대시보드{% endblock %}
{% block header_title %}설정{% endblock %}

{% block content %}
    <div class="settings-container">
        <!-- 설정 페이지 내용 -->
    </div>
{% endblock %}

{% block scripts %}
    <script src="{{ url_for('static', filename='js/settings.js') }}"></script>
{% endblock %}
```

### 2. Flask 라우트 추가
`sensor_api_simple.py`에 새 라우트를 추가합니다:

```python
@app.route('/settings')
def settings():
    """설정 페이지"""
    return render_template('pages/settings.html')
```

### 3. 사이드바 메뉴 업데이트
`templates/base.html`의 사이드바에 새 메뉴 항목을 추가합니다:

```html
<a href="{{ url_for('settings') }}" class="menu-item {% if request.endpoint == 'settings' %}active{% endif %}">
    <i class="fas fa-cog"></i>
    <span>설정</span>
</a>
```

## 🧩 재사용 가능한 컴포넌트 만들기

### 1. 컴포넌트 템플릿 생성
`templates/components/` 폴더에 컴포넌트를 생성합니다:

```html
<!-- templates/components/sensor_card.html -->
<div class="card">
    <div class="card-header">
        <div class="card-title">{{ title }}</div>
        <div class="card-icon">
            <i class="{{ icon }}"></i>
        </div>
    </div>
    <div class="sensor-value">{{ value }}<span class="sensor-unit">{{ unit }}</span></div>
    {% if show_chart %}
    <div class="chart-container">
        <canvas id="{{ chart_id }}"></canvas>
    </div>
    {% endif %}
</div>
```

### 2. 컴포넌트 사용하기
페이지 템플릿에서 컴포넌트를 include합니다:

```html
{% include 'components/sensor_card.html' with context %}
```

## 🎨 CSS 스타일 확장

### 1. 새 CSS 파일 추가
페이지별 또는 컴포넌트별 CSS 파일을 생성합니다:

```
static/css/
├── styles.css          # 메인 스타일
├── dashboard.css       # 대시보드 전용 스타일
├── settings.css        # 설정 페이지 전용 스타일
└── components/         # 컴포넌트별 스타일
    └── sensor_card.css
```

### 2. 템플릿에서 추가 CSS 로드
```html
{% block styles %}
    <link rel="stylesheet" href="{{ url_for('static', filename='css/settings.css') }}">
{% endblock %}
```

## 📱 JavaScript 모듈화

### 1. 기능별 JS 파일 분리
```
static/js/
├── script.js           # 메인 JavaScript
├── dashboard.js        # 대시보드 전용 기능
├── settings.js         # 설정 페이지 전용 기능
├── api.js             # API 통신 관련
└── components/        # 컴포넌트별 JavaScript
    └── chart.js
```

### 2. 모듈 사용 예시
```javascript
// static/js/api.js
const API = {
    BASE_URL: window.location.origin + '/api',
    
    async getCurrentData() {
        const response = await fetch(`${this.BASE_URL}/current`);
        return response.json();
    },
    
    async getSensorStatus() {
        const response = await fetch(`${this.BASE_URL}/status`);
        return response.json();
    }
};
```

## 🔧 Flask 앱 확장

### 1. 블루프린트 사용 (권장)
큰 애플리케이션의 경우 블루프린트로 모듈화:

```python
# blueprints/dashboard.py
from flask import Blueprint, render_template

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
def index():
    return render_template('pages/dashboard.html')

# sensor_api_simple.py에서 등록
from blueprints.dashboard import dashboard_bp
app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
```

### 2. 템플릿 컨텍스트 프로세서
전역적으로 사용할 변수들을 정의:

```python
@app.context_processor
def inject_globals():
    return {
        'app_name': 'EZ-Dash',
        'version': '1.0.0',
        'current_time': datetime.now()
    }
```

## 📊 새로운 센서 유형 추가

### 1. 센서 데이터 구조 확장
```python
# constants.py (새로 생성)
SENSOR_TYPES = {
    'temperature': {
        'name': '온도',
        'unit': '°C',
        'icon': 'fas fa-thermometer-half',
        'color': '#ff6384'
    },
    'new_sensor': {
        'name': '새 센서',
        'unit': 'unit',
        'icon': 'fas fa-new-icon',
        'color': '#123456'
    }
}
```

### 2. 위젯 템플릿 동적 생성
```html
<!-- templates/components/sensor_widget.html -->
{% for sensor_type, config in sensor_types.items() %}
<div class="sensor-widget {{ sensor_type }}">
    <div class="widget-color-bar" style="background-color: {{ config.color }}"></div>
    <div class="widget-content">
        <div class="widget-icon" style="background-color: {{ config.color }}">
            <i class="{{ config.icon }}"></i>
        </div>
        <div class="widget-title">{{ config.name.upper() }}</div>
        <div class="widget-value" id="{{ sensor_type }}-value">--<span class="widget-unit">{{ config.unit }}</span></div>
    </div>
</div>
{% endfor %}
```

## 🛠️ 개발 모범 사례

1. **템플릿 상속 활용**: `base.html`을 확장하여 일관된 레이아웃 유지
2. **컴포넌트 재사용**: 공통 UI 요소는 컴포넌트로 분리
3. **CSS 변수 사용**: `:root`에 색상과 크기 변수 정의
4. **JavaScript 모듈화**: 기능별로 파일 분리하여 유지보수성 향상
5. **반응형 디자인**: 모바일 환경 고려한 CSS 작성
6. **API 일관성**: RESTful API 설계 원칙 준수

이 구조를 따르면 새로운 UI 화면과 기능을 쉽게 추가할 수 있습니다.