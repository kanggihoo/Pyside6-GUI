# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

block_cipher = None

# 프로젝트 루트 경로
project_root = Path(os.getcwd())

# AWS 앱 전용 데이터 파일들
added_files = [
    ('aws/config.json', 'aws'),
]

# PySide6와 AWS 관련 hidden imports
hidden_imports = [
    'PySide6.QtCore',
    'PySide6.QtGui', 
    'PySide6.QtWidgets',
    'boto3',
    'botocore',
    'urllib3',
    'certifi',
    'dateutil',
    'json',
    'requests',
    'PIL',
    'PIL.Image',
    'aws_manager',
    'image_cache',
    'widgets.main_image_viewer',
    'widgets.representative_panel',
    'widgets.product_list_widget',
    'widgets.category_selection_dialog',
    'widgets.curation_confirm_dialog',
    'widgets.pass_reason_dialog',
    'widgets.image_viewer_dialog',
    'widgets.image_widgets',
]

a = Analysis(
    ['aws/gui_main.py'],
    pathex=[str(project_root), str(project_root / 'aws')],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Windows용 실행파일 생성 - onedir 모드
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # 이 설정이 onedir 모드를 만듦
    name='AWS_Data_Curator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

# 라이브러리 수집
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AWS_Data_Curator',
)

# macOS용 앱 번들 생성
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='AWS Data Curator.app',
        icon=None,
        bundle_identifier='com.yourcompany.awsdatacurator',
        info_plist={
            'CFBundleDisplayName': 'AWS 데이터셋 큐레이션 도구',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': True,
            'NSHumanReadableCopyright': 'Copyright © 2024',
            'NSRequiresAquaSystemAppearance': False,
        },
    )