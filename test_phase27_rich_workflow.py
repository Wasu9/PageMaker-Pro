from phase27_rich_workflow import parse_html


def test_bilingual_bulk_text_and_sup_sub():
    html='<p><b>38.</b> Column-I gives physical terms.</p><p>Column-I में धारा के प्रवाह से संबंधित कुछ भौतिक राशियाँ दी गई हैं।</p><p>H<sub>2</sub>O and x<sup>2</sup> + y<sup>2</sup></p>'
    text,ranges,images=parse_html(html)
    assert '38.' in text
    assert 'Column-I में' in text
    assert 'H₂O' in text
    assert 'x²' in text
    assert images == []
    assert any(r[2] for r in ranges)
    assert any(r[4] for r in ranges)
    assert any(r[5] for r in ranges)


def test_html_table_becomes_tabbed_rows():
    html='<table><tr><th>Column-I</th><th>Column-II</th></tr><tr><td>(A) Drift Velocity</td><td>(P) m/(ne²ρ)</td></tr></table>'
    text,_,_=parse_html(html)
    assert 'Column-I\tColumn-II' in text
    assert '(A) Drift Velocity\t(P) m/(ne²ρ)' in text
    assert '\n' in text


def test_math_unicode_is_not_normalized_away():
    html='<p>α + β → γ, ∫ E·dl = 0, ΔV = IR</p>'
    text,_,_=parse_html(html)
    assert text == 'α + β → γ, ∫ E·dl = 0, ΔV = IR'
