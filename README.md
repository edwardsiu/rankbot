# rankbot
Simple discord bot to track records for cEDH ranked matches.

## Requirements
|Package|Version|
|---|---|
|aiohttp|1.0.5|
|async-timeout|2.0.1|
|chardet|3.0.4|
|discord|0.0.2|
|discord.py|0.16.12|
|hashids|1.2.0|
|multidict|4.1.0|
|pip|9.0.1|
|pymongo|3.6.1|
|PyYAML|3.12|
|setuptools|38.6.0|
|websockets|3.4|
|wheel|0.30.0|

## Testing
Create a local mongodb instance and create a bot application via Discord.
Copy the Client Id and Client Secret into the bot.yml file. A sample configuration file can be found in config/.
From the rankbot directory, call:  
```python run.py```

