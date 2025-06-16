#!/usr/bin/env python3
"""
SPS30 미세먼지 센서 클래스
- GUI 코드 제거하고 센서 통신 로직만 추출
- 기존 대시보드 시스템과 호환되는 인터페이스 제공
"""

import time
import glob
from datetime import datetime
from typing import Optional, Dict, List, Tuple

# SPS30 관련 imports
try:
    from shdlc_sps30 import Sps30ShdlcDevice
    from sensirion_shdlc_driver import ShdlcSerialPort, ShdlcConnection
    from sensirion_shdlc_driver.errors import ShdlcError
    SPS30_AVAILABLE = True
except ImportError:
    print("⚠️ SPS30 라이브러리가 설치되지 않았습니다.")
    print("설치 명령: pip install sensirion-shdlc-sps30")
    SPS30_AVAILABLE = False


class SPS30Sensor:
    """SPS30 미세먼지 센서 클래스"""
    
    def __init__(self, bus_number=None, address=None, port=None):
        """
        SPS30 센서 초기화
        
        Args:
            bus_number: 사용 안함 (I2C가 아닌 UART 통신)
            address: 사용 안함 (I2C가 아닌 UART 통신)
            port: 시리얼 포트 경로 (예: '/dev/ttyUSB0')
        """
        self.port_path = port
        self.connected = False
        self.device = None
        self.port = None
        self.serial_number = None
        self.last_measurement = None
        
        # 센서 초기화 시도
        if SPS30_AVAILABLE:
            self.connected = self._initialize()
        else:
            print("❌ SPS30 센서 라이브러리가 없어 초기화 실패")
    
    @staticmethod
    def find_sps30() -> Tuple[Optional[str], Optional[int]]:
        """
        SPS30 센서 자동 검색
        
        Returns:
            Tuple[port_path, sensor_count]: (시리얼 포트 경로, 센서 개수)
            실패 시 (None, 0) 반환
        """
        if not SPS30_AVAILABLE:
            return None, 0
            
        print("🔍 SPS30 센서 검색 중...")
        
        # USB 시리얼 포트 후보들 검색
        port_candidates = []
        port_candidates.extend(glob.glob('/dev/ttyUSB*'))  # USB-Serial 어댑터
        port_candidates.extend(glob.glob('/dev/ttyACM*'))  # Arduino/Micro 타입
        port_candidates.extend(glob.glob('/dev/ttyAMA*'))  # 라즈베리파이 UART
        
        if not port_candidates:
            print("❌ 시리얼 포트를 찾을 수 없습니다")
            return None, 0
        
        # 각 포트에서 SPS30 센서 검색
        for port_path in port_candidates:
            try:
                print(f"🔌 포트 테스트 중: {port_path}")
                
                with ShdlcSerialPort(port=port_path, baudrate=115200, timeout=2) as port:
                    device = Sps30ShdlcDevice(ShdlcConnection(port))
                    
                    # 센서 정보 읽기 시도
                    serial_number = device.device_information_serial_number()
                    
                    if serial_number:
                        print(f"✅ SPS30 센서 발견: {port_path} (S/N: {serial_number})")
                        return port_path, 1
                        
            except Exception as e:
                print(f"⚠️ 포트 {port_path} 테스트 실패: {e}")
                continue
        
        print("❌ SPS30 센서를 찾을 수 없습니다")
        return None, 0
    
    def _initialize(self) -> bool:
        """센서 초기화"""
        try:
            # 포트가 지정되지 않은 경우 자동 검색
            if not self.port_path:
                port_path, count = self.find_sps30()
                if not port_path:
                    return False
                self.port_path = port_path
            
            print(f"🔌 SPS30 센서 연결 시도: {self.port_path}")
            
            # 센서 연결 테스트
            with ShdlcSerialPort(port=self.port_path, baudrate=115200, timeout=3) as port:
                device = Sps30ShdlcDevice(ShdlcConnection(port))
                
                # 센서 정보 확인
                self.serial_number = device.device_information_serial_number()
                
                if not self.serial_number:
                    print("❌ SPS30 센서 시리얼 번호 읽기 실패")
                    return False
                
                print(f"✅ SPS30 센서 연결 성공")
                print(f"📊 시리얼 번호: {self.serial_number}")
                
                return True
                
        except Exception as e:
            print(f"❌ SPS30 센서 초기화 실패: {e}")
            return False
    
    def _safe_float(self, value) -> float:
        """안전한 숫자 변환"""
        try:
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                return float(value)
            elif isinstance(value, tuple) and len(value) > 0:
                return float(value[0])  # 튜플의 첫 번째 값 사용
            elif hasattr(value, '__float__'):
                return float(value)
            else:
                return 0.0
        except Exception:
            return 0.0
    
    def read_data(self) -> Optional[Dict]:
        """
        센서 데이터 읽기
        
        Returns:
            Dict: {
                'pm1': float,      # PM1.0 (μg/m³)
                'pm25': float,     # PM2.5 (μg/m³)
                'pm4': float,      # PM4.0 (μg/m³)
                'pm10': float,     # PM10 (μg/m³)
                'timestamp': str   # 측정 시간
            }
            실패 시 None 반환
        """
        if not self.connected or not SPS30_AVAILABLE:
            return None
        
        try:
            with ShdlcSerialPort(port=self.port_path, baudrate=115200, timeout=3) as port:
                device = Sps30ShdlcDevice(ShdlcConnection(port))
                
                # 측정이 시작되지 않았다면 시작
                try:
                    device.start_measurement()
                    time.sleep(1)  # 측정 안정화 대기
                except:
                    pass  # 이미 측정 중일 수 있음
                
                # 데이터 읽기
                raw_data = device.read_measured_value()
                
                if not raw_data or len(raw_data) < 3:
                    print(f"⚠️ SPS30 데이터 부족: {len(raw_data) if raw_data else 0}개")
                    return None
                
                # 데이터 파싱
                pm1_val = self._safe_float(raw_data[0])
                pm25_val = self._safe_float(raw_data[1])
                pm10_val = self._safe_float(raw_data[2])
                pm4_val = 0.0
                
                # 4개 데이터가 있는 경우 PM4.0 포함
                if len(raw_data) >= 4:
                    pm4_val = self._safe_float(raw_data[2])
                    pm10_val = self._safe_float(raw_data[3])
                
                measurement = {
                    'pm1': pm1_val,
                    'pm25': pm25_val,
                    'pm4': pm4_val,
                    'pm10': pm10_val,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                self.last_measurement = measurement
                return measurement
                
        except Exception as e:
            print(f"❌ SPS30 데이터 읽기 실패: {e}")
            return None
    
    def get_air_quality_index(self, pm25_value: float) -> Tuple[str, int]:
        """
        PM2.5 값을 기반으로 공기질 지수 계산 (한국 기준)
        
        Args:
            pm25_value: PM2.5 농도 (μg/m³)
            
        Returns:
            Tuple[상태명, 점수]: ('좋음', 85) 형태
        """
        if pm25_value <= 15:
            return "좋음", 100 - int(pm25_value)
        elif pm25_value <= 35:
            return "보통", 85 - int((pm25_value - 15) * 2)
        elif pm25_value <= 75:
            return "나쁨", 45 - int((pm25_value - 35) * 1.5)
        else:
            return "매우나쁨", max(0, 20 - int((pm25_value - 75) * 0.5))
    
    def get_sensor_info(self) -> Dict:
        """센서 정보 반환"""
        return {
            'type': 'SPS30',
            'name': 'SPS30 미세먼지 센서',
            'manufacturer': 'Sensirion',
            'serial_number': self.serial_number,
            'port': self.port_path,
            'connected': self.connected,
            'measurements': ['PM1.0', 'PM2.5', 'PM4.0', 'PM10'],
            'units': 'μg/m³',
            'update_interval': 3000  # 3초 권장
        }
    
    def reset_sensor(self) -> bool:
        """센서 리셋"""
        if not self.connected or not SPS30_AVAILABLE:
            return False
            
        try:
            with ShdlcSerialPort(port=self.port_path, baudrate=115200, timeout=3) as port:
                device = Sps30ShdlcDevice(ShdlcConnection(port))
                device.device_reset()
                time.sleep(2)  # 리셋 후 대기
                print("✅ SPS30 센서 리셋 완료")
                return True
                
        except Exception as e:
            print(f"❌ SPS30 센서 리셋 실패: {e}")
            return False
    
    def start_measurement(self) -> bool:
        """측정 시작"""
        if not self.connected or not SPS30_AVAILABLE:
            return False
            
        try:
            with ShdlcSerialPort(port=self.port_path, baudrate=115200, timeout=3) as port:
                device = Sps30ShdlcDevice(ShdlcConnection(port))
                device.start_measurement()
                print("✅ SPS30 측정 시작")
                return True
                
        except Exception as e:
            print(f"❌ SPS30 측정 시작 실패: {e}")
            return False
    
    def stop_measurement(self) -> bool:
        """측정 중지"""
        if not self.connected or not SPS30_AVAILABLE:
            return False
            
        try:
            with ShdlcSerialPort(port=self.port_path, baudrate=115200, timeout=3) as port:
                device = Sps30ShdlcDevice(ShdlcConnection(port))
                device.stop_measurement()
                print("✅ SPS30 측정 중지")
                return True
                
        except Exception as e:
            print(f"❌ SPS30 측정 중지 실패: {e}")
            return False
    
    def close(self):
        """센서 연결 종료"""
        if self.connected:
            self.stop_measurement()
            self.connected = False
            print("🔌 SPS30 센서 연결 종료")


# 테스트 함수
def test_sps30_sensor():
    """SPS30 센서 테스트"""
    print("🧪 SPS30 센서 테스트 시작")
    
    # 센서 검색
    port, count = SPS30Sensor.find_sps30()
    if not port:
        print("❌ SPS30 센서를 찾을 수 없습니다")
        return False
    
    # 센서 초기화
    sensor = SPS30Sensor(port=port)
    if not sensor.connected:
        print("❌ SPS30 센서 연결 실패")
        return False
    
    # 센서 정보 출력
    info = sensor.get_sensor_info()
    print(f"📊 센서 정보: {info}")
    
    # 데이터 읽기 테스트
    print("📈 데이터 읽기 테스트 (5회)")
    for i in range(5):
        data = sensor.read_data()
        if data:
            quality, score = sensor.get_air_quality_index(data['pm25'])
            print(f"[{i+1}] PM1.0={data['pm1']:.1f} PM2.5={data['pm25']:.1f} "
                  f"PM4.0={data['pm4']:.1f} PM10={data['pm10']:.1f} μg/m³ "
                  f"(공기질: {quality}, 점수: {score})")
        else:
            print(f"[{i+1}] 데이터 읽기 실패")
        
        time.sleep(3)
    
    # 정리
    sensor.close()
    print("✅ SPS30 센서 테스트 완료")
    return True


if __name__ == "__main__":
    test_sps30_sensor()