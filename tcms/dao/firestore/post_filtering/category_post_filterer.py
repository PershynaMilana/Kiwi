from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class CategoryPostFilterer(BasePostFilterer):
    """
    Post-filterer for Category Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
