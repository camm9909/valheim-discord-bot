# Valheim Discord Bot
![](https://github.com/ckbaudio/valheim-discord-bot/blob/main/img/vhb_ban2.png)

The aim here is to connect player stats and server events to Discord seemlessly. 
## Prerequisites
As per; install requirements via `pip install -r requirements.txt` in the code directory. It's recommended to run a python virtual environment but not necessary. The script is intended to run on the same server as the game host for interrupted access to server logs. Logs can be invoked on a dedicated valheimserver by passing the `-logfile` flag. For instances where the script and server are on different machines, remote logs could be possible in the future but this is something that would have to be developed.
## [config.py](https://github.com/ckbaudio/valheim-discord-bot/blob/main/code/config.py)
Editing this config is necessary but it should be self-explanitory. You must have a server log file to make use of things like event reporting and death leaderboards, exceptions are handled if not possible. Pass `-logfile /home/steam/somelog.txt` if using [steamCMD](https://developer.valvesoftware.com/wiki/SteamCMD)

A2S player count ticker should work without logs assuming you have access to the ports required from your script's host. 

Set the `PORT` under `SERVER_ADDRESS` as +1 of your server's set port.
## How it works:
### Usage
Prefix is dictated by bot command var in `vdb_main.py` - change it if needed. Default is `;` 

`help` shows help info

`stats` shows 24 hours by default, other availables: w, 12

`deaths` shows death leaderboards


This bot uses simple csv databases to store data like player deaths (via server logs) and player count (via Valve_Python API). The bot has not been tested on configurations with rotating logs, but it should (in theory) still work. 

The `_logsubprocess.py` script keeps databases updated so it is recommended that you use this in a separate `screen` instance or create it as a service under systemd. This ensures that even if you need to reload the main bot, the databases aren't corrupted. 

Most limitations on information gathered are rather a result of the server logs which are mostly cryptic engine-level debug info. This bot makes use of the most relevant ocurrances of the information given. The hope is that we will get more usable info in the future to expand on functionality of third-party applications such as this :)

## Features:
![](https://github.com/ckbaudio/valheim-discord-bot/blob/main/img/Capture3.PNG "Player ticker")
![](https://github.com/ckbaudio/valheim-discord-bot/blob/main/img/deaths.png "Death leaderboards")
![](https://github.com/ckbaudio/valheim-discord-bot/blob/main/img/serverstats.png "Server stats with 12/24/W ranges")
![](https://github.com/ckbaudio/valheim-discord-bot/blob/main/img/events.png "Event reporting")
![](https://github.com/ckbaudio/valheim-discord-bot/blob/main/img/help.PNG "Help commands for other members")


## To do:
+ Allow admins to configure bot with server info from Discord
+ Allow admins to configure bot to report events to whatever channel #mentioned from Discord
+ Allow admins to configure bot presence for custom status
+ Automatically create VC channel stats on new guild join
+ Change format of Random Mob Event to Embed type with unique formatting for each mob type
+ Create argument vars for top 10 for servers with more activity
