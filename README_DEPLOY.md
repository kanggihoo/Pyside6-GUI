# PySide6 GUI 애플리케이션 배포 가이드

이 문서는 PySide6로 개발된 "AI 학습용 이미지 선정 도구"를 실행파일로 빌드하고 배포하는 방법을 설명합니다.

## 📋 목차

1. [준비사항](#준비사항)
2. [빠른 시작](#빠른-시작)
3. [상세 빌드 과정](#상세-빌드-과정)
4. [배포 옵션](#배포-옵션)
5. [문제 해결](#문제-해결)
6. [플랫폼별 주의사항](#플랫폼별-주의사항)

## 🔧 준비사항

### 시스템 요구사항
- Python 3.8 이상
- 충분한 디스크 공간 (빌드 시 약 500MB 필요)
- 메모리 4GB 이상 권장

### 의존성 설치
```bash
# uv를 사용하는 경우 (권장)
uv sync

# pip를 사용하는 경우
pip install -r requirements.txt
```

## 🚀 빠른 시작

### 원클릭 배포
전체 프로세스를 자동으로 실행:
```bash
python deploy.py
```

### 단계별 실행
```bash
# 1. 애플리케이션 빌드
python build.py

# 2. 배포 패키지 생성
python package.py
```

## 🔨 상세 빌드 과정

### 1. 빌드 스크립트 (build.py)

#### 기본 빌드
```bash
python build.py
```

#### 옵션들
```bash
# 클린 빌드 (이전 빌드 파일 삭제)
python build.py --clean

# 단일 실행파일 생성 (배포 용이, 느림)
python build.py --onefile

# 디버그 모드
python build.py --debug

# 콘솔 창 포함 (디버깅용)
python build.py --console
```

### 2. 패키징 스크립트 (package.py)

#### 기본 패키징
```bash
python package.py
```

#### 옵션들
```bash
# TAR.GZ 형식으로 패키징
python package.py --format tar

# 소스코드 포함
python package.py --include-src

# 출력 디렉토리 지정
python package.py --output-dir ./releases
```

### 3. 전체 배포 스크립트 (deploy.py)

#### 완전 자동화
```bash
python deploy.py
```

#### 고급 옵션
```bash
# 의존성 설치 건너뛰기
python deploy.py --skip-deps

# 클린 빌드 + TAR 패키징
python deploy.py --clean --format tar

# 단일 파일 + 소스코드 포함
python deploy.py --onefile --include-src
```

## 📦 배포 옵션

### 배포 형태별 특징

| 형태 | 장점 | 단점 | 권장 용도 |
|------|------|------|-----------|
| 디렉토리 배포 | 빠른 실행, 작은 다운로드 | 여러 파일 | 로컬 배포 |
| 단일 실행파일 | 간단한 배포 | 느린 실행, 큰 파일 크기 | 원격 배포 |
| 앱 번들 (macOS) | 네이티브 경험 | macOS 전용 | Mac 사용자 |

### 플랫폼별 결과물

#### Windows
- `dist/AI_Image_Selector.exe` (단일 파일)
- `dist/AI_Image_Selector/` (디렉토리 + 실행파일)

#### macOS
- `dist/AI Image Selector.app` (앱 번들)
- `dist/AI_Image_Selector` (실행파일)

#### Linux
- `dist/AI_Image_Selector` (실행파일)
- `dist/AI_Image_Selector/` (디렉토리 + 실행파일)

## 🔧 문제 해결

### 일반적인 문제들

#### 1. PyInstaller 설치 오류
```bash
# 해결방법
pip install --upgrade pyinstaller
```

#### 2. 모듈 import 오류
`app.spec` 파일의 `hidden_imports` 섹션에 누락된 모듈 추가:
```python
hidden_imports = [
    'PySide6.QtCore',
    'missing_module_name',  # 여기에 추가
]
```

#### 3. 파일 크기가 너무 큰 경우
불필요한 모듈을 제외:
```python
excludes = [
    'matplotlib',
    'numpy',
    'pandas',
    'unnecessary_module',  # 여기에 추가
]
```

#### 4. 실행 시 오류
디버그 모드로 빌드하여 오류 확인:
```bash
python build.py --debug --console
```

### 플랫폼별 문제

#### Windows
- **바이러스 백신 차단**: 빌드 폴더를 예외 목록에 추가
- **권한 오류**: 관리자 권한으로 실행
- **DLL 오류**: Visual C++ Redistributable 설치

#### macOS
- **개발자 인증 오류**: 
  ```bash
  xattr -cr "AI Image Selector.app"
  ```
- **Gatekeeper 차단**: 시스템 환경설정에서 허용

#### Linux
- **라이브러리 의존성**:
  ```bash
  sudo apt-get install libxcb-xinerama0
  ```
- **실행 권한**:
  ```bash
  chmod +x AI_Image_Selector
  ```

## 🎯 플랫폼별 주의사항

### Windows 배포
- **코드 서명**: 상용 배포시 인증서 필요
- **설치 프로그램**: Inno Setup 또는 NSIS 사용 권장
- **자동 업데이트**: Sparkle 또는 유사 도구 고려

### macOS 배포
- **공증 (Notarization)**: App Store 외부 배포시 필요
- **앱 번들 구조**: 올바른 Info.plist 설정 중요
- **DMG 생성**: 배포용 디스크 이미지 생성 권장

### Linux 배포
- **AppImage**: 다양한 배포판 호환성
- **Flatpak/Snap**: 샌드박스 환경에서 실행
- **패키지 관리자**: deb/rpm 패키지 생성 고려

## 📊 성능 최적화

### 빌드 크기 줄이기
1. **불필요한 모듈 제외**
2. **UPX 압축 사용** (이미 활성화됨)
3. **리소스 파일 최적화**

### 실행 속도 향상
1. **디렉토리 배포 방식 사용**
2. **자주 사용하는 모듈을 미리 로드**
3. **애플리케이션 시작 시간 최적화**

## 🛡️ 보안 고려사항

### 코드 보호
- **코드 난독화**: PyArmor 등 도구 사용
- **중요 정보 분리**: 설정파일이나 환경변수 활용

### 배포 보안
- **체크섬 제공**: SHA256 해시값 함께 배포
- **HTTPS 배포**: 안전한 다운로드 채널 사용

## 📈 배포 후 관리

### 사용자 피드백
- **오류 보고**: 자동 크래시 리포트 수집
- **사용 통계**: 익명화된 사용 패턴 분석

### 업데이트 관리
- **버전 관리**: 시맨틱 버저닝 사용
- **자동 업데이트**: 사용자 편의성 향상

---

## 📞 지원

문제가 발생하거나 도움이 필요한 경우:
1. 이 문서의 문제 해결 섹션 확인
2. GitHub Issues에 문제 보고
3. 개발팀에 직접 문의

**Happy Deploying! 🚀** 