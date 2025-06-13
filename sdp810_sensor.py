#!/usr/bin/env python3
"""
SDP810 차압센서 클래스
Sensirion SDP810 differential pressure sensor driver
"""

import time
import smbus2


class SDP810Sensor:
    """SDP810 차압센서 클래스"""
    
    # SDP810 명령어
    CMD_CONTINUOUS_MEASUREMENT = 0x3603
    CMD_STOP_MEASUREMENT = 0x3FF9
    CMD_SOFT_RESET = 0x0006
    
    def __init__(self, bus, address=0x25):
        self.bus = bus
        self.address = address
        self.connected = False
        self.measurement_started = False
        
        # 연결 테스트 및 초기화
        self.connected = self._initialize()
    
    def _initialize(self):
        """SDP810 센서 초기화"""
        try:
            # 소프트 리셋 (선택적)
            self._soft_reset()
            time.sleep(0.1)
            
            # 연속 측정 시작
            self._start_continuous_measurement()
            time.sleep(0.1)
            
            # 첫 번째 더미 읽기 (센서 안정화)
            test_data = self._read_measurement()
            
            if test_data is not None:
                print(f"✅ SDP810 센서 초기화 완료 (주소: 0x{self.address:02X})")
                return True
            else:
                print(f"❌ SDP810 초기화 실패: 데이터 읽기 실패")
                return False
                
        except Exception as e:
            print(f"❌ SDP810 초기화 실패: {e}")
            return False
    
    def _soft_reset(self):
        """소프트 리셋"""
        try:
            # 소프트 리셋 명령 전송 (2바이트 명령)
            cmd_bytes = [(self.CMD_SOFT_RESET >> 8) & 0xFF, self.CMD_SOFT_RESET & 0xFF]
            write_msg = smbus2.i2c_msg.write(self.address, cmd_bytes)
            self.bus.i2c_rdwr(write_msg)
            time.sleep(0.02)
        except Exception as e:
            print(f"⚠️ SDP810 소프트 리셋 실패: {e}")
    
    def _start_continuous_measurement(self):
        """연속 측정 시작"""
        try:
            # 연속 측정 시작 명령 전송
            cmd_bytes = [(self.CMD_CONTINUOUS_MEASUREMENT >> 8) & 0xFF, 
                        self.CMD_CONTINUOUS_MEASUREMENT & 0xFF]
            write_msg = smbus2.i2c_msg.write(self.address, cmd_bytes)
            self.bus.i2c_rdwr(write_msg)
            self.measurement_started = True
            time.sleep(0.01)
        except Exception as e:
            print(f"❌ SDP810 연속 측정 시작 실패: {e}")
            self.measurement_started = False
    
    def _stop_measurement(self):
        """측정 중지"""
        try:
            cmd_bytes = [(self.CMD_STOP_MEASUREMENT >> 8) & 0xFF, 
                        self.CMD_STOP_MEASUREMENT & 0xFF]
            write_msg = smbus2.i2c_msg.write(self.address, cmd_bytes)
            self.bus.i2c_rdwr(write_msg)
            self.measurement_started = False
            time.sleep(0.01)
        except Exception as e:
            print(f"❌ SDP810 측정 중지 실패: {e}")
    
    def _read_measurement(self):
        """측정 데이터 읽기"""
        try:
            # 9바이트 읽기 (차압 2바이트 + CRC 1바이트 + 온도 2바이트 + CRC 1바이트 + 스케일링 팩터 2바이트 + CRC 1바이트)
            read_msg = smbus2.i2c_msg.read(self.address, 9)
            self.bus.i2c_rdwr(read_msg)
            
            data = list(read_msg)
            
            if len(data) >= 9:
                # 차압 데이터 추출 (첫 2바이트)
                pressure_raw = (data[0] << 8) | data[1]
                
                # 2의 보수 처리 (음수 차압값 지원)
                if pressure_raw > 32767:
                    pressure_raw -= 65536
                
                # 온도 데이터 추출 (4, 5번째 바이트)
                temp_raw = (data[3] << 8) | data[4]
                
                # 스케일링 팩터 추출 (7, 8번째 바이트)
                scale_factor = (data[6] << 8) | data[7]
                
                # 차압 계산 (Pa 단위)
                if scale_factor != 0:
                    pressure_pa = pressure_raw / scale_factor
                else:
                    # 기본 스케일링 팩터 사용 (SDP810 일반값)
                    pressure_pa = pressure_raw / 240.0
                
                # 온도 계산 (섭씨)
                temperature = temp_raw / 200.0
                
                return {
                    'pressure': pressure_pa,
                    'temperature': temperature,
                    'raw_pressure': pressure_raw,
                    'scale_factor': scale_factor
                }
            
            return None
            
        except Exception as e:
            print(f"❌ SDP810 측정 데이터 읽기 실패: {e}")
            return None
    
    def read_data(self):
        """차압 데이터 읽기 (외부 인터페이스)"""
        if not self.connected:
            return None
        
        # 연속 측정이 시작되지 않았다면 시작
        if not self.measurement_started:
            self._start_continuous_measurement()
            time.sleep(0.1)  # 첫 측정 대기
        
        measurement = self._read_measurement()
        
        if measurement is not None:
            # 차압 값만 반환 (센서 범위 제한 적용)
            pressure = measurement['pressure']
            pressure = max(-500.0, min(500.0, pressure))  # ±500 Pa 범위 제한
            return pressure
        
        return None
    
    def read_full_data(self):
        """전체 데이터 읽기 (차압 + 온도)"""
        if not self.connected:
            return None
        
        if not self.measurement_started:
            self._start_continuous_measurement()
            time.sleep(0.1)
        
        return self._read_measurement()
    
    def close(self):
        """센서 연결 해제"""
        if self.connected and self.measurement_started:
            self._stop_measurement()
        self.connected = False
        self.measurement_started = False


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
                              f"온도={full_data['temperature']:.2f}°C, "
                              f"스케일={full_data['scale_factor']}")
                else:
                    print("데이터 읽기 실패")
                
                time.sleep(1)
            
            sensor.close()
            
        else:
            print("센서 연결 실패")
            
    except Exception as e:
        print(f"테스트 실패: {e}")
    
    print("테스트 완료")