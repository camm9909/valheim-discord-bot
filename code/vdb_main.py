import os, time, re, csv
import discord, asyncio
import config, emoji
from valve.source.a2s import ServerQuerier, NoResponseError
from config import LOGCHAN_ID as lchanID
from config import VCHANNEL_ID as chanID
from config import file
from discord.ext import commands
import matplotlib.dates as md
import matplotlib.ticker as ticker
import matplotlib.spines as ms
from matplotlib import pyplot as plt
from datetime import datetime, timedelta
import pandas as pd
import typing

pdeath = '.*?Got character ZDOID from (\w+) : 0:0'
pevent = '.*? Random event set:(\w+)'

server_name = config.SERVER_NAME
bot = commands.Bot(command_prefix=';', help_command=None)

    # maybe in the future for reformatting output of random mob events
    # eventype = ['Skeletons', 'Blobs', 'Forest Trolls', 'Wolves', 'Surtlings']

@bot.event
async def on_ready():
    print('Bot is online :)')
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
    help_embed.set_footer(text="Valbot v0.42")
    await ctx.send(embed=help_embed)

@bot.command(name="deaths")
async def leaderboards(ctx):
    top_no = 5
    ldrembed = discord.Embed(title=":skull_crossbones: __Death Leaderboards (top 5)__ :skull_crossbones:", color=0xFFC02C)
    df = pd.read_csv('csv\deathlog.csv', header=None, usecols=[0, 1])
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
    if tmf.lower() in ['w', 'week', 'weeks'] :
        user_range = 168 - 1
        interval = 24
        date_format = '%m/%d'
        timedo = 'week'
        description = 'Players online in the past ' + timedo + ':'
    elif tmf.lower() in ['6', '6hr', '6h']:
        user_range = 12 - 0.15
        interval = 1
        date_format = '%H'
        timedo = '6hrs'
        description = 'Players online in the past ' + timedo + ':'
    else:
        user_range = 24 - 0.30
        interval = 2
        date_format = '%H'
        timedo = '24hrs'
        description = 'Players online in the past ' + timedo + ':'

    #Get data from csv
    df = pd.read_csv('csv\playerstats.csv', header=None, usecols=[0, 1], parse_dates=[0], dayfirst=True)
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

async def mainloop(file):
    await bot.wait_until_ready()
    lchannel = bot.get_channel(lchanID)
    print('Main loop: init')
    try:
        testfile = open(file)
        testfile.close()
        while not bot.is_closed():
            with open(file) as f:
                f.seek(0,2)
                while True:
                    line = f.readline()
                    if(re.search(pdeath, line)):
                        pname = re.search(pdeath, line).group(1)
                        await lchannel.send(':skull: **' + pname + '** just died!')
                    if(re.search(pevent, line)):
                        eventID = re.search(pevent, line).group(1)
                        await lchannel.send(':loudspeaker: Random mob event: **' + eventID + '** has occurred')
                    await asyncio.sleep(0.2)
    except IOError:
        print('No valid log found, event reports disabled. Please check config.py')
        print('To generate server logs, run server with -logFile launch flag')  
        
async def serverstatsupdate():
	await bot.wait_until_ready()
	while not bot.is_closed():
		try:
			with ServerQuerier(config.SERVER_ADDRESS) as server:
				channel = bot.get_channel(chanID)
				await channel.edit(name=f"{emoji.emojize(':eggplant:')} In-Game: {server.info()['player_count']}" +" / 10")

		except NoResponseError:
			print('Cannot connect to valve A2S')
			channel = bot.get_channel(chanID)
			await channel.edit(name=f"{emoji.emojize(':cross_mark:')} Server Offline")
		await asyncio.sleep(30)

bot.loop.create_task(mainloop(file))
bot.run(config.BOT_TOKEN)