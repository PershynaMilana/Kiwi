from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class ComponentPostFilterer(BasePostFilterer):
    """
    Post-filterer for Component Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
