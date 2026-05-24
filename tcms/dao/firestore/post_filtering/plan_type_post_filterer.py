from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class PlanTypePostFilterer(BasePostFilterer):
    """
    Post-filterer for PlanType Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
