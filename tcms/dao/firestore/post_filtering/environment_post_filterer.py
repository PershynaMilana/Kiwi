from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class EnvironmentPostFilterer(BasePostFilterer):
    """
    Post-filterer for Environment Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """


class EnvironmentPropertyPostFilterer(BasePostFilterer):
    """
    Post-filterer for EnvironmentProperty Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
