"""
Document Diff/Change Detection Module

Analyzes differences between document versions to identify:
- Text changes (insertions, deletions, modifications)
- Article-level changes
- Semantic change detection
"""
import difflib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import re


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class DiffAnalyzer:
    """
    Analyzes differences between document versions.
    Provides article-level and text-level diff capabilities.
    """

    def __init__(self):
        """Initialize the diff analyzer."""
        pass

    def compare_documents(
        self,
        old_text: str,
        new_text: str,
        old_articles: Optional[List[Dict]] = None,
        new_articles: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Compare two document versions and return structured diff.

        Args:
            old_text: Full text of the old version
            new_text: Full text of the new version
            old_articles: Optional list of articles from old version
            new_articles: Optional list of articles from new version

        Returns:
            Dictionary containing:
                - summary: High-level summary of changes
                - text_diff: Line-by-line diff
                - article_changes: Article-level changes (if articles provided)
                - statistics: Change statistics
        """
        if not old_text or not new_text:
            return {
                "error": "Both old and new text must be provided",
                "summary": {},
                "text_diff": [],
                "article_changes": [],
                "statistics": {}
            }

        # Generate line-by-line diff
        text_diff = self._generate_text_diff(old_text, new_text)

        # Calculate statistics
        statistics = self._calculate_statistics(text_diff)

        # Analyze article-level changes if articles provided
        article_changes = []
        if old_articles and new_articles:
            article_changes = self._analyze_article_changes(old_articles, new_articles)

        # Generate summary
        summary = self._generate_summary(statistics, article_changes)

        return {
            "summary": summary,
            "text_diff": text_diff,
            "article_changes": article_changes,
            "statistics": statistics,
            "comparison_date": utc_now().isoformat()
        }

    def _generate_text_diff(self, old_text: str, new_text: str) -> List[Dict[str, Any]]:
        """
        Generate line-by-line diff using Python's difflib.

        Returns list of diff operations with context.
        """
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()

        # Use unified diff for structured output
        differ = difflib.Differ()
        diff = list(differ.compare(old_lines, new_lines))

        # Structure the diff output
        structured_diff = []
        line_number_old = 0
        line_number_new = 0

        for line in diff:
            if line.startswith('  '):  # Unchanged
                line_number_old += 1
                line_number_new += 1
                structured_diff.append({
                    "type": "unchanged",
                    "content": line[2:],
                    "old_line": line_number_old,
                    "new_line": line_number_new
                })
            elif line.startswith('- '):  # Deletion
                line_number_old += 1
                structured_diff.append({
                    "type": "deletion",
                    "content": line[2:],
                    "old_line": line_number_old,
                    "new_line": None
                })
            elif line.startswith('+ '):  # Insertion
                line_number_new += 1
                structured_diff.append({
                    "type": "insertion",
                    "content": line[2:],
                    "old_line": None,
                    "new_line": line_number_new
                })

        return structured_diff

    def _calculate_statistics(self, text_diff: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate statistics from the diff."""
        insertions = sum(1 for d in text_diff if d["type"] == "insertion")
        deletions = sum(1 for d in text_diff if d["type"] == "deletion")
        unchanged = sum(1 for d in text_diff if d["type"] == "unchanged")

        total_changes = insertions + deletions

        return {
            "insertions": insertions,
            "deletions": deletions,
            "unchanged": unchanged,
            "total_changes": total_changes,
            "change_percentage": round((total_changes / (unchanged + total_changes) * 100), 2) if (unchanged + total_changes) > 0 else 0
        }

    def _analyze_article_changes(
        self,
        old_articles: List[Dict],
        new_articles: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Analyze changes at the article level.

        Returns list of article changes with type (added, deleted, modified).
        """
        changes = []

        # Create lookup maps
        old_articles_map = {art["number"]: art for art in old_articles}
        new_articles_map = {art["number"]: art for art in new_articles}

        # Find added and modified articles
        for article_num, new_article in new_articles_map.items():
            if article_num not in old_articles_map:
                changes.append({
                    "article": article_num,
                    "type": "added",
                    "title": new_article.get("title", ""),
                    "content_preview": new_article.get("content", "")[:200]
                })
            else:
                old_article = old_articles_map[article_num]
                if old_article.get("content") != new_article.get("content"):
                    changes.append({
                        "article": article_num,
                        "type": "modified",
                        "title": new_article.get("title", ""),
                        "old_content_preview": old_article.get("content", "")[:200],
                        "new_content_preview": new_article.get("content", "")[:200]
                    })

        # Find deleted articles
        for article_num, old_article in old_articles_map.items():
            if article_num not in new_articles_map:
                changes.append({
                    "article": article_num,
                    "type": "deleted",
                    "title": old_article.get("title", ""),
                    "content_preview": old_article.get("content", "")[:200]
                })

        return changes

    def _generate_summary(
        self,
        statistics: Dict[str, int],
        article_changes: List[Dict]
    ) -> Dict[str, Any]:
        """Generate a high-level summary of changes."""
        article_summary = {}
        if article_changes:
            article_summary = {
                "articles_added": sum(1 for c in article_changes if c["type"] == "added"),
                "articles_deleted": sum(1 for c in article_changes if c["type"] == "deleted"),
                "articles_modified": sum(1 for c in article_changes if c["type"] == "modified"),
            }

        return {
            "has_changes": statistics["total_changes"] > 0,
            "change_magnitude": self._classify_change_magnitude(statistics["change_percentage"]),
            "line_changes": {
                "insertions": statistics["insertions"],
                "deletions": statistics["deletions"],
                "total": statistics["total_changes"]
            },
            "article_changes": article_summary
        }

    def _classify_change_magnitude(self, percentage: float) -> str:
        """Classify the magnitude of changes."""
        if percentage == 0:
            return "none"
        elif percentage < 5:
            return "minor"
        elif percentage < 20:
            return "moderate"
        elif percentage < 50:
            return "major"
        else:
            return "substantial"

    def generate_html_diff(self, old_text: str, new_text: str) -> str:
        """
        Generate an HTML representation of the diff.
        Useful for frontend display.
        """
        old_lines = old_text.splitlines()
        new_lines = new_text.splitlines()

        differ = difflib.HtmlDiff()
        html_diff = differ.make_table(
            old_lines,
            new_lines,
            fromdesc="Previous Version",
            todesc="Current Version",
            context=True,
            numlines=3
        )

        return html_diff
