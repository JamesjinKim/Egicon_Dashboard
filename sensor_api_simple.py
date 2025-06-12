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
    
    # I2C 스캐너 초기화 (Mac 테스트용 모킹 모드 지원)
    mock_mode = os.getenv('EZDASH_MOCK_MODE', 'false').lower() == 'true'
    print(f"I2C 스캐너 초기화 중... (모킹 모드: {mock_mode})")
    i2c_scanner = WebI2CScanner(mock_mode=mock_mode)
    
    # 센서 매니저 초기화
    print("실제 센서 연결 중...")
    sensor_manager = SensorManager()
    
    if sensor_manager.initialize_sensors():
        status = sensor_manager.get_sensor_status()
        print(f"센서 초기화 완료: {status['sensor_count']}/2개 센서 연결")
        return True
    else:
        print("센서 연결 실패")
        sensor_manager = None
        return False

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
    """현재 센서 데이터 조회"""
    global sensor_manager
    
    if not sensor_manager:
        return jsonify({'error': '센서가 연결되지 않음'}), 500
    
    try:
        # 실제 센서 데이터 읽기
        sensor_data = sensor_manager.read_all_sensors()
        
        return jsonify({
            'timestamp': sensor_data['timestamp'],
            'temperature': sensor_data['temperature'],
            'humidity': sensor_data['humidity'],
            'light': sensor_data['light'],
            'pressure': sensor_data['pressure'],
            'vibration': sensor_data['vibration'],
            'gas_resistance': sensor_data['gas_resistance'],
            'air_quality': sensor_data['air_quality'],
            'absolute_pressure': sensor_data['absolute_pressure']
        })
        
    except Exception as e:
        print(f"센서 읽기 오류: {e}")
        return jsonify({'error': f'센서 읽기 실패: {e}'}), 500

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
            'total_sensors': status['sensor_count'],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    else:
        return jsonify({
            'connected': False,
            'bme688': False,
            'bh1750': False,
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
    
    print(f"\n🚀 서버 시작: http://0.0.0.0:5002")
    print("Ctrl+C로 종료\n")
    
    try:
        app.run(debug=False, host='0.0.0.0', port=5002, threaded=True)
    except KeyboardInterrupt:
        print("\n서버 종료 중...")
        if sensor_manager:
            sensor_manager.close_sensors()
        print("서버가 정상적으로 종료되었습니다.")