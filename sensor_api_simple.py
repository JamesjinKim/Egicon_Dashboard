#!/usr/bin/env python3
"""
EG-Dash 심플 센서 API 서버
- 실제 센서 데이터만 사용
- 더미 데이터 제거
- 단순한 구조로 최적화
"""

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from datetime import datetime
import os
from sensor_manager import SensorManager
from database import SensorDatabase
from i2c_scanner import WebI2CScanner

app = Flask(__name__)
CORS(app)

# 전역 객체들
sensor_manager = None
sensor_db = None
i2c_scanner = None

def initialize_sensors():
    """센서 매니저 초기화"""
    global sensor_manager, sensor_db, i2c_scanner
    
    # 데이터베이스 초기화
    print("센서 데이터베이스 초기화 중...")
    sensor_db = SensorDatabase()
    
    # I2C 스캐너 초기화 (라즈베리파이 전용)
    print("I2C 스캐너 초기화 중...")
    i2c_scanner = WebI2CScanner()
    
    # 센서 매니저 초기화
    print("실제 센서 연결 중...")
    sensor_manager = SensorManager()
    
    if sensor_manager.initialize_sensors():
        status = sensor_manager.get_sensor_status()
        print(f"센서 초기화 완료: {status['sensor_count']}/2개 센서 연결")
        return True
    else:
        print("⚠️ 센서 연결 실패 - 데이터 없는 상태로 서비스 시작")
        # sensor_manager를 None으로 설정하지 않고 유지
        return True  # 서비스는 계속 시작

@app.route('/')
def index():
    """메인 대시보드 페이지"""
    return render_template('pages/dashboard.html')

@app.route('/dashboard')
def dashboard():
    """대시보드 페이지 (별칭)"""
    return render_template('pages/dashboard.html')

@app.route('/settings')
def settings():
    """설정 페이지"""
    return render_template('pages/settings.html')

@app.route('/api/current', methods=['GET'])
def get_current_data():
    """현재 센서 데이터 조회 (센서 상태 포함)"""
    global sensor_manager
    
    try:
        if sensor_manager:
            # 실제 센서 데이터 읽기
            sensor_data = sensor_manager.read_all_sensors()
            
            return jsonify({
                'timestamp': sensor_data['timestamp'],
                'temperature': sensor_data['temperature'],
                'humidity': sensor_data['humidity'],
                'light': sensor_data['light'],
                'pressure': sensor_data['pressure'],  # BME688 절대압력 (hPa)
                'differential_pressure': sensor_data['differential_pressure'],  # SDP810 차압 (Pa)
                'vibration': sensor_data['vibration'],
                'gas_resistance': sensor_data['gas_resistance'],
                'air_quality': sensor_data['air_quality'],
                'absolute_pressure': sensor_data['absolute_pressure'],
                # SPS30 미세먼지 데이터 추가
                'pm1': sensor_data.get('pm1'),
                'pm25': sensor_data.get('pm25'),
                'pm4': sensor_data.get('pm4'),
                'pm10': sensor_data.get('pm10'),
                'sensor_status': sensor_data['sensor_status']
            })
        else:
            # 센서 매니저가 없을 때 기본 응답
            return jsonify({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'temperature': None,
                'humidity': None,
                'light': None,
                'pressure': None,
                'differential_pressure': None,
                'vibration': 0.0,
                'gas_resistance': None,
                'air_quality': None,
                'absolute_pressure': None,
                # SPS30 미세먼지 데이터 추가
                'pm1': None,
                'pm25': None,
                'pm4': None,
                'pm10': None,
                'sensor_status': {
                    'bme688': False,
                    'bh1750': False,
                    'sht40': False,
                    'sdp810': False,
                    'sps30': False
                }
            })
        
    except Exception as e:
        print(f"센서 읽기 오류: {e}")
        # 오류 발생 시도 기본 응답 반환
        return jsonify({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'temperature': None,
            'humidity': None,
            'light': None,
            'pressure': None,
            'differential_pressure': None,
            'vibration': 0.0,
            'gas_resistance': None,
            'air_quality': None,
            'absolute_pressure': None,
            # SPS30 미세먼지 데이터 추가
            'pm1': None,
            'pm25': None,
            'pm4': None,
            'pm10': None,
            'sensor_status': {
                'bme688': False,
                'bh1750': False,
                'sht40': False,
                'sdp810': False,
                'sps30': False
            },
            'error': str(e)
        })

@app.route('/api/current-multi', methods=['GET'])
def get_current_data_multi():
    """현재 센서 데이터 조회 (멀티 센서 지원)"""
    global sensor_manager
    
    try:
        if sensor_manager:
            # 멀티 센서 데이터 읽기
            sensor_data = sensor_manager.read_all_sensors_multi()
            return jsonify(sensor_data)
        else:
            # 센서 매니저가 없을 때 기본 응답
            return jsonify({
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'sensors': {
                    'sht40': [],
                    'bme688': [],
                    'bh1750': [],
                    'sdp810': []
                },
                'sensor_status': {
                    'sht40': False,
                    'bme688': False,
                    'bh1750': False,
                    'sdp810': False
                }
            })
        
    except Exception as e:
        print(f"멀티 센서 읽기 오류: {e}")
        # 오류 발생 시도 기본 응답 반환
        return jsonify({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'sensors': {
                'sht40': [],
                'bme688': [],
                'bh1750': [],
                'sdp810': []
            },
            'sensor_status': {
                'sht40': False,
                'bme688': False,
                'bh1750': False,
                'sdp810': False
            },
            'error': str(e)
        })

@app.route('/api/status', methods=['GET'])
def get_sensor_status():
    """센서 연결 상태"""
    global sensor_manager
    
    if sensor_manager:
        status = sensor_manager.get_sensor_status()
        return jsonify({
            'connected': True,
            'bme688': status['bme688_connected'],
            'bh1750': status['bh1750_connected'],
            'sht40': status['sht40_connected'],
            'sdp810': status.get('sdp810_connected', False),
            'sps30': status.get('sps30_connected', False),
            'total_sensors': status['sensor_count'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    else:
        return jsonify({
            'connected': False,
            'bme688': False,
            'bh1750': False,
            'sht40': False,
            'sdp810': False,
            'sps30': False,
            'total_sensors': 0,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

# ============================
# 설정 페이지 API 엔드포인트
# ============================

@app.route('/api/sensors', methods=['GET'])
def get_sensors():
    """모든 센서 목록 조회"""
    global sensor_db
    
    if not sensor_db:
        return jsonify({'error': '데이터베이스가 초기화되지 않음'}), 500
    
    try:
        sensors = sensor_db.get_all_sensors()
        return jsonify(sensors)
    except Exception as e:
        return jsonify({'error': f'센서 목록 조회 실패: {e}'}), 500

@app.route('/api/sensors/<int:sensor_id>', methods=['GET'])
def get_sensor(sensor_id):
    """특정 센서 정보 조회"""
    global sensor_db
    
    if not sensor_db:
        return jsonify({'error': '데이터베이스가 초기화되지 않음'}), 500
    
    try:
        sensors = sensor_db.get_all_sensors()
        sensor = next((s for s in sensors if s['id'] == sensor_id), None)
        
        if sensor:
            return jsonify(sensor)
        else:
            return jsonify({'error': '센서를 찾을 수 없음'}), 404
    except Exception as e:
        return jsonify({'error': f'센서 조회 실패: {e}'}), 500

@app.route('/api/sensors', methods=['POST'])
def add_sensor():
    """새 센서 등록"""
    global sensor_db
    
    if not sensor_db:
        return jsonify({'success': False, 'message': '데이터베이스가 초기화되지 않음'}), 500
    
    try:
        data = request.get_json()
        
        # 필수 필드 검증
        required_fields = ['address', 'name', 'type']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'message': f'{field} 필드가 필요합니다'}), 400
        
        success = sensor_db.add_sensor(
            address=data['address'],
            name=data['name'],
            sensor_type=data['type'],
            description=data.get('description', ''),
            voltage=data.get('voltage', '3.3V')
        )
        
        if success:
            return jsonify({'success': True, 'message': '센서가 성공적으로 등록되었습니다'})
        else:
            return jsonify({'success': False, 'message': '이미 등록된 주소입니다'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'센서 등록 실패: {e}'}), 500

@app.route('/api/sensors/<int:sensor_id>', methods=['PUT'])
def update_sensor(sensor_id):
    """센서 정보 수정"""
    global sensor_db
    
    if not sensor_db:
        return jsonify({'success': False, 'message': '데이터베이스가 초기화되지 않음'}), 500
    
    try:
        data = request.get_json()
        
        success = sensor_db.update_sensor(
            sensor_id=sensor_id,
            name=data.get('name', ''),
            sensor_type=data.get('type', ''),
            description=data.get('description', ''),
            voltage=data.get('voltage', '3.3V')
        )
        
        if success:
            return jsonify({'success': True, 'message': '센서 정보가 업데이트되었습니다'})
        else:
            return jsonify({'success': False, 'message': '센서 업데이트 실패 (기본 센서이거나 존재하지 않음)'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'센서 업데이트 실패: {e}'}), 500

@app.route('/api/sensors/<int:sensor_id>', methods=['DELETE'])
def delete_sensor(sensor_id):
    """센서 삭제"""
    global sensor_db
    
    if not sensor_db:
        return jsonify({'success': False, 'message': '데이터베이스가 초기화되지 않음'}), 500
    
    try:
        success = sensor_db.delete_sensor(sensor_id)
        
        if success:
            return jsonify({'success': True, 'message': '센서가 삭제되었습니다'})
        else:
            return jsonify({'success': False, 'message': '센서 삭제 실패 (기본 센서이거나 존재하지 않음)'}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'센서 삭제 실패: {e}'}), 500

@app.route('/api/i2c/scan', methods=['POST'])
def scan_i2c():
    """I2C 디바이스 스캔"""
    global i2c_scanner, sensor_db
    
    if not i2c_scanner:
        return jsonify({'success': False, 'message': 'I2C 스캐너가 초기화되지 않음'}), 500
    
    try:
        result = i2c_scanner.comprehensive_scan()
        
        if result:
            # 스캔 결과를 데이터베이스에 저장
            if sensor_db:
                for bus_num, addresses in result['buses'].items():
                    sensor_db.add_scan_result(int(bus_num), addresses)
            
            return jsonify({
                'success': True,
                'message': 'I2C 스캔이 완료되었습니다',
                'data': result
            })
        else:
            return jsonify({
                'success': False,
                'message': 'I2C 버스에 연결할 수 없습니다'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'I2C 스캔 실패: {e}'
        }), 500

@app.route('/api/i2c/test', methods=['POST'])
def test_i2c_device():
    """I2C 디바이스 테스트"""
    global i2c_scanner
    
    if not i2c_scanner:
        return jsonify({'success': False, 'message': 'I2C 스캐너가 초기화되지 않음'}), 500
    
    try:
        data = request.get_json()
        bus_number = data.get('bus_number')
        address = data.get('address')
        
        if bus_number is None or address is None:
            return jsonify({'success': False, 'message': 'bus_number와 address가 필요합니다'}), 400
        
        test_result = i2c_scanner.test_device(bus_number, address)
        
        return jsonify({
            'success': True,
            'message': '디바이스 테스트 완료',
            'data': test_result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'디바이스 테스트 실패: {e}'
        }), 500

@app.route('/api/sensors/scan-all', methods=['POST'])
def scan_all_sensors():
    """통합 센서 검색 (I2C + UART)"""
    global i2c_scanner, sensor_manager
    
    try:
        results = {
            'i2c_devices': [],
            'uart_devices': [],
            'success': True,
            'message': '통합 센서 검색 완료'
        }
        
        # I2C 디바이스 스캔
        if i2c_scanner:
            try:
                scan_result = i2c_scanner.scan_all_buses()
                for bus_num, devices in scan_result.get('buses', {}).items():
                    for device in devices:
                        sensor_info = sensor_db.get_sensor_by_address(device) if sensor_db else None
                        results['i2c_devices'].append({
                            'communication_type': 'I2C',
                            'bus': bus_num,
                            'address': f'0x{device:02X}',
                            'sensor_name': sensor_info.get('name', 'Unknown') if sensor_info else 'Unknown',
                            'sensor_type': sensor_info.get('type', '미등록') if sensor_info else '미등록',
                            'status': 'Connected'
                        })
            except Exception as e:
                print(f"I2C 스캔 오류: {e}")
        
        # UART 디바이스 검색 (SPS30)
        if sensor_manager:
            try:
                from sps30_sensor import SPS30Sensor
                port_path, count = SPS30Sensor.find_sps30()
                if port_path and count > 0:
                    results['uart_devices'].append({
                        'communication_type': 'UART',
                        'port': port_path,
                        'address': 'N/A',
                        'sensor_name': 'SPS30',
                        'sensor_type': '미세먼지센서',
                        'status': 'Connected'
                    })
            except Exception as e:
                print(f"UART 스캔 오류: {e}")
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'통합 센서 검색 실패: {e}',
            'i2c_devices': [],
            'uart_devices': []
        }), 500

@app.route('/api/sensors/cleanup-duplicates', methods=['POST'])
def cleanup_duplicate_sensors():
    """중복 센서 정리"""
    global sensor_db
    
    if not sensor_db:
        return jsonify({'success': False, 'message': '데이터베이스가 초기화되지 않음'}), 500
    
    try:
        with sensor_db.get_connection() as conn:
            cursor = conn.cursor()
            
            # SPS30 중복 제거 (가장 최근 것만 남기고 삭제)
            cursor.execute('''
                DELETE FROM sensors 
                WHERE name = 'SPS30' AND communication_type = 'UART' AND is_default = 1
                AND id NOT IN (
                    SELECT MAX(id) FROM sensors 
                    WHERE name = 'SPS30' AND communication_type = 'UART' AND is_default = 1
                )
            ''')
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': f'{deleted_count}개의 중복 센서가 정리되었습니다'
            })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'중복 센서 정리 실패: {e}'
        }), 500

@app.route('/api/sensors/rescan', methods=['POST'])
def rescan_sensors():
    """센서 재검색"""
    global sensor_manager
    
    if not sensor_manager:
        return jsonify({'success': False, 'message': '센서 매니저가 초기화되지 않음'}), 500
    
    try:
        # 센서 재검색 실행
        new_config = sensor_manager.rescan_sensors_now()
        
        return jsonify({
            'success': True,
            'message': '센서 재검색이 완료되었습니다',
            'sensor_config': new_config,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'센서 재검색 실패: {e}'
        }), 500

@app.route('/api/debug/sps30', methods=['GET'])
def debug_sps30():
    """SPS30 디버깅 정보"""
    global sensor_manager
    
    if not sensor_manager:
        return jsonify({'error': 'sensor_manager가 없습니다'})
    
    debug_info = {
        'sps30_object_exists': sensor_manager.sps30 is not None,
        'sps30_connected': sensor_manager.sps30.connected if sensor_manager.sps30 else False,
        'sps30_sensors_count': len(sensor_manager.sps30_sensors),
        'sensor_status': sensor_manager.get_sensor_status()
    }
    
    if sensor_manager.sps30:
        try:
            test_data = sensor_manager.sps30.read_data()
            debug_info['test_read_data'] = test_data
        except Exception as e:
            debug_info['test_read_error'] = str(e)
    
    return jsonify(debug_info)

# ============================
# 개별 센서 데이터 API 엔드포인트 (404 오류 해결)
# ============================

@app.route('/api/current-sensor/<sensor_type>', methods=['GET'])
def get_current_sensor_data(sensor_type):
    """개별 센서 데이터 조회"""
    global sensor_manager
    
    if not sensor_manager:
        return jsonify({'error': '센서 매니저가 초기화되지 않음', 'connected': False}), 500
    
    try:
        # 전체 센서 데이터 읽기
        all_data = sensor_manager.read_all_sensors()
        
        # 센서 타입별 데이터 반환
        response_data = {
            'timestamp': all_data['timestamp'],
            'connected': False,
            'value': None,
            'unit': '',
            'sensor_type': sensor_type
        }
        
        if sensor_type == 'bme688':
            response_data.update({
                'connected': all_data['sensor_status'].get('bme688', False),
                'temperature': all_data.get('temperature'),
                'humidity': all_data.get('humidity'),
                'pressure': all_data.get('pressure'),
                'gas_resistance': all_data.get('gas_resistance'),
                'air_quality': all_data.get('air_quality')
            })
        elif sensor_type == 'sht40':
            response_data.update({
                'connected': all_data['sensor_status'].get('sht40', False),
                'temperature': all_data.get('temperature'),
                'humidity': all_data.get('humidity')
            })
        elif sensor_type == 'bh1750':
            response_data.update({
                'connected': all_data['sensor_status'].get('bh1750', False),
                'light': all_data.get('light'),
                'unit': 'lux'
            })
        elif sensor_type == 'sdp810':
            response_data.update({
                'connected': all_data['sensor_status'].get('sdp810', False),
                'differential_pressure': all_data.get('differential_pressure'),
                'unit': 'Pa'
            })
        elif sensor_type == 'sps30':
            response_data.update({
                'connected': all_data['sensor_status'].get('sps30', False),
                'pm1': all_data.get('pm1'),
                'pm25': all_data.get('pm25'),
                'pm4': all_data.get('pm4'),
                'pm10': all_data.get('pm10'),
                'unit': 'μg/m³'
            })
        elif sensor_type == 'virtual':
            # 가상 센서 또는 계산된 값들
            response_data.update({
                'connected': True,
                'vibration': all_data.get('vibration', 0.0),
                'unit': 'various'
            })
        else:
            return jsonify({'error': f'알 수 없는 센서 타입: {sensor_type}'}), 400
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            'error': f'센서 데이터 읽기 실패: {e}',
            'connected': False,
            'sensor_type': sensor_type,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'API 엔드포인트를 찾을 수 없음'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '서버 내부 오류'}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("EZ-Dash 심플 센서 대시보드 서버")
    print("=" * 60)
    
    # 센서 초기화
    if initialize_sensors():
        print("\n✅ 센서 연결 성공")
    else:
        print("\n❌ 센서 연결 실패 - 서버만 실행됩니다")
    
    print(f"\n🚀 서버 시작: http://0.0.0.0:5003")
    print("Ctrl+C로 종료\n")
    
    try:
        app.run(debug=False, host='0.0.0.0', port=5003, threaded=True)
    except KeyboardInterrupt:
        print("\n서버 종료 중...")
        if sensor_manager:
            sensor_manager.close_sensors()
        print("서버가 정상적으로 종료되었습니다.")