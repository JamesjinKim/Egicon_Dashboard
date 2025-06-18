# 🚀 EG-Dash 실시간 센서 대시보드

**라즈베리파이 4 기반 실시간 센서 모니터링 시스템**

BME688, BH1750, SHT40, DPS810, SPS30 등 실제 센서를 사용한 온도, 습도, 압력, 조도, 공기질 데이터의 실시간 모니터링 및 
시각화를 제공하는 Flask 기반 웹 대시보드입니다.

## ✨ 주요 기능

### 🌡️ **실제 센서 연동**
- **BME688**: 온도, 습도, 압력, 가스저항 측정
- **BH1750**: 고정밀 조도 측정 (lux)
- **가상 진동 센서**: 시간대별 패턴 기반 진동 데이터
- **자동 I2C 버스 검색**: 센서 자동 인식 및 연결

### 📊 **전문적인 대시보드**
- **실시간 위젯**: 6개 센서의 현재값을 컬러풀한 위젯으로 표시
- **개별 차트**: 각 센서별 히스토리 차트 (Chart.js 기반)
- **통합 차트**: 모든 센서 데이터 통합 비교 분석
- **설정 페이지**: 센서 개별 테스트 및 I2C 스캐닝 기능
- **데이터베이스 연동**: SQLite 기반 데이터 저장 및 조회
- **모듈화된 템플릿**: Flask Jinja2 템플릿 시스템 활용
- **반응형 디자인**: 데스크톱/태블릿/모바일 최적화

### 🔄 **실시간 업데이트**
- **3초 자동 갱신**: 센서 데이터 실시간 업데이트
- **폴백 시스템**: 센서 연결 실패 시 더미 데이터로 자동 전환
- **상태 모니터링**: 센서 연결 상태 및 에러 표시
- **비동기 API**: Flask CORS 지원으로 원활한 데이터 통신

## 🏗️ 시스템 아키텍처

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   실제 센서       │───▶│  센서 매니저        │───▶│   Flask API     │───▶│   웹 대시보드      │
│                 │    │                  │    │                 │    │                 │
│ • BME688        │    │ • 자동 검색        │    │ • REST API      │    │ • 실시간 위젯      │
│   - 온도/습도     │    │ • I2C 통신        │    │ • 폴백 처리        │    │ • 개별 차트       │
│   - 압력/가스     │    │ • 데이터 변환       │    │ • 상태 모니터      │    │ • 통합 차트       │
│ • BH1750        │    │ • 에러 처리        │    │ • CORS 지원      │    │ • 사이드바 UI     │
│   - 조도         │    │                  │    │                 │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 프로젝트 구조

```
egdash/
├── 📄 sensor_api_simple.py    # 메인 API 서버 (포트 5003)
├── 🔧 sensor_manager.py       # 센서 관리 클래스 (모든 센서 통합)
├── 📝 constants.py            # BME688 센서 상수 정의
├── 🔧 개별 센서 지원 모듈
│   ├── bme688_sensor.py      # BME688 환경센서
│   ├── bh1750_sensor.py      # BH1750 조도센서
│   ├── sht40_sensor.py       # SHT40 온습도센서
│   ├── sdp810_sensor.py      # SDP810 차압센서
│   └── sps30_sensor.py       # SPS30 미세먼지센서
├── 📊 데이터베이스 지원
│   ├── database.py           # SQLite 데이터베이스 관리
│   ├── migrate_database.py   # 데이터베이스 마이그레이션
│   └── sensors.db            # SQLite 데이터베이스 파일
├── 🔍 i2c_scanner.py           # I2C 디바이스 스캐닝 도구
├── 📁 templates/              # Flask 템플릿 디렉토리
│   ├── base.html             # 기본 템플릿
│   ├── index.html            # 메인 페이지
│   ├── components/           # 재사용 가능한 컴포넌트
│   └── pages/
│       ├── dashboard.html    # 대시보드 페이지
│       └── settings.html     # 센서 설정 페이지
├── 📁 static/                # 정적 파일 디렉토리
│   ├── css/
│   │   └── styles.css        # 메인 스타일시트
│   ├── js/
│   │   ├── script.js         # 대시보드 JavaScript
│   │   └── settings.js       # 설정 페이지 JavaScript
│   └── images/               # 이미지 파일
└── 📁 Documents/
    └── prd.txt               # 프로젝트 요구사항 문서
```

## 🔍 데이터 유형 식별

### 실제 센서 데이터 vs 더미 데이터 확인 방법

#### 1️⃣ **웹 대시보드에서 확인**
- **상태 표시**: 대시보드 상단 상태바에서 센서 연결 상태 확인
  - `센서 연결됨 (2/2)` ➜ 실제 센서 데이터
  - `센서 연결됨 (1/2)` ➜ 일부 센서만 연결
  - `센서 연결 안됨 (0/2)` ➜ 더미 데이터 사용 중

#### 2️⃣ **API 엔드포인트로 확인**
```bash
# 센서 상태 확인
curl http://라즈베리파이IP:5003/api/status

# 응답 예시 (실제 센서)
{
  "connected": true,
  "bme688": true,
  "bh1750": true,
  "total_sensors": 2,
  "timestamp": "2025-06-10 15:30:00"
}

# 응답 예시 (더미 데이터)
{
  "connected": false,
  "bme688": false,
  "bh1750": false,
  "total_sensors": 0,
  "timestamp": "2025-06-10 15:30:00"
}
```

#### 3️⃣ **서버 로그에서 확인**
```bash
# 서버 실행 시 출력되는 로그 확인
python sensor_api_simple.py

# 실제 센서 연결 시
✅ 센서 연결 성공
📊 BME688: 연결 (I2C 버스 0, 주소 0x77)
📊 BH1750: 연결 (I2C 버스 1, 주소 0x23)

# 센서 연결 실패 시
❌ 센서 연결 실패 - 서버만 실행됩니다
WARNING: 모든 센서 연결 실패. 더미 데이터만 사용합니다.
```

#### 4️⃣ **센서 테스트 도구 사용**
```bash
# 종합 센서 테스트 실행
python test_sensors.py

# 테스트 결과에서 실제 센서 연결 여부 확인
🔧 개별 센서 연결 테스트
✅ BME688 연결 성공
📊 온도: 25.2°C, 습도: 45.3%, 압력: 1013.2hPa, 가스: 120000Ω

✅ BH1750 연결 성공  
📊 조도: 1250.5 lux
```

## 🚀 빠른 시작

### 1️⃣ **레포지토리 클론**
```bash
git clone https://github.com/JamesjinKim/Egicon_Dashboard.git
cd Egicon_Dashboard
```

### 2️⃣ **필요한 라이브러리 설치**
```bash
# 기본 라이브러리
pip install flask flask-cors smbus2

# 라즈베리파이에서 I2C 활성화 (필요시)
sudo raspi-config
# Interface Options > I2C > Enable 선택
```

### 3️⃣ **센서 연결 테스트** (선택사항)
```bash
# 센서 연결 상태 확인
python test_sensors.py

# 예상 출력:
# ✅ BME688 연결 성공
# ✅ BH1750 연결 성공  
# 🎉 모든 테스트 통과!
```

### 4️⃣ **서버 실행**
```bash
# 메인 대시보드 서버 실행
python sensor_api_simple.py

# 출력 예시:
# ✅ 센서 연결 성공
# 🚀 서버 시작: http://0.0.0.0:5003
```

### 5️⃣ **대시보드 접속**
웹 브라우저에서 접속:
- **로컬**: `http://localhost:5003`
- **네트워크**: `http://라즈베리파이IP:5003`

## 💻 개발자 가이드

### 🛠️ 기술 스택

| 분야       |      기술      |  버전   |    용도   |
|-----------|---------------|--------|----------|
| **백엔드**  | Python Flask  |  2.x   |  API 서버 |
| **센서 통신** | smbus2       | latest | I2C 통신 |
| **프론트엔드** | HTML5/CSS3/JS | ES6+  | 대시보드 UI |
| **차트**     | Chart.js      | 3.9.1 | 데이터 시각화 |
| **아이콘**   | Font Awesome   | 6.4.0 | UI 아이콘 |
| **하드웨어**  | 라즈베리파이 4     | -     | 메인 컴퓨터 |
| **센서**     | BME688 + BH1750 | -     | 실제 센서 |

### 🌐 API 엔드포인트

| 엔드포인트 | 메서드 | 설명 | 응답 |
|-----------|--------|------|------|
| `/` | GET | 메인 대시보드 페이지 | HTML |
| `/dashboard` | GET | 대시보드 페이지 (별칭) | HTML |
| `/api/current` | GET | 현재 센서 데이터 조회 | JSON |
| `/api/status` | GET | 센서 연결 상태 확인 | JSON |

### 📋 API 응답 형식

#### `/api/current` - 현재 센서 데이터
```json
{
  "timestamp": "2025-06-10T15:30:00.123456",
  "temperature": 25.2,
  "humidity": 45.3,
  "light": 1250,
  "pressure": 15.7,
  "vibration": 0.12,
  "gas_resistance": 120000.0,
  "air_quality": 75,
  "absolute_pressure": 1013.25
}
```

#### `/api/status` - 센서 상태
```json
{
  "connected": true,
  "bme688": true,
  "bh1750": true,  
  "total_sensors": 2,
  "timestamp": "2025-06-10 15:30:00"
}
```

### 🔧 코드 구조

#### **핵심 클래스**

1. **`SensorManager`** (sensor_manager.py)
   ```python
   class SensorManager:
       def __init__(self):
           self.bme688 = BME688Sensor()
           self.bh1750 = BH1750Sensor()
       
       def initialize_sensors(self):
           # 센서 자동 검색 및 초기화
       
       def read_all_sensors(self):
           # 모든 센서 데이터 읽기
   ```

2. **`BME688Sensor`** (sensor_manager.py)
   ```python
   class BME688Sensor:
       @staticmethod
       def find_bme688():
           # I2C 버스 0,1과 주소 0x76,0x77 자동 검색
       
       def read_sensor_data(self):
           # 온도, 습도, 압력, 가스저항 읽기
   ```

3. **`BH1750Sensor`** (sensor_manager.py)
   ```python
   class BH1750Sensor:
       @staticmethod  
       def find_bh1750():
           # I2C 버스 0,1과 주소 0x23,0x5C 자동 검색
       
       def read_light(self):
           # 조도 데이터 읽기 (lux)
   ```

#### **폴백 시스템**
```python
def generate_sensor_data():
    if sensor_manager:
        try:
            # 실제 센서 데이터 시도
            return sensor_manager.read_all_sensors()
        except Exception as e:
            print(f"WARNING: 센서 읽기 실패, 더미 데이터 사용: {e}")
    
    # 폴백: 더미 데이터 생성
    return generate_dummy_data()
```

### 🎯 센서 데이터 명세

#### **실제 센서 데이터**
| 센서 | 측정값 | 단위 | 범위 | 정확도 |
|------|--------|------|------|--------|
| BME688 온도 | 25.2°C | °C | -40~85 | ±1.0°C |
| BME688 습도 | 45.3% | % | 0~100 | ±3% |
| BME688 압력 | 1013.25hPa | hPa | 300~1250 | ±1.0hPa |
| BME688 가스 | 120000Ω | Ω | 10~500kΩ | - |
| BH1750 조도 | 1250lux | lux | 0~65535 | ±20% |
| 가상 진동 | 0.12g | g | 0~2.0 | - |

#### **더미 데이터 범위**
```python
# sensor_api_simple.py의 폴백 데이터 범위
sensor_ranges = {
    'temperature': {'min': 20, 'max': 28},    # 20~28°C
    'humidity': {'min': 40, 'max': 75},       # 40~75%
    'light': {'min': 500, 'max': 1500},       # 500~1500lux
    'pressure': {'min': 5, 'max': 20},        # 5~20Pa (차압)
    'vibration': {'min': 0.01, 'max': 0.5}   # 0.01~0.5g
}
```

### 🔌 하드웨어 연결

#### **BME688 연결**
```
라즈베리파이 4    BME688
VCC (3.3V)   ──  VCC
GND          ──  GND  
SDA (GPIO 2) ──  SDA
SCL (GPIO 3) ──  SCL
```

#### **BH1750 연결**
```
라즈베리파이 4    BH1750
VCC (3.3V)   ──  VCC
GND          ──  GND
SDA (GPIO 2) ──  SDA  
SCL (GPIO 3) ──  SCL
ADDR         ──  GND (주소 0x23)
```

### 🛠️ 개발 및 확장

#### **새로운 센서 추가**
1. `sensor_manager.py`에 새 센서 클래스 추가
2. `SensorManager.read_all_sensors()`에 센서 읽기 로직 추가
3. API 응답 형식에 새 필드 추가
4. 대시보드 UI에 새 위젯/차트 추가

#### **코드 기여**
```bash
# 포크 후 브랜치 생성
git checkout -b feature/new-sensor

# 개발 후 테스트
python test_sensors.py

# 커밋 및 풀 리퀘스트
git commit -m "feat: add new sensor support"
git push origin feature/new-sensor
```

## 🚨 트러블슈팅

### ❌ 자주 발생하는 문제들

#### **1. 센서 연결 실패**
```bash
# 증상: "ModuleNotFoundError: No module named 'constants'"
# 해결: constants.py 파일이 있는지 확인
ls constants.py

# 증상: "OSError: [Errno 2] No such file or directory: '/dev/i2c-1'"
# 해결: I2C 활성화
sudo raspi-config
# Interface Options > I2C > Enable

# 증상: "PermissionError: [Errno 13] Permission denied"
# 해결: I2C 권한 설정
sudo usermod -a -G i2c $USER
sudo reboot

# 증상: "센서 연결 실패"가 표시될 때
# 해결: 센서 테스트 도구 실행
python test_sensors.py
```

#### **2. 네트워크 접속 문제**
```bash
# 증상: 브라우저에서 "사이트에 연결할 수 없음"
# 해결: 방화벽 포트 열기 (Ubuntu/Debian)
sudo ufw allow 5002

# 라즈베리파이 IP 확인
hostname -I
```

#### **3. 라이브러리 설치 문제**
```bash
# 가상환경에서 설치 (권장)
python -m venv ezdash_env
source ezdash_env/bin/activate  # Linux/Mac
# ezdash_env\Scripts\activate  # Windows

pip install flask flask-cors smbus2
```

### 🔧 진단 도구

#### **센서 연결 상태 확인**
```bash
# I2C 디바이스 스캔
sudo i2cdetect -y 0  # 버스 0
sudo i2cdetect -y 1  # 버스 1

# 예상 결과:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 20: -- -- -- 23 -- -- -- -- -- -- -- -- -- -- -- --  (BH1750)
# 70: -- -- -- -- -- -- -- 77 -- -- -- -- -- -- -- --  (BME688)
```

#### **시스템 로그 확인**
```bash
# 시스템 로그에서 I2C 관련 오류 확인
dmesg | grep i2c

# Python 오류 로그 확인
python sensor_api_simple.py 2>&1 | tee debug.log
```

### 📞 지원

- **GitHub Issues**: [프로젝트 이슈 페이지](https://github.com/JamesjinKim/egdash/issues)
- **개발자**: JamesjinKim  
- **라이선스**: MIT License

### 🆕 최신 업데이트 (2025.06.18)

- ✅ **5개 센서 지원**: BME688, BH1750, SHT40, SDP810, SPS30 완전 연동
- ✅ **SQLite 데이터베이스**: 센서 데이터 저장 및 조회 기능
- ✅ **Settings 페이지**: 센서 개별 테스트 및 I2C 스캔 기능
- ✅ **미세먼지 모니터링**: SPS30 센서로 PM2.5, PM10 측정
- ✅ **고정밀 차압 측정**: SDP810 센서 연동
- ✅ **데이터베이스 마이그레이션**: 자동 DB 업데이트 시스템

---

## 📸 대시보드 스크린샷

### 🖥️ 데스크톱 대시보드
- **실시간 위젯**: 6개 센서의 현재값을 컬러풀한 위젯으로 표시
- **개별 차트**: 각 센서별 24시간 히스토리 차트
- **통합 차트**: 모든 센서 데이터 통합 비교 분석
- **반응형 사이드바**: 메뉴 및 상태 정보

### 📱 모바일 대시보드  
- **모바일 최적화**: 터치 친화적 인터페이스
- **적응형 레이아웃**: 화면 크기에 따른 자동 조정
- **간편한 네비게이션**: 스와이프 지원

---

<div align="center">

**🚀 EG-Dash 센서 대시보드**

*실시간 센서 모니터링의 새로운 표준*

[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue)](https://github.com/JamesjinKim/egdash)
[![Python](https://img.shields.io/badge/Python-3.7+-green)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.x-red)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

</div>