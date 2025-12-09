from pysciencemode import Rehastim2 as St
from pysciencemode import Modes, Device

from pysciencemode import Channel as Ch


#  Create a channel
list_channels = [
    Ch(
        mode=Modes.SINGLE,
        no_channel=1,
        amplitude=71,  # Modify here the intensity MICK max = 71 in optim = 50
        pulse_width=300,  # 100, 500
        enable_low_frequency=True,
        name="Biceps",
        device_type=Device.Rehastim2,
    )
]

# Create our object Stimulator
stimulator = St(
    port="COM3", # Enter the port on which the stimulator is connected
    show_log=False,
)

# Initialise the channel
stimulator.init_channel(
    stimulation_interval=200, list_channels=list_channels, low_frequency_factor=2
)

"""
Start the stimulation.
It is possible to :
- Give a time after which the stimulation will be stopped but not disconnected.
- Update the parameters of the channel by giving a new list of channels. The channel given must have been 
  initialised first.
"""
stimulator.start_stimulation()
# stimulator.start_stimulation(stimulation_duration=10, upd_list_channels=nw_list_channel)

# Stop the stimulation if still running
stimulator.pause_stimulation()
stimulator.end_stimulation()
stimulator.disconnect()
stimulator.close_port()