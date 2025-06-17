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
        
        # 센서 안정성 개선을 위한 변수들
        self.last_read_time = 0
        self.min_interval = 3.0  # 3초 최소 간격
        self.cached_data = None
        self.cache_valid_time = 2.0  # 캐시 유효 시간
        self.error_count = 0
        self.max_errors = 3
        self.backoff_time = 30.0  # 30초 대기
        
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
        """캘리브레이션 데이터 읽기 (BME688 공식 방식)"""
        try:
            # 첫 번째 블록 읽기 (0x89~0xA1)
            coeff1 = self.bus.read_i2c_block_data(self.address, const.COEFF_ADDR1, const.COEFF_ADDR1_LEN)
            # 두 번째 블록 읽기 (0xe1~0xf0)
            coeff2 = self.bus.read_i2c_block_data(self.address, const.COEFF_ADDR2, const.COEFF_ADDR2_LEN)
            
            # 전체 캘리브레이션 배열 생성
            calibration = coeff1 + coeff2
            
            # 온도 캘리브레이션 계수
            self.calibration_data['par_t1'] = const.bytes_to_word(calibration[const.T1_MSB_REG], calibration[const.T1_LSB_REG])
            self.calibration_data['par_t2'] = const.bytes_to_word(calibration[const.T2_MSB_REG], calibration[const.T2_LSB_REG], bits=16, signed=True)
            self.calibration_data['par_t3'] = const.twos_comp(calibration[const.T3_REG], bits=8)
            
            # 압력 캘리브레이션 계수
            self.calibration_data['par_p1'] = const.bytes_to_word(calibration[const.P1_MSB_REG], calibration[const.P1_LSB_REG])
            self.calibration_data['par_p2'] = const.bytes_to_word(calibration[const.P2_MSB_REG], calibration[const.P2_LSB_REG], bits=16, signed=True)
            self.calibration_data['par_p3'] = const.twos_comp(calibration[const.P3_REG], bits=8)
            self.calibration_data['par_p4'] = const.bytes_to_word(calibration[const.P4_MSB_REG], calibration[const.P4_LSB_REG], bits=16, signed=True)
            self.calibration_data['par_p5'] = const.bytes_to_word(calibration[const.P5_MSB_REG], calibration[const.P5_LSB_REG], bits=16, signed=True)
            self.calibration_data['par_p6'] = const.twos_comp(calibration[const.P6_REG], bits=8)
            self.calibration_data['par_p7'] = const.twos_comp(calibration[const.P7_REG], bits=8)
            self.calibration_data['par_p8'] = const.bytes_to_word(calibration[const.P8_MSB_REG], calibration[const.P8_LSB_REG], bits=16, signed=True)
            self.calibration_data['par_p9'] = const.bytes_to_word(calibration[const.P9_MSB_REG], calibration[const.P9_LSB_REG], bits=16, signed=True)
            self.calibration_data['par_p10'] = calibration[const.P10_REG]
            
            # 습도 캘리브레이션 계수
            self.calibration_data['par_h1'] = (calibration[const.H1_MSB_REG] << const.HUM_REG_SHIFT_VAL) | (calibration[const.H1_LSB_REG] & const.BIT_H1_DATA_MSK)
            self.calibration_data['par_h2'] = (calibration[const.H2_MSB_REG] << const.HUM_REG_SHIFT_VAL) | (calibration[const.H2_LSB_REG] >> const.HUM_REG_SHIFT_VAL)
            self.calibration_data['par_h3'] = const.twos_comp(calibration[const.H3_REG], bits=8)
            self.calibration_data['par_h4'] = const.twos_comp(calibration[const.H4_REG], bits=8)
            self.calibration_data['par_h5'] = const.twos_comp(calibration[const.H5_REG], bits=8)
            self.calibration_data['par_h6'] = calibration[const.H6_REG]
            self.calibration_data['par_h7'] = const.twos_comp(calibration[const.H7_REG], bits=8)
            
            # 가스 히터 캘리브레이션 계수
            self.calibration_data['par_gh1'] = const.twos_comp(calibration[const.GH1_REG], bits=8)
            self.calibration_data['par_gh2'] = const.bytes_to_word(calibration[const.GH2_MSB_REG], calibration[const.GH2_LSB_REG], bits=16, signed=True)
            self.calibration_data['par_gh3'] = const.twos_comp(calibration[const.GH3_REG], bits=8)
            
            # 기타 캘리브레이션 값
            heat_range = self.bus.read_byte_data(self.address, const.ADDR_RES_HEAT_RANGE_ADDR)
            heat_value = self.bus.read_byte_data(self.address, const.ADDR_RES_HEAT_VAL_ADDR)
            sw_error = self.bus.read_byte_data(self.address, const.ADDR_RANGE_SW_ERR_ADDR)
            
            self.calibration_data['res_heat_range'] = (heat_range & const.RHRANGE_MSK) // 16
            self.calibration_data['res_heat_val'] = heat_value
            self.calibration_data['range_sw_err'] = (sw_error & const.RSERROR_MSK) // 16
            
            # t_fine 초기화
            self.calibration_data['t_fine'] = 0.0
            
            print("✅ BME688 캘리브레이션 데이터 읽기 완료")
            
        except Exception as e:
            print(f"⚠️ BME688 캘리브레이션 읽기 실패: {e}")
            # 기본값 설정 (실제 BME688 예시 값)
            self.calibration_data = {
                'par_t1': 26828, 'par_t2': 26400, 'par_t3': 3,
                'par_p1': 36477, 'par_p2': -10685, 'par_p3': 88, 'par_p4': 7032, 'par_p5': -154,
                'par_p6': 30, 'par_p7': 32, 'par_p8': -992, 'par_p9': -3424, 'par_p10': 30,
                'par_h1': 515, 'par_h2': 694, 'par_h3': 0, 'par_h4': 45, 'par_h5': 20, 'par_h6': 120, 'par_h7': -100,
                'par_gh1': -1, 'par_gh2': -15, 'par_gh3': 18,
                'res_heat_range': 1, 'res_heat_val': 0, 'range_sw_err': 0,
                't_fine': 0.0
            }
            print(f"⚠️ 기본 캘리브레이션 데이터 사용 중")
    
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
        """센서 데이터 읽기 (안정성 개선된 버전)"""
        if not self.connected:
            return self._attempt_reconnection()
        
        current_time = time.time()
        
        # 캐시된 데이터 반환 (최소 간격 제한)
        if (current_time - self.last_read_time < self.min_interval and 
            self.cached_data and 
            current_time - self.last_read_time < self.cache_valid_time):
            return self.cached_data
        
        # 에러 백오프 처리
        if self.error_count >= self.max_errors:
            if current_time - self.last_read_time < self.backoff_time:
                return self.cached_data
            else:
                self.error_count = 0  # 백오프 시간 후 에러 카운트 리셋
        
        # 실제 측정 시도
        return self._read_sensor_data_with_retry()
    
    def _read_sensor_data_with_retry(self):
        """재시도 로직을 포함한 센서 데이터 읽기"""
        max_retries = 3
        
        for retry in range(max_retries):
            try:
                data = self._read_sensor_data()
                if data:
                    # 성공 시 에러 카운트 리셋 및 캐시 업데이트
                    self.error_count = 0
                    self.last_read_time = time.time()
                    self.cached_data = data
                    return data
                else:
                    print(f"⚠️ BME688 데이터 읽기 실패 (retry {retry + 1}/{max_retries})")
                    
            except Exception as e:
                print(f"⚠️ BME688 에러 (retry {retry + 1}/{max_retries}): {e}")
                
            # 재시도 전 대기 (지수적 백오프)
            if retry < max_retries - 1:
                wait_time = 0.5 * (2 ** retry)  # 0.5, 1.0, 2.0초
                time.sleep(wait_time)
                self._reinitialize_sensor()
        
        # 모든 재시도 실패
        self.error_count += 1
        self.last_read_time = time.time()
        
        if self.error_count >= self.max_errors:
            print(f"❌ BME688 연속 에러 {self.max_errors}회, {self.backoff_time}초 대기 모드")
            self.connected = False
        
        return self.cached_data  # 마지막 성공 데이터 반환
    
    def _read_sensor_data(self):
        """실제 센서 데이터 읽기 (적응형 대기시간 적용)"""
        # 강제 모드로 측정 시작
        ctrl_meas = (const.OS_2X << const.OST_POS) | (const.OS_1X << const.OSP_POS) | const.FORCED_MODE
        self.bus.write_byte_data(self.address, const.CONF_T_P_MODE_ADDR, ctrl_meas)
        
        # 적응형 대기 시간 (최대 1초)
        max_wait_cycles = 10
        for i in range(max_wait_cycles):
            time.sleep(0.1)  # 100ms씩 대기
            
            try:
                status = self.bus.read_byte_data(self.address, const.FIELD0_ADDR)
                if status & const.NEW_DATA_MSK:  # 측정 완료 확인
                    break
            except Exception as e:
                print(f"⚠️ BME688 상태 확인 실패: {e}")
                return None
        else:
            print("⚠️ BME688 측정 타임아웃 (1초)")
            return None
            
            # BME688 필드 데이터 읽기 (17바이트)
            field_data = self.bus.read_i2c_block_data(self.address, const.FIELD0_ADDR, const.FIELD_LENGTH)
            
            # 데이터 변환 (BME688 공식 방식)
            # 온도 데이터 (0x22-0x24)
            temp_raw = (field_data[5] << 12) | (field_data[6] << 4) | (field_data[7] >> 4)
            # 압력 데이터 (0x1F-0x21)
            press_raw = (field_data[2] << 12) | (field_data[3] << 4) | (field_data[4] >> 4)
            # 습도 데이터 (0x25-0x26)
            hum_raw = (field_data[8] << 8) | field_data[9]
            # 가스 데이터 (0x2A-0x2B)
            gas_raw = (field_data[13] << 2) | (field_data[14] >> 6)
            gas_range = field_data[14] & const.GAS_RANGE_MSK
            
            # 실제 값으로 변환 (간소화된 알고리즘)
            temperature = self._compensate_temperature(temp_raw)
            pressure = self._compensate_pressure(press_raw, temperature)
            humidity = self._compensate_humidity(hum_raw, temperature)
            gas_resistance = self._compensate_gas(gas_raw, gas_range)
            
            return {
                'temperature': temperature,
                'humidity': humidity,
                'pressure': pressure,
                'gas_resistance': gas_resistance,
                'air_quality': self._calculate_air_quality(gas_resistance)
            }
            
        except Exception as e:
            print(f"❌ BME688 _read_sensor_data 에러: {e}")
            raise e  # 상위 함수에서 재시도 처리
    
    def _reinitialize_sensor(self):
        """센서 재초기화"""
        try:
            print("🔄 BME688 센서 재초기화 시도...")
            # 소프트 리셋
            self.bus.write_byte_data(self.address, const.SOFT_RESET_ADDR, const.SOFT_RESET_CMD)
            time.sleep(const.RESET_PERIOD / 1000.0)
            
            # 설정 재적용
            self._configure_sensor()
            print("✅ BME688 센서 재초기화 성공")
            
        except Exception as e:
            print(f"❌ BME688 재초기화 실패: {e}")
    
    def _attempt_reconnection(self):
        """연결 단절 시 재연결 시도"""
        current_time = time.time()
        
        # 백오프 시간 체크
        if current_time - self.last_read_time < self.backoff_time:
            return self.cached_data
        
        print("🔄 BME688 센서 재연결 시도...")
        self.connected = self._initialize()
        
        if self.connected:
            self.error_count = 0
            return self._read_sensor_data_with_retry()
        else:
            self.last_read_time = current_time
            return self.cached_data
    
    def _compensate_temperature(self, temp_raw):
        """온도 보정 (BME688 공식 알고리즘)"""
        if not temp_raw:
            return 0.0
        
        # BME688 공식 온도 보정 알고리즘
        var1 = (temp_raw / 16384.0) - (self.calibration_data['par_t1'] / 1024.0)
        var2 = var1 * self.calibration_data['par_t2']
        var3 = (var1 * var1) * (self.calibration_data['par_t3'] * 16.0)
        
        # t_fine 계산 (다른 보정에서 사용)
        self.calibration_data['t_fine'] = var2 + var3
        
        # 실제 온도 계산
        temperature = self.calibration_data['t_fine'] / 5120.0
        
        # 디버깅 정보
        if temperature < -10 or temperature > 50:
            print(f"⚠️ 비정상 온도: {temperature:.1f}°C, temp_raw: {temp_raw}, t_fine: {self.calibration_data['t_fine']:.1f}")
            print(f"   par_t1: {self.calibration_data['par_t1']}, par_t2: {self.calibration_data['par_t2']}, par_t3: {self.calibration_data['par_t3']}")
        
        return max(-40.0, min(85.0, temperature))  # 센서 범위 제한
    
    def _compensate_pressure(self, press_raw, temperature):
        """압력 보정 (BME688 공식 알고리즘)"""
        if not press_raw:
            return 0.0
        
        # BME688 공식 압력 보정 알고리즘
        var1 = (self.calibration_data['t_fine'] / 2.0) - 64000.0
        var2 = var1 * var1 * (self.calibration_data['par_p6'] / 131072.0)
        var2 = var2 + (var1 * self.calibration_data['par_p5'] * 2.0)
        var2 = (var2 / 4.0) + (self.calibration_data['par_p4'] * 65536.0)
        var1 = ((self.calibration_data['par_p3'] * var1 * var1 / 16384.0) + (self.calibration_data['par_p2'] * var1)) / 524288.0
        var1 = (1.0 + (var1 / 32768.0)) * self.calibration_data['par_p1']
        
        if var1 == 0:
            return 0.0
        
        pressure = 1048576.0 - press_raw
        pressure = ((pressure - (var2 / 4096.0)) * 6250.0) / var1
        var1 = (self.calibration_data['par_p9'] * pressure * pressure) / 2147483648.0
        var2 = pressure * (self.calibration_data['par_p8'] / 32768.0)
        var3 = (pressure / 256.0) * (pressure / 256.0) * (pressure / 256.0) * (self.calibration_data['par_p10'] / 131072.0)
        
        pressure = pressure + (var1 + var2 + var3 + (self.calibration_data['par_p7'] * 128.0)) / 16.0
        
        return max(300.0, min(1100.0, pressure / 100.0))  # Pa를 hPa로 변환
    
    def _compensate_humidity(self, hum_raw, temperature):
        """습도 보정 (BME688 공식 알고리즘)"""
        if not hum_raw:
            return 0.0
        
        # BME688 공식 습도 보정 알고리즘
        temp_scaled = self.calibration_data['t_fine'] / 5120.0
        var1 = hum_raw - (self.calibration_data['par_h1'] * 16.0 + (self.calibration_data['par_h3'] / 2.0) * temp_scaled)
        var2 = var1 * (self.calibration_data['par_h2'] / 262144.0 * (1.0 + (self.calibration_data['par_h4'] / 16384.0) * temp_scaled + (self.calibration_data['par_h5'] / 1048576.0) * temp_scaled * temp_scaled))
        var3 = self.calibration_data['par_h6'] / 16384.0
        var4 = self.calibration_data['par_h7'] / 2097152.0
        
        humidity = var2 + (var3 + var4 * temp_scaled) * var2 * var2
        
        return max(0.0, min(100.0, humidity))  # 습도 범위 제한
    
    def _compensate_gas(self, gas_raw, gas_range):
        """가스 저항 보정 (BME688 공식 알고리즘)"""
        if not gas_raw:
            return 0.0
        
        # BME688 공식 가스 저항 보정 알고리즘
        var1 = 1340.0 + 5.0 * self.calibration_data['range_sw_err']
        var2 = var1 * (1.0 + self.calibration_data['par_gh1'] / 32768.0)
        var3 = 1.0 + self.calibration_data['par_gh2'] / 32768.0
        
        gas_resistance = var2 * gas_raw / (var3 * const.lookupTable1[gas_range])
        
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