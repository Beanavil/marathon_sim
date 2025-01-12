# marathon_sim
Barcelona marathon simulation for SMDE (Statistical Modelling and Design of Experiments).

## Dependencies

* simpy
* numpy
* pandas

### Install dependencies

```shell
pip install -r requirements.txt
```

## Execution

The command

```shell
python3 sim.py
```

sets up and runs the simulation for the weather data provided in [experiments_data.csv](/data/experiments_data.csv).

## Analysis

The analysis of the data is also performed in [sim.py](./sim.py). The simulation is run using all the viable weather data shown in [experiments_data.csv](/data/experiments_data.csv) and the results are processed to obtain the best day for the Barcelona marathon.

The selection is done based on the best average pace from the runners of each day, as the objective of this project is to determine the best overall results for the race and not only the best performance of selected (elite) runners.

Some plots are generated and put in the [results](/results/) folder. We show the average pace results per day and per month, to determine which specific day resulted being the best and which month is overall more suited for holding the marathon. We also provide a histogram plot with the distribution of the runner's paces.
