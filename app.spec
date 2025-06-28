# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

block_cipher = None

# 프로젝트 루트 경로
import os
project_root = Path(os.getcwd())

# 추가할 데이터 파일들 (필요한 리소스가 있다면)
added_files = []

# PySide6와 관련된 hidden imports
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
    'widgets.project_tree',
    'widgets.workspace_panel',
    'widgets.representative_panel',
    'widgets.image_label',
    'widgets.keyboard_navigation',
    'widgets.image_grid',
    'widgets.image_viewer',
]

a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
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
        'PIL.ImageTk',
        'IPython',
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
    name='AI_Image_Selector',  # 실행파일 이름
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
    name='AI_Image_Selector',
)

# macOS용 앱 번들 생성 (macOS에서만)
if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='AI Image Selector.app',
        icon=None,  # .icns 아이콘 파일이 있다면 경로 지정
        bundle_identifier='com.yourcompany.aiimageselector',
        info_plist={
            'CFBundleDisplayName': 'AI 학습용 이미지 선정 도구',
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': True,
            'NSHumanReadableCopyright': 'Copyright © 2024',
            'NSRequiresAquaSystemAppearance': False,
        },
    ) 