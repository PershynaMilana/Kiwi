from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class BugPostFilterer(BasePostFilterer):
    """
    Post-filterer for Bug Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
