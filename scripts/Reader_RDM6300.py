"""
Support for the RDM6300 serial RFID module

1.) Connect the RDM6300 module
------------------------------
Connect the RDM6300 module to the serial GPIO pins 14 and 15.

2.) Enable GPIO serial port
---------------------------
Edit the /boot/config.txt (sudo nano /boot/config.txt) and add the following line:
    enable_uart=1

3.) Install dependecies
-----------------------
Be aware not to install the "serial" module, install "pyserial" instead:
    pip install pyserial

4.) Replace the default Reader.py
---------------------------------
Replace the Reader.py file with the Reader_RDM6300.py:
mv Reader.py Reader_default.py; mv Reader_RDM6300.py Reader.py
"""

import serial
import string
import atexit
from datetime import datetime, timedelta


class Reader:
    def __init__(self):
        device = '/dev/ttyS0'
        baudrate = 9600
        ser_timeout = 0.1
        self.last_card_id = ''
        self.retrigger_list = []    # UUIDs in this list are allowed for multi-triggering
        self.retrigger_interval = 1500  # minimal interval for re-triggering the same UUID in milliseconds
        self.next_trigger = datetime.now() + timedelta(milliseconds=self.retrigger_interval)
        atexit.register(self.cleanup)
        try:
            self.rfid_serial = serial.Serial(device, baudrate, timeout=ser_timeout)
        except serial.SerialException as e:
            print(e)
            exit(1)

    def readCard(self):
        byte_card_id = b''

        try:
            while True:
                try:
                    read_byte = self.rfid_serial.read()

                    if read_byte == b'\x02':  # start byte
                        while read_byte != b'\x03':  # end bye
                            read_byte = self.rfid_serial.read()
                            byte_card_id += read_byte

                        card_id = byte_card_id.decode('utf-8')
                        byte_card_id = ''
                        card_id = ''.join(x for x in card_id if x in string.printable)

                        # Only return UUIDs with correct length
                        if len(card_id) == 12 and \
                            (card_id != self.last_card_id or  # An other UUID as last time
                             # Same UUID but re-trigger interval is ok
                             (card_id in self.retrigger_list and self.next_trigger < datetime.now())):
                                self.next_trigger = datetime.now() + timedelta(milliseconds=self.retrigger_interval)
                                self.last_card_id = card_id
                                self.rfid_serial.reset_input_buffer()
                                return self.last_card_id

                        else:  # wrong UUID length or aleady send that UUID last time
                            self.rfid_serial.reset_input_buffer()

                except ValueError as ve:
                    print(ve)

        except serial.SerialException as se:
            print(se)

    def check_retrigger(self, uuid):
        if uuid in self.retrigger_list and \
                datetime.now() > self.next_trigger:
                    datetime.now() + timedelta(milliseconds=self.retrigger_interval)
                    return True
        else:
            return False

    def cleanup(self):
        self.rfid_serial.close()
