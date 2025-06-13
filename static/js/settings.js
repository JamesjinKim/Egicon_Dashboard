// 설정 페이지 JavaScript
// API 엔드포인트 설정
const API_URL = window.location.origin + '/api';

// 전역 변수
let currentScanResult = null;
let isScanning = false;

// DOM이 로드되면 실행
document.addEventListener('DOMContentLoaded', function() {
    initializeSettings();
    bindEventListeners();
    loadSensors();
});

// 초기화 함수
function initializeSettings() {
    console.log('설정 페이지 초기화');
}

// 이벤트 리스너 바인딩
function bindEventListeners() {
    // 스캔 버튼
    document.getElementById('scan-button').addEventListener('click', startScan);
    
    // 센서 새로고침 버튼
    document.getElementById('refresh-sensors-button').addEventListener('click', loadSensors);
    
    // 센서 등록 폼
    document.getElementById('register-sensor-form').addEventListener('submit', registerSensor);
    
    // 수동 주소 입력 토글
    document.getElementById('manual-address-input').addEventListener('change', toggleManualAddressInput);
    
    // 센서 편집 폼
    document.getElementById('edit-sensor-form').addEventListener('submit', updateSensor);
    
    // 모달 닫기 버튼들
    document.getElementById('test-modal-close').addEventListener('click', () => closeModal('test-modal'));
    document.getElementById('edit-modal-close').addEventListener('click', () => closeModal('edit-modal'));
    document.getElementById('edit-cancel-btn').addEventListener('click', () => closeModal('edit-modal'));
    
    // 모달 외부 클릭 시 닫기
    window.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            closeModal(event.target.id);
        }
    });
}

// I2C 스캔 시작
async function startScan() {
    if (isScanning) return;
    
    isScanning = true;
    const scanButton = document.getElementById('scan-button');
    const progressContainer = document.getElementById('scan-progress-container');
    const progressFill = document.getElementById('scan-progress-fill');
    const progressText = document.getElementById('scan-progress-text');
    
    // UI 업데이트
    scanButton.disabled = true;
    scanButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 스캔 중...';
    progressContainer.style.display = 'block';
    progressFill.style.width = '0%';
    progressText.textContent = '스캔 준비 중...';
    
    try {
        // 스캔 시작 요청
        const response = await fetch(`${API_URL}/i2c/scan`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`스캔 실패: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            currentScanResult = result.data;
            updateScanResults(currentScanResult);
            updateSensorConnectionStatus();
            showToast('success', '스캔이 완료되었습니다.');
        } else {
            throw new Error(result.message || '스캔 실패');
        }
        
    } catch (error) {
        console.error('스캔 오류:', error);
        showToast('error', `스캔 오류: ${error.message}`);
    } finally {
        // UI 복원
        isScanning = false;
        scanButton.disabled = false;
        scanButton.innerHTML = '<i class="fas fa-sync-alt"></i> 스캔 시작';
        progressFill.style.width = '100%';
        progressText.textContent = '스캔 완료';
        
        // 3초 후 진행률 숨기기
        setTimeout(() => {
            progressContainer.style.display = 'none';
        }, 3000);
    }
}

// 스캔 결과 업데이트
function updateScanResults(scanResult) {
    const tbody = document.getElementById('scan-results-body');
    tbody.innerHTML = '';
    
    if (!scanResult || !scanResult.buses || Object.keys(scanResult.buses).length === 0) {
        tbody.innerHTML = '<tr class="no-results"><td colspan="6">발견된 디바이스가 없습니다</td></tr>';
        return;
    }
    
    // 각 버스별로 디바이스 표시
    for (const [busNum, addresses] of Object.entries(scanResult.buses)) {
        for (const address of addresses) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>버스 ${busNum}</td>
                <td>0x${address.toString(16).toUpperCase().padStart(2, '0')}</td>
                <td id="sensor-name-${address}">-</td>
                <td id="sensor-type-${address}">-</td>
                <td><span class="status-badge status-unknown">확인 중</span></td>
                <td>
                    <button class="action-btn test-btn" onclick="testDevice(${busNum}, ${address})">
                        <i class="fas fa-vial"></i> 테스트
                    </button>
                </td>
            `;
            tbody.appendChild(row);
        }
    }
    
    // 센서 정보 업데이트
    updateScannedSensorInfo();
}

// 스캔된 센서 정보 업데이트
async function updateScannedSensorInfo() {
    if (!currentScanResult) return;
    
    try {
        const response = await fetch(`${API_URL}/sensors`);
        const sensors = await response.json();
        
        for (const [busNum, addresses] of Object.entries(currentScanResult.buses)) {
            for (const address of addresses) {
                const sensor = sensors.find(s => s.address === address);
                const nameCell = document.getElementById(`sensor-name-${address}`);
                const typeCell = document.getElementById(`sensor-type-${address}`);
                
                if (sensor) {
                    nameCell.textContent = sensor.name;
                    typeCell.textContent = sensor.type;
                } else {
                    nameCell.textContent = 'Unknown';
                    typeCell.textContent = '미등록';
                    
                    // 미등록 센서인 경우 주소 옵션에 추가
                    addUnknownAddressOption(address);
                }
            }
        }
    } catch (error) {
        console.error('센서 정보 업데이트 오류:', error);
    }
}

// 미등록 주소를 선택 옵션에 추가
function addUnknownAddressOption(address) {
    const addressSelect = document.getElementById('sensor-address');
    const hexAddress = '0x' + address.toString(16).toUpperCase().padStart(2, '0');
    
    // 이미 존재하는지 확인
    const existingOption = Array.from(addressSelect.options).find(opt => opt.value == address);
    if (!existingOption) {
        const option = document.createElement('option');
        option.value = address;
        option.textContent = `${hexAddress} (미등록)`;
        option.style.color = '#dc3545';
        addressSelect.appendChild(option);
    }
}

// 센서 목록 로드
async function loadSensors() {
    const tbody = document.getElementById('sensors-table-body');
    tbody.innerHTML = '<tr class="loading"><td colspan="7">센서 목록을 불러오는 중...</td></tr>';
    
    try {
        const response = await fetch(`${API_URL}/sensors`);
        if (!response.ok) {
            throw new Error('센서 목록 로드 실패');
        }
        
        const sensors = await response.json();
        displaySensors(sensors);
        updateSensorStats(sensors);
        
    } catch (error) {
        console.error('센서 로드 오류:', error);
        tbody.innerHTML = '<tr class="no-results"><td colspan="7">센서 목록 로드 실패</td></tr>';
        showToast('error', '센서 목록을 불러올 수 없습니다.');
    }
}

// 센서 목록 표시
function displaySensors(sensors) {
    const tbody = document.getElementById('sensors-table-body');
    tbody.innerHTML = '';
    
    if (sensors.length === 0) {
        tbody.innerHTML = '<tr class="no-results"><td colspan="7">등록된 센서가 없습니다</td></tr>';
        return;
    }
    
    sensors.forEach(sensor => {
        const row = document.createElement('tr');
        const hexAddress = '0x' + sensor.address.toString(16).toUpperCase().padStart(2, '0');
        const isConnected = currentScanResult && 
            Object.values(currentScanResult.buses).some(addresses => addresses.includes(sensor.address));
        
        const statusClass = isConnected ? 'status-connected' : 'status-disconnected';
        const statusText = isConnected ? '연결됨' : '미연결';
        const isDefault = sensor.is_default;
        
        row.innerHTML = `
            <td>${hexAddress}</td>
            <td>${sensor.name}</td>
            <td>${sensor.type}</td>
            <td>${sensor.description || '-'}</td>
            <td>${sensor.voltage}</td>
            <td><span class="status-badge ${statusClass}">${statusText}</span></td>
            <td>
                ${isConnected ? `<button class="action-btn test-btn" onclick="testSensorById(${sensor.address})">
                    <i class="fas fa-vial"></i> 테스트
                </button>` : ''}
                ${!isDefault ? `
                    <button class="action-btn edit-btn" onclick="editSensor(${sensor.id})">
                        <i class="fas fa-edit"></i> 편집
                    </button>
                    <button class="action-btn delete-btn" onclick="deleteSensor(${sensor.id})">
                        <i class="fas fa-trash"></i> 삭제
                    </button>
                ` : '<span class="status-badge status-default">기본</span>'}
            </td>
        `;
        tbody.appendChild(row);
    });
}

// 센서 통계 업데이트
function updateSensorStats(sensors) {
    const totalSensors = sensors.length;
    let connectedCount = 0;
    let unknownCount = 0;
    
    if (currentScanResult) {
        const scannedAddresses = Object.values(currentScanResult.buses).flat();
        connectedCount = sensors.filter(s => scannedAddresses.includes(s.address)).length;
        unknownCount = scannedAddresses.filter(addr => 
            !sensors.some(s => s.address === addr)
        ).length;
    }
    
    document.getElementById('total-sensors').textContent = totalSensors;
    document.getElementById('connected-sensors').textContent = connectedCount;
    document.getElementById('unknown-sensors').textContent = unknownCount;
}

// 센서 연결 상태 업데이트
function updateSensorConnectionStatus() {
    loadSensors(); // 센서 목록을 다시 로드하여 연결 상태 업데이트
}

// 디바이스 테스트
async function testDevice(busNumber, address) {
    showModal('test-modal');
    const modalBody = document.getElementById('test-modal-body');
    modalBody.innerHTML = '<div class="loading-spinner"><i class="fas fa-spinner fa-spin"></i> 테스트 중...</div>';
    
    try {
        const response = await fetch(`${API_URL}/i2c/test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                bus_number: busNumber,
                address: address
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayTestResult(result.data);
        } else {
            modalBody.innerHTML = `<div class="error">테스트 실패: ${result.message}</div>`;
        }
        
    } catch (error) {
        console.error('테스트 오류:', error);
        modalBody.innerHTML = `<div class="error">테스트 오류: ${error.message}</div>`;
    }
}

// 센서 ID로 테스트 (등록된 센서)
async function testSensorById(address) {
    if (!currentScanResult) {
        showToast('warning', '먼저 I2C 스캔을 실행하세요.');
        return;
    }
    
    // 연결된 버스 찾기
    let busNumber = null;
    for (const [bus, addresses] of Object.entries(currentScanResult.buses)) {
        if (addresses.includes(address)) {
            busNumber = parseInt(bus);
            break;
        }
    }
    
    if (busNumber !== null) {
        testDevice(busNumber, address);
    } else {
        showToast('error', '센서가 연결되어 있지 않습니다.');
    }
}

// 테스트 결과 표시
function displayTestResult(testResult) {
    const modalBody = document.getElementById('test-modal-body');
    
    if (testResult.error) {
        modalBody.innerHTML = `
            <div class="test-result error">
                <h4><i class="fas fa-exclamation-triangle"></i> 테스트 실패</h4>
                <p>${testResult.error}</p>
            </div>
        `;
        return;
    }
    
    let html = `
        <div class="test-result success">
            <h4><i class="fas fa-check-circle"></i> ${testResult.type}</h4>
            <div class="test-values">
    `;
    
    if (testResult.values) {
        // SHT40 센서의 경우 온도 → 습도 → CRC 검증 순서로 표시
        if (testResult.type && testResult.type.includes('SHT40')) {
            const orderedKeys = ['온도', '습도', 'CRC 검증'];
            for (const key of orderedKeys) {
                if (testResult.values[key]) {
                    html += `
                        <div class="value-item">
                            <span class="value-label">${key}:</span>
                            <span class="value-data">${testResult.values[key]}</span>
                        </div>
                    `;
                }
            }
            // 기타 추가 값들이 있다면 표시
            for (const [key, value] of Object.entries(testResult.values)) {
                if (!orderedKeys.includes(key)) {
                    html += `
                        <div class="value-item">
                            <span class="value-label">${key}:</span>
                            <span class="value-data">${value}</span>
                        </div>
                    `;
                }
            }
        } else {
            // 다른 센서는 기존 방식 사용
            for (const [key, value] of Object.entries(testResult.values)) {
                html += `
                    <div class="value-item">
                        <span class="value-label">${key}:</span>
                        <span class="value-data">${value}</span>
                    </div>
                `;
            }
        }
    }
    
    html += `
            </div>
        </div>
    `;
    
    modalBody.innerHTML = html;
}

// 수동 주소 입력 토글
function toggleManualAddressInput() {
    const checkbox = document.getElementById('manual-address-input');
    const selectElement = document.getElementById('sensor-address');
    const manualInput = document.getElementById('manual-address');
    
    if (checkbox.checked) {
        selectElement.style.display = 'none';
        manualInput.style.display = 'block';
        selectElement.required = false;
        manualInput.required = true;
    } else {
        selectElement.style.display = 'block';
        manualInput.style.display = 'none';
        selectElement.required = true;
        manualInput.required = false;
    }
}

// 16진수 주소를 10진수로 변환
function parseAddress(addressInput) {
    if (addressInput.startsWith('0x') || addressInput.startsWith('0X')) {
        return parseInt(addressInput, 16);
    }
    return parseInt(addressInput, 10);
}

// 센서 등록
async function registerSensor(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const isManualInput = document.getElementById('manual-address-input').checked;
    
    let address;
    if (isManualInput) {
        const manualAddress = formData.get('manual_address');
        if (!manualAddress) {
            showToast('error', '주소를 입력해주세요.');
            return;
        }
        try {
            address = parseAddress(manualAddress);
            if (address < 0x08 || address > 0x77) {
                showToast('error', 'I2C 주소는 0x08~0x77 범위여야 합니다.');
                return;
            }
        } catch (e) {
            showToast('error', '올바른 16진수 주소를 입력해주세요. (예: 0x48)');
            return;
        }
    } else {
        address = parseInt(formData.get('address'));
        if (!address) {
            showToast('error', '주소를 선택해주세요.');
            return;
        }
    }
    
    const sensorData = {
        address: address,
        name: formData.get('name'),
        type: formData.get('type'),
        description: formData.get('description'),
        voltage: formData.get('voltage')
    };
    
    try {
        const response = await fetch(`${API_URL}/sensors`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(sensorData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('success', '센서가 성공적으로 등록되었습니다.');
            event.target.reset();
            loadSensors();
            
            // 폼 리셋 및 UI 정리
            event.target.reset();
            document.getElementById('manual-address-input').checked = false;
            toggleManualAddressInput();
            
            // 등록된 주소를 선택 옵션에서 제거 (스캔된 주소만)
            const addressSelect = document.getElementById('sensor-address');
            const option = Array.from(addressSelect.options).find(opt => opt.value == sensorData.address);
            if (option && option.style.color === 'rgb(220, 53, 69)') { // 미등록 센서 옵션만 제거
                option.remove();
            }
        } else {
            showToast('error', result.message || '센서 등록에 실패했습니다.');
        }
        
    } catch (error) {
        console.error('센서 등록 오류:', error);
        showToast('error', '센서 등록 중 오류가 발생했습니다.');
    }
}

// 센서 편집
async function editSensor(sensorId) {
    try {
        const response = await fetch(`${API_URL}/sensors/${sensorId}`);
        const sensor = await response.json();
        
        if (sensor) {
            // 편집 폼에 데이터 채우기
            document.getElementById('edit-sensor-id').value = sensor.id;
            document.getElementById('edit-sensor-name').value = sensor.name;
            document.getElementById('edit-sensor-type').value = sensor.type;
            document.getElementById('edit-sensor-description').value = sensor.description || '';
            document.getElementById('edit-sensor-voltage').value = sensor.voltage;
            
            showModal('edit-modal');
        }
    } catch (error) {
        console.error('센서 정보 로드 오류:', error);
        showToast('error', '센서 정보를 불러올 수 없습니다.');
    }
}

// 센서 업데이트
async function updateSensor(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const sensorId = formData.get('id');
    const sensorData = {
        name: formData.get('name'),
        type: formData.get('type'),
        description: formData.get('description'),
        voltage: formData.get('voltage')
    };
    
    try {
        const response = await fetch(`${API_URL}/sensors/${sensorId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(sensorData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('success', '센서 정보가 업데이트되었습니다.');
            closeModal('edit-modal');
            loadSensors();
        } else {
            showToast('error', result.message || '센서 업데이트에 실패했습니다.');
        }
        
    } catch (error) {
        console.error('센서 업데이트 오류:', error);
        showToast('error', '센서 업데이트 중 오류가 발생했습니다.');
    }
}

// 센서 삭제
async function deleteSensor(sensorId) {
    if (!confirm('정말로 이 센서를 삭제하시겠습니까?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_URL}/sensors/${sensorId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            showToast('success', '센서가 삭제되었습니다.');
            loadSensors();
        } else {
            showToast('error', result.message || '센서 삭제에 실패했습니다.');
        }
        
    } catch (error) {
        console.error('센서 삭제 오류:', error);
        showToast('error', '센서 삭제 중 오류가 발생했습니다.');
    }
}

// 모달 표시
function showModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
    document.body.style.overflow = 'hidden';
}

// 모달 닫기
function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    document.body.style.overflow = 'auto';
}

// 토스트 알림 표시
function showToast(type, message) {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toast-message');
    
    // 기존 클래스 제거
    toast.className = 'toast';
    
    // 새 클래스 및 메시지 설정
    toast.classList.add(type);
    toastMessage.textContent = message;
    
    // 토스트 표시
    toast.classList.add('show');
    
    // 3초 후 자동 숨김
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}