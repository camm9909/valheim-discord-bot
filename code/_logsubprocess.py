from datetime import datetime
import time, os, re
import csv, asyncio
from valve.source.a2s import ServerQuerier, NoResponseError
import config

pdeath = '.*?Got character ZDOID from (\w+) : 0:0'
log = config.file

async def timenow():
    now = datetime.now()
    gettime = now.strftime("%d/%m/%Y %H:%M:%S")
    return gettime

async def writecsv():
    while True:    
        try:
            with ServerQuerier(config.SERVER_ADDRESS) as server:
                with open('csv/playerstats.csv', 'a', newline='') as f:
                    csvup = csv.writer(f, delimiter=',')  
                    curtime, players = await timenow(), server.info()['player_count']
                    csvup.writerow([curtime, players])
                    print(curtime, players)
        except NoResponseError:
            with open('csv/playerstats.csv', 'a', newline='') as f:
                csvup = csv.writer(f, delimiter=',')  
                curtime, players = await timenow(), '0'
                csvup.writerow([curtime, players])
                print(curtime, 'Cannot connect to server')
        await asyncio.sleep(60)

async def deathcount():
    while True:           
        with open(log, encoding='utf-8', mode='r') as f:
            f.seek(0,2)
            while True:
                line = f.readline()
                if(re.search(pdeath, line)):
                    pname = re.search(pdeath, line).group(1)
                    with open('csv/deathlog.csv', 'a', newline='') as dl:
                        curtime = await timenow()
                        deathup = csv.writer(dl, delimiter=',')
                        deathup.writerow([curtime, pname])
                        print(curtime, pname, ' has died!')
                await asyncio.sleep(0.2)

loop = asyncio.get_event_loop()
loop.create_task(deathcount())
loop.create_task(writecsv())
loop.run_forever()
