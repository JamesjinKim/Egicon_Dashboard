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
from sdp810_sensor import SDP810Sensor
from sps30_sensor import SPS30Sensor

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
                    'temperature': temperature,
                    'humidity': humidity
                }
            
            return None
            
        except Exception as e:
            print(f"❌ SHT40 데이터 읽기 실패: {e}")
            return None


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
    """라즈베리파이 전용 센서 관리자 (멀티 센서 지원)"""
    
    def __init__(self):
        # 멀티 센서 지원을 위한 리스트 구조
        self.sht40_sensors = []    # SHT40 센서들
        self.bme688_sensors = []   # BME688 센서들  
        self.bh1750_sensors = []   # BH1750 센서들
        self.sdp810_sensors = []   # SDP810 센서들
        self.sps30_sensors = []    # SPS30 미세먼지 센서들
        
        # 레거시 호환성을 위한 단일 참조 (첫 번째 센서)
        self.sht40 = None
        self.bme688 = None
        self.bh1750 = None
        self.sdp810 = None
        self.sps30 = None
        
        self.buses = {}
        self.sensor_error_count = {}  # 센서별 오류 카운트
        self.last_sensor_config = {}  # 센서 구성 저장
        
        print("🚀 센서 관리자 초기화 (라즈베리파이 전용 - 멀티 센서 지원)")
    
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
        
        # SHT40 센서들 검색 (우선순위 1)
        print("🔍 SHT40 센서 검색 중...")
        self.sht40_sensors = self._find_all_sht40()
        if self.sht40_sensors:
            self.sht40 = self.sht40_sensors[0]['sensor']  # 레거시 호환성 - 센서 객체 참조
            success_count += len(self.sht40_sensors)
        
        # BME688 센서들 검색
        print("🔍 BME688 센서 검색 중...")
        self.bme688_sensors = self._find_all_bme688()
        if self.bme688_sensors:
            self.bme688 = self.bme688_sensors[0]['sensor']  # 레거시 호환성 - 센서 객체 참조
            success_count += len(self.bme688_sensors)
        
        # BH1750 센서들 검색  
        print("🔍 BH1750 센서 검색 중...")
        self.bh1750_sensors = self._find_all_bh1750()
        if self.bh1750_sensors:
            self.bh1750 = self.bh1750_sensors[0]['sensor']  # 레거시 호환성 - 센서 객체 참조
            success_count += len(self.bh1750_sensors)
        
        # SDP810 센서들 검색
        print("🔍 SDP810 센서 검색 중...")
        self.sdp810_sensors = self._find_all_sdp810()
        if self.sdp810_sensors:
            self.sdp810 = self.sdp810_sensors[0]['sensor']  # 레거시 호환성 - 센서 객체 참조
            success_count += len(self.sdp810_sensors)
        
        # SPS30 센서들 검색 (시리얼 통신)
        print("🔍 SPS30 센서 검색 중...")
        self.sps30_sensors = self._find_all_sps30()
        if self.sps30_sensors:
            self.sps30 = self.sps30_sensors[0]['sensor']  # 레거시 호환성 - 센서 객체 참조
            success_count += len(self.sps30_sensors)
        
        total_sensors = 5  # SPS30 추가로 5개 센서 타입
        print(f"📊 센서 초기화 완료: {success_count}/{total_sensors}개 센서 연결")
        
        # 현재 센서 구성 저장
        self._update_sensor_config()
        
        return success_count > 0  # 하나라도 연결되면 성공
    
    def _update_sensor_config(self):
        """현재 센서 구성 업데이트"""
        self.last_sensor_config = {
            'sht40': self.sht40 is not None and self.sht40.connected,
            'bme688': self.bme688 is not None and self.bme688.connected,
            'bh1750': self.bh1750 is not None and self.bh1750.connected,
            'sdp810': self.sdp810 is not None and self.sdp810.connected,
            'sps30': self.sps30 is not None and self.sps30.connected
        }
    
    def _find_all_sht40(self):
        """모든 SHT40 센서들 찾기"""
        found_sensors = []
        sensor_count = 0
        
        for bus_num, bus in self.buses.items():
            for addr in [0x44, 0x45]:  # SHT40 일반적인 주소
                try:
                    sht40 = SHT40Sensor(bus, addr)
                    if sht40.connected:
                        sensor_count += 1
                        alias = f"SHT40-{sensor_count}"
                        sensor_info = {
                            'sensor': sht40,
                            'bus': bus_num,
                            'address': addr,
                            'alias': alias,
                            'id': f"sht40_{sensor_count}"
                        }
                        found_sensors.append(sensor_info)
                        print(f"✅ SHT40 센서 발견 (버스 {bus_num}, 주소 0x{addr:02X}) - {alias}")
                except Exception as e:
                    continue
        
        if not found_sensors:
            print("❌ SHT40 센서를 찾을 수 없습니다")
        
        return found_sensors
    
    def _find_all_bme688(self):
        """모든 BME688 센서들 찾기"""
        found_sensors = []
        sensor_count = 0
        
        for bus_num, bus in self.buses.items():
            for addr in [0x76, 0x77]:  # BME688 일반적인 주소
                try:
                    bme688 = BME688Sensor(bus, addr)
                    if bme688.connected:
                        sensor_count += 1
                        alias = f"BME688-{sensor_count}"
                        sensor_info = {
                            'sensor': bme688,
                            'bus': bus_num,
                            'address': addr,
                            'alias': alias,
                            'id': f"bme688_{sensor_count}"
                        }
                        found_sensors.append(sensor_info)
                        print(f"✅ BME688 센서 발견 (버스 {bus_num}, 주소 0x{addr:02X}) - {alias}")
                except Exception as e:
                    # 해당 주소에 센서가 없음 (정상적인 동작)
                    pass
        
        if not found_sensors:
            print("❌ BME688 센서를 찾을 수 없습니다")
        
        return found_sensors
    
    def _find_all_bh1750(self):
        """모든 BH1750 센서들 찾기"""
        found_sensors = []
        sensor_count = 0
        
        for bus_num, bus in self.buses.items():
            for addr in [0x23, 0x5C]:  # BH1750 일반적인 주소
                try:
                    bh1750 = BH1750Sensor(bus, addr)
                    if bh1750.connected:
                        sensor_count += 1
                        alias = f"BH1750-{sensor_count}"
                        sensor_info = {
                            'sensor': bh1750,
                            'bus': bus_num,
                            'address': addr,
                            'alias': alias,
                            'id': f"bh1750_{sensor_count}"
                        }
                        found_sensors.append(sensor_info)
                        print(f"✅ BH1750 센서 발견 (버스 {bus_num}, 주소 0x{addr:02X}) - {alias}")
                except Exception as e:
                    continue
        
        if not found_sensors:
            print("❌ BH1750 센서를 찾을 수 없습니다")
        
        return found_sensors
    
    def _find_all_sdp810(self):
        """모든 SDP810 센서들 찾기 (simpleEddy.py 방식)"""
        found_sensors = []
        sensor_count = 0
        
        for bus_num, bus in self.buses.items():
            for addr in [0x25, 0x26]:  # SDP810 일반적인 주소
                try:
                    # simpleEddy.py 방식으로 직접 통신 테스트
                    success, pressure, crc_ok = self._test_sdp810_direct(bus, addr)
                    
                    if success:
                        # 통신 성공 시 SDP810Sensor 객체 생성
                        sdp810 = SDP810Sensor(bus, addr)
                        if sdp810.connected:
                            sensor_count += 1
                            alias = f"SDP810-{sensor_count}"
                            status = "✓" if crc_ok else "⚠"
                            sensor_info = {
                                'sensor': sdp810,
                                'bus': bus_num,
                                'address': addr,
                                'alias': alias,
                                'id': f"sdp810_{sensor_count}"
                            }
                            found_sensors.append(sensor_info)
                            print(f"✅ SDP810 센서 발견 (버스 {bus_num}, 주소 0x{addr:02X}) - {alias} {pressure:.1f} Pa {status}")
                except Exception as e:
                    print(f"⚠️ SDP810 테스트 중 오류 (버스 {bus_num}, 주소 0x{addr:02X}): {e}")
                    continue
        
        if not found_sensors:
            print("❌ SDP810 센서를 찾을 수 없습니다")
        
        return found_sensors
    
    def _find_all_sps30(self):
        """모든 SPS30 센서들 찾기 (시리얼 통신)"""
        found_sensors = []
        sensor_count = 0
        
        print("🔍 SPS30 미세먼지 센서 검색 중...")
        
        try:
            # SPS30 센서 자동 검색
            port_path, count = SPS30Sensor.find_sps30()
            
            if port_path and count > 0:
                # 센서 연결 시도
                sps30 = SPS30Sensor(port=port_path)
                
                if sps30.connected:
                    sensor_count += 1
                    alias = f"SPS30-{sensor_count}"
                    
                    sensor_info = {
                        'sensor': sps30,
                        'alias': alias,
                        'type': 'SPS30',
                        'port': port_path,
                        'serial_number': sps30.serial_number,
                        'measurements': ['PM1.0', 'PM2.5', 'PM4.0', 'PM10'],
                        'units': 'μg/m³'
                    }
                    
                    found_sensors.append(sensor_info)
                    print(f"✅ {alias} 연결 성공 (포트: {port_path}, S/N: {sps30.serial_number})")
                else:
                    print(f"❌ SPS30 센서 연결 실패 (포트: {port_path})")
            else:
                print("❌ SPS30 센서를 찾을 수 없습니다")
                
        except Exception as e:
            print(f"❌ SPS30 센서 검색 오류: {e}")
        
        print(f"📊 SPS30 센서 검색 완료: {len(found_sensors)}개 발견")
        return found_sensors
    
    def _test_sdp810_direct(self, bus, address):
        """SDP810 직접 통신 테스트 (simpleEddy.py 방식)"""
        try:
            import struct
            
            # 3바이트 직접 읽기 시도
            read_msg = smbus2.i2c_msg.read(address, 3)
            bus.i2c_rdwr(read_msg)
            raw_data = list(read_msg)
            
            if len(raw_data) == 3:
                # CRC 계산
                crc = 0xFF
                for byte in raw_data[:2]:
                    crc ^= byte
                    for _ in range(8):
                        if crc & 0x80:
                            crc = (crc << 1) ^ 0x31
                        else:
                            crc = crc << 1
                        crc &= 0xFF
                
                crc_ok = crc == raw_data[2]
                
                # 압력 계산 (simpleEddy.py 방식)
                raw_pressure = struct.unpack('>h', bytes(raw_data[:2]))[0]
                pressure_pa = raw_pressure / 60.0
                
                return True, pressure_pa, crc_ok
            
            return False, 0.0, False
            
        except Exception:
            return False, 0.0, False
    
    
    def _handle_sensor_error(self, sensor_name):
        """센서 오류 처리 (자동 재검색 제거)"""
        if sensor_name not in self.sensor_error_count:
            self.sensor_error_count[sensor_name] = 0
        
        self.sensor_error_count[sensor_name] += 1
        
        # 5회 연속 오류 시 센서 비활성화만 수행
        if self.sensor_error_count[sensor_name] >= 5:
            print(f"⚠️ {sensor_name} 센서 5회 연속 오류 - 센서 비활성화")
            print(f"💡 수동 스캔을 통해 센서를 다시 연결하세요.")
            
            if sensor_name == 'bh1750':
                self.bh1750 = None
            elif sensor_name == 'bme688':
                self.bme688 = None
            elif sensor_name == 'sht40':
                self.sht40 = None
            elif sensor_name == 'sdp810':
                self.sdp810 = None
            elif sensor_name == 'sps30':
                self.sps30 = None
            
            # 오류 카운트 리셋
            self.sensor_error_count[sensor_name] = 0
            
    
    
    def read_all_sensors(self):
        """모든 센서 데이터 읽기"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        result = {
            'timestamp': timestamp,
            'temperature': None,
            'humidity': None,
            'pressure': None,           # BME688 절대압력 (hPa)
            'differential_pressure': None,  # SDP810 차압 (Pa)
            'light': None,
            'vibration': 0.0,  # 가상 센서 (고정값)
            'gas_resistance': None,
            'air_quality': None,
            'absolute_pressure': None,
            # SPS30 미세먼지 데이터
            'pm1': None,               # PM1.0 (μg/m³)
            'pm25': None,              # PM2.5 (μg/m³)
            'pm4': None,               # PM4.0 (μg/m³)
            'pm10': None,              # PM10 (μg/m³)
            'sensor_status': {
                'bme688': self.bme688 is not None and self.bme688.connected,
                'bh1750': self.bh1750 is not None and self.bh1750.connected,
                'sht40': self.sht40 is not None and self.sht40.connected,
                'sdp810': self.sdp810 is not None and self.sdp810.connected,
                'sps30': self.sps30 is not None and self.sps30.connected
            }
        }
        
        # SHT40 데이터 읽기 (우선)
        if self.sht40 and self.sht40.connected:
            sht40_data = self.sht40.read_data()
            if sht40_data:
                result['temperature'] = sht40_data['temperature']
                result['humidity'] = sht40_data['humidity']
                # 성공 시 오류 카운트 리셋
                if 'sht40' in self.sensor_error_count:
                    self.sensor_error_count['sht40'] = 0
            else:
                self._handle_sensor_error('sht40')
        
        # BME688 데이터 읽기 (온도/습도가 없을 때만)
        if self.bme688 and self.bme688.connected:
            bme_data = self.bme688.read_data()
            if bme_data:
                # SHT40 데이터가 없을 때만 BME688 온도/습도 사용
                if result['temperature'] is None:
                    result['temperature'] = bme_data['temperature']
                if result['humidity'] is None:
                    result['humidity'] = bme_data['humidity']
                # BME688 고유 데이터는 항상 사용
                result['pressure'] = bme_data['pressure']
                result['gas_resistance'] = bme_data['gas_resistance']
                result['air_quality'] = bme_data['air_quality']
                result['absolute_pressure'] = bme_data['pressure']  # 절대압력 = 압력
                # 성공 시 오류 카운트 리셋
                if 'bme688' in self.sensor_error_count:
                    self.sensor_error_count['bme688'] = 0
            else:
                self._handle_sensor_error('bme688')
        
        # BH1750 데이터 읽기
        if self.bh1750 and self.bh1750.connected:
            light_data = self.bh1750.read_data()
            if light_data is not None:
                result['light'] = light_data
                # 성공 시 오류 카운트 리셋
                if 'bh1750' in self.sensor_error_count:
                    self.sensor_error_count['bh1750'] = 0
            else:
                self._handle_sensor_error('bh1750')
        
        # SDP810 데이터 읽기 (차압)
        if self.sdp810 and self.sdp810.connected:
            differential_pressure_data = self.sdp810.read_data()
            if differential_pressure_data is not None:
                # SDP810 차압을 별도 필드에 저장
                result['differential_pressure'] = differential_pressure_data
                # 성공 시 오류 카운트 리셋
                if 'sdp810' in self.sensor_error_count:
                    self.sensor_error_count['sdp810'] = 0
            else:
                self._handle_sensor_error('sdp810')
        
        # SPS30 데이터 읽기 (미세먼지)
        if self.sps30 and self.sps30.connected:
            print(f"🔍 SPS30 데이터 읽기 시도...")
            sps30_data = self.sps30.read_data()
            if sps30_data:
                print(f"✅ SPS30 데이터 읽기 성공: PM2.5={sps30_data['pm25']:.1f}μg/m³")
                result['pm1'] = sps30_data['pm1']
                result['pm25'] = sps30_data['pm25']
                result['pm4'] = sps30_data['pm4']
                result['pm10'] = sps30_data['pm10']
                # 성공 시 오류 카운트 리셋
                if 'sps30' in self.sensor_error_count:
                    self.sensor_error_count['sps30'] = 0
            else:
                print(f"❌ SPS30 데이터 읽기 실패")
                self._handle_sensor_error('sps30')
        else:
            if self.sps30:
                print(f"⚠️ SPS30 객체 존재하지만 연결 상태: {self.sps30.connected}")
            else:
                print(f"❌ SPS30 객체가 None입니다")
        
        return result
    
    def read_all_sensors_multi(self):
        """모든 센서 데이터 읽기 (멀티 센서 지원)"""
        result = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'sensors': {
                'sht40': [],
                'bme688': [],
                'bh1750': [],
                'sdp810': []
            },
            'sensor_status': {
                'sht40': len(self.sht40_sensors) > 0,
                'bme688': len(self.bme688_sensors) > 0,
                'bh1750': len(self.bh1750_sensors) > 0,
                'sdp810': len(self.sdp810_sensors) > 0
            }
        }
        
        # SHT40 센서들 데이터 읽기
        for sensor_info in self.sht40_sensors:
            sensor = sensor_info['sensor']
            if sensor and sensor.connected:
                data = sensor.read_data()
                if data:
                    result['sensors']['sht40'].append({
                        'id': sensor_info['id'],
                        'alias': sensor_info['alias'],
                        'bus': sensor_info['bus'],
                        'address': f"0x{sensor_info['address']:02X}",
                        'connected': True,
                        'data': data
                    })
                else:
                    result['sensors']['sht40'].append({
                        'id': sensor_info['id'],
                        'alias': sensor_info['alias'],
                        'bus': sensor_info['bus'],
                        'address': f"0x{sensor_info['address']:02X}",
                        'connected': False,
                        'data': None
                    })
        
        # BME688 센서들 데이터 읽기
        for sensor_info in self.bme688_sensors:
            sensor = sensor_info['sensor']
            if sensor and sensor.connected:
                data = sensor.read_data()
                if data:
                    result['sensors']['bme688'].append({
                        'id': sensor_info['id'],
                        'alias': sensor_info['alias'],
                        'bus': sensor_info['bus'],
                        'address': f"0x{sensor_info['address']:02X}",
                        'connected': True,
                        'data': data
                    })
                else:
                    result['sensors']['bme688'].append({
                        'id': sensor_info['id'],
                        'alias': sensor_info['alias'],
                        'bus': sensor_info['bus'],
                        'address': f"0x{sensor_info['address']:02X}",
                        'connected': False,
                        'data': None
                    })
        
        # BH1750 센서들 데이터 읽기
        for sensor_info in self.bh1750_sensors:
            sensor = sensor_info['sensor']
            if sensor and sensor.connected:
                data = sensor.read_data()
                if data is not None:
                    result['sensors']['bh1750'].append({
                        'id': sensor_info['id'],
                        'alias': sensor_info['alias'],
                        'bus': sensor_info['bus'],
                        'address': f"0x{sensor_info['address']:02X}",
                        'connected': True,
                        'data': {'light': data}
                    })
                else:
                    result['sensors']['bh1750'].append({
                        'id': sensor_info['id'],
                        'alias': sensor_info['alias'],
                        'bus': sensor_info['bus'],
                        'address': f"0x{sensor_info['address']:02X}",
                        'connected': False,
                        'data': None
                    })
        
        # SDP810 센서들 데이터 읽기
        for sensor_info in self.sdp810_sensors:
            sensor = sensor_info['sensor']
            if sensor and sensor.connected:
                data = sensor.read_data()
                if data is not None:
                    result['sensors']['sdp810'].append({
                        'id': sensor_info['id'],
                        'alias': sensor_info['alias'],
                        'bus': sensor_info['bus'],
                        'address': f"0x{sensor_info['address']:02X}",
                        'connected': True,
                        'data': {'differential_pressure': data}
                    })
                else:
                    result['sensors']['sdp810'].append({
                        'id': sensor_info['id'],
                        'alias': sensor_info['alias'],
                        'bus': sensor_info['bus'],
                        'address': f"0x{sensor_info['address']:02X}",
                        'connected': False,
                        'data': None
                    })
        
        return result
    
    def rescan_sensors_now(self):
        """즉시 센서 재검색 (API 호출용)"""
        print("🔄 수동 센서 재검색 시작...")
        
        # 기존 센서 상태 저장
        old_config = self.last_sensor_config.copy()
        
        # 모든 센서 재검색
        self.sht40 = self._find_sht40()
        self.bme688 = self._find_bme688()
        self.bh1750 = self._find_bh1750()
        self.sdp810 = self._find_sdp810()
        
        # 오류 카운트 리셋
        self.sensor_error_count.clear()
        
        # 센서 구성 업데이트
        self._update_sensor_config()
        
        # 변경사항 로그
        changes = []
        for sensor, status in self.last_sensor_config.items():
            if old_config.get(sensor) != status:
                status_text = "연결됨" if status else "해제됨"
                changes.append(f"{sensor}: {status_text}")
        
        if changes:
            print(f"🔄 센서 상태 변경: {', '.join(changes)}")
        else:
            print("🔄 센서 상태 변경 없음")
        
        return self.last_sensor_config
    
    def get_sensor_status(self):
        """센서 연결 상태 반환"""
        sht40_connected = self.sht40 is not None and self.sht40.connected
        bme688_connected = self.bme688 is not None and self.bme688.connected
        bh1750_connected = self.bh1750 is not None and self.bh1750.connected
        sdp810_connected = self.sdp810 is not None and self.sdp810.connected
        sps30_connected = self.sps30 is not None and self.sps30.connected
        
        return {
            'sht40_connected': sht40_connected,
            'bme688_connected': bme688_connected,
            'bh1750_connected': bh1750_connected,
            'sdp810_connected': sdp810_connected,
            'sps30_connected': sps30_connected,
            'sensor_count': int(sht40_connected) + int(bme688_connected) + int(bh1750_connected) + int(sdp810_connected) + int(sps30_connected)
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
        self.sht40 = None
        self.bme688 = None
        self.bh1750 = None
        self.sdp810 = None
        
        print("✅ 센서 연결 해제 완료")