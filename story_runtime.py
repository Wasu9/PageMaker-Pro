"""Canonical Story/TextFrame runtime for PageMaker Pro.

Phase 3 makes the Story the live editing source of truth. UI adapters can push
an edit into the Story, reflow it through the current thread, and render the
result back to frame widgets without rebuilding the document.
"""
import sys
from flow_engine import FlowEngine


class StoryRuntime:
    def __init__(self, document):
        self.document = document
        self.engine = FlowEngine()
        self.active_story_id = None
        self.last_remaining = ""
        self.last_result = []

    def ensure_story(self, text=""):
        story = self.story()
        if story is not None:
            return story
        story = self.document.add_story(text)
        self.active_story_id = story.id
        return story

    def story(self):
        return self.document.stories.get(self.active_story_id)

    def set_text(self, story, text):
        story.text = text or ""

    def edit_story(self, text, story=None):
        """Update the canonical story without touching any UI widget."""
        story = story or self.ensure_story()
        story.text = text or ""
        return story

    def attach_frames(self, story, mode="next_column", frame_ids=None):
        """Attach an explicit persistent thread when supplied."""
        ids = list(frame_ids) if frame_ids is not None else self.engine.ordered_frame_ids(self.document, mode)
        ids = [fid for fid in ids if fid in self.document.frames]
        story.frame_ids = ids
        for fid, frame in self.document.frames.items():
            frame.story_id = story.id if fid in ids else None
        return list(ids)

    def thread_frames(self, story, frame_ids):
        return self.attach_frames(story, frame_ids=list(frame_ids))

    def unthread_after(self, story, frame_id):
        if frame_id not in story.frame_ids:
            return list(story.frame_ids)
        index = story.frame_ids.index(frame_id) + 1
        story.frame_ids = story.frame_ids[:index]
        for fid, frame in self.document.frames.items():
            frame.story_id = story.id if fid in story.frame_ids else None
        return list(story.frame_ids)

    @staticmethod
    def capacity_for_frame(frame, chars_per_line=95, line_height=17):
        lines = max(1, int(frame.rect.height / max(1, line_height)))
        chars = max(8, int(frame.rect.width / 7.2))
        return max(80, lines * min(chars, chars_per_line))

    def capacities(self, story):
        return [self.capacity_for_frame(self.document.frames[fid])
                for fid in story.frame_ids if fid in self.document.frames]

    def reflow(self, story=None, capacities=None, mode="next_column", frame_ids=None):
        """Reflow using the Phase 12 geometry-aware Unicode line layout engine."""
        story = story or self.ensure_story()
        ids = list(frame_ids) if frame_ids is not None else list(story.frame_ids)
        if not ids:
            ids = self.engine.ordered_frame_ids(self.document, mode)
        self.attach_frames(story, mode, frame_ids=ids)

        try:
            from dtp_text_layout import DTPTextLayout
            frames = []
            for fid in story.frame_ids:
                frame = self.document.frames.get(fid)
                if frame is not None:
                    frames.append({"id": fid, "width": frame.rect.width,
                                   "height": frame.rect.height,
                                   "line_height": max(12.0, min(24.0, frame.rect.height / 42.0))})
            engine = DTPTextLayout(font_size=12.0)
            placements, remaining = engine.paginate(story.text, frames)
            for fid in story.frame_ids:
                if fid in self.document.frames:
                    self.document.frames[fid].text = ""
            result = []
            for info, start, end, lines in placements:
                value = story.text[start:end]
                self.document.frames[info["id"]].text = value
                result.append(type("FlowResult", (), {"frame_id": info["id"], "text": value})())
            self.last_result = result
            self.last_remaining = remaining or ""
            return result, self.last_remaining
        except Exception:
            # Safe fallback keeps the editor usable if the optional layout
            # module is unavailable or an exotic font/runtime fails.
            if capacities is None:
                capacities = self.capacities(story)
            result, remaining = self.engine.distribute(
                self.document, story, capacities, mode=mode, frame_ids=story.frame_ids)
            self.last_result = result
            self.last_remaining = remaining or ""
            return result, self.last_remaining

    def distribute(self, story, capacities=None, mode="next_column", frame_ids=None):
        return self.reflow(story, capacities, mode, frame_ids)

    def live_edit(self, text, mode="next_column", frame_ids=None, capacities=None):
        """Commit an edit to Story, then immediately calculate its new flow."""
        story = self.edit_story(text)
        result, remaining = self.reflow(
            story, capacities=capacities, mode=mode, frame_ids=frame_ids)
        return story, result, remaining

    def move_frame(self, frame_id, x, y):
        return self.document.move_frame(frame_id, x, y)

    def resize_frame(self, frame_id, width, height):
        return self.document.resize_frame(frame_id, width, height)


def _install_live_editor_patch(app):
    """Debounced UI adapter: every edit becomes a Story edit and reflow."""
    if getattr(app, '_pm_phase3_live_patch', False):
        return
    app._pm_phase3_live_patch = True
    original_changed = app.changed

    def changed(widget=None):
        original_changed(widget)
        if getattr(app, '_pm_rendering', False) or getattr(app, '_pm_canonical_busy', False):
            return
        try:
            pending = getattr(app, '_pm_live_reflow_after', None)
            if pending:
                app.root.after_cancel(pending)
            app._pm_live_reflow_after = app.root.after(180, _run)
        except Exception:
            pass

    def _run():
        app._pm_live_reflow_after = None
        if getattr(app, '_pm_rendering', False) or getattr(app, '_pm_canonical_busy', False):
            return
        try:
            from sitecustomize import _reflow_story
            _reflow_story(app)
        except Exception:
            pass

    app.changed = changed


_profile_installed = False


def _phase3_profile(frame, event, arg):
    if event == 'return' and frame.f_code.co_name == '__init__':
        app = frame.f_locals.get('self')
        if app is not None and app.__class__.__name__ == 'App':
            try:
                _install_live_editor_patch(app)
            except Exception:
                pass
    return _phase3_profile


if not _profile_installed:
    try:
        sys.setprofile(_phase3_profile)
        _profile_installed = True
    except Exception:
        pass
