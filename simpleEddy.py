#!/usr/bin/env python3
"""
Raspberry Pi I2C Master Test Code for SDP810 Slave Device
통신 포맷: |S|0x25|R|ACK|DATA[0]|ACK|DATA[1]|ACK|CRC[2]|NACK|P|
"""

import smbus2
import time
import struct

class SDP810_I2C_Test:
    def __init__(self, bus_number=1, slave_address=0x25):
        """
        Initialize I2C communication
        
        Args:
            bus_number: I2C bus number (default: 1 for Raspberry Pi)
            slave_address: 7-bit slave address (default: 0x25)
        """
        self.bus = smbus2.SMBus(bus_number)
        self.slave_address = slave_address
        self.packet_size = 3  # Pressure(2) + CRC(1)
        
        print(f"I2C Master initialized - Bus: {bus_number}, Slave: 0x{slave_address:02X}")
    
    def calculate_crc8(self, data):
        """
        Calculate CRC-8 (SDP810 compatible)
        Polynomial: 0x31 (x^8 + x^5 + x^4 + 1)
        
        Args:
            data: List of bytes to calculate CRC
            
        Returns:
            CRC-8 value
        """
        crc = 0xFF  # Initial value
        
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31  # Polynomial 0x31
                else:
                    crc = crc << 1
                crc &= 0xFF  # Keep 8-bit
        
        return crc
    
    def read_pressure_data(self):
        """
        Read pressure data from slave device
        통신 포맷: |S|0x25|R|ACK|DATA[0]|ACK|DATA[1]|ACK|CRC[2]|NACK|P|
        
        Returns:
            tuple: (success, pressure_pa, raw_data)
        """
        try:
            # I2C Read: 3 bytes (Pressure MSB, LSB, CRC)
            raw_data = self.bus.read_i2c_block_data(self.slave_address, 0, self.packet_size)
            
            if len(raw_data) != self.packet_size:
                print(f"ERROR: Expected {self.packet_size} bytes, got {len(raw_data)}")
                return False, 0.0, raw_data
            
            # Extract data
            pressure_msb = raw_data[0]
            pressure_lsb = raw_data[1]
            received_crc = raw_data[2]
            
            # Verify CRC
            calculated_crc = self.calculate_crc8([pressure_msb, pressure_lsb])
            
            if calculated_crc != received_crc:
                print(f"CRC ERROR: Calculated=0x{calculated_crc:02X}, Received=0x{received_crc:02X}")
                return False, 0.0, raw_data
            
            # Convert to pressure value (signed 16-bit, divide by 60)
            raw_pressure = struct.unpack('>h', bytes([pressure_msb, pressure_lsb]))[0]  # Big-endian signed
            pressure_pa = raw_pressure / 60.0
            
            return True, pressure_pa, raw_data
            
        except Exception as e:
            print(f"I2C Communication Error: {e}")
            return False, 0.0, []
    
    def test_single_read(self):
        """
        Single pressure reading test
        """
        print("\n=== Single Read Test ===")
        
        success, pressure, raw_data = self.read_pressure_data()
        
        if success:
            print(f"✓ Success!")
            print(f"  Raw Data: {[f'0x{b:02X}' for b in raw_data]}")
            print(f"  Raw Pressure: {struct.unpack('>h', bytes(raw_data[:2]))[0]}")
            print(f"  Final Pressure: {pressure:.2f} Pa")
            print(f"  CRC: 0x{raw_data[2]:02X}")
        else:
            print(f"✗ Failed!")
            if raw_data:
                print(f"  Raw Data: {[f'0x{b:02X}' for b in raw_data]}")
    
    def test_continuous_read(self, duration=10, interval=0.5):
        """
        Continuous pressure reading test
        
        Args:
            duration: Test duration in seconds
            interval: Reading interval in seconds
        """
        print(f"\n=== Continuous Read Test ({duration}s, {interval}s interval) ===")
        
        start_time = time.time()
        read_count = 0
        success_count = 0
        
        try:
            while (time.time() - start_time) < duration:
                success, pressure, raw_data = self.read_pressure_data()
                read_count += 1
                
                if success:
                    success_count += 1
                    print(f"[{read_count:3d}] Pressure: {pressure:7.2f} Pa | Raw: {[f'0x{b:02X}' for b in raw_data]}")
                else:
                    print(f"[{read_count:3d}] ✗ Read Failed")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
        
        print(f"\nTest Results:")
        print(f"  Total Reads: {read_count}")
        print(f"  Successful: {success_count}")
        print(f"  Success Rate: {(success_count/read_count*100):.1f}%" if read_count > 0 else "N/A")
    
    def test_stress(self, count=100):
        """
        Stress test - rapid reading
        
        Args:
            count: Number of reads to perform
        """
        print(f"\n=== Stress Test ({count} reads) ===")
        
        success_count = 0
        min_pressure = float('inf')
        max_pressure = float('-inf')
        total_pressure = 0.0
        
        start_time = time.time()
        
        for i in range(count):
            success, pressure, _ = self.read_pressure_data()
            
            if success:
                success_count += 1
                total_pressure += pressure
                min_pressure = min(min_pressure, pressure)
                max_pressure = max(max_pressure, pressure)
            
            if (i + 1) % 10 == 0:
                print(f"Progress: {i+1}/{count} ({(i+1)/count*100:.0f}%)")
        
        elapsed_time = time.time() - start_time
        
        print(f"\nStress Test Results:")
        print(f"  Total Reads: {count}")
        print(f"  Successful: {success_count}")
        print(f"  Success Rate: {(success_count/count*100):.1f}%")
        print(f"  Elapsed Time: {elapsed_time:.2f}s")
        print(f"  Read Rate: {count/elapsed_time:.1f} reads/sec")
        
        if success_count > 0:
            avg_pressure = total_pressure / success_count
            print(f"  Pressure Range: {min_pressure:.2f} ~ {max_pressure:.2f} Pa")
            print(f"  Average Pressure: {avg_pressure:.2f} Pa")
    
    def close(self):
        """
        Close I2C bus
        """
        self.bus.close()
        print("I2C bus closed")

def main():
    """
    Main test function
    """
    print("=== Raspberry Pi I2C Master Test for SDP810 Slave ===")
    print("통신 포맷: |S|0x25|R|ACK|DATA[0]|ACK|DATA[1]|ACK|CRC[2]|NACK|P|")
    
    # Initialize I2C
    try:
        i2c_test = SDP810_I2C_Test(bus_number=1, slave_address=0x25)
    except Exception as e:
        print(f"Failed to initialize I2C: {e}")
        print("Make sure I2C is enabled: sudo raspi-config -> Interface Options -> I2C")
        return
    
    try:
        while True:
            print("\n" + "="*50)
            print("Select Test:")
            print("1. Single Read Test")
            print("2. Continuous Read Test (10s)")
            print("3. Stress Test (100 reads)")
            print("4. Custom Continuous Test")
            print("5. Exit")
            
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == '1':
                i2c_test.test_single_read()
            
            elif choice == '2':
                i2c_test.test_continuous_read(duration=10, interval=0.5)
            
            elif choice == '3':
                i2c_test.test_stress(count=100)
            
            elif choice == '4':
                try:
                    duration = float(input("Duration (seconds): "))
                    interval = float(input("Interval (seconds): "))
                    i2c_test.test_continuous_read(duration, interval)
                except ValueError:
                    print("Invalid input!")
            
            elif choice == '5':
                break
            
            else:
                print("Invalid choice!")
    
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    
    finally:
        i2c_test.close()
        print("Test completed")

if __name__ == "__main__":
    main()