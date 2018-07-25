from src import table

title = "Title"
columns = ["Name", "Value", "Description"]
rows =  [
        ["Varolz", "10", "The Best"],
        ["JVP", "20", "The Bluest"],
        ["Captain Crunch", "10", "Awesome"]]
t = table.Table(title, columns, rows)
print(t)
