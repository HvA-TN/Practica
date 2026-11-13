from machine import Pin, I2C

i2c = I2C(
    0,
    sda=Pin(20),
    scl=Pin(21),
    freq=100000
)

# Fabrikant-ID van INA226 uitlezen
try:
    data = i2c.readfrom_mem(0x40, 0xFE, 2)
    print("Fabrikant-ID:", data.hex())
except OSError as fout:
    print("I2C-fout:", fout)