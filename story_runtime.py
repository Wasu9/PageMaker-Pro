"""Canonical Story/TextFrame runtime for PageMaker Pro."""
from flow_engine import FlowEngine


class StoryRuntime:
    def __init__(self, document):
        self.document = document
        self.engine = FlowEngine()
        self.active_story_id = None

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

    def attach_frames(self, story, mode="next_column", frame_ids=None):
        """Thread all text frames into one Story in deterministic order."""
        ids = list(frame_ids) if frame_ids is not None else self.engine.ordered_frame_ids(self.document, mode)
        ids = [fid for fid in ids if fid in self.document.frames]
        story.frame_ids = ids
        for fid, frame in self.document.frames.items():
            frame.story_id = story.id if fid in ids else None
        return list(ids)

    @staticmethod
    def capacity_for_frame(frame, chars_per_line=95, line_height=17):
        lines = max(1, int(frame.rect.height / max(1, line_height)))
        chars = max(8, int(frame.rect.width / 7.2))
        return max(80, lines * min(chars, chars_per_line))

    def capacities(self, story):
        return [self.capacity_for_frame(self.document.frames[fid])
                for fid in story.frame_ids if fid in self.document.frames]

    def distribute(self, story, capacities=None, mode="next_column"):
        self.attach_frames(story, mode)
        if capacities is None:
            capacities = self.capacities(story)
        return self.engine.distribute(self.document, story, capacities,
                                      mode=mode, frame_ids=story.frame_ids)

    def move_frame(self, frame_id, x, y):
        return self.document.move_frame(frame_id, x, y)

    def resize_frame(self, frame_id, width, height):
        return self.document.resize_frame(frame_id, width, height)
