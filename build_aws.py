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
    
    # PyInstaller 실행
    cmd = [sys.executable, '-m', 'PyInstaller', 'aws_app.spec']
    
    try:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("Build successful!")
        
        # 결과 확인
        dist_path = Path('dist')
        if dist_path.exists():
            if sys.platform == 'darwin':
                app_path = dist_path / 'AWS Data Curator.app'
                if app_path.exists():
                    print(f"macOS app created: {app_path}")
            elif sys.platform.startswith('win'):
                exe_path = dist_path / 'AWS_Data_Curator.exe'
                if exe_path.exists():
                    print(f"Windows executable created: {exe_path}")
            else:
                exe_path = dist_path / 'AWS_Data_Curator'
                if exe_path.exists():
                    print(f"Linux executable created: {exe_path}")
        
    except subprocess.CalledProcessError as e:
        print("Build failed!")
        print(f"Error: {e.stderr}")
        sys.exit(1)

if __name__ == '__main__':
    build_app()