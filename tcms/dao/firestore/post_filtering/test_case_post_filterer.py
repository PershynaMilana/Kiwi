from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class TestCasePostFilterer(BasePostFilterer):
    """
    Post-filterer for TestCase Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
