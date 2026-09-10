"""PageMaker Pro Phase 17 — constraint-aware pagination.

This layer turns paragraph constraints into deterministic page/column breaks.
It is deliberately UI-independent so the same decisions can later drive the
Canvas renderer and PDF/DOCX exporters.
"""
from dataclasses import dataclass


@dataclass
class Block:
    start: int
    end: int
    lines: int
    line_height: float
    space_before: float = 0.0
    space_after: float = 0.0
    keep_with_next: bool = False
    widow_lines: int = 2
    orphan_lines: int = 2

    @property
    def height(self):
        return self.lines * self.line_height + self.space_before + self.space_after


@dataclass
class BreakDecision:
    start_line: int
    lines_on_page: int
    moved_lines: int
    reason: str = "fit"


class PaginationEngine:
    def __init__(self, min_widow=2, min_orphan=2):
        self.min_widow=max(1,int(min_widow))
        self.min_orphan=max(1,int(min_orphan))

    def _split_lines(self, block, available):
        cap=max(0,int((available-block.space_before-block.space_after)//max(1.0,block.line_height)))
        if block.lines <= cap:
            return BreakDecision(0,block.lines,0,"fit")
        if cap <= 0:
            return BreakDecision(0,0,block.lines,"block-does-not-fit")
        widow=max(self.min_widow,block.widow_lines)
        orphan=max(self.min_orphan,block.orphan_lines)
        take=cap
        # Avoid a stranded one-line (or otherwise too-short) remainder.
        if block.lines-take < widow:
            take=block.lines-widow
        if take < orphan:
            # Let the whole block move; the caller can place it on the next frame.
            return BreakDecision(0,0,block.lines,"orphan-protection")
        return BreakDecision(0,take,block.lines-take,"widow-orphan")

    def paginate(self, blocks, frame_heights):
        """Return pages as lists of (block, first_line, line_count).

        Keep-with-next groups are treated atomically when possible. If a group
        cannot fit an empty frame, its individual blocks are then paginated so
        a single oversized block never causes an infinite loop.
        """
        frames=[]; frame_index=0; used=0.0; current=[]
        blocks=list(blocks); i=0
        while i<len(blocks):
            block=blocks[i]
            group=[block]; j=i+1
            while group[-1].keep_with_next and j<len(blocks):
                group.append(blocks[j]); j+=1
            group_h=sum(b.height for b in group)
            limit=float(frame_heights[min(frame_index,len(frame_heights)-1)]) if frame_heights else 0
            if current and used+group_h>limit:
                frames.append(current); current=[]; used=0.0; frame_index+=1; continue
            if not current and group_h<=limit:
                for b in group:
                    current.append((b,0,b.lines)); used+=b.height
                i=j; continue
            # Paginate first block when the group/paragraph cannot fit intact.
            remaining=max(0.0,limit-used)
            d=self._split_lines(block,remaining)
            if d.lines_on_page:
                current.append((block,0,d.lines_on_page)); used+=d.lines_on_page*block.line_height
                if d.moved_lines:
                    frames.append(current); current=[]; used=0.0; frame_index+=1
                    # Replace with the remainder, preserving source offsets.
                    blocks[i]=Block(block.start,block.end,d.moved_lines,block.line_height,
                                    0.0,block.space_after,block.keep_with_next,block.widow_lines,block.orphan_lines)
                    continue
                i+=1
            else:
                if current:
                    frames.append(current); current=[]; used=0.0; frame_index+=1
                else:
                    # Oversized block: force progress rather than loop forever.
                    current.append((block,0,block.lines)); used=block.height; i+=1
        if current: frames.append(current)
        return frames


def install(app):
    if getattr(app,"_pm17_installed",False): return
    app._pm17_installed=True
    app.pm17_pagination_engine=PaginationEngine()
