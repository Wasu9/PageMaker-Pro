"""PageMaker-style threaded text flow.

A story owns text; frames are merely containers. Flow order is explicit:
column 1 -> column 2 -> next page column 1, unless the selected mode says
same-column-next-page. This module is independent of the UI.
"""
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class FlowResult:
    frame_id: str
    text: str


class FlowEngine:
    MODES = ("next_column", "same_column", "ask")

    def ordered_frames(self, document, page_index=0):
        frames = []
        for page in document.pages[page_index:]:
            frames.extend(document.frame_order(page))
        return frames

    def split_to_capacity(self, text, capacity):
        if capacity <= 0 or len(text) <= capacity:
            return text, ""
        cut = text.rfind("\n", 0, capacity + 1)
        if cut < max(1, capacity // 2):
            cut = text.rfind(" ", 0, capacity + 1)
        if cut < 1:
            cut = capacity
        return text[:cut], text[cut:].lstrip(" \n")

    def distribute(self, document, story, capacities, mode="next_column"):
        """Distribute a story through its existing frame order.

        capacities is a list of character capacities matching story.frame_ids.
        The method never silently changes story text; it returns overflow when
        there are insufficient frames. The renderer can then create a new page.
        """
        if mode not in self.MODES:
            mode = "next_column"
        remaining = story.text
        result: List[FlowResult] = []
        for fid, cap in zip(story.frame_ids, capacities):
            part, remaining = self.split_to_capacity(remaining, int(cap))
            document.frames[fid].text = part
            result.append(FlowResult(fid, part))
            if not remaining:
                break
        return result, remaining
