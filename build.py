#!/usr/bin/env python3
"""
PySide6 GUI 애플리케이션 빌드 스크립트

사용법:
    python build.py                    # 기본 빌드
    python build.py --clean            # 클린 빌드 (이전 빌드 파일 삭제 후 빌드)
    python build.py --onefile          # 단일 실행파일로 빌드 (느리지만 배포 용이)
    python build.py --debug            # 디버그 모드로 빌드
"""

import subprocess
import sys
import shutil
import os
import argparse
from pathlib import Path

def parse_arguments():
    """명령줄 인수 파싱"""
    parser = argparse.ArgumentParser(description='PySide6 GUI 애플리케이션 빌드 도구')
    parser.add_argument('--clean', action='store_true', 
                       help='이전 빌드 파일을 삭제하고 클린 빌드 수행')
    parser.add_argument('--onefile', action='store_true',
                       help='단일 실행파일로 빌드 (배포 용이하지만 느림)')
    parser.add_argument('--debug', action='store_true',
                       help='디버그 모드로 빌드')
    parser.add_argument('--console', action='store_true',
                       help='콘솔 창과 함께 빌드 (디버깅용)')
    return parser.parse_args()

def clean_build_dirs():
    """이전 빌드 디렉토리 정리"""
    build_dirs = ['build', 'dist', '__pycache__']
    for dir_name in build_dirs:
        if os.path.exists(dir_name):
            print(f"🧹 이전 빌드 디렉토리 정리: {dir_name}")
            shutil.rmtree(dir_name)
    
    # .pyc 파일들도 정리
    for pyc_file in Path('.').rglob('*.pyc'):
        pyc_file.unlink()

def check_dependencies():
    """필요한 의존성 확인"""
    try:
        import PyInstaller
        print(f"✅ PyInstaller 버전: {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller가 설치되지 않았습니다.")
        print("설치 명령: uv add pyinstaller")
        sys.exit(1)
    
    try:
        import PySide6
        print(f"✅ PySide6 버전: {PySide6.__version__}")
    except ImportError:
        print("❌ PySide6가 설치되지 않았습니다.")
        sys.exit(1)

def build_application(args):
    """애플리케이션 빌드"""
    
    print("🚀 PySide6 GUI 애플리케이션 빌드 시작...")
    
    # 의존성 확인
    check_dependencies()
    
    # 클린 빌드인 경우 이전 파일들 정리
    if args.clean:
        clean_build_dirs()
    
    # PyInstaller 명령 구성
    cmd = [sys.executable, '-m', 'PyInstaller']
    
    if args.onefile:
        # 단일 파일 모드
        cmd.extend([
            '--onefile',
            '--windowed' if not args.console else '',
            '--name', 'AI_Image_Selector',
            'main.py'
        ])
        if not args.console:
            cmd.remove('')  # 빈 문자열 제거
    else:
        # 스펙 파일 사용
        cmd.extend(['app.spec'])
    
    if args.clean:
        cmd.append('--clean')
    
    if args.debug:
        cmd.extend(['--debug', 'all'])
    
    # 빌드 실행
    try:
        print(f"📦 실행 중: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print("✅ 빌드 성공!")
        
        if args.debug:
            print("\n빌드 출력:")
            print(result.stdout)
        
        # 결과 확인 및 정보 출력
        show_build_results(args.onefile)
        
    except subprocess.CalledProcessError as e:
        print("❌ 빌드 실패!")
        print(f"오류 코드: {e.returncode}")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        sys.exit(1)

def show_build_results(onefile_mode=False):
    """빌드 결과 정보 표시"""
    
    dist_path = Path('dist')
    if not dist_path.exists():
        print("❌ dist 폴더가 생성되지 않았습니다.")
        return
    
    if sys.platform == 'darwin': # macOS 환경 
        if onefile_mode:
            exe_path = dist_path / 'AI_Image_Selector'
            if exe_path.exists():
                print(f"\n🎉 macOS 실행파일이 생성되었습니다: {exe_path}")
                print("사용법: 터미널에서 실행하거나 Finder에서 더블클릭")
        else:
            app_path = dist_path / 'AI Image Selector.app'
            if app_path.exists():
                print(f"\n🎉 macOS 앱 번들이 생성되었습니다: {app_path}")
                print("사용법: 더블클릭하여 실행하거나 Applications 폴더로 이동")
    elif sys.platform.startswith('win'): # Windows 환경
        exe_path = dist_path / 'AI_Image_Selector.exe'
        if exe_path.exists():
            print(f"\n🎉 Windows 실행파일이 생성되었습니다: {exe_path}")
            print("사용법: 더블클릭하여 실행")
    else:  # Linux 환경
        exe_path = dist_path / 'AI_Image_Selector'
        if exe_path.exists():
            print(f"\n🎉 Linux 실행파일이 생성되었습니다: {exe_path}")
            print("사용법: ./AI_Image_Selector 또는 더블클릭")
    
    # 크기 정보
    if dist_path.exists():
        total_size = sum(f.stat().st_size for f in dist_path.rglob('*') if f.is_file())
        print(f"📏 전체 크기: {total_size / (1024*1024):.1f} MB")
    
    # 사용 안내
    print("\n📋 다음 단계:")
    print("1. 빌드된 애플리케이션을 다른 컴퓨터에서 테스트")
    print("2. 필요시 python package.py 실행하여 배포 패키지 생성")
    print("3. 상용 배포시 코드 서명 고려")

def main():
    """메인 함수"""
    args = parse_arguments()
    
    # app.spec 파일 존재 확인 (onefile 모드가 아닌 경우)
    if not args.onefile and not Path('app.spec').exists():
        print("❌ app.spec 파일이 없습니다.")
        print("app.spec 파일을 먼저 생성하거나 --onefile 옵션을 사용하세요.")
        sys.exit(1)
    
    # main.py 파일 존재 확인
    if not Path('main.py').exists():
        print("❌ main.py 파일이 없습니다.")
        sys.exit(1)
    
    build_application(args)

if __name__ == '__main__':
    main() 