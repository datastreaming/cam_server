import numpy


def transform_image(image, camera_config):

    if camera_config.parameters["mirror_x"]:
        image = numpy.fliplr(image)

    if camera_config.parameters["mirror_y"]:
        image = numpy.flipud(image)

    if camera_config.parameters["rotate"] != 0:
        image = numpy.rot90(image, camera_config.parameters["rotate"])

    if not image.flags['C_CONTIGUOUS']:
        image = numpy.ascontiguousarray(image)

    return image