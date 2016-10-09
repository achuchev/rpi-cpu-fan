#!/usr/bin/python

from optparse import OptionParser
import os
from time import sleep
import time

import RPi.GPIO as GPIO


GPIO_PIN = 18  # The GPIO PIN ID
CPU_TEMP_FAN_ON = 57  # C - The max temp after which will start the fan
CPU_TEMP_FAN_OFF = 47  # C - Same as above, but will stop the fan
CHECK_INTERVAL_FAN_ON = 10  # Seconds between the checks when the fan is ON
CHECK_INTERVAL_FAN_OFF = 30  # Seconds between the checks when the fan is OFF
MAX_FAN_ON_TIME = 1 * 60 * 60  # Seconds - Maximum time when the fan is ON
MIN_FAN_ON_TIME = 3 * 60  # Seconds - Minimum time when the fan is ON

_FAN_MODE_AUTO = 'auto'
_FAN_MODE_ON = 'on'
_FAN_MODE_OFF = 'off'


def log_msg(msg):
    """
    Logs the messages if the logging is enabled.
    """
    if is_verbose:
        print msg


def get_cpu_temp():
    """
    Gets the CPU temperature in Celsius.
    """
    res = os.popen('vcgencmd measure_temp').readline()
    temp = res.replace('temp=', '').replace('\'C\n', '')
    log_msg('CPU temp: {}'.format(temp))
    return float(temp)


class Fan(object):
    """
    This class Allows you to control the fan.
    """

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GPIO_PIN, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.setwarnings(False)

        self.is_fan_on = False
        self.fan_on_time_max = 0
        self.fan_on_time_min = 0
        self.check_interval = CHECK_INTERVAL_FAN_OFF

    def auto(self):
        current_cpu_temp = get_cpu_temp()
        if not self.is_fan_on and current_cpu_temp > CPU_TEMP_FAN_ON:
            self.on()
        elif self.fan_on_time_max != 0 and self.fan_on_time_max < time.time():
            log_msg('Action: Max fan ON time exceeded. Stopping the fan.')
            self.off()
        elif self.is_fan_on and self.min_fan_on_time <= time.time() and current_cpu_temp <= CPU_TEMP_FAN_OFF:
            self.off()
        else:
            log_msg('Action: No need')
        log_msg('Fan State: {}'.format('ON' if self.is_fan_on else 'OFF'))

    def on(self):
        self._action(True)
        self.max_fan_on_time = time.time() + MAX_FAN_ON_TIME
        self.min_fan_on_time = time.time() + MIN_FAN_ON_TIME
        self.check_interval = CHECK_INTERVAL_FAN_ON

    def off(self):
        self._action(False)
        self.max_fan_on_time = 0
        self.min_fan_on_time = 0
        self.check_interval = CHECK_INTERVAL_FAN_OFF

    def _action(self, is_on):
        GPIO.output(GPIO_PIN, GPIO.LOW if is_on else GPIO.HIGH)
        self.is_fan_on = is_on
        log_msg('Action: Fan state changed to {}'.format(
            'ON' if self.is_fan_on else 'OFF'))

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-a', '--action', dest='action', default=_FAN_MODE_AUTO,
                      help='fan action: ON or OFF')
    parser.add_option("-1", "--run_once",
                      action="store_true", dest="run_once", default=False,
                      help="run once and exit")
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="set to enable the logging")
    (options, args) = parser.parse_args()
    is_verbose = options.verbose
    if options.action in [_FAN_MODE_ON, _FAN_MODE_OFF]:
        # I case in forced Stop or Start we need to set the run once mode
        options.run_once = True
    try:
        action = options.action.lower()
        fan = Fan()
        while True:
            if action == _FAN_MODE_AUTO:
                fan.auto()
            elif action == _FAN_MODE_ON:
                fan.on()
            elif action == _FAN_MODE_OFF:
                fan.off()
            else:
                raise ValueError(
                    'Unrecognized option for Action \'{}\''.format(options.action))

            if options.run_once is True:
                sleep(MIN_FAN_ON_TIME)
                break
            log_msg('')
            sleep(fan.check_interval)
    except KeyboardInterrupt:
        log_msg('CTRL+C keyboard hit. Exiting...')
    finally:
        # resets all GPIO ports used by this program
        GPIO.cleanup()
