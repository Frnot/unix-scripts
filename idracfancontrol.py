#!/usr/bin/env python3

version="1.4"

# control the idrac fans automatically using a PID controller

# This script requires ipmitool
# dnf/apt install ipmitool
# Create the following system file
# enable it with: systemctl enable --now idracfancontrol.service

#### /etc/systemd/system/idracfancontrol.service ###
"""
[Unit]
Description=iDRAC fan control system

[Service]
Type=simple
ExecStart=/usr/bin/idracfancontrol.py
Restart=always
KillSignal=SIGINT
TimeoutStopSec=3

[Install]
WantedBy=multi-user.target
"""
####################################################

import atexit
import re
import subprocess
import time
from shutil import which

# tuning parameters
target_tdelta = 30  # degrees
Kp = 2
Ki = 0.01
Kd = 5

idrac_has_control = False

fan_regex = re.compile(r"fan\d", flags=re.IGNORECASE)

def main():
    if which("ipmitool") is None:
        print("Error: you need to have ipmitool installed")
        print("dnf/apt install ipmitool")
        return

    atexit.register(exit)

    # Take fan cotnrol from idrac
    execute("ipmitool raw 0x30 0x30 0x01 0x00")

    try:
        last_sample_time = time.time()
        while True:
            time.sleep(1)

            if (temps := get_temps()) is None:
                continue

            t_ambient, t_cpu = temps
            sample_time = time.time()

            if idrac_handoff(t_cpu):
                continue

            elapsed_time = sample_time - last_sample_time
            last_sample_time = sample_time

            tdelta = t_cpu - t_ambient
            error = tdelta - target_tdelta

            P = calculate_P(error)
            I = calculate_I(error, elapsed_time)
            D = calculate_D(error, elapsed_time)

            control = int(P + I - D)

            if control > 100:
                control = 100
            if control < 0:
                control = 0

            set_fan_speed(control)

            fanspeed = get_fan_speed()

            print(f"Ambient temp: '{t_ambient}' | CPU avg: '{t_cpu}'")
            print(f"T_delta: {tdelta}")
            print(f"Error: {error}")
            print(f"P: {P}")
            print(f"I: {I}")
            print(f"D: {D}")
            print(f"Control: {control}")
            print(f"Fan avg: {fanspeed}")

    except KeyboardInterrupt:
        return


def calculate_P(error):
    return error * Kp


total = 10/Ki
def calculate_I(error, elapsed_time):
    global total
    total += error * elapsed_time
    if total*Ki > 50:
        total = 50/Ki
    elif total*Ki < 0:
        total = 0

    return total*Ki


previous_error = 0
previous_diff_error = 0
time_since_previous_error = 0
def calculate_D(error, elapsed_time):
    global previous_error
    global previous_diff_error
    global time_since_previous_error

    if error == previous_error:
        time_since_previous_error += elapsed_time
    else: # error != previous_error
        previous_diff_error = previous_error
        time_since_previous_error = elapsed_time

    rate_error = (error - previous_diff_error) / time_since_previous_error
    previous_error = error

    return Kd*rate_error


last_speed = 0
def set_fan_speed(speed):
    global last_speed
    if speed != last_speed:
        execute(f"ipmitool raw 0x30 0x30 0x02 0xff {hex(speed)}")
    last_speed = speed


def get_fan_speed():
    rawstring = execute("ipmitool sdr type fan")
    speeds = [int(line.split("|")[4].strip().split(" ")[0]) for line in rawstring.split('\n') if line and fan_regex.match(line) and "Disabled" not in line]
    fan_avg = sum(speeds) / len(speeds)
    return fan_avg


def get_temps():
    rawstring = execute("ipmitool sdr type temperature")

    stringlines = [line for line in rawstring.split('\n') if line]

    ambient = []
    cpu = []
    for line in stringlines:
        temp = line.split("|")[4].strip().split(" ")[0]
        if temp == "No":
            print("bad data from ipmi!!!!")
            print(rawstring)
            return None
        if temp == "Disabled":
            continue
        if "inlet" in line.lower():
            ambient.append(int(temp))
        else: # "inlet" not in line
            cpu.append(int(temp))

    ambient = sum(ambient) / len(ambient)
    cpu = sum(cpu) / len(cpu)

    return int(ambient), int(cpu)


def idrac_handoff(cpu_temp):
    global idrac_has_control
    if cpu_temp > 90:
        if not idrac_has_control:
            print("Temperature overlimit! releasing fan control to idrac")
            execute("ipmitool raw 0x30 0x30 0x01 0x01")
            idrac_has_control = True
    else:
        if idrac_has_control:
            print("Temperature in acceptable range. taking fan control from idrac")
            execute("ipmitool raw 0x30 0x30 0x01 0x00")
            idrac_has_control = False
    return idrac_has_control


def execute(command):
    cmdarr = command.split()
    result = subprocess.run(cmdarr, text=True, capture_output=True)
    return result.stdout


def exit():
    # Return control to idrac so system doesn't overheat during soft reboots
    execute("ipmitool raw 0x30 0x30 0x01 0x01")


if __name__ == "__main__":
    main()
