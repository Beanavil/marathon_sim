#################################################################
#                      SMDE Second Assignment                   #
#                     Weather Data Processing                   #
#################################################################

# Load required libraries
install.packages("jsonlite")
install.packages("dplyr")
library(jsonlite)
library(dplyr)

# Load data
data_firsthalf <- fromJSON('data/jan-jun2024.json')
data_secondhalf <- fromJSON('data/jul-dec2024.json')

# Function to categorize temperature values
categorize_temperature <- function(temp) {
  if (temp <= 11.7) {
    return("Low")
  } else if (temp <= 17.0) {
    return("Medium")
  } else {
    return("High")
  }
}

# Function to categorize relative humidity values
categorize_humidity <- function(humidity) {
  if (humidity <= 43) {
    return("Low")
  } else if (humidity <= 56.9) {
    return("Medium")
  } else {
    return("High")
  }
}

# Function to categorize wind values
categorize_wind <- function(wind) {
  if (wind <= 16.1) {
    return("Low")
  } else if (wind <= 22.5) {
    return("Medium")
  } else {
    return("High")
  }
}

# Function to clean the data by:
# * Selecting only relevant columns (date, mean temperature, humidity, wind speed)
# * Interpreting values as numerical
# * Converting the numerical values to categorical according to the ranges used in our linear model
# * Removing the days that have a 'low' value for any of the weather conditons (the model do not consider those)
#   |-> Note: given that in Barcelona in 2024 there were no windy days (with other than "Low" level of wind),
#             we don't apply the 'velmedia != "Low"' filter.
clean_and_categorize <- function(data) {
  data %>%
    select(fecha, tmed, hrMedia, velmedia) %>%
    mutate(
      tmed = as.numeric(gsub(",", ".", tmed)),
      hrMedia = as.numeric(hrMedia),
      velmedia = as.numeric(velmedia)
    ) %>%
    mutate(
      tmed = sapply(tmed, categorize_temperature),
      hrMedia = sapply(hrMedia, categorize_humidity),
      velmedia = sapply(velmedia, categorize_wind)
    ) %>%
    filter(tmed != "Low", hrMedia != "Low")
}

# Clean data from both halves of the year
cleaned_data_firsthalf <- clean_and_categorize(data_firsthalf)
cleaned_data_secondhalf <- clean_and_categorize(data_secondhalf)

# Export cleaned data to csv file, easily readable by pandas in python for our experiments
output_file_path <- "data/experiments_data.csv"
write.table(cleaned_data_firsthalf,
            file = output_file_path,
            sep = ",",
            col.names = FALSE,
            row.names = FALSE)
write.table(cleaned_data_secondhalf,
            file = output_file_path,
            sep = ",",
            col.names = FALSE,
            row.names = FALSE,
            append = TRUE)

