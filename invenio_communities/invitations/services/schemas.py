# -*- coding: utf-8 -*-
#
# Copyright (C) 2022 Northwestern University.
#
# Invenio-Communities is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Invitation schemas."""

from marshmallow import Schema, fields, validate, validates

from ...members import ROLE_TYPES



class MemberInvitationPayloadSchema(Schema):
    """Community Member Invitation Schema."""

    role = fields.String(required=True)

    @validates("role")
    def validate_role(self, value):
        """Validate role."""
        return validate.OneOf(ROLE_TYPES)
