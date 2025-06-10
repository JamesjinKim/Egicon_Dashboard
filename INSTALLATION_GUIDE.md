# EZ-Dash 실제 센서 연동 설치 가이드

## 🎯 개요

이 가이드는 EZ-Dash 시스템을 라즈베리파이 4에서 실제 센서(BME688 + BH1750)와 연동하여 실행하는 방법을 설명합니다.

## 📋 필요한 하드웨어

### 1. 메인 보드
- **라즈베리파이 4** (2GB 이상 권장)
- MicroSD 카드 (32GB 이상)
- 전원 어댑터 (5V 3A)

### 2. 센서 모듈
- **BME688**: 온도, 습도, 압력, 가스 센서 (I2C: 0x77)
- **BH1750**: 조도 센서 (I2C: 0x23)

### 3. 연결
```
라즈베리파이 4     BME688        BH1750
GPIO 2 (SDA)   →   SDA       →   SDA
GPIO 3 (SCL)   →   SCL       →   SCL  
3.3V           →   VCC       →   VCC
GND            →   GND       →   GND
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
cd /Users/kimkookjin/Projects/egicon/ezdash/
pip3 install flask flask-cors smbus2
```

### 2. 센서 테스트
```bash
python3 test_sensors.py
```

이 명령으로 다음을 확인할 수 있습니다:
- 시스템 요구사항
- 개별 센서 연결 상태
- 센서 매니저 통합 기능
- API 기능

### 3. 데이터베이스 초기화
```bash
python3 sensor_data_generator.py
```

## 🚀 시스템 실행

### 1. API 서버 시작
```bash
python3 sensor_api.py
```

서버가 정상적으로 시작되면 다음과 같은 메시지가 표시됩니다:
```
=============================================================
EZ-Dash 센서 대시보드 API 서버 시작
=============================================================

실제 센서 연결 시도 중...
BME688 센서 연결 성공 (칩 ID: 0x61)
BME688 초기화 완료
BH1750 조도센서 연결 성공 (주소: 0x23)

센서 초기화 완료: 2/2개 센서 연결
SUCCESS: 모든 센서 정상 연결됨.

Flask 서버 시작... (포트 5001)
대시보드 접속: http://localhost:5001
Ctrl+C로 종료
```

### 2. 웹 대시보드 접속
브라우저에서 다음 주소로 접속:
- **로컬**: `http://localhost:5001`
- **네트워크**: `http://[라즈베리파이IP]:5001`

## 📊 대시보드 기능

### 센서 위젯 (6개)
1. **온도** (BME688): °C
2. **습도** (BME688): %
3. **조도** (BH1750): lux
4. **차압** (BME688 압력 변환): Pa
5. **진동** (가상): g
6. **공기질** (BME688 가스저항 변환): /100

### 차트
- 개별 센서 히스토리 차트
- 통합 센서 차트
- 3초마다 자동 업데이트

### API 엔드포인트
- `/api/sensor-data`: 기본 센서 데이터
- `/api/extended-data`: 가스/공기질 데이터
- `/api/sensor-status`: 센서 연결 상태

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
- 센서 연결 확인
- `test_sensors.py` 실행하여 개별 센서 테스트
- 서버 로그에서 에러 메시지 확인

### 3. 웹페이지 접속 안됨
```bash
# 방화벽 확인
sudo ufw status

# 포트 개방
sudo ufw allow 5001

# 서버 실행 확인
ps aux | grep sensor_api
```

### 4. 센서 데이터 부정확
- BME688 온도 오프셋 조정: `sensor_manager.py`에서 `temp_offset` 값 변경
- 센서 안정화 시간 대기 (약 1-2분)

## 🔄 자동 시작 설정 (선택사항)

### systemd 서비스 생성
```bash
sudo nano /etc/systemd/system/ezdash.service
```

파일 내용:
```ini
[Unit]
Description=EZ-Dash Sensor Dashboard
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/Users/kimkookjin/Projects/egicon/ezdash
ExecStart=/usr/bin/python3 sensor_api.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

서비스 활성화:
```bash
sudo systemctl enable ezdash.service
sudo systemctl start ezdash.service
sudo systemctl status ezdash.service
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
1. `test_sensors.py` 실행 결과
2. I2C 센서 스캔 결과
3. 서버 로그 메시지
4. 하드웨어 연결 상태

---

✅ **설치 완료 후 다음을 확인하세요:**
- [ ] 센서 연결 정상 (`i2cdetect -y 1`)
- [ ] 테스트 스크립트 통과 (`python3 test_sensors.py`)
- [ ] API 서버 정상 실행 (`python3 sensor_api.py`)
- [ ] 웹 대시보드 접속 가능 (`http://라즈베리파이IP:5001`)
- [ ] 실제 센서 데이터 표시 확인