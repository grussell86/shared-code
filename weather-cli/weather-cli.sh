#! /bin/bash
#
### Script to Extract Weather Data from NOAA Web Site
###	and Astronomy Data from US Naval Observatory
#
set +e # Suspend Error Trapping
# Configuration Defaults
program=$(echo "$0" | sed 's|.*/||' | cut -d'.' -f1)	# Name of Current Program
config_dir="$HOME/.config/$program"						# Configuration File Location
config_file="$config_dir/$program.config"				# Configuration File Name
refresh_interval=1700									# Number of Seconds to Cache Data
max_trys=5												# Maximum Number of Trys to Get a Non-Empty Value from Cache
metar="KIMS"											# Default Location (Madison Municipal Airport, IN)
result=""												# Initialize Return Value
# Read Configuration Information from Config File
if [ -f "$config_file" ]; then
	while read -r line
	do
		if [[ ! -z $(echo "$line" | cut -d'=' -f2) ]]; then
			eval "$line"
		fi
	done < "$config_file"
else
	# Create a Default Config File
	mkdir -p "$config_dir"
	echo -e "metar=$metar" > "$config_file"
fi
# Set METAR icao id from Command line and Update Config File
if [ "$1" == '--metar' ] || [ "$1" == '-m' ]; then
	metar="$2"
	sed -i "s/metar=.*/metar=$metar/" "$config_file"
fi
# Cached Data Files
cache_dir="/tmp/$program/$USER/$metar"					# Cached Files Location
conditions="$cache_dir/conditions.xml"					# Cached Conditions File
forecast="$cache_dir/forecast.xml"						# Cached Forecast File
alerts="$cache_dir/alerts.txt"							# Cached Alerts File
astronomy="$cache_dir/astronomy.txt"					# Cached Astronomy File
#
# Convert Fahrenheit to Celsius
function f_to_c {
	echo $(( ($1 - 32) * 5 / 9 ))
}
# Format Temperature Units
function fmt_temp {
	unit=${2:- }
	na=${3:-N/A}
	echo "$1" | sed -e "s/\.0//g" -e "/.*[0-9]/ s/$/°$unit/" -e "s|^$|$na|"
}
# Generate a Weather Icon Using the ConkyWeather font
function get_weather_icon {
	result=$(echo "$1" | sed -e 's/A Few Clouds/b/g' -e 's|Rain/Snow|x|g' -e 's|Drizzle/Snow|x|g' -e 's|Drizzle/Flurries|x|g' -e 's|Rain/Ice|y|g' -e 's|Rain/Freezing Rain|y|g' -e 's|Drizzle/Freezing Drizzle|y|g' -e 's/Slight Chance Showers/g/' -e 's/Slight Chance Rain/g/' -e 's/Scattered Snow Showers/q/' -e 's/Scattered Showers/g/' -e 's/Clouds.*/0/g')
	result=$(echo "$result" | sed -e 's/Areas//g' -e 's/Light//g' -e 's/Heavy//g' -e 's/Blowing//g' -e 's/Drifting//g' -e 's/Low//g' -e 's/Small//g' -e 's/Mist//g' -e 's/Pellets//g' -e 's/Grains//g' -e 's/Crystals//g' -e 's/Patches of//g' -e 's/Patches//g' -e 's/Patchy//g' -e 's/Frost then//g' -e 's/Dense//g' -e 's/Likely//g' -e 's/Shallow//g' -e 's/Slight//g' -e 's/Chance//g' -e 's/Isolated//g' -e 's/Increasing//g' -e 's/Decreasing//g' -e 's/Severe//g' -e 's/Scattered//g' -e 's/in Vicinity.*//g' -e 's/ of //g' -e 's/then.*//' -e 's/with.*//' -e 's/and.*//')
	result=$(echo "$result" | sed 's/^[ \t]*//;s/[ \t]*$//') # Trim Leading/Trailing Spaces
	result=$(echo "$result" | sed -e 's/Gradual Clearing/g/g' -e 's/Mostly Clear/b/g' -e 's/Mostly Sunny/b/g' -e 's/Becoming Sunny/b/g' -e 's/Partly Sunny/d/g' -e 's/Sunny/a/g'  -e 's/Partly Cloudy/c/g' -e 's/Mostly Cloudy/d/g' -e 's/Clear/a/g' -e 's/Fair/a/g' -e 's/Overcast/f/g' -e 's/Cloudy/f/g' -e 's/Sprinkles/g/' -e 's/Drizzle/h/g' -e 's/Rain Ice/y/g' -e 's/Rain.*/i/g' -e 's/Showers.*/i/g' -e 's/^Thunderstorms.*/n/g' -e 's/Thunderstorm/m/g' -e 's/T-storms/m/g' -e 's/Wintry Mix/x/g')
	result=$(echo "$result" | sed -e 's/^Ice.*/u/g' -e 's/^Snow.*/r/g' -e 's/^Hail.*/u/g' -e 's/^Freezing.*/v/g' -e 's/Funnel Cloud/1/g' -e 's/Tornado/1/g' -e 's/Tropical Storm.*/2/g' -e 's/Hurricane.*/3/g' -e 's/Fog.*/9/g' -e 's/^Windy.*/6/g' -e 's/^Breezy.*/6/g' -e 's/Haze/9/g' -e 's/Dust/7/g' -e 's/Smoke/4/g' -e 's/Sand/7/g' -e 's/Hot/5/g' -e 's/Cold/a/g' -e 's/Flurries/p/g')
	echo "${result:--}" # Hyphen Character Displays N/A Icon for Null Result
}
# Return the User Specified Item from the Conditions Cache File
function get_conditions_item {
	result=""
	# Loop Until the Cache File is Complete Up to 15 Seconds
	trys=0
	while ! egrep -q "</current_observation>|</html>" "$conditions"
	do
		if [ $trys -gt 15 ]; then
			echo "CCNA" # Invalid Conditions Cache
			return
		fi
		trys=$(( trys + 1 ))
		sleep 1
	done
	# Display All Conditions Items Formatted for Easy Reading
	if [ "$1" == "conditions_all" ]; then
		egrep -v "^<|xml|xsi:|image>" "$conditions" | sed -e 's|</.*||g' -e 's|<||g' -e 's|>|: |g' -e 's/^[ \t]*//;s/[ \t]*$//'
		return
	fi
	# Try Up to $max_trys Times to Get a Valid Result
	trys=0
	while [ $trys -lt $max_trys ]
	do
		result=$(grep -i "<$1>" "$conditions" | cut -d'>' -f2 | cut -d'<' -f1)
		if [ ! -z "$result" ]; then
			break
		fi
		trys=$(( trys + 1 ))
		sleep 1
	done
	#
	echo "$result"
}
# Return the User Specified Item from the Forecast Cache File
function get_forecast_item {
	# Initialize Arrays and Result
	times=0; lows=0; highs=0; details=0; precips=0; hazards=0; detailed_forecasts=0
	result=""
	# Loop Until the Cache File is Complete Up to 15 Seconds
	trys=0
	while ! egrep -q "</dwml>|</html>" "$forecast"
	do
		if [ $trys -gt 15 ]; then
			echo "FCNA" # Invalid Forecast Cache
			return
		fi
		trys=$(( trys + 1 ))
		sleep 1
	done
	# Convert Holidays to a Day of the Week
	if egrep -q "Independence|Labor|Memorial|Thanksgiving|Christmas|New Year's|M.L.King|Washington's Birthday|President's" "$forecast"; then
		july4=$(date --date="$(date +%Y)-7-4" +%A); christmas=$(date --date="$(date +%Y)-12-25" +%A); newyear=$(date --date="$(( $(date +%Y) + 1 ))-1-1" +%A)
		sed -i -e "s|Independence|$july4|g" -e 's/Labor/Monday/g' -e 's/Memorial/Monday/g' -e 's/M.L.King/Monday/g' -e "s/President's/Monday/g" -e "s/Washington's Birthday/Monday/g" -e 's/Thanksgiving/Thursday/g' -e "s|Christmas|$christmas|g" -e "s|New Year's|$newyear|g" -e 's/ Day//g' "$forecast"
	fi
	# Try Up to $max_trys Times to Get a Valid Time Layout
	time_layout=""
	trys=0
	while [ -z "$time_layout" ] && [ $trys -lt $max_trys ]
	do
		time_layout=$(grep -A1 "k-p12h-n" "$forecast" | head -1 | cut -d'>' -f2 | cut -d'<' -f1)
		trys=$(( trys + 1 ))
	done
	if [ -z "$time_layout" ]; then
		echo "Invalid Time Layout"
		return
	fi
	num=$(echo "$time_layout" | cut -d'-' -f3 | sed 's/n//g')
	readarray times < <(grep -A"$num" "<layout-key>$time_layout</layout-key>" "$forecast" | tail -"$num" | cut -d'"' -f2)
	times_len=${#times[@]}
	ndx=-1
	# Test for Numeric Day Offset
	if [ ! -z "$(echo "$2" | tr -d '0-9' | tr -d '\n')" ]; then
		#Invalid Day Format
		echo "Invalid Day Offset: $2"
		return
	fi
	day="${2:-0}"
	if [[ $day -gt 7 ]]; then
		echo ""
		return
	fi
	if [[ $day -eq 0 ]]; then
		ndx=1
	else
		day=$(date -d "$day days" +%A) # Convert Numeric Day Offset to Day of the Week
		for (( i=1; i<times_len+1; i++ )); do
			test=$(echo "${times[$i-1]}" | grep -v -i "night" | cut -d' ' -f1 | grep -i "$day")
			if [ ! -z "$test" ]; then
				ndx=$i
				break
			fi
		done
	fi
	#
	if [ $ndx -gt -1 ]; then
		item=$(echo "$1" | tr '[:upper:]' '[:lower:]') # Convert $1 to Lower Case
		case "$item" in
			conditions|forecast_all|forecast_all_f|forecast_all_c)
				readarray forecasts < <(grep -A$((num + 1)) "<weather time-layout=\"$time_layout\"" "$forecast" | tail -"$num" | cut -d'=' -f2 | sed -e 's/\/>//g' -e 's/\"//g')
				if [ "$item" != "conditions" ]; then
					hndx=0
					lndx=0
					temp_units="F"
					readarray details < <(get_forecast_item 'details')
					readarray highs < <(get_forecast_item 'highs')
					readarray lows < <(get_forecast_item 'lows')
					readarray precips < <(get_forecast_item 'precips')
					for (( i=0; i<times_len; i++ )); do
						if [ "${times[$i]: -5:4}" == "ight" ]; then
							temp=${lows[$lndx]::-1}
							lndx=$(( (lndx + 1) ))
							hl="L"
						else
							temp=${highs[$hndx]::-1}
							hndx=$(( (hndx + 1) ))
							hl="H"
						fi
						if [ "${item: -1}" == "c" ]; then
							temp=$(f_to_c "$temp")
							temp_units="C"
						fi
						if [ -z "$temp" ]; then
							temp='--'
						fi
						if [[ "${forecasts[$i]::-1}" == "Cold" ]]; then
							forecasts[$i]=$(echo "${details[$i]::-1}" | sed -e 's/,.*//g' -e 's/\..*//g' -e 's/^[ \t]*//;s/[ \t]*$//' -e 's/[^ ]\+/\L\u&/g' -e 's/And/and/g' -e 's/With/with/g' -e 's/Then/then/g' -e 's/In/in/g' -e 's/Of/of/g' -e 's|$|\n|')
						fi
						result=$result$(printf "%15s: (%1s) %-35s  %1s: %4s°%1s  CoP:%5s%s" "${times[$i]::-1}" "$(get_weather_icon "${forecasts[$i]::-1}")" "$(echo -n "${forecasts[$i]}" | fold -sw 35 | head -1)" "$hl" "$temp" "$temp_units" "${precips[$i]::-1}" "\n")
						if [[ ${#forecasts[$i]} -gt 36 ]]; then # Display Extra Lines of Forecast
							result="$result$(echo "${forecasts[$i]::-1}" | fold -sw 35 | tail -n +2 | sed 's|^|                     |g')\n"
						fi
					done
					result="${result::-2}" # Remove Trailing Newline
				else
					result=${forecasts[$ndx-1]::-1}
				fi
				if [[ "$result" == "Cold" ]]; then
					result=$(get_forecast_item 'detailed_forecast' "$2" | head -2 | tail -1 | sed -e 's/,.*//g' -e 's/\..*//g' -e 's/^[ \t]*//;s/[ \t]*$//' -e 's/[^ ]\+/\L\u&/g' -e 's/And/and/g' -e 's/With/with/g' -e 's/Then/then/g' -e 's/In/in/g' -e 's/Of/of/g')
				fi
				;;
			detailed_forecast|detailed_forecast_all|details)
				readarray detailed_forecasts < <(grep -A$((num + 1)) "<wordedForecast time-layout=\"$time_layout\"" "$forecast" | tail -"$num" | cut -d'>' -f2 | cut -d'<' -f1)
				if [ "${item: -3}" == "all" ]; then
					for (( i=0; i<times_len; i++ )); do
						result="$result${times[$i]}$(echo -n "${detailed_forecasts[$i]}" | fold -sw 75 | sed 's|^|  |')\n" # Show Detailed Forecast Offset 2 Spaces
					done
				else
					result="${times[$ndx-1]}$(echo ${detailed_forecasts[$ndx-1]} | fold -sw 75 | sed 's|^|  |')\n"
					if [ "${times[$ndx-1]::-1}" != "Tonight" ] && [ $ndx -lt $times_len ]; then
						result="$result${times[$ndx]}$(echo "${detailed_forecasts[$ndx]}" | fold -sw 75 | sed 's|^|  |')\n" # Show Detailed Forecast Offset 2 Spaces
					fi
				fi
				result="${result::-2}" # Remove Trailing Newline
				if [ "${item: -1}" == "s" ]; then
					result=${detailed_forecasts[*]} # Return Array
				fi
				;;
			high|high_f|high_c|highs)
				readarray highs < <(grep -A8 "Daily Maximum Temperature" "$forecast" | tail -8 | grep -v "temperature" | cut -d'>' -f2 | cut -d'<' -f1)
				if [ "${times[0]::-1}" == "Tonight" ] && [[ "$day" == "0" ]]; then
						result=""
				else
					ndx=$(( (ndx - 1) / 2 ))
					result=${highs[$ndx]::-1}
				fi
				if [ "${item: -1}" == "c" ]; then
					result=$(f_to_c "$result")
				fi
				if [ "${item: -1}" == "s" ]; then
					result=${highs[*]} # Return Array
				fi
				;;
			low|low_f|low_c|lows)
				readarray lows < <(grep -A7 "Daily Minimum Temperature" "$forecast" | tail -7 | cut -d'>' -f2 | cut -d'<' -f1)
				if [ "${times[0]::-1}" == "Tonight" ]; then
					ndx=$(( ndx / 2 ))
				else
					ndx=$(( (ndx - 1) / 2 ))
				fi
				result=${lows[$ndx]::-1}
				if [ "${item: -1}" == "c" ]; then
					result=$(f_to_c "$result")
				fi
				if [ "${item: -1}" == "s" ]; then
					result=${lows[*]} # Return Array
				fi
				;;
			precip|precips)
				readarray precips < <(grep -A"$num" "<name>12 Hourly Probability of Precipitation</name>" "$forecast" | tail -"$num" | cut -d'>' -f2 | cut -d'<' -f1 | sed -e '/^[0-9]/ s/$/%/' -e 's/^$/0%/')
				result=${precips[$ndx-1]::-1}
				if [[ "$day" != "0" ]] && [[ "${times[$ndx-1]::-1}" != "Tonight" ]] && [[ ${precips[$ndx]::-2} -gt ${precips[$ndx-1]::-2} ]]; then
					result=${precips[$ndx]::-1}
				fi
				if [ "${item: -1}" == "s" ]; then
					result=${precips[*]} # Return Array
				fi
				;;
			alerts|alerts_flag)
				readarray hazards < <(grep "<hazardTextURL>" "$forecast" | cut -d'>' -f2 | cut -d'<' -f1 | sed 's/amp;//g')
				hazards_len=${#hazards[@]}
				if [ ! -f "$alerts" ]; then
					if [[ $hazards_len -gt 0 ]]; then
						for (( i=0; i<hazards_len; i++ )); do
							curl -s "${hazards[$i]::-1}" | egrep -v "<|>|&&|$$|^13$|^ |Page last modified" | sed '$!N; /^\(.*\)\n\1$/!P; D' >> "$alerts"
						done					
					fi
				fi
				if [ "$item" == "alerts_flag" ]; then
					if [ -s "$alerts" ]; then
						result=$(echo "!$hazards_len "| sed -e 's|!1 |! |' -e s/[[:space:]]*$//)
					fi
				else
					result=$(cat "$alerts" 2> /dev/null)
				fi
				;;
			*)
				result="--"
				;;
		esac
	else
		result=""
	fi
	#
	echo -e "$result"
}
# Return the User Specified Item from the Astronomy Cache File
function get_astronomy_item {
	result=""
	# Loop Until the Cache File is Complete Up to 15 Seconds
	trys=0
	while [[ ! -f "$astronomy" ]]
	do
		if [ $trys -gt 15 ]; then
			echo "ACNA" # Invalid Astronomy Cache
			return
		fi
		trys=$(( trys + 1 ))
		sleep 1
	done
	# Return All Astronomy Items
	if [ "$1" == "astronomy_all" ]; then
		cat "$astronomy"
		return
	fi
	# Try Up to $max_trys Times to Get a Valid Result
	trys=0
	while [ $trys -lt $max_trys ]
	do
		result=$(grep -i "^$1=" "$astronomy" | cut -d'=' -f2)
		if [ ! -z "$result" ]; then
			break
		fi
		trys=$(( trys + 1 ))
		sleep 1
	done
	#
	echo "${result:-N/A}"
}
# Display Usage Instructions
function display_usage {
	echo "Usage: $program conditions_item|forecast_item[day_offset]|astronomy_item"
	echo "       [day_offset] - Displays Forecast for 0-6 days from today 0=Today"
	echo
	echo "             day[#] : Displays Date # days from today 0=Today, e.g., 'Wed 22'"
	echo
	echo "   conditions_items : real_feel[_f|_c]|wind_icon|conditions|conditions_icon"
	echo "                      conditions_all - Displays Valid Current Condition Items"
	echo
	echo "     forecast_items : forecast_conditions|forecast_high[_f|_c]"
	echo "                      forecast_low[_f|_c]|forecast_high_low[_f|_c]"
	echo "                      forecast_precip|detailed_forecast|detailed_forecast_all"
	echo "                      forecast_all - Displays Forecast for 7 Days"
	echo "                      detailed_forecast_all - Detailed Forecast for 7 Days"
	echo "                      alerts - Active Watches, Warnings, and Advisories"
	echo "                      alerts_text - Text of Watches, Warnings, and Advisories"
	echo
	echo "    astronomy_items : sunrise|sunset|moonrise|moonset|moonphase|moonpct"
	echo "                      nextmoonphase|nextmoondate|moonage|moonicon"
	echo "                      astronomy_all - Displays All Astronomy Items"
	echo
	echo "          wind_icon : ConkyNESW Font Icon Character for Wind Direction"
	echo
	echo "    conditions_icon|forecast_icon - ConkyWeather Font Icon Character"
	echo "                                    for Current/Forecasted Weather Conditions"
	echo
	echo "    moonicon        : Displays MoonPhases font Icon Character for Moon Phase"
	echo
	echo "    Sample Usage: '$program conditions' - Displays Current Weather Conditions"
	echo "    Sample Usage: '$program forecast_high 1' - Forecast Tomorrow's High °F"
	echo "    Sample Usage: '$program moonphase' - Displays the Current Moon Phase"
	echo "    Sample Usage: '$program -t|--template filename' - Displays 'filename'"
	echo "                                                         with Item Substitution"
	echo
	echo "    Sample Usage: '$program -m|--metar icao_id' - Set METAR Station Used for"
	echo "                                                     Conditions/Forecast and"
	echo "                                                     Update Config File"
	echo
	echo "    ICAO Codes: http://www.rap.ucar.edu/weather/surface/stations.txt"
	echo "        Some Experimentation May Be Necessary to Select a Good Location"
}
# If No Command-line Options or 'help' Specified, Display Usage and Exit
if [ -z "$1" ] || [ "$(echo "$1" | egrep -q "help|-h")" == 0 ]; then
	display_usage
	exit 1
fi
# Delete Cache Files If Refresh Specified
if [ "$1" == "refresh" ]; then
	# Loop Until Only One Instance of Program is Running
	while [ "$(pgrep -c "$program")" -gt 2 ]
	do
		sleep 1
	done
	# Delete the Cache Files
	rm -f "$conditions"
	rm -f "$forecast"
	rm -f "$alerts"
	rm -f "$astronomy"
fi
# Update Cache Files If Update Time Limit Has Been Passed
filedate=0
if [ -f "$conditions" ]; then
	filedate=$(stat -c %Y  "$conditions") # Get Time of Last Update
fi
updatecache=$(( $(date +%s) > $(( filedate + refresh_interval )) ))
# Create the Directory for the Cache Files
mkdir -p "$cache_dir"
# Get the Current Conditions from NOAA and Output to a Cache File
if [[ $updatecache -eq 1 ]] || [ ! -f "$conditions" ]; then
	curl -s "http://w1.weather.gov/xml/current_obs/$metar.xml" -o "$conditions"
fi
# Get Longitude & Latitude from Conditions Cache for Forecast and Astronomy
latitude=$(get_conditions_item 'latitude')
longitude=$(get_conditions_item 'longitude')
if [ -z "$latitude" ] || [ -z "$longitude" ]; then
	echo "UGLL" # Unable to Get Latitude/Longitude
	exit 2
fi
# Get the Forecast from NOAA and Output to a Cache File
if [[ $updatecache -eq 1 ]] || [ ! -f "$forecast" ]; then
	rm -f "$alerts"
	curl -s "https://forecast.weather.gov/MapClick.php?lat=$latitude&lon=$longitude&unit=0&lg=english&FcstType=dwml" -o "$forecast" # unit=0 Fahrenheit
fi
# Get the Astronomy Data from USNO, Process and Output to a Cache File
if [[ $updatecache -eq 1 ]] || [ ! -f "$astronomy" ]; then
	# Initialize Astronomy Variables
	moonphase=0; moonpct=0; moonage=0; moonicon=0; newmoon=0; firstqtr=0; fullmoon=0; lastqtr=0; nextmoonphase=0; nextmoondate=0
	# Ages and Offsets for Moon Age Calculation
	ages=(18 0 11 22 3 14 25 6 17 28 9 20 1 12 23 4 15 26 7)
	offsets=(-1 1 0 1 2 3 4 5 7 7 9 9)
	# MoonPhases font Characters - New Moon to Full Moon
	moonicons=("@" "N" "O" "P" "Q" "R" "S" "T" "T" "U" "V" "W" "X" "Y" "Z" "0" "0" "A" "B" "C" "D" "E" "F" "G" "H" "I" "J" "K" "L")
	# Get Astronomy Data Using Timezone from Current Conditions Data
	utcoffset=$(get_conditions_item 'observation_time_rfc822' | awk '{print $NF}' | sed -e "s/0//g")
	timezone=$(get_conditions_item 'observation_time' | awk '{print $NF}' | sed -e "s/^$/$(date +%Z)/" -e "s/EDT/EST5EDT/" -e "s/CDT/CST6CDT/" -e "s/MDT/MST7MDT/" -e "s/PDT/PST8PDT/") # Defaults to Local Time Zone If Not Found in Conditions File
	data=$(curl -s "http://aa.usno.navy.mil/rstt/onedaytable?ID=AA&year=$(date +%Y)&month=$(date +%m)&day=$(date +%d)&place=&coords=$latitude,$longitude&tz=$utcoffset")
	nextphases=$(curl -s "http://aa.usno.navy.mil/cgi-bin/aa_phases.pl?&year=$(date +%Y)&month=$(date +%m)&day=$(date +%d)&nump=4&format=t")
	trys=0
	while [[ -z "$data" ]]
	do
		if [ $trys -gt 15 ]; then
			break # Unable to Get Astronomy Data
		fi
		trys=$(( trys + 1 ))
		sleep 1
	done
	# Extract the Required Item from the Data Variable and Format the Output
	for item in sunrise sunset moonrise moonset # ${item} is the Variable while ${!item} is its Value
	do
		value=$(echo "$data" | grep -i "${item}" | grep -v " on" | tail -1 | cut -d'>' -f5 | cut -d'<' -f1 | sed -e 's/\(.*\)/\U\1/' -e 's/^[ \t]*//' | cut -d' ' -f1-2)
		if [[ -z "$value" ]]; then
			value="A.A.H." # Moon is Always Above Horizon
			if [[ "${item:0:3}" == "sun" ]]; then
				value="A.B.H." # Sun is Always Below Horizon
			fi
			eval "${item}=\"$value\""
		else
			eval "${item}=\"$(TZ="$utcoffset" date -d "$value UTC" +"%-I:%M %p")\"" # Set Sun/Moon Variable & Format Time to Local Timezone
		fi
	done
	moonphase=$(echo "$data" | grep -i "Phase of the Moon" | awk -F'>' '{print $NF}' | awk -F':' '{print $NF}' | sed -e 's/^[ \t]*//' | awk '{print $1, $2}' | sed -e 's/^[ \t]*//' -e 's/Waxing/Wax/' -e 's/Waning/Wan/' -e 's/New\($\)/New Moon\1/g' -e 's/Full\($\)/Full Moon\1/g')
	moonpct=$(echo "$data" | grep -i "% of the Moon" | cut -d'h' -f2 | cut -d' ' -f2 | sed 's/ //g')
	moonage=$(( ((${ages[$(( ($(date +%Y) + 1) % 19 ))]} + (($(date +%-d) + ${offsets[(( $(date +%-m) - 1 ))]}) % 30) + ($(date +%Y) < 1900)) % 30) ))
	moonicon=${moonicons[$moonage]}
	moonicon="${moonicon:-@}" # Default to New Moon Icon
	# Get Upcoming Moon Phase Dates
	phases=(fullmoon lastqtr newmoon firstqtr)
	phasetext=("Full Moon" "Last Quarter" "New Moon" "First Quarter")
	for ((i=0; i<${#phases[@]}; i++))
	do
		phasedate=$(echo "$nextphases" | grep "${phasetext[i]}" -A1 | tail -1 | cut -d'>' -f2 | cut -d'<' -f1 | awk '{print $2, $3, $4, "UTC", $1}') # Get Phase Date
		eval "${phases[i]}=\"$(TZ="$timezone" date -d "$phasedate" +"%b %-d")\"" # Set Phase Variable & Format Date to Local Timezone
	done
	case "$moonphase" in
		"New Moon")
			moonicon="@"
			moonpct="${moonpct:-0%}"
			;;
		"First Quarter")
			moonicon="T"
			moonpct="${moonpct:-50%}"
			;;
		"Full Moon")
			moonicon="0"
			moonpct="${moonpct:-100%}"
			;;
		"Last Quarter")
			moonicon="G"
			moonpct="${moonpct:-50%}"
			;;
	esac
	case "$moonphase" in
		"New Moon"|"Wax Crescent")
			nextmoonphase="First Qtr"
			nextmoondate="$firstqtr"
			;;
		"Full Moon"|"Wan Gibbous")
			nextmoonphase="Last Qtr"
			nextmoondate="$lastqtr"
			;;
		"Last Quarter"|"Wan Crescent")
			nextmoonphase="New Moon"
			nextmoondate="$newmoon"
			;;
		*)
			# Default to Full Moon as Next Moon Phase
			nextmoonphase="Full Moon"
			nextmoondate="$fullmoon"
			;;
	esac
	export nextmoonphase; export nextmoondate # To get shellcheck off my back
	# Output the Extracted Data to the Cache File
	rm -f "$astronomy"
	for item in sunrise sunset moonrise moonset moonphase moonpct moonage moonicon newmoon firstqtr fullmoon lastqtr nextmoonphase nextmoondate
	do
		echo "${item}=${!item}" >> "$astronomy"
	done
fi
# Process Template File
function process_template {
	if [ -z "$1" ] || [ ! -f "$1" ]; then
		echo "Invalid Template File"
		return
	fi
	# Load the Template File for Processing
	result=$(cat "$1")
	# Get a List of Weather Items from the Template
	while [ ! -z "$1" ]; do
		items=$(echo "$result" | grep '\[' | cut -d'[' -f2 | cut -d']' -f1)
		if [ -z "$items" ]; then
			break
		fi
		# Replace the Requested Items in the Template
		for item in $items; do
			value=$(get_item "$item")
			result=${result//\[$item\]/$value}
		done
	done
	# Return the Processed Template
	echo "$result"
}
# Display the Requested Data Item(s) or N/A
function get_item {
	t_units=$(echo -n "$1" | tail -c 1 | tr '[:lower:]' '[:upper:]' | tr -C 'C' 'F') # Temperature Units - F/C; Default is Fahrenheit
	case "$1" in
		temp*)
			fmt_temp "$(get_conditions_item temp_"$t_units")" "$t_units"
			;;
		dewpoint*)
			fmt_temp "$(get_conditions_item dewpoint_"$t_units")" "$t_units"
			;;
		real_feel*)
			# Display the Real Feel Temperature
			result="$(get_conditions_item heat_index_"$t_units")"
			if [ -z "$result" ]; then
				result="$(get_conditions_item windchill_"$t_units")"
			fi
			if [ -z "$result" ]; then
				result="$(get_conditions_item temp_"$t_units")"
			fi
			fmt_temp "$result" "$t_units"
			;;
		relative_humidity)
			get_conditions_item "$1" | sed '/^[0-9]/ s/$/%/'
			;;
		pressure_in)
			get_conditions_item "$1" | sed '/^[0-9]/ s/$/ in./'
			;;
		wind_mph|wind_gust_mph|wind_kt|wind_gust_kt)
			w_units=$(echo -n "$1" | sed -e 's/wind_//g' -e 's/gust_//g')
			get_conditions_item "$1" | sed -e "/^[0-9]/ s/$/ $w_units/" -e "s/0.0 $w_units/   Calm/"
			;;
		conditions|current_conditions|weather)
			# Display the Current Conditions
			get_conditions_item 'weather' | sed -e 's/Light/Lt/g' -e 's/and/\&/g'
			;;
		conditions_icon)
			# Display a Weather Icon for the Current Conditions
			result=$(get_weather_icon "$(get_conditions_item 'weather')")
			# Translate to Night Icons If Current Time is Before Sunrise or After Sunset
			if [[ "$(get_astronomy_item 'sunrise')" != "N/A" ]] && [[ "$(get_astronomy_item 'sunset')" != "N/A" ]] && [[ "$(get_astronomy_item 'sunrise')" != "A.B.H." ]] && [[ "$(get_astronomy_item 'sunset')" != "A.B.H." ]]; then
				if [[ $(date +%s) -lt $(date --date="$(get_astronomy_item 'sunrise')" +%s) ]] || [[ $(date +%s) -gt $(date --date="$(get_astronomy_item 'sunset')" +%s) ]]; then
					result=$(echo "$result" | tr 'a-dgko' 'A-DGKO') # Only Certain Icons Have Specific Night Equivalents
				fi
			fi
			echo "$result"
			;;
		wind_icon)
			# Display a Wind Icon for Current Conditions Using the ConkyNESW font
			result=$(get_conditions_item 'wind_dir')
			result=$(echo "$result" | sed -e 's/Calm/%/g' -e 's/Variable/!/g' -e 's/Not Available//g' -e 's/NA//g' -e 's/N\/A//g' -e 's/na//g' -e 's/n\/a//g')
			result=$(echo "$result" | sed -e 's/East­ Northeast/4/g' -e 's/East­ Southeast/6/g' -e "s/North­ Northeast/2/g" -e "s/North­ Northwest/@/g")
			result=$(echo "$result" | sed -e 's/West­ Northwest/>/g' -e 's/West­ Southwest/</g' -e "s/South­ South­east/8/g" -e "s/South­­ South­west/:/g")
			result=$(echo "$result" | sed -e 's/Northeast/3/g' -e 's/Northwest/?/g' -e 's/Southeast/7/g' -e 's/Southwest/;/g')
			result=$(echo "$result" | sed -e 's/North/1/g' -e 's/South/9/g' -e 's/East/5/g' -e 's/West/=/g')
			echo "${result:--}" # Hyphen Character Displays N/A Icon for Null Result
			;;
		forecast_conditions*)
			# Display the Forecasted Conditions for the Specified Day - * is Numerical Day - 0=Today
			day=$(echo -n "$1" | tail -c 1 | tr 's' '0' | sed "s/^$/0/")
			result=$(get_forecast_item 'conditions' "$day")
			if [ "$day" == "0" ]; then
				# Special Formatting for Today's Forecast
				result=$(echo "$result" | sed -e 's/Light/Lt/g' -e 's/Partly/P/g' -e 's/Mostly/M/g' -e 's/Mixed/Mix/g' -e 's/Freezing/Frzg/g' -e 's/Decreasing/Dec/g' -e 's/Heavy //g' -e 's/Scattered //g' -e 's/Isolated //g' -e 's/Slight //g' -e 's/Chance //g' -e 's/Light /Lt/g' -e 's/ Likely//g' -e 's/Patchy//g' -e 's/^Showers.*/Showers/g' -e 's/^Thunderstorm.*/T-Storms/g' -e 's/Increasing/Inc/g' -e 's/Severe/Svr/' -e 's/Thunderstorm/T-storm/' -e 's/and.*//g' -e 's/then.*//g' -e 's|/ |/|g' -e 's/^[ \t]*//;s/[ \t]*$//')
			fi
			echo "${result:-N/A}"
			;;
		forecast_icon*)
			# Generate a Weather Icon for Forecasted Conditions for Specific Day - * is Numerical Day - 0=Today
			day=$(echo -n "$1" | tail -c 1 | tr 'n' '0' | sed "s/^$/0/")
			get_weather_icon "$(get_forecast_item 'conditions' "$day")"
			;;
		forecast_high_low*)
			# Display the Forecasted High/Low for Specific Day - * is Numerical Day - 0=Today
			day=$(echo -n "$1" | tail -c 1 | tr 'wfc' '000' | sed "s/^$/0/")
			high="$(fmt_temp "$(get_forecast_item high_"$t_units" "$day")" " " "--")"
			low="$(fmt_temp "$(get_forecast_item low_"$t_units" "$day")" "$t_units" "--")"
			echo "$high/$low" | sed -e "s/ //g" -e "s|°/--|°$t_units/--|" -e "s|°/$t_units|°$t_units/--|"
			;;
		forecast_high*|forecast_low*)
			# Display the Forecasted High or Low for Specific Day - * is Numerical Day - 0=Today
			day=$(echo -n "$1" | tail -c 1 | tr 'hwfc' '0000' | sed "s/^$/0/")
			type=$(echo -n "$1" | tr -d '0-9' | sed -e 's/forecast_//' -e 's/$//') # high or low
			fmt_temp "$(get_forecast_item "$type" "$day")" "$t_units" "--"
			;;
		forecast_precip*)
			# Display the Forecasted Probability of Precipitation - * is Numerical Day - 0=Today
			day=$(echo -n "$1" | tail -c 1 | tr 'p' '0' | sed "s/^$/0/")
			get_forecast_item 'precip' "$day" | sed 's|^$|N/A|'
			;;
		alerts|alerts_flag)
			# Display Watches, Warnings, and Advisories
			get_forecast_item "$1"
			;;
		detailed_forecast|detailed_forecast_all|forecast_all|forecast_all_f|forecast_all_c)
			# Display Detailed Forecast for the Specific Day - $2 is Numerical Day - 0=Today or Daily Summary Forecast
			get_forecast_item "$1" "$2"
			;;
		sunrise|sunset|moonrise|moonset|moonphase|moonpct|moonage|moonicon|newmoon|firstqtr|fullmoon|lastqtr|nextmoonphase|nextmoondate|astronomy_all)
			# Retrieve the Requested Astronomy Item from the Cache File
			get_astronomy_item "$1"
			;;
		day*)
			# Get the Day and Date, e.g., 'Mon 11' - * is Numerical Day - 0=Today
			date -d "$(echo -n "$1" | tail -c 1 | tr 'y' '0') days" +"%a %-e"
			;;
		-h|--help|help|"")
			# Display Usage Instructions
			display_usage
			;;
		-t|--template)
			# Process Template File
			process_template "$2"
			;;
		-m|--metar)
			# Update the METAR icao id
			echo "Config File Modified with New METAR: $2"
			;;
		refresh)
			# Refresh the Cache Files
			echo 'Refresh complete'
			;;
		*)
			# Retrieve the Specified Current Conditions Item from the Cache File
			get_conditions_item "$1" | sed 's|^$|N/A|'
			;;
	esac
}
# Get the Requested Item
get_item "$1" "$2" "$3"
#
set -e # Enable Error Trapping
#
exit 0
