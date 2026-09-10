"""PageMaker Pro Phase 12 — activate the real DTP text layout core.

This replaces the old character-capacity approximation used by StoryRuntime
with geometry-based Unicode-aware line breaking.  The Story remains canonical;
Tk widgets remain an editing adapter until the native renderer phase.
"""
from dtp_text_layout import DTPTextLayout
import story_runtime


def _install_runtime_patch():
    cls = story_runtime.StoryRuntime
    if getattr(cls, "_pm12_layout_patch", False):
        return
    original = cls.reflow

    def reflow(self, story=None, capacities=None, mode="next_column", frame_ids=None):
        story = story or self.ensure_story()
        ids = list(frame_ids) if frame_ids is not None else list(story.frame_ids)
        if not ids:
            ids = self.engine.ordered_frame_ids(self.document, mode)
        self.attach_frames(story, mode, frame_ids=ids)
        frames = []
        for fid in story.frame_ids:
            frame = self.document.frames.get(fid)
            if frame is None:
                continue
            frames.append({
                "id": fid,
                "width": frame.rect.width,
                "height": frame.rect.height,
                "line_height": max(12.0, min(24.0, frame.rect.height / 42.0)),
            })
        engine = DTPTextLayout(font_size=12.0)
        result, remaining = engine.paginate(story.text, frames)
        # Clear every threaded frame first so stale overflow cannot survive an edit.
        for fid in story.frame_ids:
            if fid in self.document.frames:
                self.document.frames[fid].text = ""
        compact = []
        for frame_info, start, end, lines in result:
            fid = frame_info["id"]
            value = story.text[start:end]
            self.document.frames[fid].text = value
            compact.append(type("FlowResult", (), {"frame_id": fid, "text": value})())
        self.last_result = compact
        self.last_remaining = remaining or ""
        return compact, self.last_remaining

    cls.reflow = reflow
    cls._pm12_layout_patch = True
    cls.pm12_layout_engine = DTPTextLayout


_install_runtime_patch()


def install(app):
    """Expose layout diagnostics/API on the running app."""
    if getattr(app, "_pm12_installed", False):
        return
    app._pm12_installed = True
    app.pm12_layout_engine = DTPTextLayout
