import multiprocessing
import time
from logging import getLogger

from cam_server import config

_logger = getLogger(__name__)


class InstanceManager(object):
    def __init__(self):
        self.instances = {}

    def get_info(self):
        """
        Return the instance manager info.
        :return: Dictionary with the info.
        """
        info = {"active_instances": dict((instance.get_instance_id(), instance.get_info())
                                         for instance in self.instances.values() if instance.is_running())}

        return info

    def add_instance(self, instance_name, instance_wrapper):
        """
        Add instance to the list of instances.
        :param instance_name: Instance name to add.
        :param instance_wrapper: Instance wrapper.
        """
        self.instances[instance_name] = instance_wrapper

    def is_instance_present(self, instance_name):
        """
        Check if instance is already present in the instances pool.
        :param instance_name: Name to check.
        :return: True if instance is already present.
        """
        return instance_name in self.instances

    def get_instance(self, instance_name):
        """
        Retrieve the requested instance.
        :param instance_name: Name od the instance to return.
        :return:
        """
        if instance_name not in self.instances:
            raise ValueError("Instance '%s' does not exist." % instance_name)

        return self.instances[instance_name]

    def start_instance(self, instance_name):
        """
        Start the instance.
        :param instance_name: Instance to start.
        """
        instance = self.get_instance(instance_name)

        if not instance.is_running():
            instance.start()

        instance.start()

    def stop_instance(self, instance_name):
        """
        Terminate the instance of the specified name.
        :param instance_name: Name of the instance to stop.
        """
        _logger.info("Stopping instance '%s'.", instance_name)

        if instance_name in self.instances:
            self.instances[instance_name].stop()

    def stop_all_instances(self):
        """
        Terminate all the instances.
        :return:
        """
        _logger.info("Stopping all instances.")

        for instance_name in self.instances:
            self.stop_instance(instance_name)

    def delete_instance(self, instance_name):
        if instance_name not in self.instances:
            raise ValueError("Instance '%s' does not exist." % instance_name)

        del self.instances[instance_name]


class InstanceWrapper:
    def __init__(self, instance_name, process_function, *args):

        self.instance_name = instance_name
        self.process_function = process_function
        # Arguments to pass to the process function.
        self.args = args

        self.process = None
        self.manager = multiprocessing.Manager()

        self.stop_event = multiprocessing.Event()
        # The initial value of the stop event is set -> when the process starts, it un-sets it to signal the start.
        self.stop_event.set()

        self.statistics = self.manager.Namespace()
        self.parameter_queue = multiprocessing.Queue()

    def start(self):
        if self.process and self.process.is_alive():
            _logger.info("Instance '%s' already running.", self.instance_name)
            return

        self.stop_event.set()

        self.process = multiprocessing.Process(target=self.process_function,
                                               args=(self.stop_event, self.statistics, self.parameter_queue,
                                                     *self.args))
        self.process.start()

        # Wait for the processor to clear the flag - indication that the process is ready.
        start_timestamp = time.time()
        while self.stop_event.is_set():
            time.sleep(config.PROCESS_POLL_INTERVAL)
            # Check if the timeout has already elapsed.
            if time.time() - start_timestamp > config.PROCESS_COMMUNICATION_TIMEOUT:
                self.process.terminate()
                error_message = "Could not start the '%s' instance in time. Terminated. See logs." % \
                                self.instance_name
                _logger.error(error_message)
                raise Exception(error_message)

    def stop(self):
        if not self.process:
            _logger.info("Instance '%s' already stopped.", self.instance_name)
            return

        self.stop_event.set()

        # Wait for the processor to clear the flag - indication that the process is ready.
        start_timestamp = time.time()

        while self.process.is_alive():
            time.sleep(config.PROCESS_POLL_INTERVAL)
            # Check if the timeout has already elapsed.
            if time.time() - start_timestamp > config.PROCESS_COMMUNICATION_TIMEOUT:
                _logger.warning("Could not stop the '%s' instance in time. Terminated.", self.instance_name)
                break

        # Kill process - no-op in case process already terminated
        self.process.terminate()
        self.process = None

    def wait(self):
        self.process.join()

    def set_parameter(self, parameters):
        self.parameter_queue.put(parameters)

    def is_running(self):
        return self.process and self.process.is_alive()

    def get_instance_id(self):
        return self.instance_name
