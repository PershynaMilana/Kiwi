from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class TestRunPostFilterer(BasePostFilterer):
    """
    Post-filterer for TestRun Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
