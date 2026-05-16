import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from analysis import get_grade_from_score, analyze_static_quality, get_file_stats

def test_grade_logic():
    """Smoke test to ensure grading logic works."""

    grade, _ = get_grade_from_score(95)
    assert grade == 'A++'

 
    grade, _ = get_grade_from_score(40)
    assert grade == 'C'

def test_static_analysis_smoke():
    """Smoke test for static analysis engine."""
    files = {
        "main.py": "def run(): pass",
        "README.md": "# Hello World"
    }
    score, breakdown = analyze_static_quality(files, 2)
    
    assert isinstance(score, int)
    assert 'Documentation' in breakdown

    assert "Readme: 10" in breakdown['Documentation']

def test_file_stats():
    """Smoke test for file processing stats."""
    files = {
        "app.py": "line1\nline2",
        "data.csv": "a,b,c"
    }
    ext_counts, total_lines, total_size = get_file_stats(files)
    
    assert ext_counts['py'] == 1
    assert ext_counts['csv'] == 1
    assert total_lines == 4  