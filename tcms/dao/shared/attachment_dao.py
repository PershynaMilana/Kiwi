from tcms.rpc import utils


class AttachmentDAO:
    # ------------------------------------------------------------------
    # READ operations
    # ------------------------------------------------------------------

    def list_attachments(self, request, model_obj):
        """
        List attachments for the given model object.
        Returns a list of attachment info dicts with download URLs.
        """
        return utils.get_attachments_for(request, model_obj)

    # ------------------------------------------------------------------
    # WRITE operations
    # ------------------------------------------------------------------

    def add_attachment(self, obj_id, model_label, user, filename, b64content):
        """
        Add attachment to a model object.
        model_label is e.g. "testcases.TestCase", "testplans.TestPlan", etc.
        """
        utils.add_attachment(obj_id, model_label, user, filename, b64content)


attachment_dao = AttachmentDAO()
