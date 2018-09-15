#!/usr/bin/env python

import time,sys

import smbus2 as smbus


# this device has two I2C addresses
DISPLAY_RGB_ADDR = 0x62
DISPLAY_TEXT_ADDR = 0x3e


class i2cLCD(object):
    def __init__(self):
        self.bus = smbus.SMBus(1)

    # set backlight to (R,G,B) (values from 0..255 for each)
    def setRGB(self, r, g, b):
        self.bus.write_byte_data(DISPLAY_RGB_ADDR, 0, 0)
        self.bus.write_byte_data(DISPLAY_RGB_ADDR, 1, 0)
        self.bus.write_byte_data(DISPLAY_RGB_ADDR, 0x08, 0xaa)
        self.bus.write_byte_data(DISPLAY_RGB_ADDR, 4, r)
        self.bus.write_byte_data(DISPLAY_RGB_ADDR, 3, g)
        self.bus.write_byte_data(DISPLAY_RGB_ADDR, 2, b)

    # send command to display (no need for external use)
    def textCommand(self, cmd):
        self.bus.write_byte_data(DISPLAY_TEXT_ADDR, 0x80, cmd)

    # set display text \n for second line(or auto wrap)
    def setText(self, text):
        self.textCommand(0x01) # clear display
        time.sleep(.05)
        self.textCommand(0x08 | 0x04) # display on, no cursor
        self.textCommand(0x28) # 2 lines
        time.sleep(.05)
        count = 0
        row = 0
        for c in text:
            if c == '\n' or count == 16:
                count = 0
                row += 1
                if row == 2:
                    break
                self.textCommand(0xc0)
                if c == '\n':
                    continue
            count += 1
            self.bus.write_byte_data(DISPLAY_TEXT_ADDR, 0x40, ord(c))

    #Update the display without erasing the display
    def setText_norefresh(self, text):
        self.textCommand(0x02) # return home
        time.sleep(.05)
        self.textCommand(0x08 | 0x04) # display on, no cursor
        self.textCommand(0x28) # 2 lines
        time.sleep(.05)
        count = 0
        row = 0
        while len(text) < 32: #clears the rest of the screen
            text += ' '
        for c in text:
            if c == '\n' or count == 16:
                count = 0
                row += 1
                if row == 2:
                    break
                self.textCommand(0xc0)
                if c == '\n':
                    continue
            count += 1
            self.bus.write_byte_data(DISPLAY_TEXT_ADDR,0x40,ord(c))

    # Create a custom character (from array of row patterns)
    def create_char(self, location, pattern):
        """
        Writes a bit pattern to i2cLCD CGRAM

        Arguments:
        location -- integer, one of 8 slots (0-7)
        pattern -- byte array containing the bit pattern, like as found at
                   https://omerk.github.io/lcdchargen/
        """
        location &= 0x07 # Make sure location is 0-7
        self.textCommand(0x40 | (location << 3))
        self.bus.write_i2c_block_data(DISPLAY_TEXT_ADDR, 0x40, pattern)

# example code
if __name__=="__main__":
    lcd = i2cLCD()
    lcd.setText("Hello world\nThis is an i2cLCD test")
    lcd.setRGB(0,128,64)
    time.sleep(2)
    for c in range(0,255):
        lcd.setText_norefresh("Going to sleep in {}...".format(str(c)))
        lcd.setRGB(c,255-c,0)
        time.sleep(0.1)
    lcd.setRGB(0,255,0)
    setText("Bye bye, this should wrap onto next line")
