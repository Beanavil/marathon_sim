# Data

## Runners

The data available consists of the results from the Boston marathon for the years [2015](/data/marathon_results_2015.csv), [2016](/data/marathon_results_2016.csv) and [2017](/data/marathon_results_2017.csv).

The data used to infer the runner's base pace distribution for the simulation is reduced to the [2017 marathon results](/data/marathon_results_2017.csv).

The original data can be found in [Kaggle](https://www.kaggle.com/datasets/rojour/boston-results), but we have preprocessed it with the script [process_marathon_data.r](/data/process_marathon_data.r).

## Weather

The data used is the one obtained from [AEMET OpenData (Acceso General)](https://opendata.aemet.es/centrodedescargas/productosAEMET?). It is stored withing the files [jan-jun2024.json](/data/jan-jun2024.json) and [jul-dec2024.json](/data/jul-dec2024.json).

The linear model used for the weather effect on the runners' pace uses categorical variables, so we did some preprocessing of this data to convert the **temperature**, **humidity** and **wind** data to the categorical variables `Low`, `Medium` and `High` and remove the data entries for the days that have `Low` values, as those are not adjusted in the model.

The preprocessing is done with the script [process_weather_data.r](/data/process_weather_data.r), and the generated data for the experiments is [experiments_data.csv](/data/experiments_data.csv).
