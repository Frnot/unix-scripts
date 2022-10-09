#!/usr/bin/env python3

version="1.0"

# control the idrac fans automatically using a PID controller
# in its finaly state, this program will hopefully be implemented in c++

# This script requires ipmitool
# dnf/apt install ipmitool
# Create the following system file
# enable it with: systemctl enable --now idracfancontrol.service

#### /etc/systemd/system/idracfancontrol.service ###
#
# [Unit]
# Description=iDRAC fan control system
#
# [Service]
# Type=simple
# ExecStart=/usr/bin/idracfancontrol.py
# Restart=always
#
# [Install]
# WantedBy=multi-user.target
#
####################################################

import subprocess
import time
from shutil import which


# tuning parameters
target_tdelta = 50  # degrees
Kp = 2
Ki = 0.01
Kd = 5

idrac_control = False

def main():
    if which("ipmitool") is None:
        print("Error: you need to have ipmitool installed")
        print("dnf/apt install ipmitool")
        return

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


def set_fan_speed(speed):
    execute(f"ipmitool raw 0x30 0x30 0x02 0xff {hex(speed)}")


def get_fan_speed():
    rawstring = execute("ipmitool sdr type fan")
    stringlines = [line for line in rawstring.split('\n') if line and not line.startswith("Fan Redundancy")]
    fan_avg = 0
    for line in stringlines:
        speed = int(line.split("|")[4].strip().split(" ")[0])
        fan_avg += speed
    fan_avg /= len(stringlines)
    return fan_avg


def get_temps():
    rawstring = execute("ipmitool sdr type temperature")

    stringlines = [line for line in rawstring.split('\n') if line]

    ambient = stringlines[0].split("|")[4].strip().split(" ")[0]
    if ambient == "No":
        print("bad data from ipmi!!!")
        print(rawstring)
        return None
    cpu = 0
    for line in stringlines[1:]:
        temp = line.split("|")[4].strip().split(" ")[0]
        if temp == "No":
            print("bad data from ipmi!!!!")
            print(rawstring)
            return None
        cpu += int(temp)
    cpu /= len(stringlines[1:])

    return int(ambient), int(cpu)


def idrac_handoff(cpu_temp):
    global idrac_control
    if cpu_temp > 90:
        if not idrac_control:
            print("Temperature overlimit! releasing fan control to idrac")
            execute("ipmitool raw 0x30 0x30 0x01 0x01")
            idrac_control = True
    else:
        if idrac_control:
            print("Temperature in acceptable range. taking fan control from idrac")
            execute("ipmitool raw 0x30 0x30 0x01 0x00")
            idrac_control = False
    return idrac_control


def execute(command):
    cmdarr = command.split()
    result = subprocess.run(cmdarr, text=True, capture_output=True)
    return result.stdout


if __name__ == "__main__":
    main()
