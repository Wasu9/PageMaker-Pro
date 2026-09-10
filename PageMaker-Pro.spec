# -*- mode: python ; coding: utf-8 -*-
import glob
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

# Tkinter's Python package is not the same thing as Tcl/Tk's script libraries.
# _tkinter can be present while Tcl's init.tcl is missing, which makes a frozen
# GUI fail at startup. Collect both pieces explicitly.
tk_datas, tk_binaries, tk_hiddenimports = collect_all('tkinter')
tk_hiddenimports += collect_submodules('tkinter')
tk_hiddenimports += ['_tkinter']

# Locate the Tcl/Tk script libraries from the exact Python installation used by
# the Windows GitHub Actions runner. Versions are discovered dynamically so the
# spec does not depend on a hard-coded Tcl/Tk minor version.
tcl_root = os.path.join(sys.base_prefix, 'tcl')
tcl_dirs = sorted(glob.glob(os.path.join(tcl_root, 'tcl*')))
tk_dirs = sorted(glob.glob(os.path.join(tcl_root, 'tk*')))

# Keep only actual Tcl/Tk library directories (not unrelated files).
tcl_dir = next((p for p in tcl_dirs if os.path.isdir(p) and os.path.isfile(os.path.join(p, 'init.tcl'))), None)
tk_dir = next((p for p in tk_dirs if os.path.isdir(p) and os.path.isfile(os.path.join(p, 'tk.tcl'))), None)

if not tcl_dir or not tk_dir:
    raise RuntimeError(
        f'Tcl/Tk runtime not found under {tcl_root!r}: '
        f'tcl={tcl_dirs!r}, tk={tk_dirs!r}'
    )

# Preserve the directory names expected by Tk at runtime.
tcl_name = os.path.basename(tcl_dir)
tk_name = os.path.basename(tk_dir)
tk_datas += [
    (tcl_dir, os.path.join('tcl', tcl_name)),
    (tk_dir, os.path.join('tcl', tk_name)),
]

hiddenimports = [
    'tkinter', '_tkinter',
    'tkinter.ttk', 'tkinter.filedialog', 'tkinter.messagebox',
    'tkinter.simpledialog', 'tkinter.colorchooser',
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
] + tk_hiddenimports

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=tk_binaries,
    datas=tk_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='PageMaker-Pro', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False,
)
