# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [
    'sitecustomize', 'pagemaker_core', 'flow_engine', 'story_runtime',
    'pagemaker_workspace', 'equation_engine', 'dtp_text_layout',
    'phase4_visual', 'phase5_canvas', 'phase5_bootstrap', 'phase6_object_editing',
    'phase7_text_engine', 'phase8_images', 'phase9_tables', 'phase10_master_pages',
    'phase11_export', 'phase12_text_layout', 'phase13_native_renderer',
    'phase14_renderer', 'phase14_unicode_shaping', 'phase15_mixed_runs',
    'phase16_paragraph_engine', 'phase17_pagination_engine',
    'phase18_text_frames', 'phase19_threading_ui', 'phase20_text_frame_tools',
    'phase21_text_engine', 'phase22_objects_tables', 'phase23_document_system',
    'phase24_release_qa',
]

a = Analysis(
    ['app.py'], pathex=['.'], binaries=[], datas=[], hiddenimports=hiddenimports,
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='PageMaker-Pro', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, console=False,
)
