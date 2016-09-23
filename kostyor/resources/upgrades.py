import six

from flask import request
from flask_restful import Resource, fields, marshal_with, abort

from kostyor.common import constants, exceptions
from kostyor.db import api as db_api


_PUBLIC_ATTRIBUTES = {
    'id': fields.String,
    'cluster_id': fields.String,
    'from_version': fields.String,
    'to_version': fields.String,
    'status': fields.String,
    'upgrade_start_time': fields.DateTime('iso8601'),
    'upgrade_end_time': fields.DateTime('iso8601'),
}


class Upgrades(Resource):

    @marshal_with(_PUBLIC_ATTRIBUTES)
    def get(self):
        return db_api.get_upgrades()

    @marshal_with(_PUBLIC_ATTRIBUTES)
    def post(self):
        payload = request.get_json()

        # TODO: replace a set of validations with some sort of schema
        #       validation (e.g. cerberus).
        if 'to_version' not in payload:
            abort(400, message='"to_version" is a required parameter.')
        elif payload['to_version'].lower() not in constants.OPENSTACK_VERSIONS:
            abort(400, message=('Unsupported "to_version": %s' %
                                payload['to_version']))

        if 'cluster_id' not in payload:
            abort(400, message='"cluster_id" is a required parameter.')

        try:
            upgrade = db_api.create_cluster_upgrade(
                payload['cluster_id'],
                payload['to_version']
            )
        except exceptions.BadRequest as exc:
            abort(400, message=six.text_type(exc))
        except exceptions.NotFound as exc:
            abort(404, message=six.text_type(exc))

        return upgrade, 201


class Upgrade(Resource):

    _actions = {
        'pause': db_api.pause_cluster_upgrade,
        'continue': db_api.continue_cluster_upgrade,
        'cancel': db_api.cancel_cluster_upgrade,
        'rollback': db_api.rollback_cluster_upgrade,
    }

    @marshal_with(_PUBLIC_ATTRIBUTES)
    def get(self, upgrade_id):
        upgrade = db_api.get_upgrade(upgrade_id)

        if not upgrade:
            abort(404, message='Upgrade %s not found.' % upgrade_id)

        return upgrade

    @marshal_with(_PUBLIC_ATTRIBUTES)
    def put(self, upgrade_id):
        # FIXME: dbapi implicitly retrieves recent upgrade task. i have no
        #        idea what to do with receied upgrade_id for now. I think
        #        we should either pass it to DBAPI or use another API design.
        payload = request.get_json()

        if 'cluster_id' not in payload:
            abort(400, message='"cluster_id" is a required parameter.')

        if payload['action'] not in self._actions:
            abort(400, message='Action %s not supported.' % payload['action'])

        fn = self._actions[payload['action']]

        # Would it better to pass upgrade_id instead?
        return fn(payload['cluster_id'])