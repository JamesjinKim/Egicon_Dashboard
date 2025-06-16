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
                
                with ShdlcSerialPort(port=port_path, baudrate=115200) as port:
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
            with ShdlcSerialPort(port=self.port_path, baudrate=115200) as port:
                device = Sps30ShdlcDevice(ShdlcConnection(port))
                
                # 센서 정보 확인
                self.serial_number = device.device_information_serial_number()
                
                if not self.serial_number:
                    print("❌ SPS30 센서 시리얼 번호 읽기 실패")
                    return False
                
                print(f"✅ SPS30 센서 연결 성공")
                print(f"📊 시리얼 번호: {self.serial_number}")
                
                # 센서 안정화 대기 (측정 시작은 read_data에서 처리)
                time.sleep(1)
                
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
        
        max_retries = 2  # 최대 재시도 횟수
        
        for attempt in range(max_retries + 1):
            try:
                with ShdlcSerialPort(port=self.port_path, baudrate=115200) as port:
                    device = Sps30ShdlcDevice(ShdlcConnection(port))
                    
                    # 첫 번째 시도가 아닌 경우, 센서 상태 확인 및 초기화
                    if attempt > 0:
                        print(f"🔄 SPS30 재시도 {attempt}/{max_retries}")
                        try:
                            # 측정 중지 (상태 초기화)
                            try:
                                device.stop_measurement()
                                time.sleep(1)
                            except Exception:
                                pass  # 이미 중지된 경우 무시
                            
                            # 센서 리셋
                            device.device_reset()
                            print("✅ SPS30 센서 리셋 완료")
                            time.sleep(3)  # 리셋 후 충분한 대기
                            
                            # 측정 시작
                            device.start_measurement()
                            print("✅ SPS30 측정 재시작")
                            
                            # 안정화 대기 및 상태 확인
                            for wait_time in range(8):  # 8초 대기하면서 상태 확인
                                time.sleep(1)
                                try:
                                    ready = device.read_data_ready()
                                    if ready:
                                        print(f"✅ SPS30 측정 준비 완료 ({wait_time + 1}초 후)")
                                        break
                                except Exception:
                                    pass
                            else:
                                print("⚠️ SPS30 측정 준비 상태 확인 불가")
                            
                        except Exception as reset_error:
                            print(f"⚠️ SPS30 리셋 중 오류: {reset_error}")
                            if attempt == max_retries:
                                return None
                            continue
                    
                    # 데이터 읽기 시도
                    raw_data = device.read_measured_value()
                    print(f"🔍 SPS30 원시 데이터 (시도 {attempt + 1}): {raw_data} (길이: {len(raw_data) if raw_data else 0})")
                    
                    # 데이터 유효성 검사
                    if not raw_data or len(raw_data) < 3:
                        print(f"⚠️ SPS30 데이터 부족: {len(raw_data) if raw_data else 0}개")
                        if attempt < max_retries:
                            continue  # 다음 시도로
                        else:
                            print("❌ SPS30 모든 시도 실패")
                            return None
                    
                    # 정상 작동하는 코드의 안전한 숫자 변환 함수 사용
                    def safe_float(value):
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
                    
                    # 데이터 파싱 (정상 동작 코드와 동일한 방식)
                    pm1_val = safe_float(raw_data[0])
                    pm25_val = safe_float(raw_data[1])
                    pm10_val = safe_float(raw_data[2])
                    pm4_val = 0.0  # 기본값
                    
                    measurement = {
                        'pm1': pm1_val,
                        'pm25': pm25_val,
                        'pm4': pm4_val,  # 3개 데이터인 경우 PM4.0 없음
                        'pm10': pm10_val,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # 4개 이상 데이터가 있는 경우 PM4.0 포함
                    if len(raw_data) >= 4:
                        pm4_val = safe_float(raw_data[2])
                        pm10_val = safe_float(raw_data[3])
                        measurement['pm4'] = pm4_val
                        measurement['pm10'] = pm10_val
                        print(f"✅ SPS30 데이터(4개): PM1.0={pm1_val:.1f} PM2.5={pm25_val:.1f} PM4.0={pm4_val:.1f} PM10={pm10_val:.1f}")
                    else:
                        # 3개 데이터: PM1.0, PM2.5, PM10
                        print(f"✅ SPS30 데이터(3개): PM1.0={pm1_val:.1f} PM2.5={pm25_val:.1f} PM10={pm10_val:.1f}")
                    
                    self.last_measurement = measurement
                    return measurement  # 성공 시 즉시 반환
                    
            except Exception as e:
                print(f"❌ SPS30 데이터 읽기 예외 (시도 {attempt + 1}): {e}")
                if attempt == max_retries:
                    return None
                # continue로 다음 시도
        
        # 모든 시도 실패
        print("❌ SPS30 센서 모든 재시도 실패")
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
            with ShdlcSerialPort(port=self.port_path, baudrate=115200) as port:
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
            with ShdlcSerialPort(port=self.port_path, baudrate=115200) as port:
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
            with ShdlcSerialPort(port=self.port_path, baudrate=115200) as port:
                device = Sps30ShdlcDevice(ShdlcConnection(port))
                device.stop_measurement()
                print("✅ SPS30 측정 중지")
                return True
                
        except Exception as e:
            print(f"❌ SPS30 측정 중지 실패: {e}")
            return False
    
    def get_measurement_status(self) -> bool:
        """측정 상태 확인"""
        if not self.connected or not SPS30_AVAILABLE:
            return False
            
        try:
            with ShdlcSerialPort(port=self.port_path, baudrate=115200) as port:
                device = Sps30ShdlcDevice(ShdlcConnection(port))
                # 측정 상태 확인 (read_data_ready 사용)
                ready = device.read_data_ready()
                return ready
                
        except Exception as e:
            print(f"❌ SPS30 측정 상태 확인 실패: {e}")
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