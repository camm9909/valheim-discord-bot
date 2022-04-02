import enum
import os, time, re, csv, discord, asyncio, config, emoji, sys, colorama, typing, signal, errno
from valve.source.a2s import ServerQuerier, NoResponseError
from matplotlib import pyplot as plt
from datetime import datetime, timedelta
from colorama import Fore, Style, init
from config import LOGCHAN_ID as lchanID
from config import VCHANNEL_ID as chanID
from config import file
from discord.ext import commands
import matplotlib.dates as md
import matplotlib.ticker as ticker
import matplotlib.spines as ms
import pandas as pd
import copy

#Color init
colorama.init()

pdeath = '.*?Got character ZDOID from (\w+) : 0:0'
pevent = '.*? Random event set:(\w+)'
plog = '(Got character ZDOID from )([\w ]+)(\s:)'
phandshake = '.*handshake from client (\d+)'
pdisconnected = '.*Closing socket (\d+)'
timestamp = '(\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}:\d{2})'

server_name = config.SERVER_NAME
bot = commands.Bot(command_prefix=';', help_command=None)

players = {}
lastPlayer = None

    # maybe in the future for reformatting output of random mob events
    # eventype = ['Skeletons', 'Blobs', 'Forest Trolls', 'Wolves', 'Surtlings']

def signal_handler(signal, frame):          # Method for catching SIGINT, cleaner output for restarting bot
  os._exit(0)

signal.signal(signal.SIGINT, signal_handler)

class User(object):
    def __init__(self, name, id, connected, disconnected):
        self.name = name
        self.id = id
        self.connected = connected
        self.disconnected = disconnected

    def __repr__(self):
        return f'name: {self.name}, connected: {self.connected}, disconnected: {self.disconnected}, id: {self.id}'

async def timenow():
    now = datetime.now()
    gettime = now.strftime("%d/%m/%Y %H:%M:%S")
    return gettime

# Basic file checking
def check_csvs():
    try: 
        os.makedirs('csv')
    except OSError as e:
        if e.errno != errno.EEXIST:
            print(Fore.RED + 'Cannot create csv directory' + Style.RESET_ALL)
            raise os._exit(1)

    files = ['csv/playerstats.csv', 'csv/deathlog.csv']
    for f in files:
        if os.path.isfile(f):
            print(Fore.GREEN + f'{f} found!' + Style.RESET_ALL)
        else:
            with open(f, 'w+'):
                print(Fore.YELLOW + f'{f} doesn\'t exist, creating new...' + Style.RESET_ALL)
            time.sleep(0.2)

check_csvs()

@bot.event
async def on_ready():
    print(Fore.GREEN + f'Bot connected as {bot.user} :)' + Style.RESET_ALL)
    print('Log channel : %d' % (lchanID))
    if config.USEVCSTATS == True:
        print('VoIP channel: %d' % (chanID))
        bot.loop.create_task(serverstatsupdate())

@bot.command(name='help')
async def help_ctx(ctx):  
    help_embed = discord.Embed(description="[**Valheim Discord Bot**](https://github.com/ckbaudio/valheim-discord-bot)", color=0x33a163,)
    help_embed.add_field(name="{}stats <n>".format(bot.command_prefix),
                        value="Plots a graph of connected players over the last X hours.\n Example: `{}stats 12` \n Available: 24, 12, w (*default: 24*)".format(bot.command_prefix),
                        inline=True)
    help_embed.add_field(name="{}deaths".format(bot.command_prefix), 
                        value="Shows a top 5 leaderboard of players with the most deaths. \n Example:`{}deaths`".format(bot.command_prefix),
                        inline=True)
    help_embed.add_field(name="{}players".format(bot.command_prefix), 
                        value="Show players online and offline:`{}players`".format(bot.command_prefix),
                        inline=True)                        
    help_embed.set_footer(text="Valbot v0.42")
    await ctx.send(embed=help_embed)

@bot.command(name="deaths")
async def leaderboards(ctx):
    top_no = 5
    ldrembed = discord.Embed(title=":skull_crossbones: __Death Leaderboards (top 5)__ :skull_crossbones:", color=0xFFC02C)
    df = pd.read_csv('csv/deathlog.csv', header=None, usecols=[0, 1])
    df_index = df[1].value_counts().nlargest(top_no).index
    df_score = df[1].value_counts().nlargest(top_no)
    x = 0
    l = 1 #just in case I want to make listed iterations l8r
    for ind in df_index:
        grammarnazi = 'deaths'
        leader = ''
        # print(df_index[x], df_score[x]) 
        if df_score[x] == 1 :
            grammarnazi = 'death'
        if l == 1:
            leader = ':crown:'
        ldrembed.add_field(name="{} {}".format(df_index[x],leader),
                           value='{} {}'.format(df_score[x],grammarnazi),
                           inline=False)
        x += 1
        l += 1
    await ctx.send(embed=ldrembed)

@bot.command(name="stats")
async def gen_plot(ctx, tmf: typing.Optional[str] = '24'):
    user_range = 0
    if tmf.lower() in ['w', 'week', 'weeks']:
        user_range = 168 - 1
        interval = 24
        date_format = '%m/%d'
        timedo = 'week'
        description = 'Players online in the past ' + timedo + ':'
    elif tmf.lower() in ['12', '12hrs', '12h', '12hr']:
        user_range = 12 - 0.15
        interval = 1
        date_format = '%H'
        timedo = '12hrs'
        description = 'Players online in the past ' + timedo + ':'
    else:
        user_range = 24 - 0.30
        interval = 2
        date_format = '%H'
        timedo = '24hrs'
        description = 'Players online in the past ' + timedo + ':'

    #Get data from csv
    df = pd.read_csv('csv/playerstats.csv', header=None, usecols=[0, 1], parse_dates=[0], dayfirst=True)
    lastday = datetime.now() - timedelta(hours = user_range)
    last24 = df[df[0]>=(lastday)]

    # Plot formatting / styling matplotlib
    plt.style.use('seaborn-pastel')
    plt.minorticks_off()
    fig, ax = plt.subplots()
    ax.grid(b=True, alpha=0.2)
    ax.set_xlim(lastday, datetime.now())
    # ax.set_ylim(0, 10) Not sure about this one yet
    for axis in [ax.xaxis, ax.yaxis]:
        axis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(md.DateFormatter(date_format))
    ax.xaxis.set_major_locator(md.HourLocator(interval=interval))
    for spine in ax.spines.values():
        spine.set_visible(False)
    for tick in ax.get_xticklabels():
        tick.set_color('gray')
    for tick in ax.get_yticklabels():
        tick.set_color('gray')
    
    #Plot and rasterize figure
    plt.gcf().set_size_inches([5.5,3.0])
    plt.plot(last24[0], last24[1])
    plt.tick_params(axis='both', which='both', bottom=False, left=False)
    plt.margins(x=0,y=0,tight=True)
    plt.tight_layout()
    fig.savefig('temp.png', transparent=True, pad_inches=0) # Save and upload Plot
    image = discord.File('temp.png', filename='temp.png')
    plt.close()
    embed = discord.Embed(title=server_name, description=description, colour=12320855)
    embed.set_image(url='attachment://temp.png')
    await ctx.send(file=image, embed=embed)

@bot.command(name="players")
async def users(ctx):
    try:
        checkLogsForPlayerConnections()
        online_embed = discord.Embed(title=":axe: __Online Players__ :axe:", color=0xFFC02C)
        offline_embed = discord.Embed(title=":axe: __Offline Players__ :axe:", color=0xFFC02C)

        for id in players:
            player = players[id]
            if(player.disconnected):
                offline_embed.add_field(name="{}".format(player.name), 
                    value="connected at {}, disconnected at {}".format(player.connected, player.disconnected),
                    inline=False)   
            else:
                online_embed.add_field(name="{}".format(player.name), 
                    value="connected at {}".format(player.connected),
                    inline=False)     

        if(online_embed.fields):
            await ctx.send(embed=online_embed)


        if(offline_embed.fields):
            await ctx.send(embed=offline_embed)        

    except IOError:
        print('issue getting players')
    return

async def mainloop(file):
    await bot.wait_until_ready()
    lchannel = bot.get_channel(lchanID)
    print('Main loop: init')
    try:
        checkLogsForPlayerConnections()
        testfile = open(file)
        testfile.close()
        while not bot.is_closed():
            with open(file, encoding='utf-8', mode='r') as f:
                f.seek(0,2)
                while True:
                    line = f.readline()
                    playerToAnnounce = checkLogLineForPlayerConnections(line)
                    if(playerToAnnounce):
                        await sendPlayerAnnouncement(playerToAnnounce)             
                    if(re.search(pdeath, line)):
                        pname = re.search(pdeath, line).group(1)
                        await lchannel.send(':skull: **' + pname + '** just died!')
                    if(re.search(pevent, line)):
                        eventID = re.search(pevent, line).group(1)
                        await lchannel.send(':loudspeaker: Random mob event: **' + eventID + '** has occurred')
                    await asyncio.sleep(0.2)
    except IOError:
        print('No valid log found, event reports disabled. Please check config.py')
        print('To generate server logs, run server with -logfile launch flag')  

async def sendPlayerAnnouncement(newPlayer):
    global players
    lchannel = bot.get_channel(lchanID)

    try:
        existingPlayer = players[newPlayer.id]
        if (newPlayer.disconnected):
            await lchannel.send(':axe: **' + existingPlayer.name + '** has left the server: ' + server_name)
        elif(newPlayer.connected):
            await lchannel.send(':axe: **' + existingPlayer.name + '** has entered the server: ' + server_name)
        existingPlayer = newPlayer    

    except IOError:
        print("Error sending player announcement") 

def checkLogsForPlayerConnections():
    global lastPlayer

    testFile = open(file)
    testFile.close()
    with open(file, encoding='utf-8', mode='r') as f:
        f.seek(0,0)
        lastPlayer = None
        while True:
            line = f.readline()
            if not line: 
                break
            checkLogLineForPlayerConnections(line)
                
def checkLogLineForPlayerConnections(line):
    global players
    global lastPlayer

    playerToAnnounce = None

    handShake = re.search(phandshake, line)
    player = re.search(plog, line)
    disconnected = re.search(pdisconnected, line)

    if(handShake):
        id = handShake.group(1)
        time = re.search(timestamp, line).group(1)
        playerToAdd = User(None, id, time, None)
        players[id] =  playerToAdd
        lastPlayer = playerToAdd

    elif(disconnected):
        id = disconnected[1]
        if not players[id]:
            return
        player = players[id]
        time = re.search(timestamp, line).group(1)
        player.disconnected = time
        playerToAnnounce = player

    elif(player):
        playerName = player.group(2)
        if(lastPlayer):
            playerToAnnounce = copy.deepcopy(lastPlayer)
            lastPlayer.name = playerName
            lastPlayer = None

    return playerToAnnounce

async def serverstatsupdate():
	await bot.wait_until_ready()
	while not bot.is_closed():
		try:
			with ServerQuerier(config.SERVER_ADDRESS) as server:
				channel = bot.get_channel(chanID)
				await channel.edit(name=f"{emoji.emojize(':eggplant:')} In-Game: {server.info()['player_count']}" +" / 10")

		except NoResponseError:
			print(Fore.RED + await timenow(), 'No reply from A2S, retrying (30s)...' + Style.RESET_ALL)
			channel = bot.get_channel(chanID)
			await channel.edit(name=f"{emoji.emojize(':cross_mark:')} Server Offline")
		await asyncio.sleep(30)
        
bot.loop.create_task(mainloop(file))
bot.run(config.BOT_TOKEN)
