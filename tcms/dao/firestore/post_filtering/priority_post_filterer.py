from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class PriorityPostFilterer(BasePostFilterer):
    """
    Post-filterer for Priority Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
