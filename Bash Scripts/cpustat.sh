#! /bin/bash
# cpustatus
#
# Prints the current state of the CPU like temperature, voltage and speed.
# The temperature is reported in degrees Celsius (C) while
# the CPU speed is calculated in megahertz (MHz).

function convert_to_MHz {
    let value=$1/1000
    echo "$value" | awk '{printf "%4s MHz", $1}'
}

function convert_to_GHz {
    let value=$1
    echo "scale=2;$value/1000/1000" | bc | awk '{printf "%4s GHz", $1}'
}

temp=$(sensors | grep -E "CPU Temperature|Core 0" | tr '°' ' ' | awk '{print $3,$4}' | sed -e 's/+//g' -e 's/ /°/')

volts=$(sensors | grep "Vcore Voltage" | awk '{print $3}' | sed 's/+//g' | awk '{printf "%s V", $1}')
if [ -z "$volts" ]; then
    volts=$(sudo dmidecode --type processor | grep Voltage | cut -d':' -f2)
fi

minFreq=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_min_freq)
minFreq=$(convert_to_GHz "$minFreq")

maxFreq=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq)
maxFreq=$(convert_to_GHz "$maxFreq")

freq=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq)
freq=$(convert_to_GHz "$freq")

governor=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)

echo "Temperature:   $temp"
echo "Voltage:       $volts"
echo "Min speed:     $minFreq"
echo "Max speed:     $maxFreq"
echo "Current speed: $freq"
echo "Governor:      $governor"

exit 0
