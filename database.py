#!/usr/bin/env python3
"""
EG-Dash 센서 데이터베이스 관리 모듈
SQLite 기반 센서 정보 및 스캔 히스토리 관리
"""

import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple

class SensorDatabase:
    """센서 데이터베이스 관리 클래스"""
    
    def __init__(self, db_path: str = "sensors.db"):
        """
        데이터베이스 초기화
        
        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self.init_database()
        self.insert_default_sensors()
    
    def get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 반환"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
        return conn
    
    def init_database(self):
        """데이터베이스 초기화 - 테이블 생성"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 센서 정보 테이블 (확장된 스키마)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sensors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address INTEGER,
                    name VARCHAR(50) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    description TEXT,
                    voltage VARCHAR(20),
                    communication_type VARCHAR(20) DEFAULT 'I2C',
                    port_info VARCHAR(100),
                    is_default BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(address, communication_type)
                )
            ''')
            
            # I2C 스캔 히스토리 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bus_number INTEGER NOT NULL,
                    address INTEGER NOT NULL,
                    sensor_id INTEGER,
                    scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (sensor_id) REFERENCES sensors(id)
                )
            ''')
            
            # 인덱스 생성
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensors_address ON sensors(address)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_scan_history_address ON scan_history(address)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_scan_history_time ON scan_history(scan_time)')
            
            conn.commit()
    
    def insert_default_sensors(self):
        """기본 센서 정보 삽입 (I2C 및 시리얼 센서 포함)"""
        # I2C 센서들
        i2c_sensors = [
            # BH1750 조도센서
            (0x23, "BH1750", "광센서", "디지털 조도 센서", "3.3V/5V", "I2C"),
            (0x5C, "BH1750", "광센서", "디지털 조도 센서 (ADDR=H)", "3.3V/5V", "I2C"),
            
            # BME688 환경센서
            (0x76, "BME688", "온습도환경센서", "온습도기압 또는 가스센서", "3.3V", "I2C"),
            (0x77, "BME688", "온습도환경센서", "온습도기압 또는 가스센서", "3.3V", "I2C"),
            
            # SHT40 온습도센서
            (0x44, "SHT40", "온습도센서", "고정밀 디지털 온습도 센서", "3.3V", "I2C"),
            (0x45, "SHT40", "온습도센서", "고정밀 디지털 온습도 센서 (ALT)", "3.3V", "I2C"),
            
            # SDP810 차압센서
            (0x25, "SDP810", "차압센서", "차압정보를 제공해 주는 센서", "3.3V", "I2C"),
        ]
        
        # 시리얼/UART 센서들
        serial_sensors = [
            # SPS30 미세먼지센서
            (None, "SPS30", "미세먼지센서", "PM1.0/PM2.5/PM4.0/PM10 미세먼지 측정 센서", "5V", "UART", "/dev/ttyUSB*"),
        ]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # I2C 센서들 삽입
            for address, name, sensor_type, description, voltage, comm_type in i2c_sensors:
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO sensors 
                        (address, name, type, description, voltage, communication_type, is_default)
                        VALUES (?, ?, ?, ?, ?, ?, 1)
                    ''', (address, name, sensor_type, description, voltage, comm_type))
                except sqlite3.IntegrityError:
                    # 이미 존재하는 주소는 무시
                    pass
            
            # 시리얼 센서들 삽입 (엄격한 중복 체크)
            for address, name, sensor_type, description, voltage, comm_type, port_info in serial_sensors:
                try:
                    # UART 센서의 경우 name과 communication_type으로 중복 체크
                    if comm_type == 'UART':
                        cursor.execute('''
                            SELECT COUNT(*) FROM sensors 
                            WHERE name = ? AND communication_type = ? AND is_default = 1
                        ''', (name, comm_type))
                        
                        if cursor.fetchone()[0] > 0:
                            print(f"ℹ️ 기본 센서 이미 존재: {name} ({comm_type})")
                            continue
                    
                    # 센서 삽입
                    cursor.execute('''
                        INSERT INTO sensors 
                        (address, name, type, description, voltage, communication_type, port_info, is_default)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    ''', (address, name, sensor_type, description, voltage, comm_type, port_info))
                    
                    print(f"✅ 기본 센서 추가: {name} ({comm_type})")
                    
                except sqlite3.IntegrityError as e:
                    # 이미 존재하는 센서는 무시 (주로 I2C 센서의 주소 중복)
                    print(f"ℹ️ 센서 이미 존재 (무시): {name} ({comm_type})")
                    pass
            
            # 기존 I2C 센서 중 기본 센서로 업데이트해야 할 항목들
            cursor.execute('''
                UPDATE sensors 
                SET is_default = 1, name = ?, type = ?, description = ?, voltage = ?
                WHERE address = 0x25 AND communication_type = 'I2C' AND is_default = 0
            ''', ("SDP810", "차압센서", "차압정보를 제공해 주는 센서", "3.3V"))
            
            conn.commit()
    
    def get_all_sensors(self) -> List[Dict]:
        """모든 센서 정보 조회"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM sensors 
                ORDER BY address
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_sensor_by_address(self, address: int, comm_type: str = "I2C") -> Optional[Dict]:
        """주소로 센서 정보 조회"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sensors WHERE address = ? AND communication_type = ?', (address, comm_type))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_sensor_by_name(self, name: str) -> Optional[Dict]:
        """이름으로 센서 정보 조회 (시리얼 센서용)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sensors WHERE name = ?', (name,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def add_sensor(self, address: Optional[int], name: str, sensor_type: str, 
                   description: str = "", voltage: str = "3.3V", 
                   comm_type: str = "I2C", port_info: Optional[str] = None) -> bool:
        """새 센서 추가 (I2C 및 시리얼 센서 지원)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sensors (address, name, type, description, voltage, 
                                       communication_type, port_info, is_default)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                ''', (address, name, sensor_type, description, voltage, comm_type, port_info))
                
                conn.commit()
                return True
                
        except sqlite3.IntegrityError:
            # 이미 존재하는 센서
            return False
    
    def update_sensor(self, sensor_id: int, name: str, sensor_type: str, 
                     description: str, voltage: str) -> bool:
        """센서 정보 수정"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE sensors 
                    SET name = ?, type = ?, description = ?, voltage = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND is_default = 0
                ''', (name, sensor_type, description, voltage, sensor_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error:
            return False
    
    def delete_sensor(self, sensor_id: int) -> bool:
        """센서 삭제 (기본 센서는 삭제 불가)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM sensors 
                    WHERE id = ? AND is_default = 0
                ''', (sensor_id,))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except sqlite3.Error:
            return False
    
    def add_scan_result(self, bus_number: int, addresses: List[int]):
        """스캔 결과 저장"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for address in addresses:
                # 해당 주소의 센서 ID 찾기
                sensor = self.get_sensor_by_address(address)
                sensor_id = sensor['id'] if sensor else None
                
                cursor.execute('''
                    INSERT INTO scan_history (bus_number, address, sensor_id)
                    VALUES (?, ?, ?)
                ''', (bus_number, address, sensor_id))
            
            conn.commit()
    
    def get_recent_scan_results(self, limit: int = 50) -> List[Dict]:
        """최근 스캔 결과 조회"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    sh.id,
                    sh.bus_number,
                    sh.address,
                    sh.scan_time,
                    s.name,
                    s.type,
                    s.description
                FROM scan_history sh
                LEFT JOIN sensors s ON sh.sensor_id = s.id
                ORDER BY sh.scan_time DESC
                LIMIT ?
            ''', (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_unknown_addresses(self, scanned_addresses: List[int]) -> List[int]:
        """DB에 등록되지 않은 주소 찾기"""
        if not scanned_addresses:
            return []
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # IN 절을 위한 플레이스홀더 생성
            placeholders = ','.join('?' * len(scanned_addresses))
            
            cursor.execute(f'''
                SELECT address FROM sensors 
                WHERE address IN ({placeholders})
            ''', scanned_addresses)
            
            known_addresses = {row[0] for row in cursor.fetchall()}
            unknown_addresses = [addr for addr in scanned_addresses if addr not in known_addresses]
            
            return unknown_addresses
    
    def get_connection_status(self, scan_result: Dict) -> Dict:
        """센서 연결 상태 분석"""
        all_sensors = self.get_all_sensors()
        
        # 현재 스캔된 주소들 수집
        scanned_addresses = set()
        for bus_num, addresses in scan_result.get('buses', {}).items():
            scanned_addresses.update(addresses)
        
        # 센서별 연결 상태 분석
        sensor_status = {}
        for sensor in all_sensors:
            address = sensor['address']
            is_connected = address in scanned_addresses
            
            sensor_status[address] = {
                'sensor': sensor,
                'connected': is_connected,
                'bus': None
            }
            
            # 연결된 경우 버스 번호 찾기
            if is_connected:
                for bus_num, addresses in scan_result.get('buses', {}).items():
                    if address in addresses:
                        sensor_status[address]['bus'] = bus_num
                        break
        
        # 미등록 센서 찾기
        unknown_addresses = self.get_unknown_addresses(list(scanned_addresses))
        
        return {
            'sensor_status': sensor_status,
            'unknown_addresses': unknown_addresses,
            'total_sensors': len(all_sensors),
            'connected_sensors': len([s for s in sensor_status.values() if s['connected']]),
            'unknown_count': len(unknown_addresses)
        }

def test_database():
    """데이터베이스 테스트 함수"""
    print("=" * 60)
    print("센서 데이터베이스 테스트")
    print("=" * 60)
    
    # 테스트용 DB 파일
    test_db_path = "test_sensors.db"
    
    # 기존 테스트 DB 삭제
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    # 데이터베이스 초기화
    db = SensorDatabase(test_db_path)
    
    print("\n1. 기본 센서 목록 조회:")
    sensors = db.get_all_sensors()
    for sensor in sensors[:5]:  # 처음 5개만 출력
        print(f"  0x{sensor['address']:02X}: {sensor['name']} ({sensor['type']})")
    print(f"  ... 총 {len(sensors)}개 센서 등록됨")
    
    print("\n2. 특정 센서 조회 (0x23):")
    sensor = db.get_sensor_by_address(0x23)
    if sensor:
        print(f"  {sensor['name']}: {sensor['description']}")
    
    print("\n3. 새 센서 추가 테스트:")
    success = db.add_sensor(0x99, "Test Sensor", "테스트센서", "테스트용 센서", "5V")
    print(f"  센서 추가 결과: {'성공' if success else '실패'}")
    
    print("\n4. 스캔 결과 저장 테스트:")
    db.add_scan_result(1, [0x23, 0x77, 0x99])
    print("  스캔 결과 저장 완료")
    
    print("\n5. 최근 스캔 결과 조회:")
    recent_scans = db.get_recent_scan_results(5)
    for scan in recent_scans:
        name = scan['name'] or 'Unknown'
        print(f"  버스 {scan['bus_number']}: 0x{scan['address']:02X} ({name})")
    
    print("\n6. 미등록 센서 찾기 테스트:")
    unknown = db.get_unknown_addresses([0x23, 0x88, 0x99])
    print(f"  미등록 주소: {[f'0x{addr:02X}' for addr in unknown]}")
    
    print("\n7. 연결 상태 분석 테스트:")
    scan_result = {
        'buses': {
            1: [0x23, 0x77],
            0: [0x44]
        }
    }
    status = db.get_connection_status(scan_result)
    print(f"  총 센서: {status['total_sensors']}")
    print(f"  연결된 센서: {status['connected_sensors']}")
    print(f"  미등록 센서: {status['unknown_count']}")
    
    # 테스트 DB 정리
    os.remove(test_db_path)
    print("\n✅ 데이터베이스 테스트 완료")

if __name__ == "__main__":
    test_database()