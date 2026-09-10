from phase17_pagination_engine import Block, PaginationEngine


def test_widow_orphan_break():
    e=PaginationEngine(min_widow=2,min_orphan=2)
    b=Block(0,100,10,10,widow_lines=2,orphan_lines=2)
    pages=e.paginate([b],[55,100])
    assert pages
    assert pages[0][0][2] >= 2
    assert sum(x[2] for p in pages for x in p)==10


def test_keep_with_next_group_moves_together():
    e=PaginationEngine()
    a=Block(0,10,2,10,keep_with_next=True)
    b=Block(10,20,2,10)
    pages=e.paginate([a,b],[25,100])
    assert len(pages)==2
    assert pages[0][0][0] is a
    assert pages[1][0][0] is b


def test_oversized_block_progresses():
    e=PaginationEngine()
    b=Block(0,10,20,10)
    pages=e.paginate([b],[50])
    assert pages
