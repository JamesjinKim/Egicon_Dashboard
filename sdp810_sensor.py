#!/usr/bin/env python3
"""
SDP810 차압센서 클래스
Sensirion SDP810 differential pressure sensor driver
"""

import time
import smbus2

class SDP810Sensor:
    """SDP810 차압센서 클래스 (simpleEddy.py 방식)"""
    
    def __init__(self, bus, address=0x25):
        self.bus = bus
        self.address = address
        self.connected = False
        
        # 연결 테스트 및 초기화
        self.connected = self._initialize()
    
    def _initialize(self):
        """SDP810 센서 초기화 (직접 통신 테스트)"""
        try:
            # 직접 3바이트 읽기 시도 (simpleEddy.py 방식)
            pressure, crc_ok, msg = self._read_pressure_direct()
            
            if pressure is not None:
                print(f"✅ SDP810 센서 초기화 완료 (주소: 0x{self.address:02X}) - 압력: {pressure:.1f} Pa")
                return True
            else:
                print(f"❌ SDP810 초기화 실패: {msg}")
                return False
                
        except Exception as e:
            print(f"❌ SDP810 초기화 실패: {e}")
            return False
    
    def _calculate_crc8(self, data):
        """CRC-8 계산 (simpleEddy.py 방식)"""
        crc = 0xFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = crc << 1
                crc &= 0xFF
        return crc
    
    def _read_pressure_direct(self):
        """직접 압력 읽기 (simpleEddy.py 방식)"""
        try:
            # 3바이트 직접 읽기 [pressure_msb, pressure_lsb, crc]
            read_msg = smbus2.i2c_msg.read(self.address, 3)
            self.bus.i2c_rdwr(read_msg)
            raw_data = list(read_msg)
            
            if len(raw_data) != 3:
                return None, False, f"데이터 길이 오류: {len(raw_data)}"
            
            pressure_msb = raw_data[0]
            pressure_lsb = raw_data[1]
            received_crc = raw_data[2]
            
            # CRC 검증
            calculated_crc = self._calculate_crc8([pressure_msb, pressure_lsb])
            crc_ok = calculated_crc == received_crc
            
            # 압력 계산 (simpleEddy.py 방식)
            import struct
            raw_pressure = struct.unpack('>h', bytes([pressure_msb, pressure_lsb]))[0]
            pressure_pa = raw_pressure / 60.0  # simpleEddy.py의 스케일링
            
            return pressure_pa, crc_ok, "OK"
            
        except Exception as e:
            return None, False, f"읽기 오류: {e}"
    
    def read_data(self):
        """차압 데이터 읽기 (외부 인터페이스)"""
        if not self.connected:
            return None
        
        # 직접 읽기 방식 사용
        pressure, crc_ok, msg = self._read_pressure_direct()
        
        if pressure is not None:
            # 센서 범위 제한 적용 (±500 Pa)
            pressure = max(-500.0, min(500.0, pressure))
            return pressure
        
        return None
    
    def read_full_data(self):
        """전체 데이터 읽기 (차압 + CRC 상태)"""
        if not self.connected:
            return None
        
        pressure, crc_ok, msg = self._read_pressure_direct()
        
        if pressure is not None:
            return {
                'pressure': pressure,
                'crc_ok': crc_ok,
                'message': msg
            }
        
        return None
    
    def close(self):
        """센서 연결 해제"""
        self.connected = False


# 테스트 코드
if __name__ == "__main__":
    import time
    
    print("SDP810 센서 테스트 시작...")
    
    try:
        # I2C 버스 1에 연결 (라즈베리파이 기본)
        bus = smbus2.SMBus(1)
        sensor = SDP810Sensor(bus, 0x25)
        
        if sensor.connected:
            print("센서 연결 성공!")
            
            # 10초간 데이터 읽기
            for i in range(10):
                pressure = sensor.read_data()
                full_data = sensor.read_full_data()
                
                if pressure is not None:
                    print(f"차압: {pressure:.2f} Pa")
                    if full_data:
                        print(f"상세: 차압={full_data['pressure']:.2f} Pa, "
                              f"CRC 검증={full_data['crc_ok']}, "
                              f"메시지={full_data['message']}")
                else:
                    print("데이터 읽기 실패")
                
                time.sleep(1)
            
            sensor.close()
            
        else:
            print("센서 연결 실패")
            
    except Exception as e:
        print(f"테스트 실패: {e}")
    
    print("테스트 완료")