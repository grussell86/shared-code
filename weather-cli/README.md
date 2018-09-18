# weather-cli

#### Description: Display Current Weather Conditions, Forecast and Astronomy Information for a Specific Location from the Command-line.
####			  Most often used in a `conky` script to display individual items

---

**How to install:**

```shell
cp weather-cli.sh /usr/bin/weather-cli
chmod +rx /usr/bin/weather-cli

# If you need autocomplete support, follow these two steps
cp bash_completion.d/weather-cli /etc/bash_completion.d/weather-cli
source /etc/bash_completion.d/weather-cli
```

---

**How to use:**

Run `weather-cli refresh` from the command-line to generate an initial config file in
	$HOME/.config/weather-cli/weather-cli.config

Edit the config file replacing `KIMS` in the line `metar=KIMS` with the ICAO Airport Code of your choice.
	Run `weather-cli refresh` a second time to update to the new Airport location.

A list of ICAO Codes can be found at: http://www.rap.ucar.edu/weather/surface/stations.txt
	Some Experimentation May Be Necessary to Select a Location that Will Display Conditions, Forecast and Astronomy Data

If you want to display the the current weather conditions, 
then just type:
     `weather-cli conditions`

In fact, You can simply type <code>weather-cli *\<starting few letters\>*</code> like `weather-cli v[TAB]` or `weather-cli vi[TAB]`

If there is more than one option hitting [TAB] twice will display all available options

