from pyftdi.i2c import I2cController, I2cNackError
import crcengine


def check_and_convert(response):
    temp_valid = False
    hum_valid = False

    crc_sensirion = crcengine.create(0x31, 8, 0xFF, ref_in=False, ref_out=False, xor_out=0, name='crc-8-sensirion')
    crc_result_temp = crc_sensirion([response[0], response[1]])
    crc_result_hum = crc_sensirion([response[3], response[4]])

    if crc_result_temp == response[2]:
        temp_valid = True

    if crc_result_hum == response[5]:
        hum_valid = True

    temp_raw = (response[0] << 8) | response[1]
    hum_raw = (response[3] << 8) | response[4]
    temp = -45 + ((175 * temp_raw) / 2 ** 16)
    hum = -49 + ((315 * hum_raw) / 2 ** 16)

    return hum, temp, hum_valid, temp_valid


class SHT3x:
    """
    Class resembling a Sensirion SHT3x sensor and its methods
    """

    I2C_ADDR_A = 0x44
    I2C_ADDR_B = 0x45

    # Commands
    CMD_SOFT_RESET = [0x30, 0xA2]
    CMD_HEATER_ON = [0x30, 0x6D]
    CMD_HEATER_OFF = [0x30, 0x66]
    CMD_ENABLE_ART = [0x2B, 0x32]
    CMD_BREAK_COMMAND = [0x30, 0x93]
    CMD_FETCH = [0xE0, 0x00]
    GET_STATUS = [0x30, 0x41]

    # Single Shot
    SINGLE_REP_HIGH_CS_EN = [0x2c, 0x06]
    SINGLE_REP_MID_CS_EN = [0x2c, 0x0D]
    SINGLE_REP_LOW_CS_EN = [0x2c, 0x10]

    SINGLE_GROUP = [SINGLE_REP_HIGH_CS_EN, SINGLE_REP_MID_CS_EN, SINGLE_REP_LOW_CS_EN]

    # Periodic measurement
    PERIODIC_05MPS_REP_HIGH = [0x20, 0x32]
    PERIODIC_05MPS_REP_MED = [0x20, 0x24]
    PERIODIC_05MPS_REP_LOW = [0x20, 0x2F]

    PERIODIC_1MPS_REP_HIGH = [0x21, 0x30]
    PERIODIC_1MPS_REP_MED = [0x21, 0x26]
    PERIODIC_1MPS_REP_LOW = [0x21, 0x2D]

    PERIODIC_2MPS_REP_HIGH = [0x22, 0x36]
    PERIODIC_2MPS_REP_MED = [0x22, 0x20]
    PERIODIC_2MPS_REP_LOW = [0x22, 0x2B]

    PERIODIC_4MPS_REP_HIGH = [0x23, 0x34]
    PERIODIC_4MPS_REP_MED = [0x23, 0x22]
    PERIODIC_4MPS_REP_LOW = [0x23, 0x29]

    PERIODIC_10MPS_REP_HIGH = [0x27, 0x37]
    PERIODIC_10MPS_REP_MED = [0x27, 0x21]
    PERIODIC_10MPS_REP_LOW = [0x27, 0x2A]

    PERIODIC_GROUP = [PERIODIC_05MPS_REP_HIGH, PERIODIC_05MPS_REP_MED, PERIODIC_05MPS_REP_LOW, PERIODIC_1MPS_REP_HIGH,
                      PERIODIC_1MPS_REP_MED, PERIODIC_1MPS_REP_LOW, PERIODIC_2MPS_REP_HIGH, PERIODIC_2MPS_REP_MED,
                      PERIODIC_2MPS_REP_LOW, PERIODIC_4MPS_REP_HIGH, PERIODIC_4MPS_REP_MED, PERIODIC_4MPS_REP_LOW,
                      PERIODIC_10MPS_REP_HIGH, PERIODIC_10MPS_REP_MED, PERIODIC_10MPS_REP_LOW, CMD_ENABLE_ART]

    def __init__(self, ftdi_uri, i2c_addr):
        self.running = False
        self.mode = None
        self.i2c_addr = i2c_addr
        self.i2c = I2cController()
        self.i2c.configure(ftdi_uri)

    def get_measurement_single(self, mode):
        """
        Executes a single shot measurement using the clock stretching mode.

        :param mode: Single shot measurement mode (SINGLE_REP_HIGH_CS_EN, SINGLE_REP_MID_CS_EN, SINGLE_REP_LOW_CS_EN)
        :type mode: list
        :return: returns humidity, temperature, hum_data_valid, temp_data_valid
        :rtype: list
        """
        if mode not in self.SINGLE_GROUP:
            raise ValueError("Wrong Parameter for single shot read!")

        self.mode = mode

        response = self.i2c.exchange(self.i2c_addr, mode, 6)

        return check_and_convert(response)

    def cmd_soft_reset(self):
        # We need to send a break first. Otherwise, our SOFT_RESET is getting NACK'ed
        self.cmd_break()
        self.i2c.write(self.i2c_addr, self.CMD_SOFT_RESET)
        self.mode = None

    def cmd_enable_heater(self, state):
        """
        Enables (True) or disables (False) the sensor heat plate. Can be used for testing the sensor

        :param state: True or False for Enabling or disabling the sensor
        :type state: bool
        """
        if state:
            self.i2c.write(self.i2c_addr, self.CMD_HEATER_ON)
        else:
            self.i2c.write(self.i2c_addr, self.CMD_HEATER_OFF)

    def cmd_enable_art(self):
        self.i2c.write(self.i2c_addr, self.CMD_ENABLE_ART)

    def get_status(self):
        self.i2c.write(self.i2c_addr, self.GET_STATUS)
        response = self.i2c.read(self.i2c_addr, 2)
        return (response[0] << 8) | response[1]

    def cmd_break(self):
        """
        Stops the periodic measurement mode and read loop
        """
        self.running = False
        self.i2c.write(self.i2c_addr, self.CMD_BREAK_COMMAND)

    def cmd_set_periodic(self, mode):
        if mode not in self.PERIODIC_GROUP:
            raise ValueError("Wrong Parameter for perodic read!")

        self.mode = mode
        self.i2c.write(self.i2c_addr, mode)

    def get_measurement_periodic(self, callback):
        """
        Handles the readout of the periodic sensors readings and calls a callback function containing the values.

        :param callback: Callback routine to bring the temperature and humidity to your application
        :type callback: function
        """
        if self.mode is None:
            raise ValueError("You need to set a mode otherwise periodic reading will not work")

        if self.mode not in self.PERIODIC_GROUP:
            raise ValueError("Wrong mode set for fetch command")

        self.running = True

        while self.running:
            try:
                response = self.i2c.exchange(self.i2c_addr, self.CMD_FETCH, 6)
                hum, temp, hum_valid, temp_valid = check_and_convert(response)
                callback(hum, temp, hum_valid, temp_valid)
            except I2cNackError:
                # NACK: No fresh data available
                continue
