import socket
import uuid
from itertools import cycle
from logging import getLogger

from cam_server import config
from cam_server.instance_management.management import InstanceManager, InstanceWrapper
from cam_server.pipeline.configuration import PipelineConfig
from cam_server.pipeline.transceiver import receive_process_send
from cam_server.utils import get_host_port_from_stream_address

_logger = getLogger(__name__)


class PipelineInstanceManager(InstanceManager):
    def __init__(self, config_manager, cam_server_client):
        super(PipelineInstanceManager, self).__init__()

        self.config_manager = config_manager
        self.cam_server_client = cam_server_client

        self.port_generator = cycle(iter(range(*config.PIPELINE_STREAM_PORT_RANGE)))

    def get_pipeline_list(self):
        return self.config_manager.get_pipeline_list()

    def create_pipeline(self, pipeline_name=None, configuration=None):
        """
        Create the pipeline stream address. Either pass the pipeline name, or the configuration.
        :param pipeline_name: Name of the pipeline to load from config.
        :param configuration: Configuration to load the pipeline with.
        :return: Pipeline stream address.
        """
        # You cannot specify both or none.
        if (pipeline_name is None) == (configuration is None):
            raise ValueError("You must specify either the pipeline name or the configuration for the pipeline.")

        if configuration:
            self.config_manager.validate_config(configuration)
            pipeline = PipelineConfig(pipeline_name, configuration)
        else:
            pipeline = self.config_manager.load_pipeline(pipeline_name)

        stream_port = next(self.port_generator)

        camera_name = pipeline.camera_name
        camera_stream_address = self.cam_server_client.get_camera_stream(camera_name)["stream"]

        # Random uuid as the instance id.
        instance_id = uuid.uuid4()

        _logger.info("Creating pipeline '%s' on port '%d' for camera '%s' on stream '%s'. instance_id=%s",
                     pipeline_name, stream_port, camera_name, camera_stream_address, instance_id)

        self.add_instance(instance_id, PipelineInstance(
            instance_id=instance_id,
            process_function=receive_process_send,
            pipeline_config=pipeline,
            output_stream_port=stream_port,
            source_stream_address=camera_stream_address
        ))

        self.start_instance(pipeline_name)

        pipeline = self.get_instance(instance_id).get_stream_address()

        return pipeline.get_id(), pipeline.get_stream_address()

    def get_instance_stream(self, instance_id):
        if not self.is_instance_present(instance_id):
            try:
                pipeline_config = self.config_manager.load_pipeline(instance_id)
            except ValueError:
                raise ValueError("Instance '%s' is not present on server and it is not a saved pipeline name." %
                                 instance_id)

            stream_port = next(self.port_generator)

            camera_name = pipeline_config.get_camera_name()
            camera_stream_address = self.cam_server_client.get_camera_stream(camera_name)["stream"]

            _logger.info("Creating pipeline '%s' on port '%d' for camera '%s' on stream '%s'. instance_id=%s",
                         instance_id, stream_port, camera_name, camera_stream_address, instance_id)

            self.add_instance(instance_id, PipelineInstance(
                instance_id=instance_id,
                process_function=receive_process_send,
                pipeline_config=pipeline_config,
                output_stream_port=stream_port,
                source_stream_address=camera_stream_address,
                read_only_config=True  # Implicitly created instances are read only.
            ))

        self.start_instance(instance_id)

        return self.get_instance(instance_id).get_stream_address()


class PipelineInstance(InstanceWrapper):
    def __init__(self, instance_id, process_function, pipeline_config, output_stream_port, source_stream_address,
                 read_only_config=False):
        source_host, source_port = get_host_port_from_stream_address(source_stream_address)

        super(PipelineInstance, self).__init__(instance_id, process_function,
                                               source_host, source_port, pipeline_config, output_stream_port)

        self.pipeline = pipeline_config
        self.stream_address = "tcp://%s:%d" % (socket.gethostname(), self.stream_port)
        self.read_only_config = read_only_config

    def get_info(self):
        return {"stream_address": self.stream_address,
                "is_stream_active": self.is_running(),
                "camera_stream_address": self.source_stream_address,
                "config": self.pipeline.get_parameters(),
                "pipeline_name": self.instance_name,
                "read_only": self.read_only_config}

    def get_config(self):
        return self.pipeline.to_dict()

    def get_stream_address(self):
        return self.stream_address

    def set_parameter(self, parameters):
        if self.read_only_config:
            raise ValueError("Cannot set config on a read only instance.")

        super().set_parameter(parameters)

        # Update the parameters on the local instance as well.
        self.pipeline.parameters = parameters

    def get_name(self):
        return self.pipeline.get_name()
