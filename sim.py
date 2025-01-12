#! /usr/bin/env python3

import simpy
import random
import json
import numpy as np
import pandas as pd

##########################
#     Data obtaining     #
##########################

# Reads the simulation configuration data. Such as distance of the race,
# position of the provisioning stations, services available, etc.
def read_simulation_config(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)  # Load JSON data directly

# Reads the weather data. Such as temperature, humidity and wind for each day.
def read_weather_data(file_path):
    df = pd.read_csv(file_path, header=None, names=['date', 'temperature', 'humidity', 'wind'])
    return df

# Get simulation configuration.
sim_conf = read_simulation_config('./data/simulation_config.json')
NUM_RUNNERS = int(sim_conf['NUM_RUNNERS'])
RACE_DISTANCE = float(sim_conf['RACE_DISTANCE'])
STATIONS = sim_conf['STATIONS']
SERVICES = sim_conf['SERVICES']
NEED_INCREASE_DISTR = sim_conf['NEED_INCREASE_DISTR']
WAIT_DISTR = sim_conf['WAIT_DISTR']
WEATHER_MODEL = sim_conf['WEATHER_MODEL']

# Get weather data.
weather_data = read_weather_data('./data/experiments_data.csv')



##########################
#  SimPy implementation  #
##########################

class Service(simpy.Resource):
    def __init__(self, env, name, capacity=5):
        super().__init__(env, capacity)
        self.name = name
        mean, stddev = WAIT_DISTR[name]
        self.service_time = max(0, np.random.normal(mean, stddev))

    def request(self, *args, **kwargs):
        req = super().request(*args, **kwargs)
        return req

    def get_time(self):
        return self.service_time

class Runner:
  def __init__(self, env, runner_id, base_pace, queues, weather_state):
    self.env = env
    self.runner_id = runner_id
    self.pace = base_pace
    self.curr_runtime = lambda distance: self.pace * distance
    self.curr_km = 0
    self.necessities = {service: 0 for service in SERVICES.keys()}
    self.checkpoints = list(STATIONS.keys())
    self.stop_times = []
    self.action = env.process(self.run())
    self.need_functions = {
    service: lambda rng=NEED_INCREASE_DISTR.get(service): random.uniform(*rng)
        for service in self.necessities
    }
    self.queues = queues
    self.weather_conditions = {k: v for k, v in zip(WEATHER_MODEL.keys(), weather_state)}

  # Simulates the running process of a runner across a race.
  def run(self):
    yield self.env.timeout(0)  # initial time measurement is 0
    for i in range(0, len(self.checkpoints)):
        self.curr_km = self.checkpoints[i]
        # Runner advances to next station.
        yield self.env.timeout(self.curr_runtime(float(self.curr_km)))
        # Runner potentially uses services in station. Its pace varies according to the time spent at the station.
        yield from self.use_provisioning_station(self.curr_km)
         # After passing a station, update runner pace based on weather condition and update necessities.
        self.update_pace()
        self.update_necessities()

  # Updates necessity levels of a runner, as they naturally increase throughout the race.
  def update_necessities(self):
    for service, func in self.need_functions.items():
        self.necessities[service] = min(self.necessities[service] + func(), 100)

  # Updates pace based on weather conditions using a linear model.
  def update_pace(self):
    temperature_lvl, humidity_lvl, wind_lvl = self.weather_conditions.values()
    self.pace += WEATHER_MODEL['temperature'][temperature_lvl] + WEATHER_MODEL['humidity'][humidity_lvl] + WEATHER_MODEL['wind'][wind_lvl]

  # Simulates the interaction between a runner and a provisioning station.
  def use_provisioning_station(self, km):
    services_at_station = STATIONS[km]
    # Get random necessities thresholds for whether to use each of the services at the station.
    random_thresholds = {service: random.uniform(0, 100) for service in services_at_station}
    use_service = {service: (random_thresholds[service] < self.necessities[service])
                    for service in services_at_station}

    if any(use_service.values()):
      self.stop_times.append(self.env.now)

      for service, should_use in use_service.items():
        if should_use:
          service_time = self.queues[km][service].get_time()
          yield self.queues[km][service].request()
          yield self.env.timeout(service_time)
          self.necessities[service] = 0 # reset necessity after using service
          self.pace += service_time / float(self.curr_km) # slow down mean pace due to stop

# Represents a simulation for a race.
class RaceSimulation:
  def __init__(self, env):
    self.env = env
    self.resources = {}
    self.runners = []
    self.services_aval = {service: [capacity] * len(STATIONS) for service, capacity in SERVICES.items()}

  def assign_services_to_stations(self):
    for km, services in STATIONS.items():
      self.resources[km] = {
          service: Service(self.env, service, self.services_aval[service][list(STATIONS.keys()).index(km)])
          for service in services
      }

  def populate_runners(self, weather_state, running_time_mean, running_time_stddev):
    for i in range(0, NUM_RUNNERS):
        self.runners.append(
            Runner(
                env,
                runner_id=i,
                base_pace=np.random.normal(running_time_mean, running_time_stddev),
                queues=self.resources,
                weather_state=weather_state
            )
        )

  def run(self, weather_state, running_time_mean, running_time_stddev):
    self.assign_services_to_stations()
    self.populate_runners(weather_state, running_time_mean, running_time_stddev)
    self.env.run() # run simulation
    return [self.runners, self.resources]



##########################
# Simulation entrypoint  #
##########################

# Initialize simulation environment. This manages the simulation time as well as the scheduling
# and processing of events. It also provides means to execute the simulation.
env = simpy.Environment()

# Populate simulation configuration data.
marathon_sim = RaceSimulation(env)



##########################
#   Simulation running   #
##########################

# Run simulation
for index, row in weather_data.iterrows():
    date, temperature, humidity, wind = row
    print(f"Running simulation for date {date} with temperature {temperature}, humidity {humidity}, wind {wind}")
    runners, resources = marathon_sim.run([temperature, humidity, wind], 12895, 1500) # magic numbers come from data analysis (data/process_marathon_data.r)



##########################
#  Simulation analysis   #
##########################
