# rankbot
Simple discord bot to track records for cEDH ranked matches.

## Running
Create a mongodb instance and create a bot application via Discord.
Copy the Client Id and Client Secret into the bot.yml file. A sample configuration file can be found in config/.

Using a virtual environment is highly recommended. Python version should be 3.7+.
To install the dependencies, do the following:
1. python -m pip install -U https://github.com/Rapptz/discord.py/archive/rewrite.zip#egg=discord.py
2. python -m pip install -r requirements.txt

To run the bot, from the rankbot/src directory, call:  
```python run.py```
