# Bayesian stimulation hand cycling project

## Required installation
- Python==3.9 (for the stimulator)

### Stimulator:
- pysciencemode: conda install -c conda-forge pysciencemode (https://github.com/s2mLab/pyScienceMode)

### Encoder:
- nidaqmx: conda install conda-forge::nidaqmx-python (https://anaconda.org/conda-forge/nidaqmx-python)
- NI-DAQ software and drivers: https://www.ni.com/fr/support/downloads/drivers/download.ni-daq-mx.html?srsltid=AfmBOoq5Z4j-iU1ba810SYTwTJGMpS7VuC-yRcFi3tORrE3IQoFDrhIf#577117

### Optimization:
- skopt: conda install conda-forge::scikit-optimize (https://anaconda.org/conda-forge/scikit-optimize)

### Automation of the opening/closing of the Sensix software
DID NOT WORK since the sensix app is not standard
- pywinauto: conda install -c conda-forge pywinauto


## Codes to run
1. Calibrate the pedals using I-Crankset.exe
2. Start collecting using I-Crankset.exe
3. [stimulation_range_from_borg.py](stimulation_range_from_borg.py): Stimulate muscle by muscle until a Borg scale 8 is hit
4. Then, change the `pulse_intensity` range for each muscle in the `constants.py` file

Bayesian optimization condition:
5. [main.py](main.py): Run the optimization of the stimulation parameters
6. [load_and_plot_results.py](load_and_plot_results.py): Load and plot the results from the optimization
7. [stimulate_with_specific_params.py](stimulate_with_specific_params.py): Stimulate with the optimal parameters

Manual tuning condition:
5. [main_manually.py](main_manually.py): Modify the stimulation parameters manually using the GUI
6. [stimulate_with_specific_params.py](stimulate_with_specific_params.py): Stimulate with the parameters found manually
