#! /usr/bin/env python3

import simpy
import random
import json
import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

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
CUTOFF = int(sim_conf['CUTOFF'])
CUTOFF_PACE = float(CUTOFF / RACE_DISTANCE)

# Get weather data.
weather_data = read_weather_data('./data/experiments_data.csv')

##########################
#  SimPy implementation  #
##########################

class Service(simpy.Resource):
    def __init__(self, env, name, capacity):
        super().__init__(env, capacity)
        self.name = name
        self.availability = capacity
        mean, stddev = WAIT_DISTR[name]
        self.service_time = max(0, np.random.normal(mean, stddev))

    def request(self, *args, **kwargs):
        req = super().request(*args, **kwargs)
        self.availability -= 1
        return req

    def is_available(self):
        return self.availability > 0

    def release(self):
        self.availability += 1

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
      # We consider that a runner dropped from the race when they run at CUTOFF_PACE or greater.
      # Runners that drop do not continue using services and do not update their pace.
      if self.pace < CUTOFF_PACE:
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
    use_service = {service: (random_thresholds[service] < self.necessities[service]) and (self.queues[km][service].is_available())
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
          # Release re-usable services.
          if service in ['wcs', 'redcross']:
            self.queues[km][service].release()

    # If, after using services, a runner still has 100 necessity for some service (that is,
    # it must use it but is not available) then we assume the runner cannot continue running and
    # we set it's pace to the cutoff pace (meaning that it drops from the race).
    if any((self.necessities[service] == 100 and service in services_at_station) for service in self.necessities):
      self.pace = CUTOFF_PACE

# Represents a simulation for a race.
class RaceSimulation:
  def __init__(self, env, budget_factor=1.0):
    self.env = env
    self.resources = {}
    self.runners = []
    self.budget_factor = budget_factor

  def assign_services_to_stations(self):
    for km, services in STATIONS.items():
      self.resources[km] = {
          service: Service(self.env, service, int(SERVICES[service] * self.budget_factor))
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

# Run simulation and perform analysis
simulation_results = {}
num_repetitions = 15
budget_scenarios = {'tight': 0.3, 'adjusted': 1.0, 'slack': 2}
for scenario, factor in budget_scenarios.items():
  all_simulation_runs = []
  print(f"\nRunning {num_repetitions} simulations for scenario {scenario}")
  for _ in range(num_repetitions):
    temp_results = []

    # Populate simulation configuration data.
    marathon_sim = RaceSimulation(env, factor)

    # Run simulation for all applicable days of the year.
    for index, row in weather_data.iterrows():
      date, temperature, humidity, wind = row
      # print(f"Running simulation with {scenario} budget for date {date} with temperature {temperature}, humidity {humidity}, wind {wind}")
      runners, resources = marathon_sim.run([temperature, humidity, wind], 12895, 1500)
      avg_pace = np.mean([runner.pace for runner in runners])
      temp_results.append((date, avg_pace))

    all_simulation_runs.append(temp_results)

  # Compute the average results across all repetitions.
  avg_results = {}
  for day in range(len(weather_data)):
      avg_pace = np.mean([run[day][1] for run in all_simulation_runs])
      avg_results[weather_data.iloc[day, 0]] = avg_pace

  simulation_results[scenario] = list(avg_results.items())

  ##########################
  #  Simulation analysis   #
  ##########################

  # Get day with best average results
  results_df = pd.DataFrame(simulation_results[scenario], columns=['Date', 'Average pace'])
  best_day = results_df.loc[results_df['Average pace'].idxmin()]
  print(f"Best Simulation Day: {best_day['Date']} with average runners' pace: {best_day['Average pace']:.2f}")

  # Get also the month with best results
  results_df['Date'] = pd.to_datetime(results_df['Date'])
  results_df['Month'] = results_df['Date'].dt.to_period('M')
  monthly_avg_pace = results_df.groupby('Month')['Average pace'].mean()
  best_month = monthly_avg_pace.idxmin()
  best_pace = monthly_avg_pace.min()

  # Set up plots style
  sns.set_style("whitegrid")

  # Save PNG graph with average runner's pace per day of the year
  plt.figure(figsize=(12, 6))
  norm = mcolors.Normalize(vmin=results_df['Average pace'].min(), vmax=results_df['Average pace'].max())
  colors = plt.cm.coolwarm(norm(results_df['Average pace']))
  bars = plt.bar(results_df['Date'], results_df['Average pace'], color=colors)
  plt.axhline(y=best_day['Average pace'], color='gold', linestyle='--', linewidth=2, label=f'Best day: {best_day["Date"]}')
  plt.xlabel('Date', fontsize=14, fontweight='bold')
  plt.ylabel('Average pace', fontsize=14, fontweight='bold')
  plt.title(f"Simulation results ({scenario} budget): average runner pace per day', fontsize=16, fontweight='bold', color='darkslateblue")
  plt.xticks(rotation=45, fontsize=10)
  plt.yticks(fontsize=12)
  plt.legend(fontsize=12)
  plt.tight_layout()
  plt.savefig(f"results/simulation_results_{scenario}.png")

  # Plot also a histogram with the distribution of the paces
  plt.figure(figsize=(10, 5))
  plt.hist(results_df['Average pace'], bins=30, color='skyblue', edgecolor='black', alpha=0.7)
  plt.xlabel('Average pace')
  plt.ylabel('Frequency')
  plt.title(f"Distribution of daily average paces ({scenario} budget)")
  plt.savefig(f"results/pace_distribution_results_{scenario}.png")

  # Save also a plot for the results per month
  plt.figure(figsize=(12, 6))
  norm_month = mcolors.Normalize(vmin=monthly_avg_pace.min(), vmax=monthly_avg_pace.max())
  colors_month = plt.cm.coolwarm(norm_month(monthly_avg_pace))
  bars_month = plt.bar(monthly_avg_pace.index.astype(str), monthly_avg_pace, color=colors_month, edgecolor='black')
  bars_month[monthly_avg_pace.index.get_loc(best_month)].set_color('gold')
  bars_month[monthly_avg_pace.index.get_loc(best_month)].set_edgecolor('darkgoldenrod')
  plt.axhline(y=best_pace, color='crimson', linestyle='--', linewidth=2, label=f'Best month: {best_month}')
  plt.xlabel('Month', fontsize=14, fontweight='bold')
  plt.ylabel('Average pace', fontsize=14, fontweight='bold')
  plt.title(f"Simulation results: average runner pace per month ({scenario} budget)", fontsize=16, fontweight='bold', color='darkslateblue')
  plt.xticks(rotation=45, fontsize=12)
  plt.yticks(fontsize=12)
  plt.legend(fontsize=12)
  plt.grid(axis='y', linestyle='--', alpha=0.5)
  plt.tight_layout()
  plt.savefig(f"results/monthly_simulation_results_{scenario}.png")
