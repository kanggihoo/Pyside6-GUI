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
- **효율적 이미지 조회**: DynamoDB에 저장된 파일 리스트를 기반으로 S3 객체 키를 직접 구성하여 `list_objects_v2` 호출 최소화

### 사용자 경험 최적화
- **비동기 처리**: QThread를 활용해 AWS 통신 중에도 GUI가 멈추지 않는 반응형 UI 구현
- **로컬 캐싱**: 조회한 썸네일 이미지를 캐싱하여 반복 조회 시 로딩 속도 향상 및 비용 절감
- **즉시 반영**: 이미지 파일 리스트가 DynamoDB에 저장되어 있어 업로드/삭제 작업 후 즉시 UI에 반영

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

#### 1. S3 API 호출 최소화 (주요 최적화)
- **DynamoDB 기반 파일 관리**: 각 제품의 이미지 파일 리스트를 DynamoDB에 저장하여 S3 `list_objects_v2` API 호출을 대폭 감소
- **직접 키 구성**: `main_category/sub_category/product_id/folder/filename` 형태로 S3 객체 키를 직접 구성하여 조회 성능 향상
- **배치 URL 생성**: 여러 이미지의 Presigned URL을 한 번에 생성하여 API 호출 횟수 최소화

#### 2. S3 수명 주기 정책 (향후 구현 예정)
- **대표 이미지 태깅**: 큐레이션 완료 시 선정된 대표 이미지에 `status: representative` 태그 지정
- **자동 아카이빙**: 태그가 없는 이미지들을 S3 Glacier Instant Retrieval로 자동 전환하여 스토리지 비용 절감

#### 3. 데이터 전송 최적화
- **썸네일 캐싱**: 로컬에 이미지 캐시 저장으로 반복 다운로드 방지
- **온디맨드 빌링**: DynamoDB PAY_PER_REQUEST 모드로 실제 사용량에 따른 과금

## 💾 데이터 구조 설계 (Data Structure Design)

### 1. Amazon S3: 객체 키 구조
이미지와 메타데이터는 논리적 그룹화를 위해 아래와 같은 계층적 키 구조로 S3에 저장됩니다.

```
main_category/
│
└── sub_category/                  (서브 카테고리 ID)
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
**역할**: 상품의 기본 정보, 큐레이션 상태, 폴더별 이미지 파일 리스트를 관리하여 S3 `list_objects_v2` 호출을 최소화하고 비용을 효율적으로 관리합니다.

**테이블 정보**:
- 테이블명: `ProductAssets`
- 파티션 키 (PK): `sub_category` (Number)
- 정렬 키 (SK): `product_id` (String)
- 빌링 모드: PAY_PER_REQUEST (온디맨드)

#### 초기 업로드 후 생성되는 속성(Attributes):

| 속성 이름 | 데이터 타입 | 역할 및 설명 |
|-----------|-------------|--------------|
| `sub_category` | Number | (PK) 상품의 서브 카테고리 ID |
| `product_id` | String | (SK) 고유 상품 ID |
| `main_category` | String | 메인 카테고리명 (예: "TOP") |
| `current_status` | String | 큐레이션 상태 (초기값: "PENDING") |
| `created_at` | String | 제품 생성 시각 (ISO 8601 형식) |
| `last_updated_at` | String | 마지막 수정 시각 (ISO 8601 형식) |
| `detail` | List | detail 폴더의 이미지 파일명 리스트 (빈 리스트 허용) |
| `summary` | List | summary 폴더의 이미지 파일명 리스트 (빈 리스트 허용) |
| `segment` | List | segment 폴더의 이미지 파일명 리스트 (빈 리스트 허용) |
| `text` | List | text 폴더의 이미지 파일명 리스트 (빈 리스트 허용) |

#### 큐레이션 완료 후 추가되는 속성:
| 속성 이름 | 데이터 타입 | 역할 및 설명 |
|-----------|-------------|--------------|
| `representative_assets` | String | 선정된 대표 이미지 정보 (JSON 문자열) |
| `completed_by` | String | 작업 완료자 ID |

#### 파일 리스트 구조 예시:
```json
{
  "sub_category": 1005,
  "product_id": "79823",
  "main_category": "TOP",
  "current_status": "PENDING",
  "created_at": "2024-01-15T10:30:00.000Z",
  "last_updated_at": "2024-01-15T10:30:00.000Z",
  "detail": ["image_001.jpg", "image_002.jpg", "image_003.jpg"],
  "summary": ["summary_01.jpg"],
  "segment": [],
  "text": ["text_info.jpg"]
}
```

#### 특별한 메타데이터 아이템:
카테고리 통계 관리를 위한 특별한 아이템이 자동 생성됩니다:
```json
{
  "sub_category": 0,
  "product_id": "CATEGORY_METADATA",
  "categories_info": "{\"main_categories\": [\"TOP\"], \"sub_categories\": {\"TOP\": [1005]}, \"product_counts\": {\"TOP\": {\"1005\": 150}}, \"total_products\": 150}",
  "last_updated_at": "2024-01-15T10:30:00.000Z"
}
```

#### GSI (글로벌 보조 인덱스):
- **`CurrentStatus-LastUpdatedAt-GSI`**: 큐레이션 상태별 최신순 조회
  - 파티션 키: `current_status`
  - 정렬 키: `last_updated_at`
  - 프로젝션: 모든 속성 (ALL)

#### 비용 최적화 설계:
- **S3 조회 최소화**: 파일 리스트를 DynamoDB에 저장하여 `list_objects_v2` API 호출 횟수 대폭 감소
- **일관된 스키마**: 모든 제품이 동일한 필드 구조를 가져 예측 가능한 쿼리 성능 보장
- **빈 리스트 허용**: 폴더가 비어있어도 명시적으로 표현하여 데이터 상태 명확화

## 🚀 설치 및 실행

### 요구사항
- Python 3.8+
- AWS CLI 설정 완료 (`aws configure`)
- 필요한 AWS 권한:
  - S3: `s3:GetObject`, `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket`
  - DynamoDB: `dynamodb:CreateTable`, `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:UpdateItem`, `dynamodb:Query`, `dynamodb:Scan`

### 설치
```bash
# 프로젝트 클론
git clone <repository-url>
cd PySide6-GUI

# 의존성 설치
pip install boto3 PySide6 Pillow requests

# AWS 설정 파일 생성
cd aws
cp config.json.example config.json
# config.json 파일을 편집하여 버킷명과 테이블명 설정
```

### 실행

#### 1. AWS 인프라 구축
```bash
cd aws
python setup_aws_infrastructure.py --bucket-name your-bucket-name
```

#### 2. 초기 데이터 업로드
```bash
python initial_upload.py
```

#### 3. GUI 큐레이션 도구 실행
```bash
python gui_main.py
```

#### 4. 로컬 이미지 관리 도구 (선택사항)
```bash
python main.py
```

## 📁 프로젝트 구조

```
PySide6-GUI/
├── main.py                          # 메인 애플리케이션 진입점
├── aws/                             # AWS 관련 모듈
│   ├── aws_manager.py              # 통합 AWS 관리 모듈 (S3 + DynamoDB)
│   ├── initial_upload.py           # 초기 데이터 업로드 스크립트
│   ├── setup_aws_infrastructure.py # AWS 인프라 구축 스크립트
│   ├── gui_main.py                 # AWS 기반 GUI 메인
│   ├── image_cache.py              # 이미지 캐싱 모듈
│   ├── config.json                 # AWS 설정 파일
│   └── widgets/                    # AWS GUI 위젯들
│       ├── main_image_viewer.py    # 메인 이미지 뷰어
│       ├── product_list_widget.py  # 제품 목록 위젯
│       ├── representative_panel.py # 대표 이미지 선택 패널
│       ├── category_selection_dialog.py # 카테고리 선택 다이얼로그
│       └── image_viewer_dialog.py  # 이미지 상세 뷰어
├── widgets/                        # 로컬 GUI 위젯 모듈들
│   ├── image_grid.py
│   ├── image_viewer.py
│   ├── project_tree.py
│   └── ...
├── TOP/                            # 테스트 데이터 (메인 카테고리)
│   └── 1005/                       # 서브 카테고리
└── test_data_*/                    # 기타 테스트 데이터
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