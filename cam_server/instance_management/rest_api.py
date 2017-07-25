
import logging
import os

_logger = logging.getLogger(__name__)


def register_rest_interface(app, instance_manager, api_root_address):
    """
    Register the instance manager REST api.
    :param app: Bottle app to register the interface to.
    :param instance_manager: Manager for camera instances.
    :param api_root_address: Prefix to put before commands, and after api prefix.
    """

    @app.delete(api_root_address)
    def stop_all_instances():
        """
        Stop all the cameras running on the server.
        """
        instance_manager.stop_all_cameras()

        return {"state": "ok",
                "status": "All instances have been stopped."}

    @app.get(api_root_address + "/info")
    def get_instance_manager_info():
        """
        Return the current camera server instance info.
        """
        return {"state": "ok",
                "status": "Instance manager info retrieved.",
                "info": instance_manager.get_info()}

    @app.delete(api_root_address + "/<instance_name>")
    def stop_instance(instance_name):
        """
        Stop a specific camera.
        :param instance_name: Name of the camera.
        """
        instance_manager.stop_camera(instance_name)

        return {"state": "ok",
                "status": "Instance '%s' stopped." % instance_name}
