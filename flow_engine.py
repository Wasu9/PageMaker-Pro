"""PageMaker-style threaded story flow engine.

A Story owns the complete text. TextFrames are ordered containers. The engine
supports the three PageMaker Pro flow policies without depending on Tkinter.
"""
from dataclasses import dataclass
from typing import List


@dataclass
class FlowResult:
    frame_id: str
    text: str


class FlowEngine:
    MODES = ("next_column", "same_column", "ask")

    def ordered_frames(self, document, mode="next_column"):
        """Return document frames in the selected threading order.

        next_column: page 1 C1 -> C2 -> page 2 C1 -> C2
        same_column: page 1 C1 -> page 2 C1 -> ... -> C2 -> page 2 C2
        ask: defaults to page/column order; the UI may stop at overflow.
        """
        pages = list(document.pages)
        if mode == "same_column":
            frames = []
            max_cols = max((len(p.frame_ids) for p in pages), default=0)
            for ci in range(max_cols):
                for page in pages:
                    page_frames = [f for f in document.frame_order(page)
                                   if f.column == ci]
                    frames.extend(page_frames)
            return frames
        frames = []
        for page in pages:
            frames.extend(document.frame_order(page))
        return frames

    def ordered_frame_ids(self, document, mode="next_column"):
        return [f.id for f in self.ordered_frames(document, mode)]

    def split_to_capacity(self, text, capacity):
        if capacity <= 0 or len(text) <= capacity:
            return text, ""
        cut = text.rfind("\n", 0, capacity + 1)
        if cut < max(1, capacity // 2):
            cut = text.rfind(" ", 0, capacity + 1)
        if cut < 1:
            cut = capacity
        return text[:cut], text[cut:].lstrip(" \n")

    def distribute(self, document, story, capacities, mode="next_column",
                   frame_ids=None):
        """Flow the canonical story through an explicit frame sequence."""
        if mode not in self.MODES:
            mode = "next_column"
        ids = list(frame_ids) if frame_ids is not None else self.ordered_frame_ids(document, mode)
        # Keep the Story's threading sequence canonical and serializable.
        story.frame_ids = [fid for fid in ids if fid in document.frames]
        remaining = story.text
        result: List[FlowResult] = []
        for fid, cap in zip(story.frame_ids, capacities):
            part, remaining = self.split_to_capacity(remaining, int(cap))
            document.frames[fid].text = part
            result.append(FlowResult(fid, part))
            if not remaining:
                break
        return result, remaining
