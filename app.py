import streamlit as st
import pandas as pd
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from engine import CATS, estimate, valuation, trade_candidates, waiver_candidates, parse_calendar
from espn_client import get_league, load_players, nba_games

st.set_page_config(page_title='Fantasy Edge | ESPN NBA',page_icon='🏀',layout='wide')
st.markdown('''<style>
.block-container{padding-top:1.8rem;max-width:1450px}
[data-testid="stMetric"]{border:1px solid #334155;border-radius:12px;padding:12px}
</style>''',unsafe_allow_html=True)
st.title('🏀 FANTASY EDGE')
st.caption('12-team Head-to-Head Points · Private ESPN league · Read-only · Not affiliated with ESPN')
st.info('🌐 Website edition: no Python installation needed. For private-league access, deploy this as a **private Streamlit app** and enter ESPN session cookies only into your own private deployment.')

if 'players' not in st.session_state: st.session_state.players=[]
if 'teams' not in st.session_state: st.session_state.teams=[]
if 'league_label' not in st.session_state: st.session_state.league_label=''
if 'schedule' not in st.session_state: st.session_state.schedule=[]
if 'schedule_issues' not in st.session_state: st.session_state.schedule_issues=[]
if 'last_sync' not in st.session_state: st.session_state.last_sync='Not synced'

nba_today=datetime.now(ZoneInfo('America/New_York')).date()
def start_of_week(d):return d-timedelta(days=d.weekday())
def demo_data():
    # Clearly labelled synthetic demo, not real player results.
    names=['Demo Alpha','Demo Bravo','Demo Charlie','Demo Delta','Demo Echo','Demo Foxtrot',
           'Demo Golf','Demo Hotel','Demo India','Demo Juliet','Demo Kilo','Demo Lima',
           'Demo Mike','Demo November','Demo Oscar','Demo Papa','Demo Quebec','Demo Romeo']
    teams=['My Demo Team']*6+['Rival One']*4+['Rival Two']*4+['FA']*4
    pro=['BOS','DEN','NYK','LAL','GSW','SAS','OKC','CLE','MIA','PHX','TOR','MIN','DAL','MIL','ATL','ORL','HOU','BKN']
    rows=[]
    for i,name in enumerate(names):
        base=18+(i*7)%31
        splits={}
        for tag,mult in [('last_7',1+(.08 if i%3==0 else -.04)),('last_15',1.01),('season',1)]:
            splits[tag]={'gp':4 if tag=='last_7' else 9 if tag=='last_15' else 20,'fantasy':base*mult,
                         'PTS':base*.53*mult,'REB':base*.15,'AST':base*.12,'STL':.9+i%4*.17,
                         'BLK':.4+i%3*.2,'3PM':1.2+i%4*.3,'FG%':44+i%7,
                         'FT%':72+i%13,'TO':1.4+i%4*.5}
        rows.append({'key':str(i),'name':name,'owner':teams[i],'team':pro[i],
                     'position':['PG','SG','SF','PF','C'][i%5],'injury':'QUESTIONABLE' if i==5 else '',
                     'slot':'BE' if i in [4,5] else 'UT','games':0,'stats':splits})
    return rows,['My Demo Team','Rival One','Rival Two']

with st.sidebar:
    st.header('🔐 ESPN connection')
    st.caption('Only connect on a private, access-restricted deployment that you control. These browser session cookies grant access to your ESPN account. Never share them or put them in GitHub.')
    year_default=nba_today.year+1 if nba_today.month>=10 else nba_today.year
    league_id=st.text_input('ESPN League ID',placeholder='Numbers in your league URL')
    season=st.number_input('ESPN season year',min_value=2020,max_value=2040,value=year_default)
    s2=st.text_input('espn_s2 cookie',type='password',help='Your ESPN browser session cookie. Do not share it.')
    swid=st.text_input('SWID cookie',type='password',help='Include braces if the value contains them.')
    agents=st.slider('Free agents to scan',40,300,160,20)
    if st.button('🔄 Connect / refresh league',type='primary',use_container_width=True):
        if not (league_id.isdigit() and s2.strip() and swid.strip()):
            st.error('Enter a numeric league ID and both cookies.')
        else:
            try:
                with st.spinner('Reading ESPN league, teams and waiver pool…'):
                    league=get_league(int(league_id),int(season),s2,swid)
                    players, teams=load_players(league,agents)
                st.session_state.players=players
                st.session_state.teams=teams
                st.session_state.league_label=f'ESPN League {league_id} · {season}'
                st.session_state.last_sync=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                st.success(f'Synced {len(teams)} fantasy teams and {len(players)} players.')
            except Exception as exc:
                # Don't print full exception objects: some libraries include URLs/headers.
                st.error('ESPN connection failed. Check league ID, season, cookies and league access. ESPN may change its unofficial API.')
                st.caption(f'Error class: {type(exc).__name__}')
    if st.button('Try synthetic demo',use_container_width=True):
        st.session_state.players,st.session_state.teams=demo_data()
        st.session_state.league_label='SYNTHETIC DEMO — NOT LIVE DATA'
        st.session_state.last_sync='Demo'
    if st.button('Clear loaded league',use_container_width=True):
        for k,v in [('players',[]),('teams',[]),('league_label',''),('schedule',[]),('schedule_issues',[]),('last_sync','Not synced')]:st.session_state[k]=v
        st.rerun()
    st.divider()
    st.header('📅 Scoring window')
    start=st.date_input('Start (NBA Eastern Time)',value=start_of_week(nba_today))
    days=st.slider('Days to analyse',1,14,7)
    if st.button('Refresh NBA schedule',use_container_width=True):
        if st.session_state.league_label.startswith('SYNTHETIC'):
            # Demo schedule is fabricated and labelled, as with demo player data.
            pro=['BOS','DEN','NYK','LAL','GSW','SAS','OKC','CLE','MIA','PHX','TOR','MIN','DAL','MIL','ATL','ORL','HOU','BKN']
            st.session_state.schedule=[{'date':start+timedelta(days=i),'away':pro[(2*i+j)%len(pro)],'home':pro[(2*i+j+1)%len(pro)]} for i in range(days) for j in range(4)]
            st.session_state.schedule_issues=[]
        else:
            with st.spinner('Loading public NBA game calendar…'):
                st.session_state.schedule,st.session_state.schedule_issues=nba_games(start,days)
        st.success(f'Found {len(st.session_state.schedule)} games.')
    st.caption('The schedule is loaded separately so a partial scoreboard outage never erases your league data.')

players=st.session_state.players
if not players:
    st.info('Start by connecting your ESPN league in the left sidebar, or click **Try synthetic demo** to explore all tools safely.')
    st.markdown('### What the dashboard does')
    st.markdown("""**Waiver radar** · ranked add/drop combinations by expected scoring-window improvement.  
**Trade lab** · investigate manual trades and shortlist near-value trade targets from other fantasy teams.  
**Schedule edge** · games per player and by NBA date.  
**Risk board** · statuses, schedule flags and recent-vs-season performance.""")
    st.stop()

counts, by_day=parse_calendar(st.session_state.schedule,start,days)
for p in players:p['games']=counts.get(p['team'],0)
team_choice=st.selectbox('Select your fantasy team',st.session_state.teams)
score_mode=st.radio('League scoring system',['Points','9-category / custom categories'],horizontal=True,
    help='Choose your actual ESPN scoring format; category mode is a standardized proxy, not an exact H2H win probability.')
mode='points' if score_mode=='Points' else 'cats'
cats=st.multiselect('Categories included',CATS,default=CATS) if mode=='cats' else []
if mode=='cats' and not cats: st.warning('Select at least one category.'); st.stop()
w7=st.slider('Weight: last 7 days',0,100,50,5)
w15=st.slider('Weight: last 15 days',0,100-w7,30 if 100-w7>=30 else 100-w7,5)
weight=((w7)/100,w15/100,(100-w7-w15)/100)
health=st.checkbox('Apply conservative injury availability discounts (heuristic)',value=True)
ests={p['key']:estimate(p,mode,days,weight,health) for p in players}
vals=valuation(players,ests,mode,cats)

def score(p):return vals[p['key']][0]
def fmt_player(p):
    e=ests[p['key']]
    return {'Player':p['name'],'NBA':p['team'],'Position':p['position'],'Owner':p['owner'],
            'Injury status':p['injury'] or 'Not flagged','Games':e['games'],
            'Last 7':round(p['stats'].get('last_7',{}).get('fantasy',0),1),
            'Season':round(p['stats'].get('season',{}).get('fantasy',0),1),
            'Blended per game':round(e['per_game'],1),
            'Est. week pts':round(e['weekly_points'],1),
            'Relative value':round(score(p),2)}

mine=[p for p in players if p['owner']==team_choice]
free=[p for p in players if p['owner'] in ('FA','WAIVERS')]
other=[p for p in players if p['owner'] not in ('FA','WAIVERS',team_choice)]
st.caption(f'**{st.session_state.league_label}** · last sync: {st.session_state.last_sync} · {len(players)} players · schedule: {len(st.session_state.schedule)} NBA games')
if not st.session_state.league_label.startswith('SYNTHETIC') and len(st.session_state.teams)!=12:
    st.warning(f'This dashboard is tuned for 12-team H2H points. ESPN returned {len(st.session_state.teams)} teams. Check your selected league ID.')
if not st.session_state.schedule: st.warning('No NBA schedule loaded. Click **Refresh NBA schedule** in the sidebar: weekly games and waiver/trade weekly estimates will otherwise be zero.')
if st.session_state.schedule_issues:st.warning('Incomplete NBA schedule: '+', '.join(st.session_state.schedule_issues[:3]))

c1,c2,c3,c4=st.columns(4)
c1.metric('Your roster',len(mine))
c2.metric('Available players scanned',len(free))
c3.metric('Your scheduled player-games',sum(ests[p['key']]['games'] for p in mine))
c4.metric('Your estimated weekly points',f"{sum(ests[p['key']]['weekly_points'] for p in mine):.0f}" if mode=='points' else 'Category mode')
st.caption('Weekly totals are **opportunity estimates**, not guaranteed starters or actual projected fantasy scores. Bench/IR, daily start limits and scoring-specific caps are not automatically enforced.')

tabs=st.tabs(['🏠 Roster & form','🎯 H2H matchup','➕ Waiver radar','🔁 Trade lab','🗓️ Schedule edge','🚨 Risk & strategy'])
with tabs[0]:
    st.subheader('Your team: recent form versus season')
    df=pd.DataFrame([fmt_player(p) for p in mine])
    if not df.empty:st.dataframe(df.sort_values('Relative value',ascending=False),use_container_width=True,hide_index=True)
    st.caption('Last 7/season values are ESPN per-game *fantasy points* when available. For category scoring, rely on Relative value, not fantasy-point columns.')
    st.subheader('Current fantasy team rankings (blended per-game value)')
    team_values=[]
    for t in st.session_state.teams:
        owned=[p for p in players if p['owner']==t]
        team_values.append({'Fantasy team':t,'Players':len(owned),'Combined per-game relative value':round(sum(score(p) for p in owned),2),
                            'Scheduled player-games':sum(ests[p['key']]['games'] for p in owned)})
    st.dataframe(pd.DataFrame(team_values).sort_values('Combined per-game relative value',ascending=False),hide_index=True,use_container_width=True)
with tabs[1]:
    st.subheader('🎯 Weekly matchup scout — H2H points')
    st.caption('Compare your scheduled-week player opportunities with an opposing fantasy roster. Assumes every scheduled player can start: bench limits, IR, add/drop limits and ESPN matchup live scores are not included.')
    rivals=[t for t in st.session_state.teams if t!=team_choice]
    if rivals:
        target=st.selectbox('Your opponent this week',rivals,key='weekly_opponent')
        theirs=[p for p in players if p['owner']==target]
        yours_total=sum(ests[p['key']]['weekly_points'] for p in mine)
        their_total=sum(ests[p['key']]['weekly_points'] for p in theirs)
        col_a,col_b,col_c=st.columns(3)
        col_a.metric('Your model estimate',f'{yours_total:.0f} pts')
        col_b.metric('Opponent model estimate',f'{their_total:.0f} pts')
        col_c.metric('Estimated advantage',f'{yours_total-their_total:+.0f} pts')
        if mode=='points':
            st.write('**Opponent top projected contributors**')
            st.dataframe(pd.DataFrame([fmt_player(p) for p in sorted(theirs,key=lambda p:ests[p['key']]['weekly_points'],reverse=True)[:12]]),use_container_width=True,hide_index=True)
        st.caption('Select your actual opponent manually. ESPN matchups and remaining lineups are not yet synced; this is a comparison of whole-roster schedule estimates, NOT a win probability.')
    else:
        st.info('No opponent roster found. Sync a complete league.')

with tabs[2]:
    st.subheader('Top add/drop opportunities')
    ming=st.slider('Minimum NBA games for an add',0,7,1)
    waivers=waiver_candidates(players,ests,vals,team_choice,mode,ming)
    if waivers:
        st.dataframe(pd.DataFrame(waivers[:100]),use_container_width=True,hide_index=True)
        best=waivers[0]
        st.success(f"Leading estimated weekly switch: add {best['Add']}, drop {best['Drop']} (model gain: {best['Gain this week']:+.1f}).")
    else: st.info('No positive add/drop pair found with the current scoring window and data. Check the NBA schedule and ESPN stats.')
    st.subheader('Top available individual players')
    order=sorted(free,key=lambda p:ests[p['key']]['weekly_points'] if mode=='points' else score(p)*ests[p['key']]['games'],reverse=True)
    if order:st.dataframe(pd.DataFrame([fmt_player(p) for p in order[:75]]),hide_index=True,use_container_width=True)
    st.caption('Before making a move: verify ESPN eligibility, waiver processing, acquisition limits and whether the added player can actually fit an active lineup slot.')
with tabs[3]:
    st.subheader('Trade targets from league rivals')
    st.caption('The shortlist filters to 1-for-1 trades within ~30% of estimated value; counterparties are not guaranteed to accept.')
    trades=trade_candidates(players,ests,vals,team_choice)
    if trades:st.dataframe(pd.DataFrame(trades),hide_index=True,use_container_width=True)
    else:st.info('No relatively close upgrades found with the current sample. Use the manual trade comparison below.')
    st.subheader('Build your own 1-for-1 trade')
    if mine and other:
        give=st.selectbox('You send',mine,format_func=lambda p:f"{p['name']} · {p['position']}")
        receive=st.selectbox('You receive',other,format_func=lambda p:f"{p['name']} · {p['owner']}")
        g=ests[give['key']];r=ests[receive['key']]
        a,b=st.columns(2)
        a.metric('Per-game value gain',f'{score(receive)-score(give):+.2f}')
        if mode=='points':b.metric('This-week estimate change',f"{r['weekly_points']-g['weekly_points']:+.1f}")
        else:b.metric('Category proxy × games change',f"{score(receive)*r['games']-score(give)*g['games']:+.2f}")
        st.write(f"**Sending:** {give['name']} ({give['team']}, {g['games']} games, {g['status'] or 'no status flag'})")
        st.write(f"**Receiving:** {receive['name']} ({receive['team']}, {r['games']} games, {r['status'] or 'no status flag'})")
        if mode=='cats':
            diffs={c:round(vals[receive['key']][1].get(c,0)-vals[give['key']][1].get(c,0),2) for c in cats}
            st.write('Per-category relative gain (z-score units):');st.dataframe(pd.DataFrame([diffs]),hide_index=True)
        st.caption('This assesses your side only. Salary, roster sizes, positional legality, multi-player trade effects, injured slots and rival motivations need separate consideration.')
    st.subheader('2-for-1 and package trade calculator')
    st.caption('Use this for up to three players on each side. Empty slots represent roster spots that must be filled separately.')
    my_package=st.multiselect('Players you send (up to 3)',mine,max_selections=3,format_func=lambda p: p['name'],key='package_send')
    rival_team_names=sorted(set(p['owner'] for p in other))
    rival=st.selectbox('Other fantasy team',rival_team_names,key='package_rival') if rival_team_names else None
    their_players=[p for p in other if p['owner']==rival]
    their_package=st.multiselect('Players you receive (up to 3)',their_players,max_selections=3,format_func=lambda p: p['name'],key='package_receive')
    if my_package and their_package:
        my_sum=sum(score(p) for p in my_package)
        their_sum=sum(score(p) for p in their_package)
        st.metric('Your net per-game value gain',f'{their_sum-my_sum:+.2f}')
        st.caption(f'Roster slots freed: {len(my_package)-len(their_package):+d}. A 2-for-1 trade requires modelling the replacement-level player you can add into the extra slot. This calculator does not include that replacement automatically.')
        if mode=='points':
            wgain=sum(ests[p['key']]['weekly_points'] for p in their_package)-sum(ests[p['key']]['weekly_points'] for p in my_package)
            st.metric('Scheduled-week opportunity difference',f'{wgain:+.1f}')
        if mode=='cats':
            impact={c:round(sum(vals[p['key']][1].get(c,0) for p in their_package)-sum(vals[p['key']][1].get(c,0) for p in my_package),2) for c in cats}
            st.dataframe(pd.DataFrame([impact]),hide_index=True)
with tabs[4]:
    st.subheader('NBA game density for the selected period')
    sc=pd.DataFrame([{'Date (NBA ET)':(start+timedelta(days=i)).isoformat(),
                      'Games':sum(1 for x in st.session_state.schedule if x['date']==start+timedelta(days=i))} for i in range(days)])
    st.bar_chart(sc.set_index('Date (NBA ET)')['Games'])
    byteam=pd.DataFrame([{'NBA team':t,'Games':c} for t,c in counts.items()]).sort_values('Games',ascending=False) if counts else pd.DataFrame(columns=['NBA team','Games'])
    st.dataframe(byteam,use_container_width=True,hide_index=True)
    st.subheader('My roster per-day scheduled games')
    matrix=[]
    for p in mine:
        row={'Player':p['name'],'NBA':p['team']}
        for i in range(days):
            d=start+timedelta(days=i);row[d.strftime('%a %d')]='●' if p['team'] in by_day.get(d,set()) else ''
        matrix.append(row)
    st.dataframe(pd.DataFrame(matrix),hide_index=True,use_container_width=True)
    st.caption('Use days with fewer of your existing players scheduled to find streams that might actually fit your lineup.')
with tabs[5]:
    st.subheader('Injury flags requiring review')
    flagged=[p for p in players if p['owner']==team_choice and p['injury'] and str(p['injury']).upper() not in {'ACTIVE','HEALTHY'}]
    if flagged:st.dataframe(pd.DataFrame([fmt_player(p) for p in flagged]),hide_index=True,use_container_width=True)
    else:st.info('No injuries flagged by the ESPN records in this sync. Check official injury updates before tipoff.')
    st.subheader('Hot / cold watchlist')
    records=[]
    for p in mine+free:
        a=p['stats'].get('last_7',{});b=p['stats'].get('season',{})
        recent=a.get('fantasy',0);season_val=b.get('fantasy',0)
        if a.get('gp',0)>0 and b.get('gp',0)>0 and season_val>0:
            records.append({'Player':p['name'],'Owner':p['owner'],'Last 7':round(recent,1),'Season':round(season_val,1),
                            'Change %':round((recent/season_val-1)*100,1),'Injury':p['injury'] or ''})
    if records:
        a=pd.DataFrame(records).sort_values('Change %',ascending=False)
        st.dataframe(a.head(25),hide_index=True,use_container_width=True)
    st.subheader('Weekly winning checklist')
    for item in ['Confirm your exact league scoring and acquisition limits','Review tomorrow’s lineup and tipoff times',
                 'Prioritise healthy players who can actually start on low-volume days',
                 'Check questionable players against a fresh official injury report',
                 'Avoid dropping proven high-upside players for one extra streaming game',
                 'Judge trades on long-term value, category needs and the opponent’s roster']:
        st.checkbox(item,value=False,key='check_'+item)
    st.caption('Models use weighted recent form; past performance and injury statuses do not guarantee future outcomes. All trades/adds/drops must be submitted in ESPN.')
