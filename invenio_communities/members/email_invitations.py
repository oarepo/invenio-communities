import dataclasses

from flask_principal import PermissionDenied
from invenio_access.permissions import system_identity
from invenio_notifications.services.uow import NotificationOp
from invenio_records_resources.references import RecordResolver, EntityResolver
from invenio_records_resources.references.entity_resolvers import EntityProxy
from invenio_requests.records import Request
from invenio_requests.resolvers.registry import ResolverRegistry

from .. import current_communities
from ..communities.records.api import Community
from ..notifications.builders import CommunityEmailInvitationNotificationBuilder
from .services.request import CommunityEmailInvitation
from flask import request
from invenio_requests import current_requests_service

from invenio_i18n import lazy_gettext as _


def invite_via_email(identity, community, role, visible, email, message, uow):
    """Create an invitation email for the given email and send it to the user"""

    title = _('Invitation to join "{community}"').format(
        community=community.metadata["title"],
    )
    description = _('You will join as "{role}".').format(role=role.title)

    # imported locally to prevent circular import
    from invenio_communities.members.services.service import invite_expires_at
    invitation_request = current_requests_service.create(
        identity,
        {
            "title": title,
            "description": description,
            "payload": {
                "role": role.name,
                "visible": "public" if visible else "restricted"
            }
        },
        CommunityEmailInvitation,
        receiver={"user_email": email},
        creator=community,
        topic=community,
        expires_at=invite_expires_at(),
        uow=uow,
    )

    invitation_token = str(invitation_request.id)

    invitation_link = f"{request.base_url}communities/accept-invitation/{invitation_token}"

    uow.register(
        NotificationOp(
            CommunityEmailInvitationNotificationBuilder.build(
                # explicit string conversion to get the value of LazyText
                role=str(role.title),
                message=message,
                invitation_link=invitation_link,
                request=invitation_request,
            )
        )
    )


def accept_invitation(token, user):
    """Called when the user clicks on the invitation link"""
    request = Request.get_record(token)

    if request.status != "submitted":
        raise PermissionDenied("This invitation link has been already used")

    community_id = request.topic.reference_dict["community"]
    community = Community.get_record(community_id)
    current_requests_service.execute_action(system_identity, request.id, "accept")

    member_service = current_communities.service.members
    member_service.add(system_identity, community.id, {
        "role": request["payload"]["role"],
        "visible": request["payload"]["visible"] == "public",
        "members": [
            {"type": "user", "id": str(user.id)}
        ]
    })
    return community


@dataclasses.dataclass
class EmailUser:
    # fake id just to get it through notification framework
    id: str

    # email address of the user
    email: str


class UserEmailResolver(EntityResolver):
    """Community entity resolver.

    The entity resolver enables Invenio-Requests to understand communities as
    receiver and topic of a request.
    """

    type_id = "user_email"
    type_key = "user_email"
    """Type identifier for this resolver."""

    def __init__(self):
        super().__init__("users")

    def matches_reference_dict(self, ref_dict):
        """Check if the ref_dict matches the expectations of this resolver."""
        return self.type_key in ref_dict

    def matches_entity(self, entity):
        """Check if the entity matches the expectations of this resolver."""
        return isinstance(entity, EmailUser)

    def _get_entity_proxy(self, ref_dict):
        return UserEmailProxy(self, ref_dict)

    def _reference_entity(self, entity):
        """Create a reference dict for the given record."""
        return {self.type_key: str(entity.email)}


class UserEmailProxy(EntityProxy):

    def _resolve(self):
        """Resolve the User from the proxy's reference dict, or system_identity."""
        user_email = self._parse_ref_dict_id()
        return dict(id=user_email, email=user_email)

    def get_needs(self, ctx=None):
        """Get the UserNeed for the referenced user."""
        return []

    def pick_resolved_fields(self, identity, resolved_dict):
        """Select which fields to return when resolving the reference."""
        serialized_user = {
            "id": resolved_dict["id"],
            "email": resolved_dict.get("email", ""),
        }

        return serialized_user


