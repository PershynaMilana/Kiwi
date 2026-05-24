from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class BugSystemPostFilterer(BasePostFilterer):
    """
    Post-filterer for BugSystem Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
