#!/usr/bin/env python3
"""
BH1750 조도센서 클래스
디지털 조도 센서 (0-100,000 lux)
"""

import time
import smbus2


class BH1750Sensor:
    """BH1750 조도센서 클래스"""
    
    # BH1750 명령어
    CMD_POWER_ON = 0x01
    CMD_POWER_OFF = 0x00
    CMD_RESET = 0x07
    CMD_CONTINUOUS_HIGH_RES = 0x10    # 1 lux 해상도
    CMD_CONTINUOUS_HIGH_RES2 = 0x11   # 0.5 lux 해상도
    CMD_CONTINUOUS_LOW_RES = 0x13     # 4 lux 해상도
    CMD_ONE_TIME_HIGH_RES = 0x20      # 일회성 고해상도
    CMD_ONE_TIME_HIGH_RES2 = 0x21     # 일회성 고해상도 2
    CMD_ONE_TIME_LOW_RES = 0x23       # 일회성 저해상도
    
    def __init__(self, bus, address=0x23):
        self.bus = bus
        self.address = address
        self.connected = False
        self.measurement_mode = self.CMD_CONTINUOUS_HIGH_RES
        
        # 연결 테스트 및 초기화
        self.connected = self._initialize()
    
    def _initialize(self):
        """BH1750 센서 초기화"""
        try:
            # 전원 켜기
            self.bus.write_byte(self.address, self.CMD_POWER_ON)
            time.sleep(0.01)
            
            # 리셋
            self.bus.write_byte(self.address, self.CMD_RESET)
            time.sleep(0.01)
            
            # 연속 측정 모드 설정 (1 lux 해상도)
            self.bus.write_byte(self.address, self.measurement_mode)
            time.sleep(0.12)  # 측정 시간 대기
            
            print(f"✅ BH1750 센서 초기화 완료 (주소: 0x{self.address:02X})")
            return True
            
        except Exception as e:
            print(f"❌ BH1750 초기화 실패: {e}")
            return False
    
    def set_measurement_mode(self, mode):
        """측정 모드 설정"""
        valid_modes = [
            self.CMD_CONTINUOUS_HIGH_RES,
            self.CMD_CONTINUOUS_HIGH_RES2,
            self.CMD_CONTINUOUS_LOW_RES,
            self.CMD_ONE_TIME_HIGH_RES,
            self.CMD_ONE_TIME_HIGH_RES2,
            self.CMD_ONE_TIME_LOW_RES
        ]
        
        if mode in valid_modes:
            self.measurement_mode = mode
            if self.connected:
                try:
                    self.bus.write_byte(self.address, mode)
                    time.sleep(0.12)  # 측정 시간 대기
                    return True
                except Exception as e:
                    print(f"❌ BH1750 모드 설정 실패: {e}")
                    return False
        else:
            print(f"❌ 유효하지 않은 측정 모드: 0x{mode:02X}")
            return False
    
    def read_data(self):
        """조도 데이터 읽기"""
        if not self.connected:
            return None
        
        try:
            # 일회성 측정 모드인 경우 측정 명령 전송
            if self.measurement_mode in [self.CMD_ONE_TIME_HIGH_RES, 
                                       self.CMD_ONE_TIME_HIGH_RES2, 
                                       self.CMD_ONE_TIME_LOW_RES]:
                self.bus.write_byte(self.address, self.measurement_mode)
                time.sleep(0.18)  # 일회성 측정 대기시간
            
            # 데이터 읽기 (2바이트)
            data = self.bus.read_i2c_block_data(self.address, self.measurement_mode, 2)
            
            if len(data) >= 2:
                # 조도값 계산
                raw_value = (data[0] << 8) | data[1]
                
                # 해상도에 따른 변환
                if self.measurement_mode == self.CMD_CONTINUOUS_HIGH_RES2 or \
                   self.measurement_mode == self.CMD_ONE_TIME_HIGH_RES2:
                    lux = raw_value / 2.4  # 0.5 lux 해상도
                else:
                    lux = raw_value / 1.2  # 1 lux 또는 4 lux 해상도
                
                # 센서 범위 제한 (0-100,000 lux)
                lux = max(0.0, min(100000.0, lux))
                return round(lux, 2)
            
            return None
            
        except Exception as e:
            print(f"❌ BH1750 데이터 읽기 실패: {e}")
            return None
    
    def get_light_level_description(self, lux_value):
        """조도값에 따른 설명 반환"""
        if lux_value is None:
            return "측정 불가"
        elif lux_value < 1:
            return "매우 어두움"
        elif lux_value < 10:
            return "어두움" 
        elif lux_value < 50:
            return "희미함"
        elif lux_value < 200:
            return "실내 조명"
        elif lux_value < 500:
            return "밝은 실내"
        elif lux_value < 1000:
            return "매우 밝은 실내"
        elif lux_value < 10000:
            return "흐린 날 야외"
        elif lux_value < 50000:
            return "맑은 날 그늘"
        else:
            return "직사광선"
    
    def get_sensor_info(self):
        """센서 정보 반환"""
        mode_names = {
            self.CMD_CONTINUOUS_HIGH_RES: "연속측정(1lux)",
            self.CMD_CONTINUOUS_HIGH_RES2: "연속측정(0.5lux)",
            self.CMD_CONTINUOUS_LOW_RES: "연속측정(4lux)",
            self.CMD_ONE_TIME_HIGH_RES: "일회성(1lux)",
            self.CMD_ONE_TIME_HIGH_RES2: "일회성(0.5lux)",
            self.CMD_ONE_TIME_LOW_RES: "일회성(4lux)"
        }
        
        return {
            'type': 'BH1750',
            'name': 'BH1750 조도 센서',
            'manufacturer': 'ROHM',
            'address': f'0x{self.address:02X}',
            'connected': self.connected,
            'measurement_mode': mode_names.get(self.measurement_mode, f'0x{self.measurement_mode:02X}'),
            'measurements': ['Illuminance'],
            'units': ['lux'],
            'range': '0-100,000 lux',
            'accuracy': '±20%'
        }
    
    def power_down(self):
        """센서 전원 절약 모드"""
        if not self.connected:
            return False
            
        try:
            self.bus.write_byte(self.address, self.CMD_POWER_OFF)
            print("✅ BH1750 센서 전원 절약 모드")
            return True
            
        except Exception as e:
            print(f"❌ BH1750 전원 절약 모드 실패: {e}")
            return False
    
    def power_up(self):
        """센서 전원 복구"""
        if not self.connected:
            return False
            
        try:
            self.bus.write_byte(self.address, self.CMD_POWER_ON)
            time.sleep(0.01)
            # 측정 모드 재설정
            self.bus.write_byte(self.address, self.measurement_mode)
            time.sleep(0.12)
            print("✅ BH1750 센서 전원 복구")
            return True
            
        except Exception as e:
            print(f"❌ BH1750 전원 복구 실패: {e}")
            return False
    
    def close(self):
        """센서 연결 해제"""
        if self.connected:
            self.power_down()
        self.connected = False


# 테스트 코드
if __name__ == "__main__":
    import time
    
    print("BH1750 센서 테스트 시작...")
    
    try:
        # I2C 버스 1에 연결 (라즈베리파이 기본)
        bus = smbus2.SMBus(1)
        sensor = BH1750Sensor(bus, 0x23)
        
        if sensor.connected:
            print("센서 연결 성공!")
            
            # 센서 정보 출력
            info = sensor.get_sensor_info()
            print(f"센서 정보: {info}")
            
            # 다양한 측정 모드 테스트
            modes = [
                (sensor.CMD_CONTINUOUS_HIGH_RES, "연속측정(1lux)"),
                (sensor.CMD_CONTINUOUS_HIGH_RES2, "연속측정(0.5lux)"),
                (sensor.CMD_ONE_TIME_HIGH_RES, "일회성(1lux)")
            ]
            
            for mode, mode_name in modes:
                print(f"\n--- {mode_name} 모드 테스트 ---")
                sensor.set_measurement_mode(mode)
                
                for i in range(3):
                    lux = sensor.read_data()
                    
                    if lux is not None:
                        description = sensor.get_light_level_description(lux)
                        print(f"[{i+1}] 조도: {lux:.2f} lux ({description})")
                    else:
                        print(f"[{i+1}] 데이터 읽기 실패")
                    
                    time.sleep(1)
            
            sensor.close()
            
        else:
            print("센서 연결 실패")
            
    except Exception as e:
        print(f"테스트 실패: {e}")
    
    print("테스트 완료")