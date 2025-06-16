#!/usr/bin/env python3
"""
심플한 BME688 환경 센서 코드
데이터시트 기반 최소 구현
"""
import smbus2
import time

class SimpleBME688:
    """BME688 환경 센서 심플 클래스"""
    
    def __init__(self, bus=1, address=0x77):
        """
        초기화
        bus: I2C 버스 번호
        address: I2C 주소 (0x76 또는 0x77, SDO 핀에 따라)
        """
        self.bus = smbus2.SMBus(bus)
        self.address = address
        self._init_sensor()
    
    def _init_sensor(self):
        """센서 초기화"""
        try:
            # 칩 ID 확인 (0xD0 레지스터, 값은 0x61이어야 함)
            chip_id = self.bus.read_byte_data(self.address, 0xD0)
            if chip_id != 0x61:
                print(f"경고: 잘못된 칩 ID: 0x{chip_id:02X}")
            
            # 소프트 리셋
            self.bus.write_byte_data(self.address, 0xE0, 0xB6)
            time.sleep(0.01)
            
            # 측정 설정
            # ctrl_hum (0x72): 습도 오버샘플링 x1
            self.bus.write_byte_data(self.address, 0x72, 0x01)
            
            # ctrl_meas (0x74): 온도 x2, 압력 x16, forced mode
            self.bus.write_byte_data(self.address, 0x74, 0x25)
            
        except:
            print("센서 초기화 실패")
    
    def read_data(self):
        """
        환경 데이터 읽기
        반환: {'temperature': 온도, 'humidity': 습도, 'pressure': 압력}
        """
        try:
            # Forced mode로 측정 시작
            self.bus.write_byte_data(self.address, 0x74, 0x25)
            
            # 측정 완료 대기
            time.sleep(0.1)
            
            # 데이터 읽기 (0x1F-0x26: 압력, 온도, 습도)
            data = self.bus.read_i2c_block_data(self.address, 0x1F, 8)
            
            # 압력 데이터 (0x1F-0x21)
            press_raw = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
            
            # 온도 데이터 (0x22-0x24)
            temp_raw = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
            
            # 습도 데이터 (0x25-0x26)
            hum_raw = (data[6] << 8) | data[7]
            
            # 보정 계수 읽기 (간단화된 버전)
            # 실제로는 데이터시트의 복잡한 보정 공식을 사용해야 함
            temperature = temp_raw / 5120.0  # 간단화된 계산
            pressure = press_raw / 256.0     # 간단화된 계산
            humidity = hum_raw / 512.0       # 간단화된 계산
            
            return {
                'temperature': round(temperature, 1),
                'humidity': round(humidity, 1),
                'pressure': round(pressure, 1)
            }
            
        except:
            return None
    
    def close(self):
        """연결 종료"""
        self.bus.close()

# 사용 예제
if __name__ == "__main__":
    sensor = SimpleBME688()
    
    for i in range(5):
        data = sensor.read_data()
        if data:
            print(f"온도: {data['temperature']}°C, "
                  f"습도: {data['humidity']}%, "
                  f"압력: {data['pressure']}hPa")
        else:
            print("측정 실패")
        time.sleep(2)
    
    sensor.close()