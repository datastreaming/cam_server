import argparse
import logging
import os

import bottle
from cam_server.pipeline.configuration import PipelineConfigManager, BackgroundImageManager

from cam_server.pipeline.management import PipelineInstanceManager
from cam_server.pipeline.rest_api.rest_server import register_rest_interface as register_pipeline_rest_interface

from cam_server import config, CamClient, PipelineClient
from cam_server.instance_management.configuration import ConfigFileStorage

from cam_server.pipeline.proxy import Proxy as PipelineProxy

_logger = logging.getLogger(__name__)


def start_pipeline_proxy(host, port, servers, config_base, background_base, cam_server_api_address, hostname=None):


    # Check if config directory exists
    if not os.path.isdir(config_base):
        _logger.error("Configuration directory '%s' does not exist." % config_base)
        exit(-1)

    if not os.path.isdir(background_base):
        _logger.error("Background image directory '%s' does not exist." % background_base)
        exit(-1)

    sever_pool = []
    try:
        servers = [s.strip() for s in servers.split(",")]
    except:
        servers = ["http://localhost:8888"]

    for server in servers:
        sever_pool.append(PipelineClient(server))

    if hostname:
        _logger.warning("Using custom hostname '%s'." % hostname)

    cam_server_client = CamClient(cam_server_api_address)
    config_manager = PipelineConfigManager(config_provider=ConfigFileStorage(config_base))
    background_manager = BackgroundImageManager(background_base)

    app = bottle.Bottle()

    proxy = PipelineProxy(config_manager, background_manager,cam_server_client, sever_pool)
    register_pipeline_rest_interface(app=app, instance_manager=proxy)
    proxy.register_rest_interface(app)
    try:
        bottle.run(app=app, host=host, port=port)
    finally:
        #clenup
        pass


def main():
    parser = argparse.ArgumentParser(description='Pipeline processing server')
    parser.add_argument("-c", '--cam_server', default="http://0.0.0.0:8898", help="Cam server rest api address.")
    parser.add_argument('-p', '--port', default=8899, help="Server port")
    parser.add_argument('-i', '--interface', default='0.0.0.0', help="Hostname interface to bind to")
    parser.add_argument('-s', '--servers', default="http://localhost:8889",
                        help="Comma-separated list of servers")
    parser.add_argument('-b', '--base', default=config.DEFAULT_PIPELINE_CONFIG_FOLDER,
                        help="(Pipeline) Configuration base directory")
    parser.add_argument('-g', '--background_base', default=config.DEFAULT_BACKGROUND_CONFIG_FOLDER)
    parser.add_argument('-n', '--hostname', default=None, help="Hostname to use when returning the stream address.")

    parser.add_argument("--log_level", default=config.DEFAULT_LOGGING_LEVEL,
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
                        help="Log level to use.")
    arguments = parser.parse_args()

    # Setup the logging level.
    logging.basicConfig(level=arguments.log_level)

    start_pipeline_proxy(arguments.interface, arguments.port, arguments.servers, arguments.base,
                          arguments.background_base, arguments.cam_server,
                          arguments.hostname)


if __name__ == "__main__":
    main()
