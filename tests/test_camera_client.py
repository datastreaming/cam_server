import os
import signal
import unittest

from multiprocessing import Process
from time import sleep

from bsread import source, SUB

from cam_server import CamClient
from cam_server.camera.receiver import CameraSimulation
from cam_server.start_cam_server import start_camera_server
from cam_server.utils import get_host_port_from_stream_address


class CameraClientTest(unittest.TestCase):
    def setUp(self):
        self.host = "0.0.0.0"
        self.port = 8888

        test_base_dir = os.path.split(os.path.abspath(__file__))[0]
        self.config_folder = os.path.join(test_base_dir, "camera_config/")

        self.process = Process(target=start_camera_server, args=(self.host, self.port, self.config_folder))
        self.process.start()

        # Give it some time to start.
        sleep(0.5)

        server_address = "http://%s:%s" % (self.host, self.port)
        self.client = CamClient(server_address)

    def tearDown(self):
        self.client.stop_all_cameras()
        os.kill(self.process.pid, signal.SIGINT)
        try:
            os.remove(os.path.join(self.config_folder, "testing_camera.json"))
        except:
            pass
        # Wait for the server to die.
        sleep(1)

    def test_client(self):
        server_info = self.client.get_server_info()

        self.assertIsNot(server_info["active_instances"],
                         "There should be no running instances.")

        expected_cameras = ["example_1", "example_2", "example_3", "example_4", "simulation"]

        self.assertListEqual(self.client.get_cameras(), expected_cameras, "Not getting all expected cameras")

        camera_stream_address = self.client.get_camera_stream("simulation")

        self.assertTrue(bool(camera_stream_address), "Camera stream address cannot be empty.")

        self.assertTrue("simulation" in self.client.get_server_info()["active_instances"],
                        "Simulation camera not present in server info.")

        # Check if we can connect to the stream and receive data (in less than 2 seconds).
        host, port = get_host_port_from_stream_address(camera_stream_address)
        with source(host=host, port=port, receive_timeout=2000, mode=SUB) as stream:
            data = stream.receive()
            self.assertIsNotNone(data, "Received data was none.")

            required_fields = set(["image", "timestamp"])
            self.assertSetEqual(required_fields, set(data.data.data.keys()), "Required fields missing.")

            image = data.data.data["image"].value
            x_size, y_size = CameraSimulation().get_geometry()
            self.assertListEqual(list(image.shape), [y_size, x_size],
                                 "Original and received image are not the same.")

        # Stop the simulation instance.
        self.client.stop_camera("simulation")

        self.assertTrue("simulation" not in self.client.get_server_info()["active_instances"],
                        "Camera simulation did not stop.")

        self.client.get_camera_stream("simulation")

        self.assertTrue("simulation" in self.client.get_server_info()["active_instances"],
                        "Camera simulation did not start.")

        self.client.stop_all_cameras()

        self.assertTrue("simulation" not in self.client.get_server_info()["active_instances"],
                        "Camera simulation did not stop.")

        example_1_config = self.client.get_camera_config("example_1")

        self.assertTrue(bool(example_1_config), "Cannot retrieve config.")

        # Change the name to reflect tha camera.
        example_1_config["name"] = "testing_camera"

        self.client.set_camera_config("testing_camera", example_1_config)

        testing_camera_config = self.client.get_camera_config("testing_camera")

        self.assertDictEqual(example_1_config, testing_camera_config, "Saved and loaded configs are not the same.")

        geometry = self.client.get_camera_geometry("simulation")
        simulated_camera = CameraSimulation()
        self.assertListEqual(geometry, [simulated_camera.size_x, simulated_camera.size_y],
                             'The geometry of the simulated camera is not correct.')

        self.assertTrue("testing_camera" in self.client.get_cameras(), "Testing camera should be present.")

        self.client.delete_camera_config("testing_camera")

        self.assertTrue("testing_camera" not in self.client.get_cameras(), "Testing camera should not be present.")


if __name__ == '__main__':
    unittest.main()
