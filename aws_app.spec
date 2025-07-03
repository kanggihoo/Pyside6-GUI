#!/usr/bin/env python3
"""
AWS 데이터셋 큐레이션 앱 빌드 스크립트
"""

import subprocess
import sys
import shutil
import os
from pathlib import Path

def clean_build():
    """이전 빌드 파일 정리"""
    for dir_name in ['build', 'dist', '__pycache__']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    print("Cleaned previous build files")

def check_dependencies():
    """필요한 의존성 확인"""
    required_packages = ['PyInstaller', 'PySide6', 'boto3', 'requests', 'PIL']
    for package in required_packages:
        try:
            __import__(package)
            print(f"OK: {package} found")
        except ImportError:
            print(f"ERROR: {package} not installed")
            sys.exit(1)

def build_app():
    """앱 빌드"""
    print("Starting AWS app build...")
    
    # 의존성 확인
    check_dependencies()
    
    # 클린 빌드
    clean_build()
    
    # 파일 존재 확인
    spec_file = Path('aws_app.spec')
    if not spec_file.exists():
        print(f"ERROR: {spec_file} not found")
        sys.exit(1)
    
    main_file = Path('aws/gui_main.py')
    if not main_file.exists():
        print(f"ERROR: {main_file} not found")
        sys.exit(1)
    
    print(f"Found spec file: {spec_file}")
    print(f"Found main file: {main_file}")
    
    # PyInstaller 실행
    cmd = [sys.executable, '-m', 'PyInstaller', 'aws_app.spec']
    
    try:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build successful!")
        print("Build output:")
        print(result.stdout)
        
        # 결과 확인
        dist_path = Path('dist')
        if dist_path.exists():
            print(f"dist directory contents:")
            for item in dist_path.iterdir():
                print(f"  {item.name}")
            
            if sys.platform == 'darwin':
                app_path = dist_path / 'AWS Data Curator.app'
                if app_path.exists():
                    print(f"macOS app created: {app_path}")
                else:
                    print("ERROR: macOS app not found")
            elif sys.platform.startswith('win'):
                exe_path = dist_path / 'AWS_Data_Curator.exe'
                if exe_path.exists():
                    print(f"Windows executable created: {exe_path}")
                else:
                    print("ERROR: Windows executable not found")
                    # dist 폴더 내용 더 자세히 확인
                    for item in dist_path.iterdir():
                        if item.is_dir():
                            print(f"  Directory: {item.name}")
                            for subitem in item.iterdir():
                                print(f"    {subitem.name}")
            else:
                exe_path = dist_path / 'AWS_Data_Curator'
                if exe_path.exists():
                    print(f"Linux executable created: {exe_path}")
                else:
                    print("ERROR: Linux executable not found")
        else:
            print("ERROR: dist directory not created")
        
    except subprocess.CalledProcessError as e:
        print("Build failed!")
        print(f"Error code: {e.returncode}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)

if __name__ == '__main__':
    build_app()