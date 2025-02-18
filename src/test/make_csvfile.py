import csv

csv_file = "../data/data.csv"

with open(csv_file, mode="w", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["name", "age", "city"])
    writer.writerow(["John", "25", "New York"])
    writer.writerow(["Jane", "30", "Los Angeles"])
    writer.writerow(["Mike", "35", "Chicago"])
    writer.writerow(["Emily", "28", "San Francisco"])
    writer.writerow(["David", "40", "Seattle"])
    writer.writerow(["Sarah", "32", "Boston"])
    writer.writerow(["Tom", "29", "Miami"])
    writer.writerow(["Lisa", "31", "San Diego"])
    writer.writerow(["Chris", "33", "Austin"])
    writer.writerow(["Olivia", "27", "Philadelphia"])
    writer.writerow(["Daniel", "34", "San Antonio"])
    writer.writerow(["Emma", "26", "San Jose"])
    writer.writerow(["Ryan", "30", "San Francisco"])
    writer.writerow(["Ava", "28", "San Diego"])
    
