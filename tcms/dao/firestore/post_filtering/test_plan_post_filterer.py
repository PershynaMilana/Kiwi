from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class TestPlanPostFilterer(BasePostFilterer):
    """
    Post-filterer for TestPlan Firestore documents.

    All standard ORM-style criteria are handled by BasePostFilterer.
    Add TestPlan-specific filtering logic here when needed
    (e.g. full-text search across name+text, tree-depth filtering, etc.).
    """
