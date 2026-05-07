# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:\\antigravity\\#1_2_PDF_CSV\\_server_main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\antigravity\\#1_2_PDF_CSV\\web', 'web'), ('C:\\antigravity\\#1_2_PDF_CSV\\config', 'config'), ('C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages\\pyproj\\proj_dir\\share\\proj', 'proj_data'), ('C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages\\opendataloader_pdf\\jar', 'opendataloader_pdf/jar')],
    hiddenimports=['flask', 'flask.json.provider', 'werkzeug', 'werkzeug.serving', 'jinja2', 'jinja2.ext', 'pandas', 'pandas._libs.tslibs.base', 'pyproj', 'pyproj.transformer', 'fitz', 'pyhwpx', 'opendataloader_pdf', 'core', 'core.master_hybrid_extractor', 'core.table_merger', 'core.coordinate_transformer', 'core.spatial_validator', 'core.sentinel_daemon', 'parsers', 'parsers.pdf_parser_odl', 'parsers.hwp_indexed_extractor', 'parsers.hwpx_converter'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'test'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GeoBIM_Borehole',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GeoBIM_Borehole',
)
