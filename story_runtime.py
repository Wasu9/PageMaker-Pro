"""Runtime bridge for PageMaker Pro stories and text frames.

Tk widgets remain the editing view, while this module owns canonical story text
and frame sequence used for DTP flow decisions.
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

    def set_text(self, story, text):
        story.text = text or ""

    def ordered_frame_ids(self, story):
        return list(story.frame_ids)

    def distribute(self, story, capacities, mode="next_column"):
        return self.engine.distribute(self.document, story, capacities, mode=mode)

    def sync_frames_from_result(self, story, result):
        for item in result:
            if item.frame_id in self.document.frames:
                self.document.frames[item.frame_id].text = item.text
        return result
