import pytest
from invenio_access.permissions import system_identity
from invenio_requests import current_requests_service
from invenio_requests.records import Request

from invenio_communities.views.invitations import create_blueprint

from flask_security import login_user
from invenio_accounts.testutils import login_user_via_session


@pytest.fixture()
def theme_app(instance_path, app):
    """Application with template theming."""
    app.config["APP_THEME"] = ["semantic-ui"]
    app.register_blueprint(create_blueprint(app))
    yield app



@pytest.fixture()
def client_with_login(client, UserFixture, app, db):
    """Log in a user to the client."""

    u = UserFixture(
        email=f"test@test.org",
        password="abcdef",
        username="test",
        user_profile={
            "full_name": f"Test",
            "affiliations": "CERN",
        },
        preferences={
            "visibility": "public",
            "email_visibility": "restricted",
            "notifications": {
                "enabled": True,
            },
        },
        active=True,
        confirmed=True,
    )
    u.create(app, db)
    db.session.commit()
    login_user(u.user, remember=False)
    login_user_via_session(client, email=u.email)
    return client


def test_invite_user_via_email(theme_app, client_with_login, member_service, community, owner, group, db):
    """Invite a group."""
    # Groups cannot be invited (groups cannot receive invitation request)
    data = {
        "members": [{"type": "email", "id": "me@gmail.com"}],
        "role": "reader",
    }

    member_service.invite(
        system_identity,
        community._record.id,
        data
    )

    # Check that the invitation was created
    Request.index.refresh()
    requests = current_requests_service.read_all(identity=system_identity, fields=None)
    for r in requests:
        if r["type"] == 'community-email-invitation':
            request_id = r["id"]
            break
    else:
        raise AssertionError("No invitation request found")

    # Accept the invitation
    response = client_with_login.get("/communities/email-invitations/accept/{}".format(request_id))
    assert response.status_code == 302
    assert response.location == f"/me/communities/{community._record.slug}"
