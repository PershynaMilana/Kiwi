from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class TagPostFilterer(BasePostFilterer):
    """
    Post-filterer for Tag Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
