from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class TestCaseStatusPostFilterer(BasePostFilterer):
    """
    Post-filterer for TestCaseStatus Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
