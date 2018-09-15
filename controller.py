
import hashlib
import json
import logging
import requests
import sys
import time
import uuid

from pyfingerprint import PyFingerprint
from i2c_lcd import i2cLCD as LCD

API_BASE = "http://52.186.120.229"
API_REGISTER_DEVICE = "%s/register_device" % API_BASE
API_SELF_STATE = "%s/self_state" % API_BASE
API_UPDATE_SELF_STATE = "%s/update_self_state" % API_BASE
SERIAL_DEVICE = "/dev/serial0"
ID_TOKEN = uuid.uuid4().hex


class FingerprintController(object):
    def __init__(self):
        self.sensor = None
        self.lcd = None
        self.cur_state = None

    def connect(self, dev):
        logging.info("Attempting to open serial device %s", dev)
        self.sensor = PyFingerprint(dev, 57600, 0xFFFFFFFF, 0x00000000)
        if not self.sensor.verifyPassword():
            raise ValueError('The given fingerprint sensor password is wrong!')
        logging.info("Serial device opened")
        logging.info("Currently used templates: %s/%s" %
                        (self.sensor.getTemplateCount(),
                         self.sensor.getStorageCapacity()))

        self.lcd = LCD()

        self.send_update_packet({"status": "idle"})

    def send_update_packet(self, data):
        logging.info("=> %s" % data)
        resp = requests.post(url=API_UPDATE_SELF_STATE, data={
            "token": ID_TOKEN,
            "state": json.dumps(data),
        })
        logging.info("  <= %s", resp.json())

    def request_mode(self):
        try:
            logging.info("Requesting state...")
            data = requests.post(url=API_SELF_STATE, data={
                "token": ID_TOKEN,
            }, timeout=10)
            logging.info("Received response: %s", data)
            data = data.json()
            return data['state']
        except KeyboardInterrupt:
            sys.exit(0)
        except:
            logging.exception("Failed requesting state, idling...")
            return 'idle'

    def loop_forever(self):
        funcs = {
            'enroll': self.state_enroll,
            'auth': self.state_auth,
            'idle': self.state_idle,
        }

        while True:    
            mode = self.request_mode()
            action = funcs.get(mode, None)
 
            if not action:
                logging.warning("Ignoring invalid mode from server: %s", mode)
                self.state_idle()
                continue
 
            logging.info("Performing action '%s'", mode)

            try:
                action()
                if mode != 'idle':
                    time.sleep(5)
            except Exception as ex:
                self.send_update_packet({"status": "general_error",
                                         "message": ex.message})

    def state_idle(self):
        self.lcd.setText("Waiting...")
        self.lcd.setRGB(255, 150, 0)

        time.sleep(1)

    def state_enroll(self):
        self.send_update_packet({"status": "enroll_wait"})

        self.lcd.setRGB(0, 255, 0)
        self.lcd.setText("Place finger on the sensor.")

        while not self.sensor.readImage():
            pass

        self.sensor.convertImage(0x01)

        result = self.sensor.searchTemplate()
        position_num = result[0]

        if position_num >= 0:
            self.send_update_packet({"status": "enroll_fail",
                                     "reason": "Fingerprint already enrolled."})
            return

        self.lcd.setText("Lift finger off the sensor.")

        self.send_update_packet({"status": "enroll_lift"})
        time.sleep(2)

        self.lcd.setText("Place your\nfinger again.")

        self.send_update_packet({"status": "enroll_wait2"})

        while not self.sensor.readImage():
            pass

        self.sensor.convertImage(0x02)

        if not self.sensor.compareCharacteristics():
            self.lcd.setRGB(255, 0, 0)
            self.lcd.setText("Fingerprints do not match.")
            self.send_update_packet({"status": "enroll_fail",
                                     "reason": "Fingerprints do not match."})
            return

        self.sensor.createTemplate()
        characteristics = self.sensor.downloadCharacteristics(0x01)
        hash = hashlib.sha256(str(characteristics).encode('utf-8')).hexdigest()

        position_num = self.sensor.storeTemplate()

        self.lcd.setText("Fingerprint added!")
        self.send_update_packet({"status": "enroll_success", "hash": hash})

    def state_auth(self):
        self.send_update_packet({"status": "auth_wait"})

        self.lcd.setRGB(0, 255, 0)
        self.lcd.setText("Place finger on the sensor.")

        while not self.sensor.readImage():
            pass

        self.sensor.convertImage(0x01)

        result = self.sensor.searchTemplate()

        position_num = result[0]
        accuracy = result[1]

        if position_num == -1:
            self.lcd.setRGB(255, 0, 0)
            self.lcd.setText("Unknown\nfingerprint!")
            self.send_update_packet({"status": "auth_fail",
                                     "reason": "Unknown fingerprint!"})
            return

        self.lcd.setText("Successfully\nauthenticated!")
        logging.info("Found template at position #%d, score %d", position_num, accuracy)
        self.send_update_packet({"status": "auth_success"})


logging.basicConfig(level=logging.INFO)
controller = FingerprintController()
controller.connect(SERIAL_DEVICE)
controller.loop_forever()
