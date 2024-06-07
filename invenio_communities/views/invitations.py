# OAREPO: invitation to community by email views

from flask import Blueprint, request as flask_request, redirect
from flask_login import login_required, current_user
from invenio_communities.communities.records.api import Community
from invenio_communities.members.email_invitations import accept_invitation

def create_blueprint(app):
    """Create blueprint."""
    blueprint = Blueprint(
        "invenio_communities_email_invitations",
        __name__,
        template_folder="../templates",
        url_prefix="/communities/email-invitations"
    )
    blueprint.add_url_rule("/accept/<token>", view_func=accept_invitation_view, endpoint="accept_invitation")
    return blueprint


@login_required
def accept_invitation_view(token):
    """Communities creation page."""
    community: Community = accept_invitation(token=token, user=current_user)
    return redirect(f"/me/communities/{community.slug}")



