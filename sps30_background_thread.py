#!/usr/bin/env python3
"""
SPS30 센서 백그라운드 스레드 처리 클래스
- 독립적인 스레드에서 SPS30 센서 데이터를 지속적으로 수집
- Thread-safe 캐시 시스템으로 API 요청에 즉시 응답
- 기존 센서 시스템과 완전히 분리된 독립 프로세스
"""

import time
import threading
import queue
from datetime import datetime
from typing import Optional, Dict
import logging

# SPS30 관련 imports
try:
    from shdlc_sps30 import Sps30ShdlcDevice
    from sensirion_shdlc_driver import ShdlcSerialPort, ShdlcConnection
    from sensirion_shdlc_driver.errors import ShdlcError
    SPS30_AVAILABLE = True
except ImportError:
    print("⚠️ SPS30 라이브러리가 설치되지 않았습니다.")
    SPS30_AVAILABLE = False


class SPS30BackgroundThread:
    """SPS30 센서 전용 백그라운드 스레드 처리 클래스"""
    
    def __init__(self, port_path=None, update_interval=15):
        """
        백그라운드 스레드 초기화
        
        Args:
            port_path: SPS30 시리얼 포트 경로 (None이면 자동 검색)
            update_interval: 데이터 업데이트 간격 (초, 기본 15초)
        """
        self.port_path = port_path
        self.update_interval = update_interval
        self.running = False
        self.thread = None
        
        # Thread-safe 데이터 저장
        self._data_lock = threading.RLock()
        self._cached_data = {
            'pm1': 0.0,
            'pm25': 0.0, 
            'pm4': 0.0,
            'pm10': 0.0,
            'timestamp': None,
            'connected': False,
            'last_update': None,
            'error_count': 0,
            'total_reads': 0,
            'success_rate': 0.0
        }
        
        # 센서 연결 상태
        self.sensor_connected = False
        self.serial_number = None
        
        # 로깅 설정
        self.logger = logging.getLogger('SPS30Background')
        self.logger.setLevel(logging.INFO)
        
        # 초기화 시도
        if SPS30_AVAILABLE:
            self._initialize_sensor()
    
    def _initialize_sensor(self):
        """센서 초기화 (포트 검색 및 연결 테스트)"""
        try:
            if not self.port_path:
                self.port_path = self._find_sps30_port()
                
            if not self.port_path:
                print("❌ SPS30 센서 포트를 찾을 수 없습니다")
                return False
                
            # 센서 연결 테스트
            with ShdlcSerialPort(port=self.port_path, baudrate=115200) as port:
                device = Sps30ShdlcDevice(ShdlcConnection(port))
                self.serial_number = device.device_information_serial_number()
                
                if self.serial_number:
                    self.sensor_connected = True
                    print(f"✅ SPS30 백그라운드 스레드 센서 연결 성공: {self.port_path}")
                    print(f"📊 시리얼 번호: {self.serial_number}")
                    return True
                    
        except Exception as e:
            print(f"❌ SPS30 백그라운드 스레드 초기화 실패: {e}")
            return False
            
        return False
    
    def _find_sps30_port(self):
        """SPS30 센서 포트 자동 검색"""
        import glob
        
        port_candidates = []
        port_candidates.extend(glob.glob('/dev/ttyUSB*'))
        port_candidates.extend(glob.glob('/dev/ttyACM*'))
        port_candidates.extend(glob.glob('/dev/ttyAMA*'))
        
        for port_path in port_candidates:
            try:
                with ShdlcSerialPort(port=port_path, baudrate=115200) as port:
                    device = Sps30ShdlcDevice(ShdlcConnection(port))
                    serial_number = device.device_information_serial_number()
                    
                    if serial_number:
                        print(f"🔍 SPS30 센서 발견: {port_path}")
                        return port_path
                        
            except Exception:
                continue
                
        return None
    
    def _read_sensor_data(self):
        """실제 센서 데이터 읽기 (충분한 시간 확보)"""
        try:
            with ShdlcSerialPort(port=self.port_path, baudrate=115200) as port:
                device = Sps30ShdlcDevice(ShdlcConnection(port))
                
                # 센서 리셋 및 안정화 (충분한 시간 확보)
                device.device_reset()
                time.sleep(3)  # 리셋 후 안정화
                
                # 측정 시작
                device.start_measurement()
                time.sleep(6)  # 측정 안정화 시간
                
                # 데이터 읽기
                data = device.read_measured_value()
                
                if data and len(data) >= 3:
                    # 안전한 숫자 변환
                    def safe_float(value):
                        try:
                            if isinstance(value, (int, float)):
                                return float(value)
                            elif isinstance(value, str):
                                return float(value)
                            elif isinstance(value, tuple) and len(value) > 0:
                                return float(value[0])
                            elif hasattr(value, '__float__'):
                                return float(value)
                            else:
                                return 0.0
                        except Exception:
                            return 0.0
                    
                    pm1_val = safe_float(data[0])   # PM1.0
                    pm25_val = safe_float(data[1])  # PM2.5
                    pm10_val = safe_float(data[2])  # PM10
                    
                    return {
                        'pm1': pm1_val,
                        'pm25': pm25_val,
                        'pm4': 0.0,  # SPS30 샘플 코드는 PM4.0 없음
                        'pm10': pm10_val,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'connected': True
                    }
                else:
                    print(f"❌ SPS30 백그라운드: 데이터 부족 (받은 개수: {len(data) if data else 0})")
                    return None
                    
        except Exception as e:
            print(f"❌ SPS30 백그라운드 데이터 읽기 실패: {e}")
            return None
    
    def _background_worker(self):
        """백그라운드 스레드 워커 함수"""
        print(f"🚀 SPS30 백그라운드 스레드 시작 (간격: {self.update_interval}초)")
        
        while self.running:
            try:
                # 센서 데이터 읽기
                new_data = self._read_sensor_data()
                
                # Thread-safe 데이터 업데이트
                with self._data_lock:
                    self._cached_data['total_reads'] += 1
                    
                    if new_data:
                        # 성공적인 읽기
                        self._cached_data.update(new_data)
                        self._cached_data['connected'] = True
                        self._cached_data['last_update'] = time.time()
                        self._cached_data['error_count'] = 0  # 성공 시 오류 카운트 리셋
                        
                        print(f"✅ SPS30 백그라운드 데이터 업데이트: "
                              f"PM1.0={new_data['pm1']:.1f} PM2.5={new_data['pm25']:.1f} "
                              f"PM10={new_data['pm10']:.1f} μg/m³")
                    else:
                        # 읽기 실패
                        self._cached_data['error_count'] += 1
                        if self._cached_data['error_count'] >= 3:
                            self._cached_data['connected'] = False
                            print(f"⚠️ SPS30 백그라운드: 연속 {self._cached_data['error_count']}회 실패")
                    
                    # 성공률 계산
                    success_count = self._cached_data['total_reads'] - self._cached_data['error_count']
                    self._cached_data['success_rate'] = (success_count / self._cached_data['total_reads']) * 100
                
            except Exception as e:
                print(f"❌ SPS30 백그라운드 스레드 오류: {e}")
                with self._data_lock:
                    self._cached_data['error_count'] += 1
                    self._cached_data['connected'] = False
            
            # 대기 (중단 신호 확인하면서)
            for _ in range(self.update_interval):
                if not self.running:
                    break
                time.sleep(1)
        
        print("🛑 SPS30 백그라운드 스레드 종료")
    
    def start(self):
        """백그라운드 스레드 시작"""
        if not SPS30_AVAILABLE:
            print("❌ SPS30 라이브러리가 없어 백그라운드 스레드 시작 불가")
            return False
            
        if not self.sensor_connected:
            print("❌ SPS30 센서가 연결되지 않아 백그라운드 스레드 시작 불가")
            return False
            
        if self.running:
            print("⚠️ SPS30 백그라운드 스레드가 이미 실행 중입니다")
            return True
            
        self.running = True
        self.thread = threading.Thread(target=self._background_worker, daemon=True)
        self.thread.start()
        
        print("✅ SPS30 백그라운드 스레드 시작됨")
        return True
    
    def stop(self):
        """백그라운드 스레드 중지"""
        if not self.running:
            return
            
        print("🛑 SPS30 백그라운드 스레드 중지 중...")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            
        print("✅ SPS30 백그라운드 스레드 중지됨")
    
    def get_current_data(self):
        """현재 캐시된 데이터 반환 (즉시 응답)"""
        with self._data_lock:
            # 데이터 복사본 반환 (Thread-safe)
            data = self._cached_data.copy()
            
            # 데이터 유효성 확인
            if data['last_update']:
                data_age = time.time() - data['last_update']
                data['data_age_seconds'] = round(data_age, 1)
                
                # 60초 이상 오래된 데이터는 연결 해제로 표시
                if data_age > 60:
                    data['connected'] = False
                    
            return data
    
    def get_status(self):
        """백그라운드 스레드 상태 정보 반환"""
        with self._data_lock:
            return {
                'thread_running': self.running,
                'sensor_connected': self.sensor_connected,
                'port_path': self.port_path,
                'serial_number': self.serial_number,
                'update_interval': self.update_interval,
                'last_update': self._cached_data.get('last_update'),
                'total_reads': self._cached_data.get('total_reads', 0),
                'error_count': self._cached_data.get('error_count', 0),
                'success_rate': self._cached_data.get('success_rate', 0.0),
                'current_connected': self._cached_data.get('connected', False)
            }
    
    def is_healthy(self):
        """스레드 및 센서 상태 건강성 확인"""
        status = self.get_status()
        
        # 기본 조건들
        conditions = [
            status['thread_running'],
            status['sensor_connected'],
            status['current_connected'],
            status['success_rate'] > 50.0  # 50% 이상 성공률
        ]
        
        return all(conditions)


# 테스트 함수
def test_sps30_background():
    """SPS30 백그라운드 스레드 테스트"""
    print("🧪 SPS30 백그라운드 스레드 테스트 시작")
    
    # 백그라운드 스레드 생성 (5초 간격으로 테스트)
    bg_thread = SPS30BackgroundThread(update_interval=5)
    
    if not bg_thread.start():
        print("❌ 백그라운드 스레드 시작 실패")
        return False
    
    try:
        # 30초 동안 테스트
        for i in range(6):
            time.sleep(5)
            
            # 현재 데이터 조회
            data = bg_thread.get_current_data()
            status = bg_thread.get_status()
            
            print(f"\n[테스트 {i+1}/6]")
            print(f"연결 상태: {data['connected']}")
            print(f"PM1.0: {data['pm1']:.1f} μg/m³")
            print(f"PM2.5: {data['pm25']:.1f} μg/m³") 
            print(f"PM10: {data['pm10']:.1f} μg/m³")
            print(f"데이터 나이: {data.get('data_age_seconds', 0):.1f}초")
            print(f"성공률: {status['success_rate']:.1f}%")
            print(f"건강성: {'✅' if bg_thread.is_healthy() else '❌'}")
            
    except KeyboardInterrupt:
        print("\n테스트 중단됨")
    finally:
        bg_thread.stop()
        
    print("\n✅ SPS30 백그라운드 스레드 테스트 완료")
    return True


if __name__ == "__main__":
    test_sps30_background()