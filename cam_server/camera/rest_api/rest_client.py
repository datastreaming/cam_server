import requests

from cam_server import config


def validate_response(response):
    if response["state"] != "ok":
        raise ValueError(response.get("status", "Unknown error occurred."))

    return requests


class CamClient(object):
    def __init__(self, address="http://0.0.0.0:8888/"):
        """
        :param address: Address of the cam API, e.g. http://localhost:10000
        """

        self.api_address_format = address.rstrip("/") + config.API_PREFIX + config.CAMERA_REST_INTERFACE_PREFIX + "%s"

    def get_server_info(self):
        """
        Return the info of the cam server instance.
        For administrative purposes only.
        :return: Status of the server
        """
        rest_endpoint = "/info"
        response = requests.get(self.api_address_format % rest_endpoint).json()

        return validate_response(response)["info"]

    def get_cameras(self):
        """
        List existing cameras.
        :return: Currently existing cameras.
        """
        rest_endpoint = ""

        response = requests.get(self.api_address_format % rest_endpoint).json()
        return validate_response(response)["cameras"]

    def get_camera_config(self, camera_name):
        """
        Return the cam configuration.
        :param camera_name: Name of the cam.
        :return: Camera configuration.
        """
        rest_endpoint = "/%s/config" % camera_name

        response = requests.get(self.api_address_format % rest_endpoint).json()
        return validate_response(response)["config"]

    def set_camera_config(self, camera_name, config):
        """
        Set config on cam.
        :param camera_name: Camera to set the config to.
        :param config: Config to set, in dictionary format.
        :return: Actual applied config.
        """
        rest_endpoint = "/%s" % camera_name

        response = requests.post(self.api_address_format % rest_endpoint, data=config).json()
        return validate_response(response)["config"]

    def get_camera_geometry(self, camera_name):
        """
        Get cam geometry.
        :param camera_name: Name of the cam.
        :return: Camera geometry.
        """
        rest_endpoint = "/%s/geometry" % camera_name

        response = requests.get(self.api_address_format % rest_endpoint).json()
        return validate_response(response)["cameras"]

    def get_camera_image(self, camera_name):
        """
        Return the cam image in PNG format.
        :param camera_name: Camera name.
        :return: Response content (PNG).
        """
        rest_endpoint = "/%s/image" % camera_name

        response = requests.get(self.api_address_format % rest_endpoint).json()
        return response

    def get_camera_stream(self, camera_name):
        """
        Get the camera stream address.
        :param camera_name: Name of the camera to get the address for.
        :return: Stream address.
        """
        rest_endpoint = "/%s" % camera_name

        response = requests.get(self.api_address_format % rest_endpoint).json()
        return validate_response(response)["stream"]

    def stop_camera(self, camera_name):
        """
        Stop the camera.
        :param camera_name: Name of the camera to stop.
        :return: Response.
        """
        rest_endpoint = "/%s" % camera_name

        response = requests.get(self.api_address_format % rest_endpoint).json()
        validate_response(response)

    def stop_all_cameras(self):
        """
        Stop all the cameras on the server.
        :return: Response.
        """
        rest_endpoint = ""

        response = requests.get(self.api_address_format % rest_endpoint).json()
        validate_response(response)
