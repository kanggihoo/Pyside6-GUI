#!/usr/bin/env python3
"""
배포용 패키지 생성 스크립트

빌드된 애플리케이션을 배포하기 쉬운 형태로 패키징합니다.

사용법:
    python package.py                  # 기본 패키징
    python package.py --format zip     # ZIP 형식으로 패키징
    python package.py --format tar     # TAR.GZ 형식으로 패키징
    python package.py --include-src    # 소스코드도 함께 패키징
"""

import shutil
import zipfile
import tarfile
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
import os

def parse_arguments():
    """명령줄 인수 파싱"""
    parser = argparse.ArgumentParser(description='배포용 패키지 생성 도구')
    parser.add_argument('--format', choices=['zip', 'tar'], default='zip',
                       help='패키지 형식 선택 (기본값: zip)')
    parser.add_argument('--include-src', action='store_true',
                       help='소스코드도 함께 패키징')
    parser.add_argument('--output-dir', default='.',
                       help='출력 디렉토리 (기본값: 현재 디렉토리)')
    return parser.parse_args()

def get_version_info():
    """버전 정보 가져오기"""
    try:
        # pyproject.toml에서 버전 읽기
        import tomllib
        with open('pyproject.toml', 'rb') as f:
            pyproject = tomllib.load(f)
            version = pyproject.get('project', {}).get('version', '1.0.0')
    except Exception:
        # toml 라이브러리가 없거나 파일을 읽을 수 없는 경우
        version = '1.0.0'
    
    return version

def create_readme_for_package():
    """패키지용 README 생성"""
    readme_content = """# AI 학습용 이미지 선정 도구

## 사용법

### Windows
1. `AI_Image_Selector.exe` 파일을 더블클릭하여 실행
2. 또는 명령 프롬프트에서: `AI_Image_Selector.exe`

### macOS
1. `AI Image Selector.app`을 더블클릭하여 실행
2. 처음 실행 시 보안 경고가 나타날 수 있습니다:
   - 시스템 환경설정 > 보안 및 개인정보보호 > 일반에서 "확인 없이 열기" 클릭
   - 또는 앱을 우클릭하고 "열기" 선택

### Linux
1. 터미널에서: `./AI_Image_Selector`
2. 또는 파일 관리자에서 더블클릭 (실행 권한 필요)

## 기능

- 이미지 폴더 탐색 및 미리보기
- 모델 착용 이미지와 제품 단독 이미지 구분
- 대표 이미지 선정 및 저장
- 키보드 단축키 지원 (J/K로 제품 간 이동)
- 진행 상황 추적

## 시스템 요구사항

- Windows 10 이상 / macOS 10.14 이상 / Ubuntu 18.04 이상
- 메모리: 최소 4GB RAM 권장
- 저장공간: 설치 시 약 200MB

## 문제 해결

### Windows
- 바이러스 백신 소프트웨어에서 차단하는 경우 예외 목록에 추가
- "Windows에서 PC를 보호했습니다" 메시지: "추가 정보" > "실행" 클릭

### macOS
- "개발자를 확인할 수 없습니다" 오류: 시스템 환경설정에서 허용
- 앱이 손상되었다는 메시지: 터미널에서 `xattr -cr "AI Image Selector.app"` 실행

### Linux
- 실행 권한 설정: `chmod +x AI_Image_Selector`
- 라이브러리 의존성 오류: 시스템 업데이트 필요

## 지원

문제가 발생하면 개발팀에 문의하세요.
"""
    
    return readme_content

def create_package_info():
    """패키지 정보 JSON 생성"""
    info = {
        "name": "AI Image Selector",
        "version": get_version_info(),
        "build_date": datetime.now().isoformat(),
        "platform": sys.platform,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "description": "AI 학습용 의류 대표 이미지 선정 GUI 도구",
        "author": "Your Name",
        "license": "MIT"
    }
    
    return json.dumps(info, indent=2, ensure_ascii=False)

def find_executable():
    """빌드된 실행파일 찾기"""
    dist_path = Path('dist')
    
    if not dist_path.exists():
        return None, None
    
    if sys.platform == 'darwin':
        # macOS: 앱 번들 우선, 없으면 실행파일
        app_path = dist_path / 'AI Image Selector.app'
        exe_path = dist_path / 'AI_Image_Selector'
        
        if app_path.exists():
            return app_path, 'app'
        elif exe_path.exists():
            return exe_path, 'exe'
    elif sys.platform.startswith('win'):
        # Windows
        exe_path = dist_path / 'AI_Image_Selector.exe'
        if exe_path.exists():
            return exe_path, 'exe'
    else:
        # Linux
        exe_path = dist_path / 'AI_Image_Selector'
        if exe_path.exists():
            return exe_path, 'exe'
    
    return None, None

def create_zip_package(package_name, executable_path, executable_type, include_src=False):
    """ZIP 패키지 생성"""
    zip_path = f"{package_name}.zip"
    
    print(f"📦 ZIP 패키지 생성 중: {zip_path}")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
        # 실행파일 또는 앱 번들 추가
        if executable_type == 'app':
            # macOS 앱 번들의 모든 파일 추가
            for file_path in executable_path.rglob('*'):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(Path('dist')))
                    zipf.write(file_path, arcname)
        else:
            # 실행파일과 관련 라이브러리들 추가
            dist_path = Path('dist')
            for item in dist_path.iterdir():
                if item.is_file():
                    zipf.write(item, item.name)
                elif item.is_dir() and item.name == executable_path.stem:
                    # 실행파일과 같은 이름의 디렉토리 (라이브러리들)
                    for file_path in item.rglob('*'):
                        if file_path.is_file():
                            arcname = str(file_path.relative_to(dist_path))
                            zipf.write(file_path, arcname)
        
        # README 추가
        readme_content = create_readme_for_package()
        zipf.writestr('README.txt', readme_content)
        
        # 패키지 정보 추가
        package_info = create_package_info()
        zipf.writestr('package_info.json', package_info)
        
        # 소스코드 포함 옵션
        if include_src:
            print("📁 소스코드 추가 중...")
            source_files = [
                'main.py',
                'pyproject.toml',
                'app.spec',
                'build.py',
                'package.py',
            ]
            
            for src_file in source_files:
                if Path(src_file).exists():
                    zipf.write(src_file, f"source/{src_file}")
            
            # widgets 폴더 추가
            widgets_path = Path('widgets')
            if widgets_path.exists():
                for py_file in widgets_path.glob('*.py'):
                    zipf.write(py_file, f"source/{py_file}")
    
    return zip_path

def create_tar_package(package_name, executable_path, executable_type, include_src=False):
    """TAR.GZ 패키지 생성"""
    tar_path = f"{package_name}.tar.gz"
    
    print(f"📦 TAR.GZ 패키지 생성 중: {tar_path}")
    
    with tarfile.open(tar_path, 'w:gz') as tarf:
        # 실행파일 또는 앱 번들 추가
        if executable_type == 'app':
            tarf.add(executable_path, arcname=executable_path.name)
        else:
            # 실행파일과 관련 파일들 추가
            dist_path = Path('dist')
            for item in dist_path.iterdir():
                if item.name.startswith(executable_path.stem):
                    tarf.add(item, arcname=item.name)
        
        # README와 패키지 정보는 임시 파일로 생성하여 추가
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_readme:
            tmp_readme.write(create_readme_for_package())
            tmp_readme.flush()
            tarf.add(tmp_readme.name, arcname='README.txt')
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_info:
            tmp_info.write(create_package_info())
            tmp_info.flush()
            tarf.add(tmp_info.name, arcname='package_info.json')
        
        # 소스코드 포함 옵션
        if include_src:
            print("📁 소스코드 추가 중...")
            source_files = ['main.py', 'pyproject.toml', 'app.spec', 'build.py', 'package.py']
            
            for src_file in source_files:
                if Path(src_file).exists():
                    tarf.add(src_file, arcname=f"source/{src_file}")
            
            widgets_path = Path('widgets')
            if widgets_path.exists():
                tarf.add(widgets_path, arcname="source/widgets")
    
    return tar_path

def main():
    """메인 함수"""
    args = parse_arguments()
    
    # 실행파일 찾기
    executable_path, executable_type = find_executable()
    
    if not executable_path:
        print("❌ 빌드된 실행파일을 찾을 수 없습니다.")
        print("먼저 python build.py를 실행하여 애플리케이션을 빌드하세요.")
        sys.exit(1)
    
    print(f"✅ 실행파일 발견: {executable_path}")
    
    # 패키지 이름 생성
    version = get_version_info()
    date_str = datetime.now().strftime("%Y%m%d")
    platform_name = {
        'darwin': 'macOS',
        'win32': 'Windows', 
        'linux': 'Linux'
    }.get(sys.platform, sys.platform)
    
    package_name = f"AI_Image_Selector_v{version}_{platform_name}_{date_str}"
    
    # 출력 디렉토리 생성
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # 원본 작업 디렉토리 저장
    original_cwd = Path.cwd()
    
    try:
        # 출력 디렉토리로 이동
        os.chdir(output_dir)
        
        # 패키지 생성
        if args.format == 'zip':
            package_path = create_zip_package(package_name, executable_path, executable_type, args.include_src)
        else:  # tar
            package_path = create_tar_package(package_name, executable_path, executable_type, args.include_src)
        
        # 결과 출력
        package_size = Path(package_path).stat().st_size
        print(f"\n✅ 배포 패키지가 생성되었습니다!")
        print(f"📄 파일명: {package_path}")
        print(f"📏 크기: {package_size / (1024*1024):.1f} MB")
        print(f"📍 위치: {output_dir.absolute() / package_path}")
        
        print(f"\n📋 패키지 내용:")
        print(f"- 실행파일: {executable_path.name}")
        print(f"- README.txt (사용법 안내)")
        print(f"- package_info.json (패키지 정보)")
        if args.include_src:
            print(f"- source/ (소스코드)")
        
        print(f"\n🚀 배포 준비 완료!")
        print(f"이 패키지를 다른 사용자에게 전달하면 Python 설치 없이 사용할 수 있습니다.")
        
    finally:
        # 원본 디렉토리로 복귀
        os.chdir(original_cwd)

if __name__ == '__main__':
    main() 