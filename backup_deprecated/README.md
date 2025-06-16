# 사용하지 않는 파일들 백업

이 폴더에는 프로젝트 구조 개선 과정에서 사용하지 않게 된 파일들이 백업되어 있습니다.

## 백업된 파일들

### simpleBME688.py
- **용도**: BME688 센서 테스트용 간단한 클래스
- **대체**: `bme688_sensor.py`로 완전히 대체됨
- **삭제 이유**: 기능이 중복되고 더 이상 사용되지 않음

### simpleEddy.py  
- **용도**: SDP810 센서 I2C 통신 테스트 코드
- **대체**: `sdp810_sensor.py`로 완전히 대체됨
- **삭제 이유**: 테스트 코드로만 사용되었고 실제 프로덕션에서 import되지 않음

### order
- **용도**: 프로젝트 구조 설명 텍스트 파일
- **대체**: README.md에 정보가 포함됨
- **삭제 이유**: 중복된 정보로 관리 불필요

## 복구 방법

필요한 경우 다음과 같이 파일을 복구할 수 있습니다:

```bash
# 개별 파일 복구
cp backup_deprecated/simpleBME688.py .
cp backup_deprecated/simpleEddy.py .
cp backup_deprecated/order .

# 전체 백업 복구
cp backup_deprecated/* .
```

## 정리 일자
2024-06-16