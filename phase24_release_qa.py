"""Phase 24: release/QA guardrails for PageMaker Pro.

Keeps release checks deterministic and offline. The module validates the
canonical document model, checks required project modules, and exposes a
small diagnostics API used by the final UI/build pipeline.
"""
import importlib
import os
import sys

REQUIRED_MODULES = (
    "pagemaker_core", "flow_engine", "story_runtime", "pagemaker_workspace",
    "phase20_text_frame_tools", "phase21_text_engine", "phase22_objects_tables",
    "phase23_document_system",
)


def project_root():
    return os.path.dirname(os.path.abspath(__file__))


def check_modules():
    result = {}
    for name in REQUIRED_MODULES:
        try:
            importlib.import_module(name)
            result[name] = True
        except Exception as exc:
            result[name] = f"{type(exc).__name__}: {exc}"
    return result


def check_document(doc):
    errors=[]
    if doc is None:
        return ["document is None"]
    if getattr(doc, "page_width", 0) <= 0 or getattr(doc, "page_height", 0) <= 0:
        errors.append("invalid page size")
    frame_ids=set(getattr(doc,"frames",{}))
    for page in getattr(doc,"pages",[]):
        for fid in getattr(page,"frame_ids",[]):
            if fid not in frame_ids: errors.append(f"page {page.number}: missing frame {fid}")
    for fid,f in getattr(doc,"frames",{}).items():
        if f.thread_next and f.thread_next not in frame_ids: errors.append(f"frame {fid}: missing thread target")
        if f.thread_prev and f.thread_prev not in frame_ids: errors.append(f"frame {fid}: missing thread source")
    return errors


def run_checks(doc=None):
    modules=check_modules()
    errors=[f"{k}: {v}" for k,v in modules.items() if v is not True]
    errors.extend(check_document(doc))
    return {"ok": not errors, "python": sys.version.split()[0], "modules": modules, "errors": errors}


def install(app):
    app.pm24_run_checks=lambda: run_checks(getattr(app,"document",None))
    return app.pm24_run_checks
