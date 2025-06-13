#!/usr/bin/env python3
"""
EG-Dash I2C 스캐너 모듈 (라즈베리파이 전용)
실제 I2C 하드웨어만 지원, Mac 테스트 코드 제거
"""

import time
import smbus2
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime

class WebI2CScanner:
    """라즈베리파이 전용 I2C 스캐너 클래스"""
    
    def __init__(self):
        self.buses = {}
        self.scanning = False
        self.scan_thread = None
    
    def connect_buses(self) -> List[int]:
        """I2C 버스 0과 1에 연결 (실제 하드웨어만)"""
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
                print(f"✅ I2C 버스 {bus_num} 연결 성공")
            except Exception as e:
                print(f"❌ I2C 버스 {bus_num} 연결 실패: {e}")
        
        return connected_buses
    
    def scan_bus(self, bus_number: int, progress_callback: Optional[Callable] = None) -> List[int]:
        """특정 버스 스캔 (실제 하드웨어만)"""
        if bus_number not in self.buses:
            return []
        
        devices = []
        bus = self.buses[bus_number]
        total = 0x77 - 0x08 + 1
        
        print(f"🔍 버스 {bus_number} 스캔 시작...")
        
        for i, addr in enumerate(range(0x08, 0x78)):
            if not self.scanning:  # 스캔 중단 확인
                break
                
            device_found = False
            
            # 방법 1: read_byte() 시도
            try:
                bus.read_byte(addr)
                devices.append(addr)
                device_found = True
                print(f"✅ 버스 {bus_number}에서 디바이스 발견 (read_byte): 0x{addr:02X}")
            except OSError as e:
                if e.errno == 16:  # Device busy - 실제로는 디바이스 존재
                    devices.append(addr)
                    device_found = True
                    print(f"✅ 버스 {bus_number}에서 디바이스 발견 (busy): 0x{addr:02X}")
                elif e.errno in [5, 121]:  # I/O error, Remote I/O error - 디바이스 없음
                    pass
            except Exception:
                pass
            
            # 방법 2: SHT40 특화 테스트 (0x44, 0x45 주소)
            if not device_found and addr in [0x44, 0x45]:
                try:
                    # 소프트 리셋 명령으로 연결 확인
                    write_msg = smbus2.i2c_msg.write(addr, [0x94])  # CMD_SOFT_RESET
                    bus.i2c_rdwr(write_msg)
                    time.sleep(0.01)
                    
                    # 측정 명령을 보내고 데이터를 읽어봄
                    write_msg = smbus2.i2c_msg.write(addr, [0xFD])  # CMD_MEASURE_HIGH_PRECISION
                    bus.i2c_rdwr(write_msg)
                    time.sleep(0.02)
                    
                    # 데이터 읽기 시도
                    read_msg = smbus2.i2c_msg.read(addr, 6)
                    bus.i2c_rdwr(read_msg)
                    
                    devices.append(addr)
                    device_found = True
                    print(f"✅ 버스 {bus_number}에서 SHT40 발견 (저수준 I2C): 0x{addr:02X}")
                except Exception:
                    # 기존 방식으로 재시도
                    try:
                        bus.write_byte(addr, 0xFD)  # 고정밀 측정 명령
                        time.sleep(0.01)
                        data = bus.read_i2c_block_data(addr, 0xFD, 6)
                        devices.append(addr)
                        device_found = True
                        print(f"✅ 버스 {bus_number}에서 SHT40 발견 (측정 명령): 0x{addr:02X}")
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
                        print(f"✅ 버스 {bus_number}에서 디바이스 발견 (레지스터 0x{reg:02X}): 0x{addr:02X}")
                        break
                    except:
                        continue
            
            if progress_callback:
                current_progress = int((i + 1) / total * 100)
                progress_callback(current_progress)
        
        print(f"🏁 버스 {bus_number} 스캔 완료: {len(devices)}개 발견 {[f'0x{addr:02X}' for addr in devices]}")
        return devices
    
    def comprehensive_scan(self, progress_callback: Optional[Callable] = None) -> Optional[Dict]:
        """종합 스캔 - 버스 0과 1 스캔"""
        if self.scanning:
            return None
        
        self.scanning = True
        
        try:
            connected_buses = self.connect_buses()
            
            print(f"🔌 연결된 버스: {connected_buses}")
            
            if not connected_buses:
                print("❌ 사용 가능한 I2C 버스가 없습니다.")
                return None
            
            result = {
                'buses': {},
                'scan_time': datetime.now().isoformat(),
                'total_devices': 0
            }
            
            # 각 버스를 순서대로 스캔
            for idx, bus_num in enumerate(sorted(connected_buses)):
                if not self.scanning:  # 스캔 중단 확인
                    break
                    
                print(f"🔍 버스 {bus_num} 스캔 중... ({idx+1}/{len(connected_buses)})")
                
                def bus_progress_callback(progress):
                    if progress_callback:
                        total_progress = int((idx / len(connected_buses)) * 100 + (progress / len(connected_buses)))
                        progress_callback(total_progress)
                
                devices = self.scan_bus(bus_num, bus_progress_callback)
                
                if devices:
                    result['buses'][bus_num] = devices
                    result['total_devices'] += len(devices)
                    print(f"✅ 버스 {bus_num}에서 {len(devices)}개 디바이스 발견")
                else:
                    print(f"❌ 버스 {bus_num}에서 디바이스를 찾지 못함")
            
            if progress_callback:
                progress_callback(100)
            
            print(f"🎯 전체 스캔 결과: {result}")
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
        """특정 디바이스 테스트 (실제 하드웨어만)"""
        if bus_number not in self.buses:
            return {"error": "I2C 버스 연결 없음"}
        
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
            
            # SDP810 차압센서 테스트
            elif address == 0x25:
                return self._test_sdp810(bus, address)
            
            # 기본 연결 테스트
            else:
                return self._test_basic_connection(bus, address)
                
        except Exception as e:
            return {"error": str(e)}
    
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
                            "온도": f"{temperature:.2f}°C",
                            "습도": f"{humidity:.2f}%RH"
                        }
                    }
            
            return {"error": "SHT40 데이터 읽기 실패"}
            
        except Exception as e:
            return {"error": f"SHT40 테스트 실패: {e}"}
    
    def _test_bh1750(self, bus, addr: int) -> Dict:
        """BH1750 조도센서 테스트"""
        try:
            # 전원 켜기
            bus.write_byte(addr, 0x01)
            time.sleep(0.05)
            
            # 측정 모드 설정
            bus.write_byte(addr, 0x10)
            time.sleep(0.2)
            
            # 데이터 읽기
            data = bus.read_i2c_block_data(addr, 0x10, 2)
            
            if len(data) >= 2:
                lux = ((data[0] << 8) | data[1]) / 1.2
                return {
                    "success": True,
                    "type": "조도센서 (BH1750)",
                    "values": {
                        "조도": f"{lux:.2f} lux"
                    }
                }
            
            return {"error": "BH1750 데이터 읽기 실패"}
            
        except Exception as e:
            return {"error": f"BH1750 테스트 실패: {e}"}
    
    def _test_bme_series(self, bus, addr: int) -> Dict:
        """BME280/BME688 환경센서 테스트"""
        try:
            # 칩 ID 읽기
            chip_id = bus.read_byte_data(addr, 0xD0)
            
            if chip_id == 0x60:
                sensor_type = "BME280"
            elif chip_id == 0x61:
                sensor_type = "BME688"
            else:
                sensor_type = f"Unknown (ID: 0x{chip_id:02X})"
            
            return {
                "success": True,
                "type": f"환경센서 ({sensor_type})",
                "values": {
                    "칩 ID": f"0x{chip_id:02X}",
                    "센서": sensor_type
                }
            }
            
        except Exception as e:
            return {"error": f"BME 시리즈 테스트 실패: {e}"}
    
    def _test_sdp810(self, bus, addr: int) -> Dict:
        """SDP810 차압센서 테스트"""
        try:
            # 3바이트 데이터 읽기 시도
            data = bus.read_i2c_block_data(addr, 0x00, 3)
            
            if len(data) == 3:
                return {
                    "success": True,
                    "type": "차압센서 (SDP810)",
                    "values": {
                        "응답": "연결 확인됨",
                        "데이터": f"[{', '.join(f'0x{b:02X}' for b in data)}]"
                    }
                }
            
            return {"error": "SDP810 데이터 읽기 실패"}
            
        except Exception as e:
            return {"error": f"SDP810 테스트 실패: {e}"}
    
    def _test_basic_connection(self, bus, addr: int) -> Dict:
        """기본 연결 테스트"""
        try:
            # 기본 읽기 시도
            bus.read_byte(addr)
            
            return {
                "success": True,
                "type": "일반 I2C 디바이스",
                "values": {
                    "상태": "연결 확인됨",
                    "주소": f"0x{addr:02X}"
                }
            }
            
        except Exception as e:
            return {"error": f"기본 연결 테스트 실패: {e}"}
    
    def close(self):
        """리소스 정리"""
        self.stop_scan()
        for bus in self.buses.values():
            try:
                bus.close()
            except:
                pass
        self.buses.clear()