# Camera stream port range.
CAMERA_STREAM_PORT_RANGE = (10100, 11100)
# Data header compression
BSREAD_DATA_HEADER_COMPRESSION = None
# Camera image compression
BSREAD_IMAGE_COMPRESSION = None
# How many seconds do we wait before disconnecting a stream without clients.
MFLOW_NO_CLIENTS_TIMEOUT = 3

# Default folder for cam_server configs.
DEFAULT_CAMERA_CONFIG_FOLDER = "configuration"
# Default colormap to use when getting an image from the camera.
DEFAULT_CAMERA_IMAGE_COLORMAP = "rainbow"

# API prefix.
API_PREFIX = "/api/v1"
# Camera server prefix.
CAMERA_REST_INTERFACE_PREFIX = "/cam_server"
# Default logging level.
DEFAULT_LOGGING_LEVEL = "WARNING"
