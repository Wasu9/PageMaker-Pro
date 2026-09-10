"""Runtime bridge for PageMaker Pro stories and text frames.

The Tk widgets remain views/editors, while this module owns the canonical
story text and frame sequence used for DTP flow decisions.
"""
from flow_engine import FlowEngine


class StoryRuntime:
    def __init__(self, document):
        self.document = document
        self.engine = FlowEngine(document)
        self.active_story_id = None

    def ensure_story(self, text=""):
        if self.active_story_id in self.document.stories:
            return self.document.stories[self.active_story_id]
        story = self.document.add_story(text)
        self.active_story_id = story.id
        return story

    def set_text(self, story, text):
        story.text = text or ""
        for fid in story.frame_ids:
            if fid in self.document.frames:
                self.document.frames[fid].text = ""

    def ordered_frame_ids(self, story):
        return list(story.frame_ids)

    def distribute(self, story, capacities, mode="next_column"):
        """Calculate frame allocation without touching Tk widgets."""
        return self.engine.distribute(story, capacities, mode=mode)

    def sync_frames_from_result(self, story, result):
        for fid, text in zip(story.frame_ids, result.frames):
            if fid in self.document.frames:
                self.document.frames[fid].text = text
        return result.overflow
