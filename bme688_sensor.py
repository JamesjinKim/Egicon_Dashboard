#!/usr/bin/env python3
"""
BME688 환경센서 클래스
온도, 습도, 압력, 가스저항 측정
constants.py의 상수들을 활용
"""

import time
import smbus2
import constants as const


class BME688Sensor:
    """BME688 환경센서 클래스 (온도, 습도, 압력, 가스저항)"""
    
    def __init__(self, bus, address=0x76):
        self.bus = bus
        self.address = address
        self.connected = False
        self.calibration_data = {}
        
        # 연결 테스트 및 초기화
        self.connected = self._initialize()
    
    def _initialize(self):
        """BME688 센서 초기화"""
        try:
            # 칩 ID 확인
            chip_id = self.bus.read_byte_data(self.address, const.CHIP_ID_ADDR)
            if chip_id != const.CHIP_ID:
                print(f"❌ BME688 칩 ID 불일치: 0x{chip_id:02X} (예상: 0x{const.CHIP_ID:02X})")
                return False
            
            print(f"✅ BME688 센서 감지됨 (주소: 0x{self.address:02X})")
            
            # 소프트 리셋
            self.bus.write_byte_data(self.address, const.SOFT_RESET_ADDR, const.SOFT_RESET_CMD)
            time.sleep(const.RESET_PERIOD / 1000.0)
            
            # 캘리브레이션 데이터 읽기
            self._read_calibration_data()
            
            # 측정 설정
            self._configure_sensor()
            
            return True
            
        except Exception as e:
            print(f"❌ BME688 초기화 실패: {e}")
            return False
    
    def _read_calibration_data(self):
        """캘리브레이션 데이터 읽기 (간소화)"""
        try:
            # 온도 캘리브레이션
            self.calibration_data['T1'] = self.bus.read_word_data(self.address, const.COEFF_ADDR1)
            self.calibration_data['T2'] = self.bus.read_word_data(self.address, const.COEFF_ADDR1 + 1)
            self.calibration_data['T3'] = self.bus.read_byte_data(self.address, const.COEFF_ADDR1 + 3)
            
            # 압력 캘리브레이션 (일부만)
            self.calibration_data['P1'] = self.bus.read_word_data(self.address, const.COEFF_ADDR1 + 5)
            self.calibration_data['P2'] = self.bus.read_word_data(self.address, const.COEFF_ADDR1 + 7)
            
            # 습도 캘리브레이션 (일부만)
            self.calibration_data['H1'] = self.bus.read_byte_data(self.address, const.COEFF_ADDR2 + 1)
            self.calibration_data['H2'] = self.bus.read_byte_data(self.address, const.COEFF_ADDR2 + 2)
            
            print("✅ BME688 캘리브레이션 데이터 읽기 완료")
            
        except Exception as e:
            print(f"⚠️ BME688 캘리브레이션 읽기 실패: {e}")
            # 기본값 설정
            self.calibration_data = {
                'T1': 27504, 'T2': 26435, 'T3': 3,
                'P1': 36477, 'P2': -10685,
                'H1': 515, 'H2': 694
            }
    
    def _configure_sensor(self):
        """센서 측정 설정"""
        try:
            # 습도 오버샘플링 설정 (x1)
            self.bus.write_byte_data(self.address, const.CONF_OS_H_ADDR, const.OS_1X)
            
            # 온도/압력 오버샘플링 및 모드 설정 (강제 모드)
            ctrl_meas = (const.OS_2X << const.OST_POS) | (const.OS_1X << const.OSP_POS) | const.FORCED_MODE
            self.bus.write_byte_data(self.address, const.CONF_T_P_MODE_ADDR, ctrl_meas)
            
            time.sleep(0.01)
            
        except Exception as e:
            print(f"⚠️ BME688 설정 실패: {e}")
    
    def read_data(self):
        """센서 데이터 읽기"""
        if not self.connected:
            return None
        
        try:
            # 강제 모드로 측정 시작
            ctrl_meas = (const.OS_2X << const.OST_POS) | (const.OS_1X << const.OSP_POS) | const.FORCED_MODE
            self.bus.write_byte_data(self.address, const.CONF_T_P_MODE_ADDR, ctrl_meas)
            time.sleep(0.1)  # 측정 대기
            
            # 상태 확인
            status = self.bus.read_byte_data(self.address, const.FIELD0_ADDR)
            if not (status & const.NEW_DATA_MSK):  # 측정 완료 확인
                print("⚠️ BME688 측정 미완료")
                return None
            
            # 원시 데이터 읽기
            temp_data = self.bus.read_i2c_block_data(self.address, 0x22, 3)
            press_data = self.bus.read_i2c_block_data(self.address, 0x1F, 3)
            hum_data = self.bus.read_i2c_block_data(self.address, 0x25, 2)
            gas_data = self.bus.read_i2c_block_data(self.address, 0x2A, 2)
            
            # 데이터 변환 (간소화된 공식)
            temp_raw = (temp_data[0] << 12) | (temp_data[1] << 4) | (temp_data[2] >> 4)
            press_raw = (press_data[0] << 12) | (press_data[1] << 4) | (press_data[2] >> 4)
            hum_raw = (hum_data[0] << 8) | hum_data[1]
            gas_raw = (gas_data[0] << 2) | (gas_data[1] >> 6)
            
            # 실제 값으로 변환 (간소화된 알고리즘)
            temperature = self._compensate_temperature(temp_raw)
            pressure = self._compensate_pressure(press_raw, temperature)
            humidity = self._compensate_humidity(hum_raw, temperature)
            gas_resistance = self._compensate_gas(gas_raw)
            
            return {
                'temperature': temperature,
                'humidity': humidity,
                'pressure': pressure,
                'gas_resistance': gas_resistance,
                'air_quality': self._calculate_air_quality(gas_resistance)
            }
            
        except Exception as e:
            print(f"❌ BME688 데이터 읽기 실패: {e}")
            return None
    
    def _compensate_temperature(self, temp_raw):
        """온도 보정 (간소화)"""
        if not temp_raw:
            return 0.0
        
        # 간소화된 온도 계산
        var1 = (temp_raw / 16384.0 - self.calibration_data['T1'] / 1024.0) * self.calibration_data['T2']
        var2 = ((temp_raw / 131072.0 - self.calibration_data['T1'] / 8192.0) * 
                (temp_raw / 131072.0 - self.calibration_data['T1'] / 8192.0)) * (self.calibration_data['T3'] * 16.0)
        
        temperature = (var1 + var2) / 5120.0
        return max(-40.0, min(85.0, temperature))  # 센서 범위 제한
    
    def _compensate_pressure(self, press_raw, temperature):
        """압력 보정 (간소화)"""
        if not press_raw:
            return 0.0
        
        # 간소화된 압력 계산
        pressure = press_raw / 64.0 - 102400.0
        pressure = pressure + (self.calibration_data['P1'] - 16384) / 16384.0 * temperature
        pressure = max(300.0, min(1100.0, pressure))  # hPa 범위 제한
        
        return pressure
    
    def _compensate_humidity(self, hum_raw, temperature):
        """습도 보정 (간소화)"""
        if not hum_raw:
            return 0.0
        
        # 간소화된 습도 계산
        humidity = hum_raw * 100.0 / 65536.0
        humidity = humidity + (temperature - 25.0) * 0.1  # 온도 보정
        
        return max(0.0, min(100.0, humidity))  # 습도 범위 제한
    
    def _compensate_gas(self, gas_raw):
        """가스 저항 보정 (간소화)"""
        if not gas_raw:
            return 0.0
        
        # 간소화된 가스 저항 계산
        gas_resistance = gas_raw * 1000.0  # 옴 단위
        return max(0.0, min(200000.0, gas_resistance))
    
    def _calculate_air_quality(self, gas_resistance):
        """공기질 지수 계산 (0-100)"""
        if gas_resistance <= 0:
            return 0
        
        # 가스 저항값을 기반으로 공기질 점수 계산
        # 높은 저항값 = 좋은 공기질
        if gas_resistance > 50000:
            return min(100, int(gas_resistance / 1000))
        else:
            return max(0, int(gas_resistance / 500))
    
    def close(self):
        """센서 연결 해제"""
        self.connected = False


# 테스트 코드
if __name__ == "__main__":
    import time
    
    print("BME688 센서 테스트 시작...")
    
    try:
        # I2C 버스 1에 연결 (라즈베리파이 기본)
        bus = smbus2.SMBus(1)
        sensor = BME688Sensor(bus, 0x77)  # 일반적으로 0x77 주소 사용
        
        if sensor.connected:
            print("센서 연결 성공!")
            
            # 5회 데이터 읽기
            for i in range(5):
                data = sensor.read_data()
                
                if data:
                    print(f"[{i+1}] 온도: {data['temperature']:.1f}°C, "
                          f"습도: {data['humidity']:.1f}%, "
                          f"압력: {data['pressure']:.1f}hPa, "
                          f"가스저항: {data['gas_resistance']:.0f}Ω, "
                          f"공기질: {data['air_quality']}")
                else:
                    print(f"[{i+1}] 데이터 읽기 실패")
                
                time.sleep(2)
            
            sensor.close()
            
        else:
            print("센서 연결 실패")
            
    except Exception as e:
        print(f"테스트 실패: {e}")
    
    print("테스트 완료")