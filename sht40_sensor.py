#!/usr/bin/env python3
"""
SHT40 온습도센서 클래스
고정밀 디지털 온습도 센서
"""

import time
import smbus2


class SHT40Sensor:
    """SHT40 온습도센서 클래스"""
    
    # SHT40 명령어
    CMD_MEASURE_HIGH_PRECISION = 0xFD
    CMD_SOFT_RESET = 0x94
    
    def __init__(self, bus, address=0x44):
        self.bus = bus
        self.address = address
        self.connected = False
        
        # 연결 테스트 및 초기화
        self.connected = self._initialize()
    
    def _initialize(self):
        """SHT40 센서 초기화"""
        try:
            # 소프트 리셋으로 연결 확인
            write_msg = smbus2.i2c_msg.write(self.address, [self.CMD_SOFT_RESET])
            self.bus.i2c_rdwr(write_msg)
            time.sleep(0.01)
            
            # 측정 명령 테스트
            write_msg = smbus2.i2c_msg.write(self.address, [self.CMD_MEASURE_HIGH_PRECISION])
            self.bus.i2c_rdwr(write_msg)
            time.sleep(0.02)
            
            # 데이터 읽기 테스트
            read_msg = smbus2.i2c_msg.read(self.address, 6)
            self.bus.i2c_rdwr(read_msg)
            
            print(f"✅ SHT40 센서 초기화 완료 (주소: 0x{self.address:02X})")
            return True
            
        except Exception as e:
            print(f"❌ SHT40 초기화 실패: {e}")
            return False
    
    def _calculate_crc(self, data):
        """CRC-8 체크섬 계산"""
        POLYNOMIAL = 0x31
        CRC = 0xFF
        for byte in data:
            CRC ^= byte
            for _ in range(8):
                if CRC & 0x80:
                    CRC = ((CRC << 1) ^ POLYNOMIAL) & 0xFF
                else:
                    CRC = (CRC << 1) & 0xFF
        return CRC
    
    def read_data(self):
        """온도와 습도 측정"""
        if not self.connected:
            return None
            
        try:
            # 고정밀 측정 명령 전송
            write_msg = smbus2.i2c_msg.write(self.address, [self.CMD_MEASURE_HIGH_PRECISION])
            self.bus.i2c_rdwr(write_msg)
            time.sleep(0.02)
            
            # 6바이트 데이터 읽기
            read_msg = smbus2.i2c_msg.read(self.address, 6)
            self.bus.i2c_rdwr(read_msg)
            
            # 읽은 데이터 처리
            data = list(read_msg)
            
            if len(data) >= 6:
                # 온도 및 습도 데이터 분리
                t_data = [data[0], data[1]]
                t_crc = data[2]
                rh_data = [data[3], data[4]]
                rh_crc = data[5]
                
                # CRC 검증
                t_crc_ok = self._calculate_crc(t_data) == t_crc
                rh_crc_ok = self._calculate_crc(rh_data) == rh_crc
                
                if not (t_crc_ok and rh_crc_ok):
                    print("⚠️ SHT40 CRC 검증 실패")
                
                # 원시 데이터를 실제 값으로 변환
                t_raw = (t_data[0] << 8) | t_data[1]
                rh_raw = (rh_data[0] << 8) | rh_data[1]
                
                # 데이터시트의 변환 공식 적용
                temperature = -45 + 175 * (t_raw / 65535.0)
                humidity = -6 + 125 * (rh_raw / 65535.0)
                humidity = max(0, min(100, humidity))  # 0-100% 범위 제한
                
                return {
                    'temperature': round(temperature, 2),
                    'humidity': round(humidity, 2)
                }
            
            return None
            
        except Exception as e:
            print(f"❌ SHT40 데이터 읽기 실패: {e}")
            return None
    
    def get_sensor_info(self):
        """센서 정보 반환"""
        return {
            'type': 'SHT40',
            'name': 'SHT40 온습도 센서',
            'manufacturer': 'Sensirion',
            'address': f'0x{self.address:02X}',
            'connected': self.connected,
            'measurements': ['Temperature', 'Humidity'],
            'units': ['°C', '%RH'],
            'accuracy': '±0.2°C, ±2%RH'
        }
    
    def reset_sensor(self):
        """센서 리셋"""
        if not self.connected:
            return False
            
        try:
            write_msg = smbus2.i2c_msg.write(self.address, [self.CMD_SOFT_RESET])
            self.bus.i2c_rdwr(write_msg)
            time.sleep(0.01)
            print("✅ SHT40 센서 리셋 완료")
            return True
            
        except Exception as e:
            print(f"❌ SHT40 센서 리셋 실패: {e}")
            return False
    
    def close(self):
        """센서 연결 해제"""
        self.connected = False


# 테스트 코드
if __name__ == "__main__":
    import time
    
    print("SHT40 센서 테스트 시작...")
    
    try:
        # I2C 버스 1에 연결 (라즈베리파이 기본)
        bus = smbus2.SMBus(1)
        sensor = SHT40Sensor(bus, 0x44)
        
        if sensor.connected:
            print("센서 연결 성공!")
            
            # 센서 정보 출력
            info = sensor.get_sensor_info()
            print(f"센서 정보: {info}")
            
            # 5회 데이터 읽기
            for i in range(5):
                data = sensor.read_data()
                
                if data:
                    print(f"[{i+1}] 온도: {data['temperature']:.2f}°C, "
                          f"습도: {data['humidity']:.2f}%")
                else:
                    print(f"[{i+1}] 데이터 읽기 실패")
                
                time.sleep(2)
            
            sensor.close()
            
        else:
            print("센서 연결 실패")
            
    except Exception as e:
        print(f"테스트 실패: {e}")
    
    print("테스트 완료")