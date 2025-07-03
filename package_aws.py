#!/usr/bin/env python3
"""
AWS 앱 패키징 스크립트
"""

import zipfile
import sys
from pathlib import Path
from datetime import datetime

def create_zip_package():
    """ZIP 패키지 생성"""
    dist_path = Path('dist')
    
    if not dist_path.exists():
        print("❌ dist 폴더가 없습니다. 먼저 빌드를 실행하세요.")
        sys.exit(1)
    
    # 플랫폼별 실행파일 찾기
    if sys.platform == 'darwin':
        app_path = dist_path / 'AWS Data Curator.app'
        if not app_path.exists():
            print("❌ macOS 앱을 찾을 수 없습니다.")
            sys.exit(1)
        executable_path = app_path
        platform_name = 'macos'
    elif sys.platform.startswith('win'):
        exe_path = dist_path / 'AWS_Data_Curator.exe'
        if not exe_path.exists():
            print("❌ Windows 실행파일을 찾을 수 없습니다.")
            sys.exit(1)
        executable_path = exe_path
        platform_name = 'windows'
    else:
        exe_path = dist_path / 'AWS_Data_Curator'
        if not exe_path.exists():
            print("❌ Linux 실행파일을 찾을 수 없습니다.")
            sys.exit(1)
        executable_path = exe_path
        platform_name = 'linux'
    
    # ZIP 파일명 생성
    version = "1.0.0"
    zip_filename = f"AWS_Data_Curator_{platform_name}_v{version}.zip"
    
    print(f"�� ZIP 패키지 생성 중: {zip_filename}")
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        if sys.platform == 'darwin':
            # macOS 앱 번들의 모든 파일 추가
            for file_path in executable_path.rglob('*'):
                if file_path.is_file():
                    arcname = str(file_path.relative_to(dist_path))
                    zipf.write(file_path, arcname)
        else:
            # 실행파일과 라이브러리들 추가
            for item in dist_path.iterdir():
                if item.is_file():
                    zipf.write(item, item.name)
                elif item.is_dir() and item.name == executable_path.stem:
                    for file_path in item.rglob('*'):
                        if file_path.is_file():
                            arcname = str(file_path.relative_to(dist_path))
                            zipf.write(file_path, arcname)
        
        # README 추가
        readme_content = f"""# AWS 데이터셋 큐레이션 도구

## 사용법

### {platform_name.title()}
1. 압축을 해제하세요
2. 실행파일을 더블클릭하여 실행하세요

## 시스템 요구사항
- AWS 계정 및 자격 증명 설정 필요
- 안정적인 인터넷 연결 필요

## 지원
문제가 발생하면 개발팀에 문의하세요.

빌드 날짜: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        zipf.writestr('README.txt', readme_content)
    
    print(f"✅ 패키지 생성 완료: {zip_filename}")
    return zip_filename

if __name__ == '__main__':
    create_zip_package()