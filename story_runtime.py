"""Canonical Story/TextFrame runtime for PageMaker Pro.

The Tk Text widgets are the editing surface, but one Story owns the complete
text. TextFrames are ordered containers; this runtime keeps the two views in
sync without making Tk's widgets the DTP data model.
"""
from flow_engine import FlowEngine


class StoryRuntime:
    def __init__(self, document):
        self.document = document
        self.engine = FlowEngine()
        self.active_story_id = None

    def ensure_story(self, text=""):
        if self.active_story_id in self.document.stories:
            return self.document.stories[self.active_story_id]
        story = self.document.add_story(text)
        self.active_story_id = story.id
        return story

    def story(self):
        return self.document.stories.get(self.active_story_id)

    def set_text(self, story, text):
        story.text = text or ""

    def attach_frames(self, story, mode="next_column"):
        """Attach every document text frame to the one canonical story."""
        ids = self.engine.ordered_frame_ids(self.document, mode)
        story.frame_ids = ids
        for fid, frame in self.document.frames.items():
            frame.story_id = story.id if fid in ids else None
        return list(ids)

    def ordered_frame_ids(self, story):
        return list(story.frame_ids)

    @staticmethod
    def capacity_for_frame(frame, chars_per_line=95, line_height=17):
        """Conservative geometry-based capacity until real text layout exists."""
        lines = max(1, int(frame.rect.height / line_height))
        chars = max(8, int(frame.rect.width / 7.2))
        return max(80, lines * min(chars, chars_per_line))

    def capacities(self, story):
        return [self.capacity_for_frame(self.document.frames[fid])
                for fid in story.frame_ids if fid in self.document.frames]

    def clear_frame_text(self, story):
        for fid in story.frame_ids:
            if fid in self.document.frames:
                self.document.frames[fid].text = ""

    def distribute(self, story, capacities=None, mode="next_column"):
        self.attach_frames(story, mode)
        self.clear_frame_text(story)
        if capacities is None:
            capacities = self.capacities(story)
        return self.engine.distribute(self.document, story, capacities,
                                      mode=mode, frame_ids=story.frame_ids)

    def sync_frames_from_result(self, story, result):
        for item in result:
            if item.frame_id in self.document.frames:
                self.document.frames[item.frame_id].text = item.text
        return result
