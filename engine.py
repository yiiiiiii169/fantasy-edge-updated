"""Pure ranking and valuation functions: no network or ESPN credentials."""
import math
import statistics
from datetime import date, timedelta

CATS = ['PTS','REB','AST','STL','BLK','3PM','FG%','FT%','TO']
LOWER = {'TO'}

def num(v, default=0.0):
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default

def split(player, period):
    return player.get('stats', {}).get(period, {}) or {}

def estimate(player, mode='points', horizon=7, weights=(0.50,0.30,0.20), health=True):
    """Blends 7-day, 15-day and season per-GAME measures; returns model estimates."""
    s7, s15, season = (split(player, p) for p in ('last_7','last_15','season'))
    sources = [s7, s15, season]
    valid = [(w,s) for w,s in zip(weights,sources) if s.get('gp',0) > 0]
    if not valid:
        valid = [(1, season)] if season else []
    def blend(key):
        denom = sum(w for w,s in valid if key in s and s[key] is not None)
        return sum(w*num(s.get(key)) for w,s in valid if key in s and s[key] is not None)/denom if denom else 0.0
    pg = blend('fantasy')
    cats = {k:blend(k) for k in CATS}
    games = int(player.get('games',0))
    status = str(player.get('injury','')).upper()
    availability = 1.0
    if health:
        if 'OUT' in status or status in {'O','SUSPENSION','SUSPENDED','INJURED_RESERVE'}: availability=.15
        elif 'DOUBT' in status: availability=.30
        elif 'QUESTION' in status or 'DAY_TO_DAY' in status: availability=.70
        elif 'PROB' in status: availability=.90
    # No injury update makes the factors uncertain, not predictions of return dates.
    return {'per_game':pg,'cats':cats,'games':games,'available':availability,
            'weekly_points':pg*games*availability,
            'long_points':pg*availability, 'status':status}

def category_rankings(players, estimates, cats):
    """Standardized per-game category score across the league pool, not a matchup simulation."""
    means, stdevs = {}, {}
    for cat in cats:
        vals = [estimates[p['key']]['cats'].get(cat,0) for p in players if split(p,'season').get('gp',0)>0]
        means[cat] = statistics.mean(vals) if vals else 0
        stdevs[cat] = max(statistics.pstdev(vals),.01) if len(vals)>1 else 1
    out = {}
    for p in players:
        e = estimates[p['key']]
        z = {}
        for c in cats:
            raw = (e['cats'].get(c,0)-means[c])/stdevs[c]
            # percentages are percentage POINTS per game: low-volume caveat shown in UI
            z[c] = max(-4,min(4, -raw if c in LOWER else raw))
        out[p['key']] = (sum(z.values())/math.sqrt(len(cats)) if cats else 0,z)
    return out

def valuation(players, estimates, mode, cats):
    if mode == 'points':
        return {p['key']: (estimates[p['key']]['long_points'],{}) for p in players}
    ranks = category_rankings(players, estimates, cats)
    return {p['key']:(score*estimates[p['key']]['available'], z) for p in players for score,z in [ranks[p['key']]]}

def trade_candidates(players, estimates, values, my_team, limit=50):
    """1-for-1 plausible trade matches: equal-ish values and positive change for user."""
    mine=[p for p in players if p['owner']==my_team]
    others=[p for p in players if p['owner'] not in {my_team,'FA','WAIVERS'}]
    rows=[]
    for give in mine:
        gv=values[give['key']][0]
        if gv <= 0: continue
        for get in others:
            rv=values[get['key']][0]
            if rv <= gv: continue
            gap=(rv-gv)/max(abs(rv),abs(gv),1)
            if gap > .30: continue # target relatively fair deals, not fantasy wishlists
            rows.append({'Give':give['name'],'Receive':get['name'],'Trade with':get['owner'],
                         'My gain':round(rv-gv,2),'Value gap %':round(gap*100,1),
                         'Give weekly':round(estimates[give['key']]['weekly_points'],1),
                         'Receive weekly':round(estimates[get['key']]['weekly_points'],1),
                         'Note':'Target only — owner acceptance not predicted'})
    return sorted(rows,key=lambda x:(x['My gain'],-x['Value gap %']), reverse=True)[:limit]

def waiver_candidates(players, estimates, values, my_team, mode, min_games=1):
    mine=[p for p in players if p['owner']==my_team and 'IR' not in p.get('slot','').upper()]
    free=[p for p in players if p['owner'] in {'FA','WAIVERS'} and estimates[p['key']]['games']>=min_games]
    rows=[]
    for add in free:
        a=estimates[add['key']]
        for drop in mine:
            d=estimates[drop['key']]
            # weekly pts for points scoring; category proxy scales normalized value by games
            if mode == 'points':
                delta=a['weekly_points']-d['weekly_points']
            else:
                delta=values[add['key']][0]*a['games']-values[drop['key']][0]*d['games']
            if delta>0:
                rows.append({'Add':add['name'],'Drop':drop['name'],'Gain this week':round(delta,1),
                             'Add games':a['games'],'Drop games':d['games'],
                             'Add status':a['status'] or 'Healthy/unknown',
                             'Drop status':d['status'] or 'Healthy/unknown',
                             'Long-term value change':round(values[add['key']][0]-values[drop['key']][0],2),
                             'Availability':'Waivers' if add['owner']=='WAIVERS' else 'Free agent'})
    return sorted(rows,key=lambda x:x['Gain this week'],reverse=True)

def parse_calendar(games, start, days):
    counts={}
    daily={}
    for g in games:
        day=g['date']
        if not (start<=day<start+timedelta(days=days)):continue
        for abbr in (g['away'],g['home']):
            counts[abbr]=counts.get(abbr,0)+1
            daily.setdefault(day,set()).add(abbr)
    return counts,daily
