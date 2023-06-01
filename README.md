# Ad Hoc Clock Synchronization

## `clock.py`

This script is used to generates a clock signal and synchronizes the clocks of multiple devices on a local network that are also running this script. It uses the UDP to synchronize the clocks.

### Prerequisites

- Python 3.11 or higher

### Usage

1. Open a terminal window and navigate to the directory containing `clock.py`.
2. Run the script by typing `python clock.py` along with its arguments and pressing Enter.
3. The script will start running and will synchronize the clocks of all devices on the network.
4. To stop the script, press Ctrl+C in the terminal window.

### Command Line Arguments

The script accepts the following command line arguments:

- `--clockperiod` or `-clkp`: Clock period in seconds (default: 1.0)
- `--broadcastnumber` or `-bn`: Broadcast period in number of clock cycles (default: 1.0)
- `--alpha` or `-a`: Shift Multiplier (default: 0.01)

Example usage: `python clock.py --clockperiod 0.5 --broadcastnumber 2 --alpha 0.5`

## `plot.py`

The `plot.py` file is used to plot data related to clock synchronization. 

### Prerequisites

- Python 3.11 or higher

### Usage

1. Open a terminal window and navigate to the directory containing `plot.py`.
2. Run the script by typing `python plot.py` along with its arguments and pressing Enter.
3. The script will start running and will output the plot to a window.
4. To stop the script, close the plot window.

The script takes two optional arguments:
- `--clockperiod` or `-clkp`: The clock period in seconds.  
Default is 1.0.  
The clock period should be the same as the clock period used in the `clock.py` script.
- `--diffmode` or `-dm`: The diff mode.  
Can be either 'rel' or 'abs'.  
Default is 'rel'.  
Selecting 'rel' will plot the average difference between a clock and the other clocks on the network as a percentage of the clock period.  
Selecting 'abs' will plot the average difference between a clock and the other clocks on the network in seconds.

Example usage: `python plot.py --clockperiod 0.5 --diffmode abs`