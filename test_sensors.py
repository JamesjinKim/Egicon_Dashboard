#!/usr/bin/env python3
"""
EG-Dash 센서 통합 테스트 스크립트
- BME688 + BH1750 센서 연결 테스트
- 센서 데이터 읽기 테스트
- API 서버 기능 테스트
"""

import time
import sys
import traceback
from sensor_manager import SensorManager

def test_individual_sensors():
    """개별 센서 테스트"""
    print("🔧 개별 센서 연결 테스트")
    print("-" * 50)
    
    # BME688 테스트
    print("1. BME688 센서 테스트...")
    try:
        from sensor_manager import BME688Sensor
        
        # 자동 검색 먼저 시도
        bme_bus, bme_addr = BME688Sensor.find_bme688()
        if bme_bus is not None:
            bme688 = BME688Sensor(bus_number=bme_bus, address=bme_addr)
            if bme688.connect():
                print("   ✅ BME688 연결 성공")
                
                # 데이터 읽기 테스트
                for i in range(3):
                    data = bme688.read_sensor_data()
                    if data:
                        print(f"   📊 온도: {data['temperature']:.1f}°C, "
                              f"습도: {data['humidity']:.1f}%, "
                              f"압력: {data['pressure']:.1f}hPa, "
                              f"가스: {data['gas_resistance']:.0f}Ω")
                        break
                    time.sleep(1)
                else:
                    print("   ⚠️ BME688 데이터 읽기 실패")
            else:
                print("   ❌ BME688 연결 실패")
        else:
            print("   ❌ BME688 센서를 찾을 수 없음")
    except Exception as e:
        print(f"   ❌ BME688 오류: {e}")
    
    print()
    
    # BH1750 테스트
    print("2. BH1750 센서 테스트...")
    try:
        from sensor_manager import BH1750Sensor
        
        # 자동 검색 먼저 시도
        bh_bus, bh_addr = BH1750Sensor.find_bh1750()
        if bh_bus is not None:
            bh1750 = BH1750Sensor(bus_number=bh_bus, address=bh_addr)
            if bh1750.connect():
                print("   ✅ BH1750 연결 성공")
                
                # 데이터 읽기 테스트
                for i in range(3):
                    light = bh1750.read_light()
                    if light is not None:
                        print(f"   📊 조도: {light:.1f} lux")
                        break
                    time.sleep(1)
                else:
                    print("   ⚠️ BH1750 데이터 읽기 실패")
            else:
                print("   ❌ BH1750 연결 실패")
        else:
            print("   ❌ BH1750 센서를 찾을 수 없음")
    except Exception as e:
        print(f"   ❌ BH1750 오류: {e}")
    
    print()

def test_sensor_manager():
    """센서 매니저 통합 테스트"""
    print("🔄 센서 매니저 통합 테스트")
    print("-" * 50)
    
    try:
        manager = SensorManager()
        
        # 초기화 테스트
        print("1. 센서 매니저 초기화...")
        if manager.initialize_sensors():
            status = manager.get_sensor_status()
            print(f"   ✅ 초기화 완료: {status['sensor_count']}/2개 센서 연결")
            print(f"   📊 BME688: {'연결' if status['bme688_connected'] else '미연결'}")
            print(f"   📊 BH1750: {'연결' if status['bh1750_connected'] else '미연결'}")
            print(f"   📊 모드: {'폴백' if status['fallback_mode'] else '실제센서'}")
        else:
            print("   ❌ 센서 매니저 초기화 실패")
            return False
        
        print()
        
        # 데이터 읽기 테스트
        print("2. 센서 데이터 읽기 테스트 (5회)...")
        for i in range(5):
            try:
                data = manager.read_all_sensors()
                print(f"   [{i+1}] {data['timestamp']}")
                print(f"       온도: {data['temperature']:5.1f}°C | "
                      f"습도: {data['humidity']:5.1f}% | "
                      f"조도: {data['light']:4d}lux")
                print(f"       차압: {data['pressure']:6.1f}Pa | "
                      f"진동: {data['vibration']:.2f}g | "
                      f"공기질: {data['air_quality']:2.0f}/100")
                print(f"       가스저항: {data['gas_resistance']:.0f}Ω | "
                      f"절대압력: {data['absolute_pressure']:.1f}hPa")
                print()
                time.sleep(2)
                
            except Exception as e:
                print(f"   ❌ 데이터 읽기 오류: {e}")
                traceback.print_exc()
        
        # 정리
        manager.close_sensors()
        print("   ✅ 센서 매니저 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 센서 매니저 오류: {e}")
        traceback.print_exc()
        return False

def test_api_functionality():
    """API 기능 테스트"""
    print("🌐 API 기능 테스트")
    print("-" * 50)
    
    try:
        # sensor_api.py 모듈 임포트 및 함수 테스트
        from sensor_api import generate_sensor_data, get_db_connection
        
        print("1. 데이터 생성 함수 테스트...")
        for i in range(3):
            data = generate_sensor_data()
            print(f"   [{i+1}] 온도: {data['temperature']:.1f}°C, "
                  f"습도: {data['humidity']:.1f}%, "
                  f"조도: {data['light']}lux, "
                  f"차압: {data['pressure']:.1f}Pa, "
                  f"진동: {data['vibration']:.2f}g")
        
        print("\n2. 데이터베이스 연결 테스트...")
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 테이블 확인
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"   ✅ 데이터베이스 연결 성공")
            print(f"   📊 테이블: {[table[0] for table in tables]}")
            
            # 현재 데이터 확인
            cursor.execute("SELECT * FROM current_readings WHERE id = 1")
            current = cursor.fetchone()
            if current:
                print(f"   📊 현재 데이터 존재: 온도 {current[1]}°C")
            else:
                print("   ⚠️ 현재 데이터 없음")
            
            conn.close()
            
        except Exception as e:
            print(f"   ❌ 데이터베이스 오류: {e}")
        
        print("   ✅ API 기능 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ API 테스트 오류: {e}")
        traceback.print_exc()
        return False

def test_system_requirements():
    """시스템 요구사항 테스트"""
    print("⚙️ 시스템 요구사항 테스트")
    print("-" * 50)
    
    # 필요한 모듈 확인
    required_modules = [
        'smbus2', 'flask', 'flask_cors', 'sqlite3'
    ]
    
    print("1. 필수 모듈 확인...")
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"   ✅ {module}")
        except ImportError:
            print(f"   ❌ {module} (설치 필요)")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n⚠️ 누락된 모듈: {missing_modules}")
        print("설치 명령: pip install " + " ".join(missing_modules))
        return False
    
    # I2C 확인
    print("\n2. I2C 인터페이스 확인...")
    try:
        import smbus2
        # I2C 버스 열어보기
        for bus_num in [0, 1]:
            try:
                bus = smbus2.SMBus(bus_num)
                bus.close()
                print(f"   ✅ I2C 버스 {bus_num} 사용 가능")
            except:
                print(f"   ⚠️ I2C 버스 {bus_num} 사용 불가")
    except Exception as e:
        print(f"   ❌ I2C 테스트 실패: {e}")
    
    # 파일 권한 확인
    print("\n3. 파일 권한 확인...")
    import os
    try:
        test_file = "test_permission.tmp"
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        print("   ✅ 파일 쓰기 권한 OK")
    except Exception as e:
        print(f"   ❌ 파일 권한 오류: {e}")
    
    print("   ✅ 시스템 요구사항 테스트 완료")
    return True

def main():
    """메인 테스트 실행"""
    print("=" * 70)
    print("🚀 EZ-Dash 센서 시스템 통합 테스트")
    print("=" * 70)
    print()
    
    test_results = []
    
    # 1. 시스템 요구사항 테스트
    test_results.append(("시스템 요구사항", test_system_requirements()))
    print()
    
    # 2. 개별 센서 테스트
    test_results.append(("개별 센서", test_individual_sensors()))
    print()
    
    # 3. 센서 매니저 테스트
    test_results.append(("센서 매니저", test_sensor_manager()))
    print()
    
    # 4. API 기능 테스트
    test_results.append(("API 기능", test_api_functionality()))
    print()
    
    # 결과 요약
    print("=" * 70)
    print("📊 테스트 결과 요약")
    print("=" * 70)
    
    passed = 0
    for test_name, result in test_results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{test_name:20s}: {status}")
        if result:
            passed += 1
    
    print(f"\n총 {len(test_results)}개 테스트 중 {passed}개 통과 ({passed/len(test_results)*100:.1f}%)")
    
    if passed == len(test_results):
        print("\n🎉 모든 테스트 통과! 시스템이 정상적으로 설정되었습니다.")
        print("이제 다음 명령으로 서버를 시작할 수 있습니다:")
        print("   python sensor_api.py")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다. 위의 오류 메시지를 확인하세요.")
        print("일반적인 해결 방법:")
        print("1. I2C 활성화: sudo raspi-config > Interface Options > I2C > Enable")
        print("2. 사용자 권한: sudo usermod -a -G i2c $USER")
        print("3. 재부팅: sudo reboot")
        print("4. 센서 연결 확인")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ 테스트가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        traceback.print_exc()
    finally:
        print("\n테스트 완료.")