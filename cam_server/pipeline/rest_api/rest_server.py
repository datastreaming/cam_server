import json
import logging

import bottle
from bottle import request, response

from cam_server import config
from cam_server.instance_management import rest_api
from cam_server.utils import collect_background, update_pipeline_config

_logger = logging.getLogger(__name__)


def register_rest_interface(app, instance_manager, interface_prefix=None):
    """
    Get the rest api server.
    :param app: Bottle app to register the interface to.
    :param instance_manager: Manager for camera instances.
    :param interface_prefix: Prefix to put before commands, and after api prefix.
    """

    if interface_prefix is None:
        interface_prefix = config.PIPELINE_REST_INTERFACE_PREFIX

    api_root_address = config.API_PREFIX + interface_prefix

    # Register instance management API.
    rest_api.register_rest_interface(app, instance_manager, api_root_address)

    @app.get(api_root_address)
    def get_pipeline_list():
        """
        Return the list of available pipelines.
        :return:
        """
        return {"state": "ok",
                "status": "List of available cameras.",
                "pipelines": instance_manager.get_pipeline_list()}

    @app.post(api_root_address)
    def create_pipeline_from_config():
        pipeline_config = request.json
        user_instance_id = request.query.decode().get("instance_id")

        instance_id, stream_address = instance_manager.create_pipeline(configuration=pipeline_config,
                                                                       instance_id=user_instance_id)

        return {"state": "ok",
                "status": "Stream address for pipeline %s." % instance_id,
                "instance_id": instance_id,
                "stream": stream_address,
                "config": instance_manager.get_instance(instance_id).get_configuration()}

    @app.post(api_root_address + '/<pipeline_name>')
    def create_pipeline_from_name(pipeline_name):
        user_instance_id = request.query.decode().get("instance_id")

        instance_id, stream_address = instance_manager.create_pipeline(pipeline_name=pipeline_name,
                                                                       instance_id=user_instance_id)

        return {"state": "ok",
                "status": "Stream address for pipeline %s." % instance_id,
                "instance_id": instance_id,
                "stream": stream_address,
                "config": instance_manager.get_instance(instance_id).get_configuration()}

    @app.get(api_root_address + '/instance/<instance_id>')
    def get_instance_stream(instance_id):
        stream_address = instance_manager.get_instance_stream(instance_id)

        return {"state": "ok",
                "status": "Stream address for pipeline %s." % instance_id,
                "stream": stream_address}

    @app.get(api_root_address + '/instance/<instance_id>/info')
    def get_instance_info(instance_id):
        return {"state": "ok",
                "status": "Pipeline instance %s info retrieved." % instance_id,
                "info": instance_manager.get_instance(instance_id).get_info()}

    @app.get(api_root_address + '/instance/<instance_id>/config')
    def get_instance_config(instance_id):
        return {"state": "ok",
                "status": "Pipeline instance %s info retrieved." % instance_id,
                "config": instance_manager.get_instance(instance_id).get_configuration()}

    @app.post(api_root_address + '/instance/<instance_id>/config')
    def set_instance_config(instance_id):
        config_updates = request.json

        if not config_updates:
            raise ValueError("Config updates cannot be empty.")

        instance_manager.update_instance_config(instance_id, config_updates)

        return {"state": "ok",
                "status": "Pipeline instance %s configuration changed." % instance_id,
                "config": instance_manager.get_instance(instance_id).get_configuration()}

    @app.get(api_root_address + '/<pipeline_name>/config')
    def get_pipeline_config(pipeline_name):
        return {"state": "ok",
                "status": "Pipeline %s configuration retrieved." % pipeline_name,
                "config": instance_manager.config_manager.get_pipeline_config(pipeline_name)}

    @app.post(api_root_address + '/<pipeline_name>/config')
    def set_pipeline_config(pipeline_name):

        instance_manager.config_manager.save_pipeline_config(pipeline_name, request.json)

        return {"state": "ok",
                "status": "Pipeline %s configuration saved." % pipeline_name,
                "config": instance_manager.config_manager.get_pipeline_config(pipeline_name)}

    @app.delete(api_root_address + '/<pipeline_name>/config')
    def delete_pipeline_config(pipeline_name):

        instance_manager.config_manager.delete_pipeline_config(pipeline_name)

        return {"state": "ok",
                "status": "Pipeline %s configuration deleted." % pipeline_name}

    @app.post(api_root_address + '/camera/<camera_name>/background')
    def collect_background_on_camera(camera_name):
        number_of_images = request.query.decode().get("n_images", config.PIPELINE_DEFAULT_N_IMAGES_FOR_BACKGROUND)

        try:
            number_of_images = int(number_of_images)
        except ValueError:
            raise ValueError("n_images must be a number.")

        stream_address = instance_manager.cam_server_client.get_camera_stream(camera_name)

        background_id = collect_background(camera_name, stream_address, number_of_images,
                                           instance_manager.background_manager)

        return {"state": "ok",
                "status": "Background collected on camera %s." % camera_name,
                "background_id": background_id}

    @app.get(api_root_address + '/camera/<camera_name>/background')
    def get_latest_background_for_camera(camera_name):

        background_id = instance_manager.background_manager.get_latest_background_id(camera_name)

        return {"state": "ok",
                "status": "Latest background for camera %s." % camera_name,
                "background_id": background_id}

    @app.error(405)
    def method_not_allowed(res):
        if request.method == 'OPTIONS':
            new_res = bottle.HTTPResponse()
            new_res.set_header('Access-Control-Allow-Origin', '*')
            new_res.set_header('Access-Control-Allow-Methods', 'PUT, GET, POST, DELETE, OPTIONS')
            new_res.set_header('Access-Control-Allow-Headers', 'Origin, Accept, Content-Type')
            return new_res
        res.headers['Allow'] += ', OPTIONS'
        return request.app.default_error_handler(res)

    @app.hook('after_request')
    def enable_cors():
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'PUT, GET, POST, DELETE, OPTIONS'
        response.headers[
            'Access-Control-Allow-Headers'] = 'Origin, Accept, Content-Type, X-Requested-With, X-CSRF-Token'

    @app.error(500)
    def error_handler_500(error):
        response.content_type = 'application/json'
        response.status = 200

        return json.dumps({"state": "error",
                           "status": str(error.exception)})
