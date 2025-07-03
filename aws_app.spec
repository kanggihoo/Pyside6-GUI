# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

block_cipher = None

# 프로젝트 루트 경로
project_root = Path(os.getcwd())

# AWS 앱 전용 데이터 파일들
added_files = [
    ('aws/config.json', 'aws'),  # AWS 설정 파일
]

# PySide6와 AWS 관련 hidden imports
hidden_imports = [
    'PySide6.QtCore',
    'PySide6.QtGui', 
    'PySide6.QtWidgets',
    # AWS 관련
    'boto3',
    'botocore',
    'botocore.vendored.requests',
    'urllib3',
    'certifi',
    'dateutil',
    'json',
    'requests',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'pathlib2',
    'python_json_logger',
    'typing_extensions',
    # AWS 앱 전용 모듈들
    'aws_manager',
    'image_cache',
    'initial_upload',
    'setup_aws_infrastructure',
    'run_setup',
    # AWS 앱 전용 위젯들
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
        'jupyter',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AWS_Data_Curator',  # 실행파일 이름
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI 앱이므로 콘솔 창 숨김 (Windows/Linux)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # 아이콘 파일(.ico/.icns)이 있다면 경로 지정
)

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

# macOS용 앱 번들 생성 (macOS에서만)
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='AWS Data Curator.app',
        icon=None,  # .icns 아이콘 파일이 있다면 경로 지정
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