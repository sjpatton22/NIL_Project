import pandas as pd

import_file_path = "/Users/sampatton/Downloads/NIL_Project/2025_coordinates_distance.csv"
export_file_path = "/Users/sampatton/Downloads/NIL_Project/2025_final.csv"

df = pd.read_csv(import_file_path)



#Investigating NA values for High Schools
#Data is worthless without High school data, must be dropped.

x = df[pd.isnull(df.HighSchool)]
df = df.dropna(subset=["HighSchool"])

#Investigating NA values for Committed Schools
#Some Players don't officialy commit to a school. If they do it is often juco.
#Data is still important so I cant get rid of it.


y = df[pd.isnull(df.CommittedTo)]

#Investigating NA values for school city
#Vast majority are fcs schools; 

z = df[pd.isnull(df.School_City)]
z_grouped = z.groupby('CommittedTo')['Player'].count()




