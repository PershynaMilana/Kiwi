from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class TestExecutionStatusPostFilterer(BasePostFilterer):
    """
    Post-filterer for TestExecutionStatus Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
