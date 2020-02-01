import numpy as np
import requests
import pandas as pd

def getSchedule(season, todays_Date):
    url = "https://statsapi.web.nhl.com/api/v1/schedule?season={}".format(season)
    r = requests.get(url)
    data = r.json()["dates"]

    teams_Playing = []

    for i in range(len(data)):
      #print("{} == {}".format(data[i]["date"], todays_Date))
      if( data[i]["date"] == todays_Date ):
        data = data[i]["games"]
        #print("here")
        for j in range(len(data)):
          teams_Playing.append( data[j]["teams"]["away"]["team"]["name"] )
          teams_Playing.append( data[j]["teams"]["home"]["team"]["name"] )
        return teams_Playing
    print("nothing found")

def getPlayerList(season, teams_Playing):

    url = "https://statsapi.web.nhl.com/api/v1/teams?expand=team.roster&season={}".format(season)
    r = requests.get(url)

    data = r.json()["teams"]

    relevant_Players = {}

    for i in range(len(data)):
      if data[i]["name"] in teams_Playing:
        for j in range(len(data[i]["roster"]["roster"])):
          ID = data[i]["roster"]["roster"][j]["person"]["id"]
          position = data[i]["roster"]["roster"][j]["position"]["code"] 
          name = data[i]["roster"]["roster"][j]["person"]["fullName"]
          relevant_Players[ ID ] = [ name, position ]
    return relevant_Players

def reformatDate(date):
    day = date[8:10]
    month = date[5:7]
    year = date[:4]
    return date, day, month, year

def getPlayerStats(player, player_id,season, position):
    url = "https://statsapi.web.nhl.com/api/v1/people/{}/stats?stats=gameLog&season={}".format(player_id,season)
    r = requests.get(url)
    data = r.json()["stats"][0]["splits"]
    important = []
    for i in range(len(data)):
        keyValue = data[i]["stat"]
        keyValue["player"] = player
        keyValue["position"] = position
        keyValue['season'] = data[i]["season"]
        keyValue['team'] = data[i]["team"]['name']
        keyValue['opponent'] = data[i]['opponent']['name']
        keyValue["date"], keyValue['day'], keyValue['month'], keyValue['year'] = reformatDate( data[i]['date'] )
        keyValue["isHome"] = data[i]["isHome"]
        keyValue["isWin"] = data[i]["isWin"]
        keyValue["isOT"] = data[i]["isOT"]

        if position == "G":
            keyValue["fantasyPoints"] = goaliePoints(keyValue)
        else:
            keyValue["fantasyPoints"] = keyValue["goals"]*3 + keyValue["assists"]*2 + keyValue["powerPlayGoals"]*1 + keyValue["shortHandedGoals"]*2


        important.append(keyValue)

    df = pd.io.json.json_normalize(important)
    return df

def goaliePoints(data):
    points = data["goalsAgainst"]*(-1) + data["shutouts"]*3
    if data["isWin"]==True:
        points += 5
    return points

def getPlayerData(season, relevant_Players):
  for ID in relevant_Players.keys():
    name = relevant_Players[ ID ][0]
    pos = relevant_Players[ ID ][1]
    new_Data = getPlayerStats( name, ID, season, pos )

    if(len(new_Data)==0):
      print("Empty: {}, {}".format(name, ID))
    else:
      new_Data = new_Data.sort_values(["year","month","day"], ascending=False)
      try:
          len(df)
      except NameError:
          df = new_Data
      else:
          df = df.append(new_Data, sort=False, ignore_index=True)
  return df

def makeTimeNumeric(List):
    reformatted=[]
    for i in range(len(List)):
        minit,sec=List[i].split(":")
        reformatted.append( ( int(sec)+60*int(minit) )/3600 )
    return reformatted

def boolToNumeric(List):
    reformatted = []
    for i in range(len(List)):
        if(List[i]):
            reformatted.append(1)
        else:
            reformatted.append(.5)
    return reformatted

divideBySixty = lambda x: x/60

def positionToNumeric(List):
    reformatted = []
    for i in range(len(List)):
        if(List[i]=="D"):
            reformatted.append(.25)
        elif(List[i]=="C"):
            reformatted.append(.5)
        elif(List[i]=="L"):
            reformatted.append(.75)
        elif(List[i]=="R"):
            reformatted.append(1.0)
    return reformatted

def percentToDecimal(List):
    reformatted = []
    for i in range(len(List)):
        reformatted.append( List[i]/100 )
    return reformatted

def reformatData( data ):
    df = data
    df = df.loc[ df["position"]!="G" ] #filter out goalies
    df = df.fillna(0)

    for attr in ["timeOnIce","powerPlayTimeOnIce","evenTimeOnIce","shortHandedTimeOnIce"]:
        df[attr] = makeTimeNumeric( df[attr].tolist() )
    
    df["penaltyMinutes"] = list(map(divideBySixty, list(map(int,df["penaltyMinutes"].tolist()))))

    for attr in ["isHome", "isWin","isOT"]:
        df[attr] = boolToNumeric( df[attr].tolist() )
    
    for attr in ["faceOffPct",'shotPct']:
        df[attr] = percentToDecimal( df[attr].tolist() )

    df["position"] = positionToNumeric( df["position"].tolist() )
    goalieColumns=df.columns[36:].tolist()
    df = df.drop(goalieColumns, axis=1)
    df = df.drop(["overTimeGoals","powerPlayPoints"], axis=1)
    df["fantasyPoints"] = list( map( int, df["fantasyPoints"].tolist() ) )
    df["plusMinus"] = map( lambda x: (x+7)/13, df["plusMinus"].tolist() )
    
    df = df.sort_values(["year","month","day"], ascending=False)
    return df

def dropExtraData(data):
    df = data
    extra_columns = ['player', 'games', 'position','season', 'team', 'opponent', 'date', 'day', 'month', 'year']
    df = df.drop(extra_columns, axis=1)
    df = df.fillna(0)
    return df