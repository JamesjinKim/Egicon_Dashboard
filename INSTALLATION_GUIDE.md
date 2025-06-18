# EG-Dash 실시간 센서 대시보드 설치 가이드

## 🎯 개요

이 가이드는 EG-Dash 시스템을 라즈베리파이 4에서 실제 센서(BME688, BH1750, SHT40, SDP810, SPS30 등)와 연동하여 실행하는 방법을 설명합니다.

## 📋 필요한 하드웨어

### 1. 메인 보드
- **라즈베리파이 4** (2GB 이상 권장)
- MicroSD 카드 (32GB 이상)
- 전원 어댑터 (5V 3A)

### 2. 센서 모듈
- **BME688**: 온도, 습도, 압력, 가스 센서 (I2C: 0x76/0x77)
- **BH1750**: 조도 센서 (I2C: 0x23/0x5C)
- **SHT40**: 온도, 습도 센서 (I2C: 0x44)
- **SDP810**: 차압 센서 (I2C: 0x25)
- **SPS30**: 미세먼지 센서 (I2C: 0x69)

### 3. 연결
```
라즈베리파이 4     모든 센서 (I2C 버스 공유)
GPIO 2 (SDA)   →   SDA (모든 센서)
GPIO 3 (SCL)   →   SCL (모든 센서)
3.3V           →   VCC (모든 센서)
GND            →   GND (모든 센서)

센서별 I2C 주소:
- BME688: 0x76 또는 0x77
- BH1750: 0x23 또는 0x5C  
- SHT40: 0x44
- SDP810: 0x25
- SPS30: 0x69
```

## 🔧 라즈베리파이 설정

### 1. I2C 활성화
```bash
sudo raspi-config
```
- `Interface Options` → `I2C` → `Enable` 선택

### 2. 사용자 권한 설정
```bash
sudo usermod -a -G i2c $USER
```

### 3. 재부팅
```bash
sudo reboot
```

### 4. I2C 도구 설치
```bash
sudo apt update
sudo apt install -y i2c-tools python3-pip
```

### 5. 센서 연결 확인
```bash
i2cdetect -y 1
```
예상 출력:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
20: -- -- -- 23 -- -- -- -- -- -- -- -- -- -- -- -- 
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
70: -- -- -- -- -- -- -- 77
```
- `23`: BH1750 조도센서
- `77`: BME688 센서

## 📦 소프트웨어 설치

### 1. Python 패키지 설치
```bash
cd /Users/kimkookjin/Projects/egicon/egdash/
pip3 install flask flask-cors smbus2 sqlite3
```

### 2. I2C 스캐닝 및 센서 확인
```bash
# I2C 디바이스 스캔
i2cdetect -y 1

# 개별 센서 테스트 (Python 인터프리터에서)
python3 -c "from sensor_manager import SensorManager; sm = SensorManager(); sm.initialize_sensors(); print(sm.get_sensor_status())"
```

### 3. 데이터베이스 확인
```bash
# 데이터베이스는 자동으로 생성됩니다
ls -la sensors.db

# 필요시 데이터베이스 마이그레이션
python3 migrate_database.py
```

## 🚀 시스템 실행

### 1. API 서버 시작
```bash
python3 sensor_api_simple.py
```

서버가 정상적으로 시작되면 다음과 같은 메시지가 표시됩니다:
```
=== EG-Dash 심플 센서 API 서버 시작 ===

센서 매니저 초기화 중...
센서 상태 확인 중...
- BME688: 연결됨 (I2C 버스 1, 주소 0x77)
- BH1750: 연결됨 (I2C 버스 1, 주소 0x23)
- SHT40: 연결됨 (I2C 버스 1, 주소 0x44)
- SDP810: 연결됨 (I2C 버스 1, 주소 0x25)
- SPS30: 연결됨 (I2C 버스 1, 주소 0x69)

 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5003
 * Running on http://[라즈베리파이IP]:5003
```

### 2. 웹 대시보드 접속
브라우저에서 다음 주소로 접속:
- **로컬**: `http://localhost:5003`
- **네트워크**: `http://[라즈베리파이IP]:5003`
- **대시보드**: `http://[라즈베리파이IP]:5003/dashboard`
- **설정**: `http://[라즈베리파이IP]:5003/settings`

## 📊 대시보드 기능

### 센서 위젯 (6개)
1. **온도** (BME688/SHT40): °C
2. **습도** (BME688/SHT40): %
3. **조도** (BH1750): lux
4. **차압** (SDP810): Pa
5. **미세먼지** (SPS30): μg/m³
6. **공기질** (BME688 가스저항 기반): 점수

### 차트
- 개별 센서 히스토리 차트
- 통합 센서 차트
- 3초마다 자동 업데이트

### API 엔드포인트
- `/api/current`: 현재 센서 데이터
- `/api/status`: 센서 연결 상태
- `/api/database`: 데이터베이스 기록 조회
- `/settings`: 센서 설정 및 테스트 페이지

## ⚠️ 문제 해결

### 1. 센서 연결 안됨
```bash
# I2C 스캔
i2cdetect -y 1

# 권한 확인
groups $USER

# I2C 재시작
sudo systemctl restart i2c
```

### 2. 더미 데이터만 표시됨
- I2C 디바이스 스캔: `i2cdetect -y 1`
- 센서 연결 확인: Settings 페이지에서 센서 테스트
- 서버 로그에서 에러 메시지 확인

### 3. 웹페이지 접속 안됨
```bash
# 방화벽 확인
sudo ufw status

# 포트 개방
sudo ufw allow 5003

# 서버 실행 확인
ps aux | grep sensor_api_simple
```

### 4. 센서 데이터 부정확
- 각 센서별 캘리브레이션 확인
- Settings 페이지에서 센서 개별 테스트
- 센서 안정화 시간 대기 (약 1-2분)
- SPS30 센서는 초기 동작 시 워밍업 필요

## 🔄 자동 시작 설정 (선택사항)

### systemd 서비스 생성
```bash
sudo nano /etc/systemd/system/egdash.service
```

파일 내용:
```ini
[Unit]
Description=EG-Dash Sensor Dashboard
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/egdash
ExecStart=/usr/bin/python3 sensor_api_simple.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

서비스 활성화:
```bash
sudo systemctl enable egdash.service
sudo systemctl start egdash.service
sudo systemctl status egdash.service
```

## 📈 성능 최적화

### 1. 센서 읽기 간격 조정
`sensor_api.py`에서 자동 업데이트 간격 수정:
```javascript
setInterval(updateSensorData, 3000);  // 3초 → 5초 등으로 변경
```

### 2. 메모리 사용량 줄이기
- 히스토리 데이터 제한
- 차트 포인트 수 제한
- 로그 레벨 조정

## 🆘 지원

문제가 발생하면 다음을 확인하세요:
1. I2C 센서 스캔: `i2cdetect -y 1`
2. Settings 페이지에서 센서 개별 테스트
3. 서버 로그 메시지
4. 하드웨어 연결 상태
5. 데이터베이스 상태: `ls -la sensors*.db`

---

✅ **설치 완료 후 다음을 확인하세요:**
- [ ] 센서 연결 정상 (`i2cdetect -y 1`)
- [ ] API 서버 정상 실행 (`python3 sensor_api_simple.py`)
- [ ] 웹 대시보드 접속 가능 (`http://라즈베리파이IP:5003`)
- [ ] Settings 페이지에서 센서 테스트 통과
- [ ] 실제 센서 데이터 표시 확인
- [ ] 데이터베이스 정상 동작 확인