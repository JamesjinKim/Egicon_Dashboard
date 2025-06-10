# EZ-Dash 센서 대시보드 시스템

실시간 센서 데이터 모니터링을 위한 웹 기반 대시보드 시스템입니다. 온도, 습도, 조도, 차압, 진동 센서의 데이터를 수집하여 SQLite 데이터베이스에 저장하고, 직관적인 웹 인터페이스로 실시간 시각화를 제공합니다.

## 주요 기능

- **실시간 센서 데이터 모니터링**: 5개 센서(온도, 습도, 조도, 차압, 진동)의 실시간 데이터 표시
- **반응형 웹 대시보드**: Chart.js를 활용한 동적 차트와 모바일 지원 반응형 디자인
- **히스토리 데이터 추적**: SQLite 데이터베이스 기반 히스토리 데이터 저장 및 조회
- **자동 데이터 갱신**: 3초 간격 자동 데이터 업데이트
- **REST API**: Flask 기반 RESTful API 제공

## 시스템 아키텍처

```
센서 하드웨어 → 데이터 수집 → SQLite DB → Flask API → 웹 대시보드
```

## 파일 구조

```
ezdash/
├── sensor_data_generator.py   # 센서 데이터 생성 및 데이터베이스 초기화
├── sensor_api.py              # Flask 웹서버 및 REST API
├── sensor_dashboard.html      # 반응형 웹 대시보드 (Chart.js 기반)
├── sensor_data.db            # SQLite 데이터베이스 (자동 생성)
├── sensor_data.json          # JSON 형태 데이터 백업 (선택사항)
└── Documents/
    └── prd.txt               # 프로젝트 요구사항 문서
```

## 설치 및 실행 방법

### 1. 필요한 라이브러리 설치

```bash
pip install flask flask-cors
```

### 2. 데이터베이스 초기화

센서 데이터 테이블 생성 및 초기 더미 데이터를 생성합니다:

```bash
python sensor_data_generator.py
```

### 3. 웹 서버 실행

Flask API 서버를 시작합니다:

```bash
python sensor_api.py
```
서버는 `0.0.0.0:5001`에서 실행되며, 로컬 네트워크의 다른 기기에서도 접속 가능합니다.

### 4. 대시보드 접속

웹 브라우저에서 다음 주소로 접속:
- **로컬 접속**: `http://localhost:5001`
- **네트워크 접속**: `http://[서버IP]:5001`

## 기술 스택

- **백엔드**: Python Flask, SQLite
- **프론트엔드**: HTML5, CSS3, JavaScript (ES6+)
- **차트 라이브러리**: Chart.js 3.9.1
- **아이콘**: Font Awesome 6.4.0
- **데이터베이스**: SQLite (경량 임베디드 DB)

## API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/` | GET | 메인 대시보드 페이지 |
| `/api/sensor-data` | GET | 전체 센서 데이터 (현재값 + 히스토리) |
| `/api/current-data` | GET | 현재 센서 데이터만 조회 |
| `/api/update-data` | GET | 센서 데이터 수동 갱신 |

### API 응답 형식

```json
{
  "current": {
    "temperature": 24.5,
    "humidity": 65,
    "light": 1200,
    "pressure": 12.3,
    "vibration": 0.05,
    "updated_at": "2025-06-10 15:30:00"
  },
  "history": {
    "timestamps": ["2025-06-10 14:00:00", "2025-06-10 15:00:00"],
    "temperature": [23.2, 24.5],
    "humidity": [60, 65],
    "light": [1100, 1200],
    "pressure": [11.8, 12.3],
    "vibration": [0.03, 0.05]
  }
}
```

## 대시보드 기능

### 실시간 모니터링
- **센서 위젯**: 각 센서의 현재값을 컬러 코딩된 위젯으로 표시
- **개별 차트**: 각 센서별 히스토리 차트 (온도/습도/차압: 라인차트, 조도/진동: 바차트)
- **통합 차트**: 모든 센서 데이터를 하나의 차트에서 비교 분석

### 사용자 인터페이스
- **반응형 사이드바**: 축소/확장 가능한 네비게이션 메뉴
- **모바일 최적화**: 태블릿과 스마트폰에서도 최적의 사용자 경험
- **자동 갱신**: 3초마다 자동으로 최신 데이터로 업데이트
- **수동 갱신**: 사이드바의 "데이터 갱신" 버튼으로 즉시 업데이트

## 실제 센서 연동하기

현재는 더미 데이터를 사용하고 있습니다. 실제 센서와 연동하려면 `sensor_api.py`의 `generate_sensor_data()` 함수를 수정하세요.

### 센서 연동 예시 (Raspberry Pi)

```python
import Adafruit_DHT
import smbus
import time
import sqlite3
from datetime import datetime

# DHT22 센서 설정
DHT_SENSOR = Adafruit_DHT.DHT22
DHT_PIN = 4  # GPIO 핀 번호

# BH1750 조도 센서 설정
DEVICE = 0x23  # 기본 I2C 주소
POWER_DOWN = 0x00
POWER_ON = 0x01
RESET = 0x07
ONE_TIME_HIGH_RES_MODE = 0x20

# I2C 버스 초기화
bus = smbus.SMBus(1)

# 조도 센서 데이터 읽기
def read_light():
    data = bus.read_i2c_block_data(DEVICE, ONE_TIME_HIGH_RES_MODE, 2)
    return (data[1] + (256 * data[0])) / 1.2

# 센서 데이터 읽기
def read_sensor_data():
    # 온습도 센서 읽기
    humidity, temperature = Adafruit_DHT.read_retry(DHT_SENSOR, DHT_PIN)
    
    # 조도 센서 읽기
    light = read_light()
    
    # 여기에 차압 및 진동 센서 코드 추가
    # 예: pressure = read_pressure_sensor()
    #     vibration = read_vibration_sensor()
    
    # 임시로 더미 데이터 사용
    pressure = 12.3  # 실제 센서 연결 시 이 부분 수정
    vibration = 0.05  # 실제 센서 연결 시 이 부분 수정
    
    return {
        "temperature": round(temperature, 1) if temperature else 0,
        "humidity": round(humidity, 0) if humidity else 0,
        "light": round(light, 0),
        "pressure": pressure,
        "vibration": vibration
    }

# 데이터베이스 연결
def get_db_connection():
    conn = sqlite3.connect('sensor_data.db')
    conn.row_factory = sqlite3.Row
    return conn

# 데이터 저장
def save_sensor_data():
    data = read_sensor_data()
    current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 현재 데이터 업데이트
    cursor.execute('''
    UPDATE current_readings 
    SET temperature = ?, humidity = ?, light = ?, pressure = ?, vibration = ?, updated_at = ?
    WHERE id = 1
    ''', (
        data['temperature'],
        data['humidity'],
        data['light'],
        data['pressure'],
        data['vibration'],
        current_timestamp
    ))
    
    # 새 데이터 확인
    if cursor.rowcount == 0:
        cursor.execute('''
        INSERT INTO current_readings 
        (id, temperature, humidity, light, pressure, vibration, updated_at)
        VALUES (1, ?, ?, ?, ?, ?, ?)
        ''', (
            data['temperature'],
            data['humidity'],
            data['light'],
            data['pressure'],
            data['vibration'],
            current_timestamp
        ))
    
    # 히스토리 데이터도 추가 (필요시 주석 해제)
    cursor.execute('''
    INSERT INTO sensor_readings 
    (timestamp, temperature, humidity, light, pressure, vibration)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        current_timestamp,
        data['temperature'],
        data['humidity'],
        data['light'],
        data['pressure'],
        data['vibration']
    ))
    
    conn.commit()
    conn.close()
    
    return data

# 메인 함수
def main():
    while True:
        try:
            data = save_sensor_data()
            print(f"데이터 저장 완료: {data}")
        except Exception as e:
            print(f"오류 발생: {e}")
        
        # 5초마다 데이터 읽기
        time.sleep(5)

if __name__ == "__main__":
    main()
```

### 센서 데이터 범위 설정

`sensor_api.py`에서 각 센서의 데이터 범위를 설정할 수 있습니다:

```python
sensor_ranges = {
    'temperature': {'min': 20, 'max': 28},    # 온도 (°C)
    'humidity': {'min': 40, 'max': 75},       # 습도 (%)
    'light': {'min': 500, 'max': 1500},       # 조도 (ADC)
    'pressure': {'min': 5, 'max': 20},        # 차압 (Pa)
    'vibration': {'min': 0.01, 'max': 0.5}   # 진동 (g)
}
```

## 데이터베이스 구조

### 테이블 스키마

**sensor_readings** (히스토리 데이터)
- `id`: PRIMARY KEY (자동 증가)
- `timestamp`: 측정 시간 (TEXT)
- `temperature`: 온도 (REAL)
- `humidity`: 습도 (REAL)
- `light`: 조도 (INTEGER)
- `pressure`: 차압 (REAL)
- `vibration`: 진동 (REAL)

**current_readings** (현재 데이터)
- `id`: PRIMARY KEY (고정값 1)
- `temperature`: 현재 온도 (REAL)
- `humidity`: 현재 습도 (REAL)
- `light`: 현재 조도 (INTEGER)
- `pressure`: 현재 차압 (REAL)
- `vibration`: 현재 진동 (REAL)
- `updated_at`: 마지막 업데이트 시간 (TEXT)

## 개발 및 확장

### 코드 구조
- `sensor_data_generator.py`: 데이터베이스 생성, 더미 데이터 생성, 실시간 시뮬레이션
- `sensor_api.py`: Flask 웹서버, REST API, 센서 데이터 관리
- `sensor_dashboard.html`: 프론트엔드 대시보드 (HTML/CSS/JavaScript)

### 확장 가능 기능
- 알림 시스템 (임계값 기반)
- 데이터 내보내기 (CSV, Excel)
- 사용자 인증 및 권한 관리
- 다중 디바이스 지원
- 클라우드 연동

## 트러블슈팅

### 일반적인 문제
1. **데이터베이스 파일이 없음**: `python sensor_data_generator.py` 실행
2. **포트 5001 사용 중**: `sensor_api.py`에서 포트 번호 변경
3. **브라우저에서 차트가 안 보임**: Chart.js CDN 연결 확인
4. **네트워크 접속 불가**: 방화벽 설정 확인 (포트 5001 허용)

### 로그 확인
Flask 서버는 콘솔에 요청 로그를 출력하므로, 문제 발생 시 서버 터미널을 확인하세요.