#!/usr/bin/env python3
"""
전체 배포 프로세스 자동화 스크립트

의존성 설치부터 빌드, 패키징까지 한번에 수행합니다.

사용법:
    python deploy.py                    # 전체 배포 프로세스 실행
    python deploy.py --skip-deps        # 의존성 설치 건너뛰기
    python deploy.py --clean            # 클린 빌드
    python deploy.py --onefile          # 단일 실행파일로 빌드
    python deploy.py --format tar       # TAR.GZ 형식으로 패키징
"""

import subprocess
import sys
import argparse
from pathlib import Path

def parse_arguments():
    """명령줄 인수 파싱"""
    parser = argparse.ArgumentParser(description='PySide6 GUI 애플리케이션 전체 배포 자동화')
    parser.add_argument('--skip-deps', action='store_true',
                       help='의존성 설치 단계 건너뛰기')
    parser.add_argument('--clean', action='store_true',
                       help='클린 빌드 수행')
    parser.add_argument('--onefile', action='store_true',
                       help='단일 실행파일로 빌드')
    parser.add_argument('--format', choices=['zip', 'tar'], default='zip',
                       help='패키지 형식 (기본값: zip)')
    parser.add_argument('--include-src', action='store_true',
                       help='소스코드도 함께 패키징')
    parser.add_argument('--debug', action='store_true',
                       help='디버그 모드')
    return parser.parse_args()

def run_command(cmd, description, check=True):
    """명령 실행 및 결과 처리"""
    print(f"\n🔄 {description}...")
    print(f"실행: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=check, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} 완료")
            if result.stdout.strip():
                print(f"출력: {result.stdout.strip()}")
        else:
            print(f"⚠️ {description} 경고 (코드: {result.returncode})")
            if result.stderr.strip():
                print(f"오류: {result.stderr.strip()}")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} 실패")
        print(f"오류 코드: {e.returncode}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False

def install_dependencies():
    """의존성 설치"""
    # uv를 직접 사용하여 의존성 동기화 (dev 그룹 포함)
    try:
        return run_command(['uv', 'sync', '--group', 'dev'], "의존성 설치", check=False)
    except FileNotFoundError:
        # uv가 없는 경우 pip 사용
        print("⚠️ uv를 찾을 수 없습니다. pip로 pyinstaller 설치를 시도합니다.")
        return run_command([sys.executable, '-m', 'pip', 'install', 'pyinstaller>=6.14.1'], "PyInstaller 설치", check=False)

def build_application(args):
    """애플리케이션 빌드"""
    cmd = [sys.executable, 'build.py']
    
    if args.clean:
        cmd.append('--clean')
    if args.onefile:
        cmd.append('--onefile')
    if args.debug:
        cmd.append('--debug')
    
    return run_command(cmd, "애플리케이션 빌드")

def package_application(args):
    """애플리케이션 패키징"""
    cmd = [sys.executable, 'package.py', '--format', args.format]
    
    if args.include_src:
        cmd.append('--include-src')
    
    return run_command(cmd, "배포 패키지 생성")

def check_prerequisites():
    """사전 요구사항 확인"""
    print("🔍 사전 요구사항 확인 중...")
    
    # 필수 파일들 확인
    required_files = ['main.py', 'pyproject.toml', 'build.py', 'package.py']
    missing_files = []
    
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ 필수 파일이 없습니다: {', '.join(missing_files)}")
        return False
    
    # Python 버전 확인
    if sys.version_info < (3, 8):
        print(f"❌ Python 3.8 이상이 필요합니다. 현재: {sys.version}")
        return False
    
    print("✅ 사전 요구사항 확인 완료")
    return True

def show_summary():
    """배포 완료 요약 정보"""
    print("\n" + "="*60)
    print("🎉 배포 프로세스 완료!")
    print("="*60)
    
    # 생성된 파일들 확인
    dist_path = Path('dist')
    if dist_path.exists():
        print(f"\n📁 생성된 파일들:")
        for item in dist_path.iterdir():
            if item.is_file():
                size = item.stat().st_size / (1024*1024)
                print(f"  - {item.name} ({size:.1f} MB)")
            elif item.is_dir():
                print(f"  - {item.name}/ (디렉토리)")
    
    # 배포 패키지 확인
    packages = list(Path('.').glob('AI_Image_Selector_*.zip')) + list(Path('.').glob('AI_Image_Selector_*.tar.gz'))
    if packages:
        print(f"\n📦 배포 패키지:")
        for package in packages:
            size = package.stat().st_size / (1024*1024)
            print(f"  - {package.name} ({size:.1f} MB)")
    
    print(f"\n📋 다음 단계:")
    print(f"1. 빌드된 실행파일을 다른 컴퓨터에서 테스트")
    print(f"2. 배포 패키지를 사용자들에게 전달")
    print(f"3. 필요시 코드 서명 및 인증서 적용")
    print(f"4. 사용자 피드백 수집 및 개선사항 반영")

def main():
    """메인 함수"""
    args = parse_arguments()
    
    print("🚀 PySide6 GUI 애플리케이션 전체 배포 프로세스 시작")
    print("="*60)
    
    # 1. 사전 요구사항 확인
    if not check_prerequisites():
        sys.exit(1)
    
    # 2. 의존성 설치 (선택적)
    if not args.skip_deps:
        if not install_dependencies():
            print("⚠️ 의존성 설치에 실패했지만 계속 진행합니다.")
    
    # 3. 애플리케이션 빌드
    if not build_application(args):
        print("❌ 빌드에 실패했습니다.")
        sys.exit(1)
    
    # 4. 패키징
    if not package_application(args):
        print("❌ 패키징에 실패했습니다.")
        sys.exit(1)
    
    # 5. 완료 요약
    show_summary()

if __name__ == '__main__':
    main() 