from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class ClassificationPostFilterer(BasePostFilterer):
    """
    Post-filterer for Classification Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
