#!/usr/bin/env python3
"""
EZ-Dash 실제 센서 관리자
- BME688: 온도, 습도, 압력, 가스저항
- BH1750: 조도
- 진동: 가상 센서 (시간대별 패턴)
"""

import time
import smbus2
import random
import math
from datetime import datetime
import constants as const

class BH1750Sensor:
    """BH1750 조도 센서 클래스"""
    
    # BH1750 주소 및 명령어
    DEVICE_ADDRESS = 0x23
    POWER_DOWN = 0x00
    POWER_ON = 0x01
    RESET = 0x07
    CONTINUOUS_HIGH_RES_MODE = 0x10
    CONTINUOUS_HIGH_RES_MODE_2 = 0x11
    CONTINUOUS_LOW_RES_MODE = 0x13
    ONE_TIME_HIGH_RES_MODE = 0x20
    ONE_TIME_HIGH_RES_MODE_2 = 0x21
    ONE_TIME_LOW_RES_MODE = 0x23
    
    def __init__(self, bus_number=1, address=0x23):
        self.bus_number = bus_number
        self.address = address
        self.bus = None
        
    def connect(self):
        """BH1750 센서 연결 및 초기화"""
        try:
            self.bus = smbus2.SMBus(self.bus_number)
            
            # 센서 초기화
            self.bus.write_byte(self.address, self.POWER_ON)
            time.sleep(0.01)
            self.bus.write_byte(self.address, self.RESET)
            time.sleep(0.01)
            self.bus.write_byte(self.address, self.CONTINUOUS_HIGH_RES_MODE)
            time.sleep(0.2)  # 측정 시간 대기
            
            print(f"BH1750 조도센서 연결 성공 (주소: 0x{self.address:02X})")
            return True
            
        except Exception as e:
            print(f"WARNING: BH1750 연결 실패: {e}")
            return False
    
    def read_light(self):
        """조도 데이터 읽기 (lux)"""
        try:
            # 연속 고해상도 모드로 측정
            self.bus.write_byte(self.address, self.CONTINUOUS_HIGH_RES_MODE)
            time.sleep(0.2)  # 측정 완료 대기
            
            # 2바이트 데이터 읽기
            data = self.bus.read_i2c_block_data(self.address, self.CONTINUOUS_HIGH_RES_MODE, 2)
            
            # 조도 계산 (BH1750 공식)
            light_lux = (data[0] << 8 | data[1]) / 1.2
            
            return round(light_lux, 1)
            
        except Exception as e:
            print(f"WARNING: BH1750 데이터 읽기 실패: {e}")
            return None

class BME688Sensor:
    """BME688 센서 클래스 (기존 코드 기반)"""
    
    def __init__(self, bus_number=1, address=0x77, temp_offset=-10.0):
        self.bus_number = bus_number
        self.address = address
        self.bus = None
        self.temp_offset = temp_offset
        self.cal_data = const.CalibrationData()
        
    def connect(self):
        """센서 연결 및 초기화"""
        try:
            self.bus = smbus2.SMBus(self.bus_number)
            
            # 칩 ID 확인
            chip_id = self.bus.read_byte_data(self.address, const.CHIP_ID_ADDR)
            if chip_id != const.CHIP_ID:
                print(f"ERROR: BME680/688이 아닙니다. 칩 ID: 0x{chip_id:02X}")
                return False
                
            print(f"BME688 센서 연결 성공 (칩 ID: 0x{chip_id:02X})")
            
            # 소프트 리셋
            self.bus.write_byte_data(self.address, const.SOFT_RESET_ADDR, const.SOFT_RESET_CMD)
            time.sleep(0.01)
            
            # 캘리브레이션 데이터 읽기
            if not self.read_calibration():
                return False
                
            # 센서 설정
            if not self.configure_sensor():
                return False
                
            print("BME688 초기화 완료")
            return True
            
        except Exception as e:
            print(f"ERROR: BME688 연결 실패: {e}")
            return False
    
    def read_calibration(self):
        """캘리브레이션 데이터 읽기"""
        try:
            # 첫 번째 캘리브레이션 영역 읽기
            coeff1 = []
            for i in range(const.COEFF_ADDR1_LEN):
                coeff1.append(self.bus.read_byte_data(self.address, const.COEFF_ADDR1 + i))
            
            # 두 번째 캘리브레이션 영역 읽기
            coeff2 = []
            for i in range(const.COEFF_ADDR2_LEN):
                coeff2.append(self.bus.read_byte_data(self.address, const.COEFF_ADDR2 + i))
            
            # 전체 캘리브레이션 배열
            calibration = coeff1 + coeff2
            self.cal_data.set_from_array(calibration)
            
            # 추가 보정값 읽기
            heat_range = self.bus.read_byte_data(self.address, const.ADDR_RES_HEAT_RANGE_ADDR)
            heat_value = self.bus.read_byte_data(self.address, const.ADDR_RES_HEAT_VAL_ADDR)
            sw_error = self.bus.read_byte_data(self.address, const.ADDR_RANGE_SW_ERR_ADDR)
            
            self.cal_data.set_other(heat_range, heat_value, sw_error)
            return True
            
        except Exception as e:
            print(f"ERROR: BME688 캘리브레이션 읽기 실패: {e}")
            return False
    
    def configure_sensor(self):
        """센서 설정"""
        try:
            # 습도 오버샘플링 x2
            self.bus.write_byte_data(self.address, const.CONF_OS_H_ADDR, const.OS_2X)
            
            # 온도 x4, 압력 x16, 강제 모드
            ctrl_meas = (const.OS_4X << const.OST_POS) | (const.OS_16X << const.OSP_POS) | const.FORCED_MODE
            self.bus.write_byte_data(self.address, const.CONF_T_P_MODE_ADDR, ctrl_meas)
            
            # IIR 필터 계수 7
            config = const.FILTER_SIZE_7 << const.FILTER_POS
            self.bus.write_byte_data(self.address, const.CONF_ODR_FILT_ADDR, config)
            
            # 가스 센서 설정
            self.setup_gas_sensor()
            return True
            
        except Exception as e:
            print(f"ERROR: BME688 센서 설정 실패: {e}")
            return False
    
    def setup_gas_sensor(self):
        """가스 센서 설정"""
        try:
            # 가스 히터 온도 계산 (320도)
            target_temp = 320
            amb_temp = 25
            
            # Bosch 공식 사용한 히터 저항 계산
            var1 = (self.cal_data.par_gh1 / 16.0) + 49.0
            var2 = ((self.cal_data.par_gh2 / 32768.0) * 0.0005) + 0.00235
            var3 = self.cal_data.par_gh3 / 1024.0
            var4 = var1 * (1.0 + (var2 * target_temp))
            var5 = var4 + (var3 * amb_temp)
            
            res_heat = int(3.4 * ((var5 * (4.0 / (4.0 + self.cal_data.res_heat_range)) *
                    (1.0 / (1.0 + (self.cal_data.res_heat_val * 0.002)))) - 25))
            
            # 가스 히터 온도 설정
            self.bus.write_byte_data(self.address, const.RES_HEAT0_ADDR, max(0, min(255, res_heat)))
            
            # 가스 히터 지속시간 (150ms)
            duration_ms = 150
            factor = 0
            durval = 0xFF
            
            if duration_ms >= 0xfc0:
                durval = 0xff
            else:
                while duration_ms > 0x3F:
                    duration_ms = duration_ms // 4
                    factor += 1
                durval = duration_ms + (factor * 64)
            
            self.bus.write_byte_data(self.address, const.GAS_WAIT0_ADDR, durval)
            
            # 가스 측정 활성화
            gas_conf = const.RUN_GAS_ENABLE << const.RUN_GAS_POS
            self.bus.write_byte_data(self.address, const.CONF_ODR_RUN_GAS_NBC_ADDR, gas_conf)
            
            # 히터 제어 활성화
            self.bus.write_byte_data(self.address, const.CONF_HEAT_CTRL_ADDR, const.ENABLE_HEATER)
            
        except Exception as e:
            print(f"WARNING: 가스 센서 설정 실패: {e}")
    
    def read_field_data(self):
        """센서 데이터 읽기"""
        try:
            # 강제 측정 모드 시작
            ctrl_meas = (const.OS_4X << const.OST_POS) | (const.OS_16X << const.OSP_POS) | const.FORCED_MODE
            self.bus.write_byte_data(self.address, const.CONF_T_P_MODE_ADDR, ctrl_meas)
            
            # 측정 완료 대기
            time.sleep(0.5)
            
            # 상태 확인
            status = self.bus.read_byte_data(self.address, const.FIELD0_ADDR)
            new_data = status & const.NEW_DATA_MSK
            
            if not new_data:
                return None
            
            # 온도 데이터 읽기 (20비트)
            temp_data = []
            for i in range(3):
                temp_data.append(self.bus.read_byte_data(self.address, 0x22 + i))
            temp_adc = (temp_data[0] << 12) | (temp_data[1] << 4) | (temp_data[2] >> 4)
            
            # 압력 데이터 읽기 (20비트)
            press_data = []
            for i in range(3):
                press_data.append(self.bus.read_byte_data(self.address, 0x1F + i))
            press_adc = (press_data[0] << 12) | (press_data[1] << 4) | (press_data[2] >> 4)
            
            # 습도 데이터 읽기 (16비트)
            hum_data = []
            for i in range(2):
                hum_data.append(self.bus.read_byte_data(self.address, 0x25 + i))
            hum_adc = (hum_data[0] << 8) | hum_data[1]
            
            # 가스 데이터 읽기
            gas_data = []
            for i in range(2):
                gas_data.append(self.bus.read_byte_data(self.address, 0x2A + i))
            gas_adc = (gas_data[0] << 2) | (gas_data[1] >> 6)
            gas_range = gas_data[1] & 0x0F
            gas_valid = gas_data[1] & const.GASM_VALID_MSK
            heat_stable = gas_data[1] & const.HEAT_STAB_MSK
            
            return {
                'temp_adc': temp_adc,
                'press_adc': press_adc,
                'hum_adc': hum_adc,
                'gas_adc': gas_adc,
                'gas_range': gas_range,
                'gas_valid': gas_valid,
                'heat_stable': heat_stable
            }
            
        except Exception as e:
            print(f"ERROR: BME688 데이터 읽기 실패: {e}")
            return None
    
    def compensate_temperature(self, temp_adc):
        """온도 보정 계산"""
        var1 = (temp_adc / 16384.0 - self.cal_data.par_t1 / 1024.0) * self.cal_data.par_t2
        var2 = ((temp_adc / 131072.0 - self.cal_data.par_t1 / 8192.0) * 
                (temp_adc / 131072.0 - self.cal_data.par_t1 / 8192.0)) * (self.cal_data.par_t3 * 16.0)
        
        self.cal_data.t_fine = var1 + var2
        temp_comp = (var1 + var2) / 5120.0
        
        return temp_comp + self.temp_offset
    
    def compensate_pressure(self, press_adc):
        """압력 보정 계산"""
        var1 = (self.cal_data.t_fine / 2.0) - 64000.0
        var2 = var1 * var1 * (self.cal_data.par_p6 / 131072.0)
        var2 = var2 + (var1 * self.cal_data.par_p5 * 2.0)
        var2 = (var2 / 4.0) + (self.cal_data.par_p4 * 65536.0)
        var1 = (((self.cal_data.par_p3 * var1 * var1) / 16384.0) + 
                (self.cal_data.par_p2 * var1)) / 524288.0
        var1 = (1.0 + (var1 / 32768.0)) * self.cal_data.par_p1
        
        if var1 == 0:
            return 0
        
        press_comp = 1048576.0 - press_adc
        press_comp = ((press_comp - (var2 / 4096.0)) * 6250.0) / var1
        var1 = (self.cal_data.par_p9 * press_comp * press_comp) / 2147483648.0
        var2 = press_comp * (self.cal_data.par_p8 / 32768.0)
        var3 = ((press_comp / 256.0) * (press_comp / 256.0) * 
                (press_comp / 256.0) * (self.cal_data.par_p10 / 131072.0))
        press_comp = press_comp + (var1 + var2 + var3 + (self.cal_data.par_p7 * 128.0)) / 16.0
        
        return press_comp / 100.0  # Pa를 hPa로 변환
    
    def compensate_humidity(self, hum_adc):
        """습도 보정 계산"""
        temp_scaled = self.cal_data.t_fine / 5120.0
        
        var1 = hum_adc - (self.cal_data.par_h1 * 16.0 + 
                         (self.cal_data.par_h3 / 2.0) * temp_scaled)
        var2 = var1 * ((self.cal_data.par_h2 / 262144.0) * 
                      (1.0 + (self.cal_data.par_h4 / 16384.0) * temp_scaled + 
                       (self.cal_data.par_h5 / 1048576.0) * temp_scaled * temp_scaled))
        var3 = self.cal_data.par_h6 / 16384.0
        var4 = self.cal_data.par_h7 / 2097152.0
        hum_comp = var2 + ((var3 + (var4 * temp_scaled)) * var2 * var2)
        
        return max(0.0, min(100.0, hum_comp))
    
    def compensate_gas_resistance(self, gas_adc, gas_range):
        """가스 저항 보정 계산"""
        if gas_adc == 0 or gas_range >= len(const.lookupTable1):
            return 0
        
        var1 = const.lookupTable1[gas_range]
        var2 = const.lookupTable2[gas_range]
        
        var3 = ((1340.0 + (5.0 * self.cal_data.res_heat_range)) * var1) / 65536.0
        gas_res = var3 + (var2 * gas_adc) / 512.0 + gas_adc
        
        return gas_res
    
    def read_sensor_data(self):
        """완전한 센서 데이터 읽기"""
        field_data = self.read_field_data()
        if not field_data:
            return None
        
        # 온도 보정 (가장 먼저)
        temperature = self.compensate_temperature(field_data['temp_adc'])
        
        # 압력 보정 (t_fine 사용)
        pressure = self.compensate_pressure(field_data['press_adc'])
        
        # 습도 보정 (t_fine 사용)
        humidity = self.compensate_humidity(field_data['hum_adc'])
        
        # 가스 저항 보정
        gas_resistance = 0
        if field_data['gas_valid'] and field_data['heat_stable']:
            gas_resistance = self.compensate_gas_resistance(
                field_data['gas_adc'], field_data['gas_range'])
        
        return {
            'temperature': temperature,
            'pressure': pressure,
            'humidity': humidity,
            'gas_resistance': gas_resistance,
            'gas_valid': bool(field_data['gas_valid']),
            'heat_stable': bool(field_data['heat_stable'])
        }

class SensorManager:
    """통합 센서 관리자"""
    
    def __init__(self):
        self.bme688 = None
        self.bh1750 = None
        self.use_real_sensors = True
        self.fallback_mode = False
        self.base_pressure = 1013.25  # 기준 대기압 (hPa)
        
        # 더미 데이터 범위 (폴백용)
        self.sensor_ranges = {
            'temperature': {'min': 20, 'max': 28},
            'humidity': {'min': 40, 'max': 75},
            'light': {'min': 500, 'max': 1500},
            'pressure': {'min': 5, 'max': 20},
            'vibration': {'min': 0.01, 'max': 0.5}
        }
    
    def initialize_sensors(self):
        """모든 센서 초기화"""
        print("=" * 50)
        print("EZ-Dash 센서 시스템 초기화")
        print("=" * 50)
        
        success_count = 0
        
        # BME688 초기화
        self.bme688 = BME688Sensor()
        if self.bme688.connect():
            success_count += 1
        else:
            self.bme688 = None
        
        # BH1750 초기화
        self.bh1750 = BH1750Sensor()
        if self.bh1750.connect():
            success_count += 1
        else:
            self.bh1750 = None
        
        # 센서 상태 요약
        print(f"\n센서 초기화 완료: {success_count}/2개 센서 연결")
        
        if success_count == 0:
            print("WARNING: 모든 센서 연결 실패. 더미 데이터 모드로 전환합니다.")
            self.fallback_mode = True
        elif success_count < 2:
            print("WARNING: 일부 센서만 연결됨. 하이브리드 모드로 동작합니다.")
        else:
            print("SUCCESS: 모든 센서 정상 연결됨.")
        
        return success_count > 0
    
    def generate_virtual_vibration(self):
        """가상 진동 센서 (시간대별 패턴)"""
        current_hour = datetime.now().hour
        
        # 시간대별 기본 진동 레벨
        if 6 <= current_hour <= 8:  # 아침 러시아워
            base_vibration = 0.15
        elif 18 <= current_hour <= 20:  # 저녁 러시아워
            base_vibration = 0.20
        elif 22 <= current_hour or current_hour <= 6:  # 야간
            base_vibration = 0.03
        else:  # 평상시
            base_vibration = 0.08
        
        # 랜덤 변동 추가 (±30%)
        variation = random.uniform(-0.3, 0.3)
        vibration = base_vibration * (1 + variation)
        
        # 가끔 스파이크 (트럭 지나가기 등)
        if random.random() < 0.05:  # 5% 확률
            vibration += random.uniform(0.1, 0.3)
        
        return round(max(0.01, min(0.5, vibration)), 2)
    
    def calculate_pressure_differential(self, absolute_pressure):
        """절대압력을 차압으로 변환"""
        # 기준 대기압과의 차이를 Pa 단위로 계산
        differential = (absolute_pressure - self.base_pressure) * 100  # hPa → Pa
        return round(differential, 1)
    
    def calculate_air_quality_index(self, gas_resistance):
        """가스 저항을 공기질 지수로 변환 (0-100)"""
        if gas_resistance <= 0:
            return 0
        
        # Bosch 권장 공식을 기반으로 한 간단한 AQI 계산
        if gas_resistance > 50000:
            aqi = 90 + (gas_resistance - 50000) / 10000  # 우수
        elif gas_resistance > 20000:
            aqi = 50 + (gas_resistance - 20000) / 750    # 보통-양호
        elif gas_resistance > 10000:
            aqi = 25 + (gas_resistance - 10000) / 400    # 나쁨-보통
        else:
            aqi = gas_resistance / 400                   # 매우나쁨-나쁨
        
        return round(min(100, max(0, aqi)))
    
    def read_all_sensors(self):
        """모든 센서 데이터 읽기"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 실제 센서 데이터 초기화
        temperature = None
        humidity = None
        pressure = None
        light = None
        gas_resistance = 0
        
        # BME688 데이터 읽기
        if self.bme688:
            try:
                bme_data = self.bme688.read_sensor_data()
                if bme_data:
                    temperature = round(bme_data['temperature'], 1)
                    humidity = round(bme_data['humidity'], 1)
                    pressure = round(bme_data['pressure'], 1)
                    gas_resistance = bme_data['gas_resistance']
            except Exception as e:
                print(f"WARNING: BME688 읽기 실패: {e}")
        
        # BH1750 데이터 읽기
        if self.bh1750:
            try:
                light_data = self.bh1750.read_light()
                if light_data is not None:
                    light = int(light_data)
            except Exception as e:
                print(f"WARNING: BH1750 읽기 실패: {e}")
        
        # 폴백 데이터 생성 (실패한 센서용)
        if temperature is None:
            temperature = round(random.uniform(20, 28), 1)
        if humidity is None:
            humidity = round(random.uniform(40, 75), 1)
        if pressure is None:
            pressure = round(random.uniform(1000, 1020), 1)
        if light is None:
            # 시간대별 조도 패턴
            current_hour = datetime.now().hour
            if 6 <= current_hour <= 18:  # 낮
                light = int(random.uniform(500, 1500))
            else:  # 밤
                light = int(random.uniform(50, 300))
        
        # 차압 계산
        pressure_differential = self.calculate_pressure_differential(pressure)
        
        # 가상 진동 센서
        vibration = self.generate_virtual_vibration()
        
        # 공기질 지수 계산
        air_quality = self.calculate_air_quality_index(gas_resistance)
        
        return {
            'timestamp': timestamp,
            'temperature': temperature,
            'humidity': humidity,
            'light': light,
            'pressure': pressure_differential,  # 차압으로 변환
            'vibration': vibration,
            'gas_resistance': gas_resistance,
            'air_quality': air_quality,
            'absolute_pressure': pressure  # 참고용 절대압력
        }
    
    def get_sensor_status(self):
        """센서 연결 상태 반환"""
        return {
            'bme688_connected': self.bme688 is not None,
            'bh1750_connected': self.bh1750 is not None,
            'fallback_mode': self.fallback_mode,
            'sensor_count': sum([
                self.bme688 is not None,
                self.bh1750 is not None
            ])
        }
    
    def close_sensors(self):
        """센서 연결 종료"""
        if self.bme688 and self.bme688.bus:
            self.bme688.bus.close()
        if self.bh1750 and self.bh1750.bus:
            self.bh1750.bus.close()

def test_sensor_manager():
    """센서 매니저 테스트"""
    print("센서 매니저 테스트 시작")
    
    manager = SensorManager()
    
    if not manager.initialize_sensors():
        print("센서 초기화 실패")
        return
    
    # 센서 상태 출력
    status = manager.get_sensor_status()
    print(f"\n센서 상태:")
    print(f"- BME688: {'연결됨' if status['bme688_connected'] else '연결안됨'}")
    print(f"- BH1750: {'연결됨' if status['bh1750_connected'] else '연결안됨'}")
    print(f"- 폴백 모드: {'활성' if status['fallback_mode'] else '비활성'}")
    
    # 데이터 읽기 테스트
    print("\n데이터 읽기 테스트 (10회):")
    print("-" * 80)
    
    for i in range(10):
        data = manager.read_all_sensors()
        print(f"[{data['timestamp']}] "
              f"온도: {data['temperature']:5.1f}°C | "
              f"습도: {data['humidity']:5.1f}% | "
              f"조도: {data['light']:4d}lux | "
              f"차압: {data['pressure']:6.1f}Pa | "
              f"진동: {data['vibration']:.2f}g | "
              f"공기질: {data['air_quality']:2.0f}/100")
        time.sleep(2)
    
    manager.close_sensors()
    print("\n테스트 완료")

if __name__ == "__main__":
    test_sensor_manager()