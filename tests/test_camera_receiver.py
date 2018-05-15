import unittest

from cam_server import config
from cam_server.camera.configuration import CameraConfig
from cam_server.camera.source.simulation import CameraSimulation


class CameraReceiverTest(unittest.TestCase):

    def test_camera_simulation(self):
        camera = CameraSimulation(CameraConfig("simulation"))

        n_images_to_receive = 5

        def callback_method(image, timestamp):
            self.assertIsNotNone(image, "Image should not be None")
            self.assertIsNotNone(timestamp, "Timestamp should not be None")

            nonlocal n_images_to_receive
            if n_images_to_receive <= 0:
                camera.clear_callbacks()
                camera.simulation_stop_event.set()

            n_images_to_receive -= 1

        camera.connect()
        camera.add_callback(callback_method)

        camera.simulation_stop_event.wait()

    def test_camera_calibration(self):
        camera = CameraSimulation(CameraConfig("simulation"))
        size_x, size_y = camera.get_geometry()

        image = camera.get_image()

        self.assertEqual(image.shape[0], size_y)
        self.assertEqual(image.shape[1], size_x)

        x_axis, y_axis = camera.get_x_y_axis()

        self.assertEqual(x_axis.shape[0], size_x)
        self.assertEqual(y_axis.shape[0], size_y)

    def test_camera_simulation_interval(self):
        camera = CameraSimulation(CameraConfig("simulation"))

        self.assertEqual(camera.simulation_interval, config.DEFAULT_CAMERA_SIMULATION_INTERVAL)

        new_simulation_interval = 1
        camera_config = CameraConfig("simulation")
        configuration = camera_config.get_configuration()
        configuration["simulation_interval"] = new_simulation_interval
        camera_config.set_configuration(configuration)

        camera = CameraSimulation(camera_config)

        self.assertEqual(camera.simulation_interval, new_simulation_interval)

if __name__ == '__main__':
    unittest.main()
