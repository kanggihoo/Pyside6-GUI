# 🤖 AWS 기반 AI 데이터셋 큐레이션 GUI 도구 (AI Dataset Curation Tool)

효율적인 AI 데이터셋 구축을 위한 데스크톱 애플리케이션입니다. 로컬에 저장된 대규모 이미지 데이터를 AWS S3와 DynamoDB로 이전하고, PySide6 기반의 GUI를 통해 사용자가 직관적으로 데이터를 정제, 선택 및 관리할 수 있도록 지원합니다.

## 🎯 프로젝트 목표 (Project Goal)

본 프로젝트는 대규모 상품 이미지 데이터셋을 AWS 클라우드 환경으로 이전하고, 여러 사용자가 일관된 기준에 따라 데이터를 효율적으로 정제하고 관리할 수 있는 통합 큐레이션 시스템을 구축하는 것을 목표로 합니다.

## ✨ 주요 기능 (Key Features)

### 대표 이미지 선정
- **대표 색상**: 정면/후면 누끼, 모델 착용샷 (총 3개) 선택
- **기타 색상**: 정면 누끼 (색상별 1개) 선택

### 이미지 관리
- **재분류**: 텍스트 포함 이미지를 text 폴더로 이동
- **삭제**: 불필요하거나 품질이 낮은 이미지 제거
- **업로드**: 로컬의 이미지를 S3에 업로드하여 즉시 큐레이션에 반영

### 대용량 데이터 처리
- **페이지네이션**: DynamoDB의 수만 건 데이터를 페이지 단위로 나누어 로드하여 메모리 및 네트워크 부하 최소화
- **작업 상태 저장**: 사용자가 앱을 종료해도 마지막 작업 지점을 기억하여, 다음 실행 시 중단된 부분부터 작업을 재개

### 사용자 경험 최적화
- **비동기 처리**: QThread를 활용해 AWS 통신 중에도 GUI가 멈추지 않는 반응형 UI 구현
- **로컬 캐싱**: 조회한 썸네일 이미지를 캐싱하여 반복 조회 시 로딩 속도 향상 및 비용 절감

## 🏛️ 시스템 아키텍처 (System Architecture)

### 전체 데이터 흐름
```
1. 최초 데이터 이전 (로컬 → AWS)
   │
   └─> 2. GUI 실행 및 AWS 인증
       │
       └─> 3. 데이터 조회 (DynamoDB 메타데이터 + S3 썸네일)
           │
           └─> 4. 사용자 큐레이션 작업 수행
               │
               └─> 5. 결과 반영 (S3 객체 및 DynamoDB 아이템 업데이트)
```

### 비용 최적화 전략
S3 수명 주기 정책: 대표 이미지로 선정되지 않은 이미지들은 접근 빈도가 현저히 낮으므로, 저렴한 스토리지 클래스(S3 Glacier Instant Retrieval)로 자동 전환하여 비용을 최적화합니다.

**구현**: GUI에서 대표 이미지를 선정할 때 해당 S3 객체에 `status: representative` 태그를 지정하고, 수명 주기 정책은 이 태그가 없는 객체에만 적용되도록 설정합니다.

## 💾 데이터 구조 설계 (Data Structure Design)

### 1. Amazon S3: 객체 키 구조
이미지와 메타데이터는 논리적 그룹화를 위해 아래와 같은 계층적 키 구조로 S3에 저장됩니다.

```
main_category/
│
└── 1005/                  (서브 카테고리 ID)
    │
    ├── 79823/             (제품 ID)
    │   ├── meta.json
    │   ├── detail/
    │   │   ├── image_001.jpg
    │   │   └── ...
    │   ├── segment/
    │   │   └── ...
    │   └── ...
    │
    └── 117785/
        └── ...
```

### 2. Amazon DynamoDB: 테이블 스키마
**역할**: 상품 정보, 큐레이션 상태, 최종 선정된 대표 이미지 S3 경로 등 모든 메타데이터를 관리합니다.

**테이블 정보**:
- 테이블명: `ProductAssets` (예시)
- 파티션 키 (PK): `sub_category_id` (String)
- 정렬 키 (SK): `product_id` (String)

#### 속성(Attributes) 상세:

| 속성 이름 | 데이터 타입 | 역할 및 설명 |
|-----------|-------------|--------------|
| `sub_category_id` | String | (PK) 상품의 서브 카테고리 ID |
| `product_id` | String | (SK) 고유 상품 ID |
| `product_info` | Map | meta.json의 기본 정보 (상품명, 브랜드, 가격 등) |
| `available_colors` | String Set | 상품의 모든 색상 리스트 |
| `current_status` | String | (GSI 후보) 작업 상태 (PENDING, COMPLETED) |
| `completed_by` | String | (GSI 후보) 마지막 작업자 ID |
| `last_updated_at` | String | (GSI 후보) 마지막 수정 시각 (ISO 8601 형식) |
| `representative_assets` | Map | 선정된 대표 이미지 정보가 저장되는 중첩 객체 |

#### `representative_assets` 중첩 구조 예시:
```json
{
  "main_color": "black",
  "images": {
    "black_segment_front": "s3://.../image_001.jpg",
    "black_segment_back": "s3://.../image_002.jpg",
    "red_segment_front": "s3://.../image_011.jpg"
  }
}
```

#### GSI (글로벌 보조 인덱스):
- `CurationStatus-LastUpdatedAt-GSI`: 큐레이션 상태별 작업 목록 조회용
<!-- - `CuratedBy-LastUpdatedAt-GSI`: 특정 작업자별 이력 조회용 -->

## 🚀 설치 및 실행

### 요구사항
- Python 3.8+
- AWS CLI 설정 완료
- 필요한 AWS 권한 (S3, DynamoDB 읽기/쓰기)

### 설치
```bash
# 프로젝트 클론
git clone <repository-url>
cd PySide6-GUI

# 의존성 설치
pip install -r requirements.txt
```

### 실행
```bash
python main.py
```

## 📁 프로젝트 구조

```
PySide6-GUI/
├── main.py                    # 메인 애플리케이션 진입점
├── s3_manager.py             # S3 관리 모듈
├── dynamodb_manager.py       # DynamoDB 관리 모듈
├── widgets/                  # GUI 위젯 모듈들
│   ├── image_grid.py
│   ├── image_viewer.py
│   ├── project_tree.py
│   └── ...
├── boto3/                    # AWS 관련 문서
└── test_data_*/             # 테스트 데이터
```

## 🤝 기여하기 (Contributing)

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스 (License)

이 프로젝트는 MIT 라이선스 하에 있습니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 연락처 (Contact)

프로젝트 관련 문의사항이 있으시면 이슈를 생성해 주세요.