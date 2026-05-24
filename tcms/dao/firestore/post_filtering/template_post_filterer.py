from tcms.dao.firestore.post_filtering.base_post_filterer import BasePostFilterer


class TemplatePostFilterer(BasePostFilterer):
    """
    Post-filterer for Template Firestore documents.
    All standard ORM-style criteria handled by BasePostFilterer.
    """
