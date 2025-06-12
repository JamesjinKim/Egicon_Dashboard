#!/usr/bin/env python3
"""
EG-Dash I2C 스캐너 모듈
gui_scanner.py의 백엔드 로직을 웹 환경에 맞게 포팅
"""

import time
import smbus2
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime

class WebI2CScanner:
    """웹 환경용 I2C 스캐너 클래스"""
    
    def __init__(self, mock_mode=False):
        self.buses = {}
        self.scanning = False
        self.scan_thread = None
        self.mock_mode = mock_mode  # 모킹 모드 (테스트용)
    
    def connect_buses(self) -> List[int]:
        """I2C 버스 0과 1에 연결"""
        # 모킹 모드인 경우
        if self.mock_mode:
            print("🔧 모킹 모드: 가상 I2C 버스 연결")
            self.buses = {0: 'mock_bus_0', 1: 'mock_bus_1'}
            return [0, 1]
        
        # 기존 연결 정리
        for bus in self.buses.values():
            try:
                bus.close()
            except:
                pass
        
        self.buses = {}
        connected_buses = []
        
        for bus_num in [0, 1]:
            try:
                print(f"I2C 버스 {bus_num} 연결 시도...")
                bus = smbus2.SMBus(bus_num)
                self.buses[bus_num] = bus
                connected_buses.append(bus_num)
                print(f"I2C 버스 {bus_num} 연결 성공")
            except Exception as e:
                print(f"I2C 버스 {bus_num} 연결 실패: {e}")
        
        return connected_buses
    
    def scan_bus(self, bus_number: int, progress_callback: Optional[Callable] = None) -> List[int]:
        """특정 버스 스캔"""
        if bus_number not in self.buses:
            return []
        
        # 모킹 모드인 경우 가상 디바이스 반환
        if self.mock_mode:
            print(f"🔧 모킹 모드: 버스 {bus_number} 가상 스캔")
            mock_devices = {
                0: [0x76, 0x77],  # BME688 가상 주소
                1: [0x23, 0x5C]   # BH1750, SHT40 가상 주소
            }
            devices = mock_devices.get(bus_number, [])
            
            # 진행률 콜백 시뮬레이션
            if progress_callback:
                for i in range(10):
                    if not self.scanning:
                        break
                    time.sleep(0.1)  # 스캔 시뮬레이션
                    base_progress = 50 if bus_number == 1 else 0
                    current_progress = int((i + 1) / 10 * 50)
                    progress_callback(base_progress + current_progress)
            
            print(f"🔧 버스 {bus_number} 가상 스캔 완료: {len(devices)}개 발견 {[f'0x{addr:02X}' for addr in devices]}")
            return devices
        
        devices = []
        bus = self.buses[bus_number]
        total = 0x77 - 0x08 + 1
        
        print(f"버스 {bus_number} 스캔 시작...")
        
        for i, addr in enumerate(range(0x08, 0x78)):
            if not self.scanning:  # 스캔 중단 확인
                break
                
            device_found = False
            
            # 방법 1: read_byte() 시도
            try:
                bus.read_byte(addr)
                devices.append(addr)
                device_found = True
                print(f"버스 {bus_number}에서 디바이스 발견 (read_byte): 0x{addr:02X}")
            except OSError as e:
                if e.errno == 16:  # Device busy - 실제로는 디바이스 존재
                    devices.append(addr)
                    device_found = True
                    print(f"버스 {bus_number}에서 디바이스 발견 (busy): 0x{addr:02X}")
                elif e.errno in [5, 121]:  # I/O error, Remote I/O error - 디바이스 없음
                    pass
            except Exception:
                pass
            
            # 방법 2: SHT40 특화 테스트 (0x44, 0x45 주소)
            if not device_found and addr in [0x44, 0x45]:
                try:
                    bus.write_byte(addr, 0x89)  # 시리얼 번호 읽기 명령
                    time.sleep(0.001)
                    data = bus.read_i2c_block_data(addr, 0x89, 6)
                    devices.append(addr)
                    device_found = True
                    print(f"버스 {bus_number}에서 SHT40 발견 (시리얼 번호): 0x{addr:02X}")
                except:
                    pass
                
                if not device_found:
                    try:
                        bus.write_byte(addr, 0xFD)  # 고정밀 측정 명령
                        time.sleep(0.01)
                        data = bus.read_i2c_block_data(addr, 0xFD, 6)
                        devices.append(addr)
                        device_found = True
                        print(f"버스 {bus_number}에서 SHT40 발견 (측정 명령): 0x{addr:02X}")
                    except:
                        pass
            
            # 방법 3: 일반적인 레지스터 읽기 시도
            if not device_found:
                common_registers = [0x00, 0x01, 0x0F, 0xD0, 0x75]
                for reg in common_registers:
                    try:
                        bus.read_byte_data(addr, reg)
                        devices.append(addr)
                        device_found = True
                        print(f"버스 {bus_number}에서 디바이스 발견 (레지스터 0x{reg:02X}): 0x{addr:02X}")
                        break
                    except:
                        continue
            
            if progress_callback:
                base_progress = 50 if bus_number == 1 else 0
                current_progress = int((i + 1) / total * 50)
                progress_callback(base_progress + current_progress)
        
        print(f"버스 {bus_number} 스캔 완료: {len(devices)}개 발견 {[f'0x{addr:02X}' for addr in devices]}")
        return devices
    
    def comprehensive_scan(self, progress_callback: Optional[Callable] = None) -> Optional[Dict]:
        """종합 스캔 - 버스 0과 1 자동 스캔"""
        if self.scanning:
            return None
        
        self.scanning = True
        
        try:
            connected_buses = self.connect_buses()
            
            print(f"연결된 버스: {connected_buses}")
            
            if not connected_buses:
                print("사용 가능한 I2C 버스가 없습니다.")
                return None
            
            result = {
                'buses': {},
                'scan_time': datetime.now().isoformat(),
                'total_devices': 0
            }
            
            # 각 버스를 순서대로 스캔
            total_buses = len(connected_buses)
            for idx, bus_num in enumerate(sorted(connected_buses)):
                if not self.scanning:  # 스캔 중단 확인
                    break
                    
                print(f"버스 {bus_num} 스캔 중... ({idx+1}/{total_buses})")
                
                def bus_progress_callback(progress):
                    if progress_callback:
                        base_progress = (idx / total_buses) * 100
                        current_bus_progress = (progress / total_buses)
                        total_progress = int(base_progress + current_bus_progress)
                        progress_callback(total_progress)
                
                devices = self.scan_bus(bus_num, bus_progress_callback)
                
                if devices:
                    result['buses'][bus_num] = devices
                    result['total_devices'] += len(devices)
                    print(f"버스 {bus_num}에서 {len(devices)}개 디바이스 발견")
                else:
                    print(f"버스 {bus_num}에서 디바이스를 찾지 못함")
            
            if progress_callback:
                progress_callback(100)
            
            print(f"전체 스캔 결과: {result}")
            return result
            
        finally:
            self.scanning = False
    
    def scan_async(self, progress_callback: Optional[Callable] = None, 
                   complete_callback: Optional[Callable] = None) -> bool:
        """비동기 스캔 시작"""
        if self.scanning:
            return False
        
        def scan_worker():
            try:
                result = self.comprehensive_scan(progress_callback)
                if complete_callback:
                    complete_callback(result, None)
            except Exception as e:
                if complete_callback:
                    complete_callback(None, str(e))
        
        self.scan_thread = threading.Thread(target=scan_worker)
        self.scan_thread.daemon = True
        self.scan_thread.start()
        return True
    
    def stop_scan(self):
        """스캔 중단"""
        self.scanning = False
        if self.scan_thread and self.scan_thread.is_alive():
            self.scan_thread.join(timeout=5.0)
    
    def test_device(self, bus_number: int, address: int) -> Dict:
        """특정 디바이스 테스트"""
        if bus_number not in self.buses:
            return {"error": "I2C 버스 연결 없음"}
        
        # 모킹 모드인 경우 가상 테스트 결과 반환
        if self.mock_mode:
            print(f"🔧 모킹 모드: 디바이스 0x{address:02X} 가상 테스트")
            return self._mock_test_device(address)
        
        bus = self.buses[bus_number]
        
        try:
            # SHT40 온습도센서 테스트
            if address in [0x44, 0x45]:
                return self._test_sht40(bus, address)
            
            # BH1750 조도센서 테스트
            elif address in [0x23, 0x5C]:
                return self._test_bh1750(bus, address)
            
            # BME280/BME688 환경센서 테스트
            elif address in [0x76, 0x77]:
                return self._test_bme_series(bus, address)
            
            # 기본 연결 테스트
            else:
                return self._test_basic_connection(bus, address)
                
        except Exception as e:
            return {"error": str(e)}
    
    def _mock_test_device(self, address: int) -> Dict:
        """모킹 모드 디바이스 테스트"""
        import random
        
        # 가상 센서 데이터 생성
        if address in [0x44, 0x45]:  # SHT40
            temp = round(random.uniform(20.0, 25.0), 1)
            humidity = round(random.uniform(40.0, 60.0), 1)
            return {
                "success": True,
                "type": "온습도센서 (SHT40) - 가상",
                "values": {
                    "온도": f"{temp}°C",
                    "습도": f"{humidity}%RH",
                    "상태": "가상 데이터"
                }
            }
        elif address in [0x23, 0x5C]:  # BH1750
            lux = round(random.uniform(100.0, 500.0), 1)
            return {
                "success": True,
                "type": "조도센서 (BH1750) - 가상",
                "values": {
                    "조도": f"{lux} lux",
                    "상태": "가상 데이터"
                }
            }
        elif address in [0x76, 0x77]:  # BME688
            return {
                "success": True,
                "type": "환경센서 (BME688) - 가상",
                "values": {
                    "센서": "BME688 확인됨",
                    "칩 ID": "0x61",
                    "상태": "가상 연결"
                }
            }
        else:
            return {
                "success": True,
                "type": "연결 테스트 - 가상",
                "values": {
                    "상태": "가상 연결 정상",
                    "응답": "가상 디바이스 응답함"
                }
            }
    
    def _test_sht40(self, bus, addr: int) -> Dict:
        """SHT40 온습도센서 테스트"""
        try:
            # 소프트 리셋
            bus.write_byte(addr, 0x94)
            time.sleep(0.002)
            
            # 고정밀 측정 명령
            bus.write_byte(addr, 0xFD)
            time.sleep(0.02)
            
            # 6바이트 데이터 읽기
            data = []
            for i in range(6):
                data.append(bus.read_byte(addr))
                time.sleep(0.001)
            
            if len(data) >= 6:
                temp_raw = (data[0] << 8) | data[1]
                hum_raw = (data[3] << 8) | data[4]
                
                temperature = -45 + 175 * temp_raw / 65535
                humidity = 100 * hum_raw / 65535
                
                if -40 <= temperature <= 125 and 0 <= humidity <= 100:
                    return {
                        "success": True,
                        "type": "온습도센서 (SHT40)",
                        "values": {
                            "온도": f"{temperature:.1f}°C",
                            "습도": f"{humidity:.1f}%RH",
                            "상태": "정상"
                        }
                    }
            
            # 측정 실패 시 연결 테스트만
            bus.write_byte(addr, 0x89)  # 시리얼 번호
            time.sleep(0.001)
            data = [bus.read_byte(addr) for _ in range(6)]
            
            return {
                "success": True,
                "type": "온습도센서 (SHT40)",
                "values": {
                    "상태": "연결 확인됨",
                    "참고": "측정 데이터 읽기 실패"
                }
            }
            
        except Exception as e:
            return {"error": f"SHT40 테스트 실패: {e}"}
    
    def _test_bh1750(self, bus, addr: int) -> Dict:
        """BH1750 조도센서 테스트"""
        try:
            bus.write_byte(addr, 0x20)
            time.sleep(0.12)
            
            data = bus.read_i2c_block_data(addr, 0x20, 2)
            lux = ((data[0] << 8) + data[1]) / 1.2
            
            return {
                "success": True,
                "type": "조도센서 (BH1750)",
                "values": {
                    "조도": f"{lux:.1f} lux",
                    "상태": "정상"
                }
            }
        except Exception as e:
            return {"error": f"BH1750 테스트 실패: {e}"}
    
    def _test_bme_series(self, bus, addr: int) -> Dict:
        """BME280/BME688 시리즈 센서 테스트"""
        try:
            chip_id = bus.read_byte_data(addr, 0xD0)
            
            sensor_name = "BME280" if chip_id == 0x60 else "BME688" if chip_id == 0x61 else "BME 시리즈"
            
            return {
                "success": True,
                "type": f"환경센서 ({sensor_name})",
                "values": {
                    "센서": f"{sensor_name} 확인됨",
                    "칩 ID": f"0x{chip_id:02X}",
                    "상태": "정상 연결"
                }
            }
        except Exception as e:
            return {"error": f"BME 시리즈 센서 테스트 실패: {e}"}
    
    def _test_basic_connection(self, bus, addr: int) -> Dict:
        """기본 연결 테스트"""
        try:
            bus.read_byte(addr)
            
            return {
                "success": True,
                "type": "연결 테스트",
                "values": {
                    "상태": "연결 정상",
                    "응답": "디바이스 응답함"
                }
            }
        except Exception as e:
            return {"error": f"연결 테스트 실패: {e}"}
    
    def close(self):
        """리소스 정리"""
        self.stop_scan()
        
        print("I2C 버스 연결 정리 중...")
        for bus_num, bus in self.buses.items():
            try:
                bus.close()
                print(f"  버스 {bus_num} 연결 해제됨")
            except Exception as e:
                print(f"  버스 {bus_num} 해제 오류: {e}")
        self.buses.clear()
        print("✅ 모든 I2C 연결 정리 완료")

def test_web_scanner():
    """웹 스캐너 테스트"""
    print("=" * 60)
    print("웹 I2C 스캐너 테스트")
    print("=" * 60)
    
    scanner = WebI2CScanner()
    
    def progress_callback(progress):
        print(f"스캔 진행률: {progress}%")
    
    try:
        print("\n1. 동기 스캔 테스트:")
        result = scanner.comprehensive_scan(progress_callback)
        
        if result:
            print(f"스캔 완료: {result['total_devices']}개 디바이스 발견")
            for bus_num, devices in result['buses'].items():
                print(f"  버스 {bus_num}: {[f'0x{addr:02X}' for addr in devices]}")
        else:
            print("스캔 실패 또는 디바이스 없음")
        
        print("\n2. 디바이스 테스트 (연결된 디바이스가 있는 경우):")
        if result and result['buses']:
            for bus_num, devices in result['buses'].items():
                if devices:
                    addr = devices[0]  # 첫 번째 디바이스 테스트
                    test_result = scanner.test_device(bus_num, addr)
                    if "error" in test_result:
                        print(f"  0x{addr:02X} 테스트 실패: {test_result['error']}")
                    else:
                        print(f"  0x{addr:02X} 테스트 성공: {test_result['type']}")
                    break
        
    finally:
        scanner.close()
    
    print("\n✅ 웹 스캐너 테스트 완료")

if __name__ == "__main__":
    test_web_scanner()