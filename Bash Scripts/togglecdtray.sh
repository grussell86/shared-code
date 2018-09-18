#!/bin/bash
#  
#  name: 	togglecdtray.sh - Toggle CD Tray Open/Closed
#  @param	Device to Open/Close - Optional, Default is /dev/sr0
#  @return	Status Code - 0=Success, !0=Failure
#  
#set -x		# Display Detailed Output for Debugging
device=$([ -z "$1" ] && echo "/dev/sr0" || echo "$1") # Device from CLI or default /dev/sr0
eject -T -s "$device" || eject "$device"	# First Command Works if Drive is Empty, Second Works Otherwise
exit $?	# Return Status Code
