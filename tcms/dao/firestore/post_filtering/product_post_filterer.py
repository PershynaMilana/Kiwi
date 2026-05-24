from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class ProductPostFilterer(BasePostFilterer):
    """
    Post-filterer for Product Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
