from pySHT3x import SHT3x

device = SHT3x('ftdi:///1', SHT3x.I2C_ADDR_A)

hum, temp, hum_valid, temp_valid = device.get_measurement_single(SHT3x.SINGLE_REP_HIGH_CS_EN)

print("Hum: "+str(hum)+" Temp: "+str(temp)+ ", Hum_Valid: "+str(hum_valid)+", Temp_Valid: "+str(temp_valid))