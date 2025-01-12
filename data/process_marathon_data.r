#################################################################
#                      SMDE Second Assignment                   #
#                     Runners Data Processing                   #
#################################################################

# Load required libraries
install.packages("dplyr")
install.packages("nortest")
library(dplyr)
library(nortest)

# Load data
data2017 <- read.csv('data/marathon_results_2017.csv')

# Convert hh:mm::ss to seconds
data2017$total_secs <- as.numeric(as.difftime(unlist(data2017['Official.Time']), units = "secs"))

# Take the 20000 more expert runners. We assume bib numbers are assigned in order starting with elite runners.
filtered_data2017<-data2017[as.numeric(sapply(data2017["Bib"], destring)) < 20000,]

# Since 95.4% of values in a normal distribution lie within ±2σ of the mean, exclude runners
# outside of 2 standard deviations
filtered_data2017$z_scores <- (filtered_data2017$total_secs - mean(filtered_data2017$total_secs)) / sd(filtered_data2017$total_secs)
filtered_data2017 <- filtered_data2017[abs(filtered_data2017$z_scores) < 2, ]
hist(filtered_data2017$total_secs, main="Histogram of total runtime", xlab="Time in Secs", ylab="Count", col="skyblue")

# Show boxplot, get outliers and remove them
boxplot <- boxplot(filtered_data2017$total_secs, plot=TRUE)
boxplot
outliers <- boxplot$out
filtered_data2017 <- filtered_data2017 %>% filter(!(filtered_data2017$total_secs %in% outliers))

# Check normality of distribution of total marathon time
hist(filtered_data2017$total_secs, main="Histogram of total runtime", xlab="Time in Secs", ylab="Count", col="skyblue")
qqnorm(filtered_data2017$total_secs, main = "Normal Q-Q Plot for total run time")
qqline(filtered_data2017$total_secs)
# Cannot use Shapiro test due to the large amount of data

# Get distribution parameter values
var(filtered_data2017$total_secs)
sqrt(var(filtered_data2017$total_secs))
mean(filtered_data2017$total_secs)

# We get a mean 12895 total running seconds and stddev of 1500.
