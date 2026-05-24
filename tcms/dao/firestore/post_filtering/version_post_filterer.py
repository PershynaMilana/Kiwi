from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class VersionPostFilterer(BasePostFilterer):
    """
    Post-filterer for Version Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
