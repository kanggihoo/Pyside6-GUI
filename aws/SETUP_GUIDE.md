# 🚀 AWS 인프라 구축 가이드

AI Dataset Curation Tool을 위한 AWS 인프라를 구축하는 단계별 가이드입니다.

## 📋 목차

1. [사전 준비](#-사전-준비)
2. [빠른 시작](#-빠른-시작)
3. [상세 설정](#-상세-설정)
4. [스크립트 사용법](#-스크립트-사용법)
5. [문제 해결](#-문제-해결)
6. [비용 관리](#-비용-관리)


### 1. 설정 파일 편집
```bash
# config.json 파일 수정
cd boto3/
nano config.json
```

`config.json` 파일에서 버킷 이름을 수정하세요:
```json
{
  "s3": {
    "bucket_name": "your-unique-bucket-name"
  }
}
```

### 2. 인프라 구축 실행
```bash
# 통합 실행 (권장)
python run_setup.py --bucket-name your-unique-bucket-name

# 또는 설정 파일 사용
python run_setup.py
```

### 3. 완료 확인
스크립트가 성공적으로 완료되면 다음과 같은 메시지가 출력됩니다:
```
🎉 축하합니다! AWS 인프라 구축이 완료되었습니다.
```

## 🔧 상세 설정

### config.json 파일 상세 설정

```json
{
  "aws": {
    "region": "ap-northeast-2",        // AWS 리전
    "profile": "default"               // AWS 프로필 (선택사항)
  },
  "s3": {
    "bucket_name": "ai-dataset-curation-bucket",  // 고유한 버킷 이름 필요
    "bucket_prefix": "main_category",
    "versioning_enabled": true,
    "public_access_blocked": true,
    "lifecycle_policy": {
      "non_representative_transition_days": 30,   // 대표 이미지가 아닌 파일들의 Glacier 이동 일수
      "target_storage_class": "GLACIER_IR"        // 목표 스토리지 클래스
    }
  },
  "dynamodb": {
    "table_name": "ProductAssets",     // 테이블 이름
    "billing_mode": "PAY_PER_REQUEST", // 요금 모드
    "global_secondary_indexes": [
      {
        "index_name": "CurationStatus-LastUpdatedAt-GSI",
        "partition_key": "curation_status",
        "sort_key": "last_updated_at"
      },
      {
        "index_name": "CuratedBy-LastUpdatedAt-GSI", 
        "partition_key": "curated_by",
        "sort_key": "last_updated_at"
      }
    ]
  }
}
```

## 📝 스크립트 사용법

### 1. AWS 설정 확인만 실행
```bash
python check_aws_setup.py
python run_setup.py --check-only
```

### 2. 인프라 구축만 실행 (확인 건너뛰기)
```bash
python run_setup.py --bucket-name my-bucket --skip-check
```

### 3. 다른 리전으로 구축
```bash
python run_setup.py --bucket-name my-bucket --region us-west-2
```

### 4. 다른 AWS 프로필 사용
```bash
python run_setup.py --bucket-name my-bucket --profile my-profile
```

### 5. 사용자 정의 설정 파일 사용
```bash
python run_setup.py --config my-config.json
```

### 6. 자동 실행 (확인 프롬프트 없이)
```bash
python run_setup.py --bucket-name my-bucket --force
```

### 7. JSON 형식으로 결과 출력
```bash
python check_aws_setup.py --json
```

## 🚨 문제 해결

### 자주 발생하는 오류

#### 1. 자격 증명 오류
```
❌ AWS 자격 증명이 설정되지 않았습니다.
```
**해결 방법:**
```bash
aws configure
# 또는
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
```

#### 2. 권한 부족 오류
```
❌ S3 권한 부족: create_bucket
```
**해결 방법:**
- IAM 콘솔에서 사용자에게 필요한 권한 추가
- 또는 관리자에게 권한 요청

#### 3. 버킷 이름 중복 오류
```
❌ S3 버킷 생성 실패: BucketAlreadyExists
```
**해결 방법:**
```bash
# 고유한 버킷 이름 사용 (예: 회사명-프로젝트명-랜덤값)
python run_setup.py --bucket-name mycompany-ai-dataset-$(date +%s)
```

#### 4. 리전 접근 오류
```
❌ 리전 "ap-northeast-2" 접근 권한이 없습니다.
```
**해결 방법:**
```bash
# 다른 리전 시도
python run_setup.py --bucket-name my-bucket --region us-east-1
```

### 로그 확인

스크립트 실행 중 오류가 발생하면 다음과 같이 상세 로그를 확인할 수 있습니다:

```bash
# 상세 출력으로 실행
python run_setup.py --bucket-name my-bucket --force 2>&1 | tee setup.log
```

## 💰 비용 관리

### 예상 비용 (ap-northeast-2 기준, 2024년)

#### S3 비용
- **Standard 스토리지**: $0.025/GB/월
- **Glacier Instant Retrieval**: $0.0125/GB/월 (30일 후 자동 이전)
- **요청 비용**: PUT $0.0047/1,000건, GET $0.0004/1,000건

#### DynamoDB 비용
- **온디맨드 모드**: 읽기 $0.285/백만 RRU, 쓰기 $1.4275/백만 WRU
- **스토리지**: $0.285/GB/월

### 비용 최적화 팁

1. **수명 주기 정책 활용**: 대표 이미지가 아닌 파일들은 자동으로 Glacier로 이동
2. **온디맨드 요금제**: 초기 단계에서는 온디맨드가 더 경제적
3. **태그 관리**: 리소스에 태그를 추가하여 비용 추적

### 비용 모니터링

```bash
# AWS CLI로 현재 월 비용 확인
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost
```

## 🔄 업데이트 및 삭제

### 인프라 업데이트
```bash
# 기존 리소스는 그대로 두고 새로운 설정 적용
python run_setup.py --bucket-name existing-bucket --force
```

### 인프라 삭제
⚠️ **주의**: 이 작업은 모든 데이터를 삭제합니다!

```bash
# S3 버킷 삭제 (모든 객체 포함)
aws s3 rb s3://your-bucket-name --force

# DynamoDB 테이블 삭제
aws dynamodb delete-table --table-name ProductAssets
```

## 📞 지원

문제가 발생하거나 질문이 있으시면:

1. **GitHub Issues**: 프로젝트 저장소에 이슈 생성
2. **AWS 공식 문서**: https://docs.aws.amazon.com/
3. **AWS 지원 센터**: https://console.aws.amazon.com/support/

---

## 📚 추가 리소스

- [AWS S3 공식 문서](https://docs.aws.amazon.com/s3/)
- [AWS DynamoDB 공식 문서](https://docs.aws.amazon.com/dynamodb/)
- [AWS CLI 공식 문서](https://docs.aws.amazon.com/cli/)
- [Boto3 공식 문서](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) 