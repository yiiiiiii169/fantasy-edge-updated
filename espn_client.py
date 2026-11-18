"""Read-only ESPN Fantasy Basketball integration. Credentials stay in memory."""
import requests
from datetime import datetime, timedelta, timezone
from engine import num

from espn_api.basketball import League

TEAM_ALIASES={'PHL':'PHI','PHO':'PHX','WSH':'WAS','GS':'GSW','NY':'NYK','SA':'SAS','NO':'NOP','UTAH':'UTA'}

def alias(team):
    t=(team or '').upper()
    return TEAM_ALIASES.get(t,t)

def get_league(league_id,year,espn_s2,swid):
    # This dependency uses ESPN's unofficial endpoints. Never log tokens.
    return League(league_id=int(league_id),year=int(year),espn_s2=espn_s2.strip(),swid=swid.strip())

def player_data(p, owner, slot=''):
    stats={}
    for suffix, key in [('last_7','last_7'),('last_15','last_15'),('total','season')]:
        # Some ESPN splits are absent early in the season.
        parts=[(k,v) for k,v in p.stats.items() if k.endswith('_'+suffix)]
        item=parts[0][1] if parts else {}
        avg=item.get('avg') or {}
        # ESPN's avg can contain all relevant 9cat plus applied ESPN fantasy points.
        # gp from total GP stat if available; projected splits are not used.
        gp=num((item.get('total') or {}).get('GP'))
        if not gp:
            total=(item.get('total') or {})
            gp=num(total.get('MIN'))/max(num(avg.get('MIN')),1) if avg.get('MIN') else 0
        stats[key]={'fantasy':num(item.get('applied_avg')),'gp':gp or (1 if item else 0)}
        for cat in ['PTS','REB','AST','STL','BLK','3PM','FG%','FT%','TO','FGM','FGA','FTM','FTA']:
            if cat in avg:stats[key][cat]=num(avg[cat])
        # ESPN percentage splits can be 0-100, normalize if clearly 0-1.
        for cat in ('FG%','FT%'):
            if cat in stats[key] and 0 < stats[key][cat] <= 1: stats[key][cat]*=100
    return {'key':str(p.playerId),'name':p.name,'owner':owner,'team':alias(p.proTeam),
            'slot':slot or p.lineupSlot,'position':p.position,'injury':p.injuryStatus or '',
            'stats':stats,'games':0}

def load_players(league, free_count=180):
    seen={}
    teams=[]
    for team in league.teams:
        teams.append(team.team_name)
        for p in team.roster:
            row=player_data(p,team.team_name,p.lineupSlot)
            seen[row['key']]=row
    # ESPN usually returns top free agents by roster percentage.
    free=league.free_agents(size=int(free_count))
    for p in free:
        row=player_data(p,'WAIVERS' if (p.acquisitionType or '').upper()=='WAIVERS' else 'FA')
        if row['key'] not in seen: seen[row['key']]=row
    return list(seen.values()),teams

def nba_games(start,days=7):
    """ESPN public NBA scoreboard. ESPN game dates are UTC; scoring day is ET."""
    session=requests.Session()
    games=[]; issues=[]; seen=set()
    # Endpoint supports a date range; schedule can vary, so query individual dates.
    for offset in range(days):
        day=start+timedelta(days=offset)
        try:
            r=session.get('https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard',
                params={'dates':day.strftime('%Y%m%d'),'limit':100},timeout=12)
            r.raise_for_status()
            for e in r.json().get('events',[]):
                if e.get('id') in seen: continue
                comp=(e.get('competitions') or [{}])[0]
                participants=comp.get('competitors',[])
                away=next((x for x in participants if x.get('homeAway')=='away'),{})
                home=next((x for x in participants if x.get('homeAway')=='home'),{})
                if not (away and home):continue
                # Dates query uses NBA schedule's America/New_York calendar.
                games.append({'id':e.get('id'),'date':day,'away':alias(away.get('team',{}).get('abbreviation')),
                              'home':alias(home.get('team',{}).get('abbreviation'))})
                seen.add(e.get('id'))
        except (requests.RequestException,ValueError) as exc:
            issues.append(f'{day.isoformat()}: schedule unavailable ({type(exc).__name__})')
    return games,issues
