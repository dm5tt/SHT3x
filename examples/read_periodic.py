import time
from threading import Thread
from pySHT3x import SHT3x


def callback(hum, temp, hum_valid, temp_valid):
    print("Hum: " + str(hum) + " Temp: " + str(temp) + ", Hum_Valid: " + str(hum_valid) + ", Temp_Valid: " + str(temp_valid))


device = SHT3x('ftdi:///1', SHT3x.I2C_ADDR_A)
device.cmd_set_periodic(SHT3x.PERIODIC_05MPS_REP_HIGH)

thread = Thread(target=device.get_measurement_periodic, args=(callback,))
thread.start()

time.sleep(3)

device.cmd_soft_reset()
