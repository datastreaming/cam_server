import socket
from logging import getLogger

from cam_server import config
from cam_server.camera.sender import process_camera_stream
from cam_server.instance_management.management import InstanceManager, InstanceWrapper
from cam_server.utils import get_port_generator, update_camera_config

_logger = getLogger(__name__)


class CameraInstanceManager(InstanceManager):
    def __init__(self, config_manager, hostname=None):
        super(CameraInstanceManager, self).__init__()

        self.config_manager = config_manager
        self.port_generator = get_port_generator(config.CAMERA_STREAM_PORT_RANGE)
        self.hostname = hostname

    def get_camera_list(self):
        return self.config_manager.get_camera_list()

    def get_camera_stream(self, camera_name):
        """
        Get the camera stream address.
        :param camera_name: Name of the camera to get the stream for.
        :return: Camera stream address.
        """

        # Check if the requested camera already exists.
        if not self.is_instance_present(camera_name):

            stream_port = next(self.port_generator)

            camera = self.config_manager.load_camera(camera_name)
            camera.verify_camera_online()

            _logger.info("Creating camera instance '%s' on port %d.", camera_name, stream_port)

            self.add_instance(camera_name, CameraInstance(
                process_function=process_camera_stream,
                camera=camera,
                stream_port=stream_port,
                hostname=self.hostname
            ))

        self.start_instance(camera_name)

        return self.get_instance(camera_name).get_stream_address()

    def update_camera_config(self, instance_id, config_updates):
        if not self.is_instance_present(instance_id):
            return

        camera_instance = self.get_instance(instance_id)

        current_config = camera_instance.get_configuration()

        new_config = update_camera_config(current_config, config_updates)
        camera_instance.set_parameter(new_config)


class CameraInstance(InstanceWrapper):
    def __init__(self, process_function, camera, stream_port, hostname=None):

        super(CameraInstance, self).__init__(camera.get_name(), process_function,
                                             camera, stream_port)

        self.camera = camera

        if not hostname:
            hostname = socket.gethostname()

        self.stream_address = "tcp://%s:%d" % (hostname, stream_port)

    def get_info(self):
        return {"stream_address": self.stream_address,
                "is_stream_active": self.is_running(),
                "camera_geometry": self.camera.get_geometry(),
                "camera_name": self.camera.get_name()}

    def get_configuration(self):
        return self.camera.camera_config.get_configuration()

    def get_name(self):
        return self.camera.get_name()

    def get_stream_address(self):
        return self.stream_address

    def set_parameter(self, configuration):
        self.camera.camera_config.set_configuration(configuration)

        # The set configuration sets the default parameters.
        super().set_parameter(self.camera.camera_config.get_configuration())
