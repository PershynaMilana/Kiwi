from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class UserPostFilterer(BasePostFilterer):
    """
    Post-filterer for User Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
