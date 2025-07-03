#!/usr/bin/env python3
"""
AWS 앱 패키징 스크립트
"""

import zipfile
import sys
import os
from pathlib import Path
from datetime import datetime

def create_zip_package():
    """ZIP 패키지 생성"""
    dist_path = Path('dist')
    
    if not dist_path.exists():
        print("ERROR: dist folder not found. Run build first.")
        sys.exit(1)
    
    print(f"dist directory contents:")
    for item in dist_path.iterdir():
        print(f"  {item.name} ({'dir' if item.is_dir() else 'file'})")
    
    # 플랫폼별 실행파일 찾기
    if sys.platform == 'darwin':
        app_path = dist_path / 'AWS Data Curator.app'
        if not app_path.exists():
            print("ERROR: macOS app not found.")
            sys.exit(1)
        executable_path = app_path
        platform_name = 'macos'
        is_app_bundle = True
    elif sys.platform.startswith('win'):
        # Windows: 실행파일과 라이브러리 폴더 모두 확인
        exe_path = dist_path / 'AWS_Data_Curator.exe'
        lib_dir = dist_path / 'AWS_Data_Curator'
        
        if not exe_path.exists():
            print(f"ERROR: Windows executable not found at {exe_path}")
            print("Available files in dist:")
            for item in dist_path.iterdir():
                print(f"  {item.name}")
            sys.exit(1)
        
        executable_path = exe_path
        platform_name = 'windows'
        is_app_bundle = False
        print(f"Found Windows executable: {exe_path}")
        if lib_dir.exists():
            print(f"Found library directory: {lib_dir}")
    else:
        exe_path = dist_path / 'AWS_Data_Curator'
        if not exe_path.exists():
            print("ERROR: Linux executable not found.")
            sys.exit(1)
        executable_path = exe_path
        platform_name = 'linux'
        is_app_bundle = False
    
    # ZIP 파일명 생성
    version = "1.0.0"
    zip_filename = f"AWS_Data_Curator_{platform_name}_v{version}.zip"
    
    print(f"Creating ZIP package: {zip_filename}")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        if is_app_bundle:
            # macOS 앱 번들의 모든 파일 추가
            for file_path in executable_path.rglob('*'):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(dist_path))
                    zipf.write(file_path, arcname)
        else:
            # Windows/Linux: 실행파일과 라이브러리들 추가
            for item in dist_path.iterdir():
                if item.is_file():
                    # 실행파일 직접 추가
                    zipf.write(item, item.name)
                    print(f"Added file: {item.name}")
                elif item.is_dir():
                    # 라이브러리 디렉토리의 모든 파일 추가
                    for file_path in item.rglob('*'):
                        if file_path.is_file():
                            arcname = str(file_path.relative_to(dist_path))
                            zipf.write(file_path, arcname)
                            print(f"Added library file: {arcname}")
        
        # README 추가
        readme_content = f"""# AWS Data Curator

## Usage

### {platform_name.title()}
1. Extract the ZIP file
2. Double-click the executable to run

## System Requirements
- AWS account and credentials required
- Stable internet connection required

## Support
Contact the development team if you encounter any issues.

Build date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        zipf.writestr('README.txt', readme_content)
        print("Added README.txt")
    
    print(f"Package created successfully: {zip_filename}")
    
    # 생성된 ZIP 파일 정보
    zip_size = os.path.getsize(zip_filename)
    print(f"ZIP file size: {zip_size / (1024*1024):.1f} MB")
    
    return zip_filename

if __name__ == '__main__':
    create_zip_package()