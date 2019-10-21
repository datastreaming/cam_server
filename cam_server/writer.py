import argparse
import logging
from cam_server.utils import get_host_port_from_stream_address
from bsread.handlers.compact import Value
from bsread.data.helpers import get_channel_specs

import h5py
import numpy
import socket
import datetime
import os
import getpass
import json

_logger = logging.getLogger(__name__)

GENERAL_GROUP = "/general/"

LAYOUT_DEFAULT = "DEFAULT"
LAYOUT_FLAT = "FLAT"
LAYOUT_BSH5 = "BSH5"

UNDEFINED_NUMBER_OF_RECORDS= -1

LOCALTIME_DEFAULT = True
CHANGE_DEFAULT = False

from bsread import source, SUB, PULL



class Writer(object):
    def __init__(self, output_file="/dev/null",
                       number_of_records = UNDEFINED_NUMBER_OF_RECORDS,
                       layout = LAYOUT_DEFAULT,
                       save_local_timestamps = LOCALTIME_DEFAULT,
                       change = CHANGE_DEFAULT,
                       attributes={}):
        self.stream = None
        self.output_file = output_file
        self.attributes = attributes or {}
        if isinstance( self.attributes, str):
            self.attributes = json.loads(self.attributes)
        self.number_of_records = number_of_records
        self.layout = layout.upper()
        self.save_local_timestamps = save_local_timestamps
        self.change = change

        self.dataset_index = 0
        self._update_paths()

        self.attributes["created"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S.%f")
        self.attributes["user"] = getpass.getuser()
        self.attributes["pid"] = os.getpid()
        self.attributes["host"] = socket.gethostname()

        _logger.info("Opening output_file=%s with attributes %s",  self.output_file, self.attributes)

        self.file = h5py.File(output_file, 'w')
        self._create_attributes_datasets()
        self._set_number_datasets()
        self.datasets = []
        self.serializers = {}

    def _update_paths(self):
        self.current_record = 0
        self.dataset_index = self.dataset_index + 1

        if self.layout == LAYOUT_BSH5:
            self.data_group = "/"
        else:
            self.data_group = "/data%d/" % (self.dataset_index,)
        if self.layout == LAYOUT_BSH5:
            self.header_group = "/"
        else:
            self.header_group = "/header%d/" % (self.dataset_index,)
        self.pulse_id_dataset = self.header_group + "pulse_id"
        self.global_timestamp_dataset = self.header_group + "global_timestamp"

        if self.layout == LAYOUT_FLAT:
            self.value_dataset_name_format = self.data_group + "%s"
            self.timestamp_dataset_name_format = self.data_group + "%s_timestamp"
        elif self.layout == LAYOUT_BSH5:
            if self.dataset_index>1:
                self.value_dataset_name_format = self.data_group + "%s"+str(self.dataset_index)+"/data"
                self.timestamp_dataset_name_format = self.data_group + "%s"+str(self.dataset_index)+"/timestamp"
                self.pulse_id_dataset = self.header_group + "pulse_id" + str(self.dataset_index)
                self.global_timestamp_dataset = self.header_group + "global_timestamp" + str(self.dataset_index)
            else:
                self.value_dataset_name_format = self.data_group + "%s/data"
                self.timestamp_dataset_name_format = self.data_group + "%s/timestamp"
        else:
            self.value_dataset_name_format = self.data_group + "%s/value"
            self.timestamp_dataset_name_format = self.data_group + "%s/timestamp"


    def _create_scalar_dataset(self, name, dtype):
        ret =  self.file.create_dataset(name=name,
                                 shape=((self.number_of_records,) if (self.number_of_records > 0) else (0,)),
                                 maxshape= ((self.number_of_records,) if (self.number_of_records > 0) else (None,)),
                                 dtype=dtype)
        self.datasets.append(ret)
        return ret

    def _create_array_dataset(self, name, dtype, size):
        ret =  self.file.create_dataset(name=name,
                                 shape=(tuple([(self.number_of_records if (self.number_of_records > 0) else 0), ] + list(size))),
                                 maxshape=(tuple([(self.number_of_records if (self.number_of_records > 0) else None), ] + list(size))),
                                 dtype=dtype)
        self.datasets.append(ret)
        return ret

    def _append_dataset(self, name, value):
        dataset = self.file[name]
        if self.number_of_records < 0:
            dataset.resize(size=self.current_record+1, axis=0)
        if name in self.serializers.keys():
            (serializer, dtype) = self.serializers[name]
            value = serializer(value, dtype)
        if isinstance(value, str):
            value = numpy.string_(value)
        dataset[self.current_record] = value

    def create_header_datasets(self):
        self._create_scalar_dataset(self.pulse_id_dataset, "uint64")
        self._create_array_dataset(self.global_timestamp_dataset, "uint64", (2,))


    def append_header(self, pulse_id, global_timestamp, global_timestamp_offset):
        self._append_dataset(self.pulse_id_dataset, pulse_id)
        self._append_dataset(self.global_timestamp_dataset, [global_timestamp, global_timestamp_offset])

    def create_channel_datasets(self, data):
        for name in data.keys():
            val = data[name]
            timestamp, timestamp_offset, value = val.timestamp, val.timestamp_offset, val.value
            if isinstance(value, numpy.ndarray):
                self._create_array_dataset(self.value_dataset_name_format % name, value.dtype, value.shape)
            else:
                if hasattr(value, 'dtype'):
                    dtype = value.dtype
                else:
                    if isinstance(value, str):
                        dtype = "S1000"
                    else:
                        dtype, _, serializer, _ = get_channel_specs(value, extended=True)
                        self.serializers[self.value_dataset_name_format % name] = (serializer, dtype)
                self._create_scalar_dataset(self.value_dataset_name_format % name, dtype)
            if self.save_local_timestamps:
                self._create_array_dataset(self.timestamp_dataset_name_format % name, "uint64", (2,))

    def append_channel_data(self, data):
        for name in data.keys():
            val = data[name]
            timestamp, timestamp_offset, value = val.timestamp, val.timestamp_offset, val.value
            value_dataset_name = self.value_dataset_name_format % name
            timestamp_dataset_name = self.timestamp_dataset_name_format % name
            self._append_dataset(value_dataset_name, value)
            if self.save_local_timestamps:
                self._append_dataset(timestamp_dataset_name, [timestamp, timestamp_offset])

    def _create_attributes_datasets(self):
        for key in self.attributes.keys():
            self.file.create_dataset(GENERAL_GROUP + key,data=self.attributes.get(key))

    def _set_number_datasets(self):
        if self.dataset_index>1:
            self.file[GENERAL_GROUP + "datasets"][()] = self.dataset_index
        else:
            self.file.create_dataset(GENERAL_GROUP + "datasets", data=self.dataset_index)

    def _close_datasets(self):
        if self.number_of_records >=0:
            if self.current_record != self.number_of_records:
                _logger.debug("Image dataset number of records set to=%s" % self.current_record)
                for dataset in self.datasets:
                    dataset.resize(size=self.current_record, axis=0)
                self.number_of_records = max(self.number_of_records - self.current_record, 0)

    def close(self):
        self._close_datasets()
        self.file.close()
        self.datasets = []
        _logger.info("Writing completed.")

    def add_record(self, pulse_id, data, format_changed, global_timestamp, global_timestamp_offset):
        if (self.number_of_records >= 0) and (self.current_record >= self.number_of_records):
            raise Exception("HDF5 Writer reached the total number of records")
        if self.current_record == 0:
            self.create_header_datasets()
            self.create_channel_datasets(data)
        else:
            if format_changed:
                if self.change:
                    self._close_datasets()
                    self._update_paths()
                    self._set_number_datasets()
                    self.create_header_datasets()
                    self.create_channel_datasets(data)
                else:
                    raise Exception("Data format changed")
        self.append_header(pulse_id, global_timestamp, global_timestamp_offset)
        self.append_channel_data(data)
        self.current_record += 1

    def start(self, stream, stream_mode=SUB):
        self.stream = stream
        try:
            stream_host, stream_port = get_host_port_from_stream_address(stream)
            with source(host=stream_host, port=stream_port, mode=stream_mode) as stream:
                while True:
                    if (self.number_of_records>=0) and (self.current_record >= self.number_of_records):
                        break
                    rec = stream.receive()

                    pulse_id, data, format_changed, global_timestamp, global_timestamp_offset = \
                        rec.data.pulse_id, rec.data.data, rec.data.format_changed, rec.data.global_timestamp, \
                        rec.data.global_timestamp_offset
                    self.add_record(pulse_id, data, format_changed, global_timestamp, global_timestamp_offset)

        finally:
            self.close()

class WriterSender(object):
    def __init__(self, output_file="/dev/null", number_of_records=UNDEFINED_NUMBER_OF_RECORDS,
                       layout = LAYOUT_DEFAULT, save_local_timestamps = LOCALTIME_DEFAULT,
                       change = CHANGE_DEFAULT, attributes={}):
        self.writer = Writer(output_file, number_of_records, layout, save_local_timestamps, change, attributes)
        self.stream=None
        self.shapes = {}

    def open(self, no_client_action=None, no_client_timeout=None):
        pass

    def send(self, data, timestamp, pulse_id):
        bsdata = {}
        shapes = {}
        for key in data.keys():
            val = data[key]
            #if hasattr(val, 'shape'):
            if isinstance(val, numpy.ndarray):
                shapes[key] = val.shape
            bsdata[key] = Value(val,timestamp[0], timestamp[1])
        changed = shapes != self.shapes
        self.shapes = shapes
        self.writer.add_record(pulse_id, bsdata, changed, timestamp[0], timestamp[1])

    def close(self):
        self.writer.close()

def main():
    parser = argparse.ArgumentParser(description='Stream writer')
    parser.add_argument('-s', '--stream', default="tcp://localhost:5555", help="Stream to connect to")
    parser.add_argument('-t', '--type', default="SUB", choices=['SUB', 'PULL'], help="Stream type")
    parser.add_argument('-f', '--filename', default='/dev/null', help="Output file")
    parser.add_argument('-r', '--records', default=UNDEFINED_NUMBER_OF_RECORDS, help="Number of records to write")
    parser.add_argument('-l', '--layout', default='DEFAULT', choices=[LAYOUT_DEFAULT, LAYOUT_FLAT, LAYOUT_BSH5 ], help="File layout")
    parser.add_argument('-e', '--localtime', default=str(LOCALTIME_DEFAULT), choices=['True', 'False'], help="Write channels local timestamps")
    parser.add_argument('-c', '--change', default=CHANGE_DEFAULT, choices=['True', 'False'],
                        help="Support data format change (create new datasets)")
    parser.add_argument('-a', '--attributes', default="{}", help="User attribute dictionary to be written to file")
    parser.add_argument("--log_level", default='INFO',
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'],
                        help="Log level to use.")
    arguments = parser.parse_args()
    logging.basicConfig(level=arguments.log_level)
    writer = Writer(arguments.filename, 10, arguments.layout, arguments.localtime.lower() != "false", \
                    arguments.change.lower() == "true", arguments.attributes)
    writer.start(arguments.stream,SUB)

if __name__ == "__main__":
    main()