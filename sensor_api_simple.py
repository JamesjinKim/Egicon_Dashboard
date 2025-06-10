#!/usr/bin/env python3
"""
EZ-Dash 심플 센서 API 서버
- 실제 센서 데이터만 사용
- 더미 데이터 제거
- 단순한 구조로 최적화
"""

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
from sensor_manager import SensorManager

app = Flask(__name__, static_folder='.')
CORS(app)

# 전역 센서 매니저
sensor_manager = None

def initialize_sensors():
    """센서 매니저 초기화"""
    global sensor_manager
    
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
    return send_from_directory('.', 'dashboard_simple.html')

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