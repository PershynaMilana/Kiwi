from tcms.core.helpers import comments


class CommentDAO:
    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def get_comments(self, model_obj):
        """
        Get all comments for the given model object.
        Returns a list of comment value dicts.
        """
        return list(comments.get_comments(model_obj).values())

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def add_comment(self, model_obj, comment_text, author, submit_date=None):
        """
        Add a comment to the given model object.
        Returns the serialized comment dict (model_to_dict).
        """
        from django.forms.models import model_to_dict

        created = comments.add_comment([model_obj], comment_text, author, submit_date)
        comment_obj = created[0]
        return model_to_dict(comment_obj)

    def remove_comment(self, model_obj, comment_id=None):
        """
        Remove all or specified comment(s) from the given model object.
        """
        to_be_deleted = comments.get_comments(model_obj)
        if comment_id:
            to_be_deleted = to_be_deleted.filter(pk=comment_id)
        to_be_deleted.delete()


comment_dao = CommentDAO()
