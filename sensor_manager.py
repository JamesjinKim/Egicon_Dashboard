#!/usr/bin/env python3
"""
EG-Dash 센서 관리자 (라즈베리파이 전용)
실제 I2C 센서만 지원, 더미 데이터 생성 제거
"""

import time
import smbus2
import random
import math
from datetime import datetime
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
            chip_id = self.bus.read_byte_data(self.address, 0xD0)
            if chip_id != 0x61:
                print(f"❌ BME688 칩 ID 불일치: 0x{chip_id:02X} (예상: 0x61)")
                return False
            
            print(f"✅ BME688 센서 감지됨 (주소: 0x{self.address:02X})")
            
            # 소프트 리셋
            self.bus.write_byte_data(self.address, 0xE0, 0xB6)
            time.sleep(0.01)
            
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
            self.calibration_data['T1'] = self.bus.read_word_data(self.address, 0xE9)
            self.calibration_data['T2'] = self.bus.read_word_data(self.address, 0x8A)
            self.calibration_data['T3'] = self.bus.read_byte_data(self.address, 0x8C)
            
            # 압력 캘리브레이션 (일부만)
            self.calibration_data['P1'] = self.bus.read_word_data(self.address, 0x8E)
            self.calibration_data['P2'] = self.bus.read_word_data(self.address, 0x90)
            
            # 습도 캘리브레이션 (일부만)
            self.calibration_data['H1'] = self.bus.read_byte_data(self.address, 0xE2)
            self.calibration_data['H2'] = self.bus.read_byte_data(self.address, 0xE3)
            
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
            self.bus.write_byte_data(self.address, 0x72, 0x01)
            
            # 온도/압력 오버샘플링 및 모드 설정 (강제 모드)
            self.bus.write_byte_data(self.address, 0x74, 0x25)  # temp x1, press x1, forced mode
            
            time.sleep(0.01)
            
        except Exception as e:
            print(f"⚠️ BME688 설정 실패: {e}")
    
    def read_data(self):
        """센서 데이터 읽기"""
        if not self.connected:
            return None
        
        try:
            # 강제 모드로 측정 시작
            self.bus.write_byte_data(self.address, 0x74, 0x25)
            time.sleep(0.1)  # 측정 대기
            
            # 상태 확인
            status = self.bus.read_byte_data(self.address, 0x1D)
            if not (status & 0x80):  # 측정 완료 확인
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


class BH1750Sensor:
    """BH1750 조도센서 클래스"""
    
    def __init__(self, bus, address=0x23):
        self.bus = bus
        self.address = address
        self.connected = False
        
        # 연결 테스트 및 초기화
        self.connected = self._initialize()
    
    def _initialize(self):
        """BH1750 센서 초기화"""
        try:
            # 전원 켜기
            self.bus.write_byte(self.address, 0x01)
            time.sleep(0.01)
            
            # 리셋
            self.bus.write_byte(self.address, 0x07)
            time.sleep(0.01)
            
            # 연속 측정 모드 설정
            self.bus.write_byte(self.address, 0x10)  # 1 lux 해상도
            time.sleep(0.12)  # 측정 시간 대기
            
            print(f"✅ BH1750 센서 초기화 완료 (주소: 0x{self.address:02X})")
            return True
            
        except Exception as e:
            print(f"❌ BH1750 초기화 실패: {e}")
            return False
    
    def read_data(self):
        """조도 데이터 읽기"""
        if not self.connected:
            return None
        
        try:
            # 데이터 읽기 (2바이트)
            data = self.bus.read_i2c_block_data(self.address, 0x10, 2)
            
            if len(data) >= 2:
                # 조도값 계산
                lux = ((data[0] << 8) | data[1]) / 1.2
                return max(0.0, min(100000.0, lux))  # 센서 범위 제한
            
            return None
            
        except Exception as e:
            print(f"❌ BH1750 데이터 읽기 실패: {e}")
            return None


class SensorManager:
    """라즈베리파이 전용 센서 관리자"""
    
    def __init__(self):
        self.bme688 = None
        self.bh1750 = None
        self.buses = {}
        
        print("🚀 센서 관리자 초기화 (라즈베리파이 전용)")
    
    def initialize_sensors(self):
        """센서 초기화"""
        print("🔍 센서 검색 및 초기화 시작...")
        
        success_count = 0
        
        # I2C 버스 연결
        for bus_num in [0, 1]:
            try:
                bus = smbus2.SMBus(bus_num)
                self.buses[bus_num] = bus
                print(f"✅ I2C 버스 {bus_num} 연결 완료")
            except Exception as e:
                print(f"❌ I2C 버스 {bus_num} 연결 실패: {e}")
        
        if not self.buses:
            print("❌ 사용 가능한 I2C 버스가 없습니다")
            return False
        
        # BME688 센서 검색
        print("🔍 BME688 센서 검색 중...")
        self.bme688 = self._find_bme688()
        if self.bme688:
            success_count += 1
        
        # BH1750 센서 검색  
        print("🔍 BH1750 센서 검색 중...")
        self.bh1750 = self._find_bh1750()
        if self.bh1750:
            success_count += 1
        
        total_sensors = 2
        print(f"📊 센서 초기화 완료: {success_count}/{total_sensors}개 센서 연결")
        
        return success_count > 0  # 하나라도 연결되면 성공
    
    def _find_bme688(self):
        """BME688 센서 찾기"""
        for bus_num, bus in self.buses.items():
            for addr in [0x76, 0x77]:  # BME688 일반적인 주소
                try:
                    bme688 = BME688Sensor(bus, addr)
                    if bme688.connected:
                        print(f"✅ BME688 센서 발견 (버스 {bus_num}, 주소 0x{addr:02X})")
                        return bme688
                except Exception as e:
                    continue
        
        print("❌ BME688 센서를 찾을 수 없습니다")
        return None
    
    def _find_bh1750(self):
        """BH1750 센서 찾기"""
        for bus_num, bus in self.buses.items():
            for addr in [0x23, 0x5C]:  # BH1750 일반적인 주소
                try:
                    bh1750 = BH1750Sensor(bus, addr)
                    if bh1750.connected:
                        print(f"✅ BH1750 센서 발견 (버스 {bus_num}, 주소 0x{addr:02X})")
                        return bh1750
                except Exception as e:
                    continue
        
        print("❌ BH1750 센서를 찾을 수 없습니다")
        return None
    
    def read_all_sensors(self):
        """모든 센서 데이터 읽기"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        result = {
            'timestamp': timestamp,
            'temperature': None,
            'humidity': None,
            'pressure': None,
            'light': None,
            'vibration': 0.0,  # 가상 센서 (고정값)
            'gas_resistance': None,
            'air_quality': None,
            'absolute_pressure': None,
            'sensor_status': {
                'bme688': self.bme688 is not None and self.bme688.connected,
                'bh1750': self.bh1750 is not None and self.bh1750.connected,
                'sht40': False,  # 추후 구현
                'sdp810': False  # 추후 구현
            }
        }
        
        # BME688 데이터 읽기
        if self.bme688 and self.bme688.connected:
            bme_data = self.bme688.read_data()
            if bme_data:
                result['temperature'] = bme_data['temperature']
                result['humidity'] = bme_data['humidity']
                result['pressure'] = bme_data['pressure']
                result['gas_resistance'] = bme_data['gas_resistance']
                result['air_quality'] = bme_data['air_quality']
                result['absolute_pressure'] = bme_data['pressure']  # 절대압력 = 압력
        
        # BH1750 데이터 읽기
        if self.bh1750 and self.bh1750.connected:
            light_data = self.bh1750.read_data()
            if light_data is not None:
                result['light'] = light_data
        
        return result
    
    def get_sensor_status(self):
        """센서 연결 상태 반환"""
        bme688_connected = self.bme688 is not None and self.bme688.connected
        bh1750_connected = self.bh1750 is not None and self.bh1750.connected
        
        return {
            'bme688_connected': bme688_connected,
            'bh1750_connected': bh1750_connected,
            'sensor_count': int(bme688_connected) + int(bh1750_connected)
        }
    
    def close_sensors(self):
        """센서 연결 해제"""
        print("🔌 센서 연결 해제 중...")
        
        for bus in self.buses.values():
            try:
                bus.close()
            except:
                pass
        
        self.buses.clear()
        self.bme688 = None
        self.bh1750 = None
        
        print("✅ 센서 연결 해제 완료")