import { Area, AreaChart, CartesianGrid, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CalendarDays, ChartSpline, Info } from 'lucide-react'
import './ForecastTrajectory.css'

function money(value){return new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2}).format(Number(value))}
function shortDate(value){return value?new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric'}).format(new Date(`${value}T12:00:00`)):'—'}

function TrajectoryTooltip({active,payload}){
  if(!active||!payload?.length)return null
  const point=payload[0].payload
  return <div className="trajectory-tooltip">
    <span>{point.day===0?'Current market close':`Trading day ${point.day}`}</span>
    <strong>{money(point.price)}</strong>
    <div><b>{shortDate(point.date)}</b><small>{point.expected_move_pct>=0?'+':''}{Number(point.expected_move_pct).toFixed(2)}%</small></div>
    {point.day>0&&<><div><b>{point.recommendation}</b><small>{point.confidence}% confidence</small></div><em>{point.source==='interpolated'?'Estimated between production model horizons':'Production horizon model'}</em></>}
  </div>
}

export default function ForecastTrajectory({trajectory=[],ticker=''}){
  if(!trajectory.length)return null
  const prices=trajectory.map(point=>Number(point.price))
  const min=Math.min(...prices),max=Math.max(...prices)
  const spread=Math.max(max-min,max*.01),pad=spread*.35
  const data=trajectory.map(point=>({...point,label:point.day===0?'Now':`Day ${point.day}`}))
  return <section className="forecast-trajectory-section">
    <div className="section-heading"><div><span className="dashboard-eyebrow">PROJECTED DAILY PATH</span><h2>{ticker} forecast trajectory</h2></div><ChartSpline size={30}/></div>
    <div className="trajectory-intro"><CalendarDays size={20}/><p>Each point represents the expected closing-price path for that trading day within the selected horizon.</p></div>
    <div className="trajectory-chart-wrap"><ResponsiveContainer width="100%" height={360}><AreaChart data={data} margin={{top:22,right:24,left:8,bottom:8}}>
      <defs><linearGradient id="trajectoryFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="currentColor" stopOpacity={.28}/><stop offset="100%" stopColor="currentColor" stopOpacity={.02}/></linearGradient></defs>
      <CartesianGrid strokeDasharray="3 7" vertical={false} opacity={.18}/>
      <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={12}/>
      <YAxis domain={[min-pad,max+pad]} tickFormatter={value=>`$${Number(value).toFixed(0)}`} tickLine={false} axisLine={false} width={66}/>
      <Tooltip content={<TrajectoryTooltip/>} cursor={{opacity:.12}}/>
      <ReferenceLine y={trajectory[0].price} strokeDasharray="5 5" opacity={.4} label={{value:'Current',position:'insideTopRight'}}/>
      <Area type="monotone" dataKey="price" stroke="none" fill="url(#trajectoryFill)"/>
      <Line type="monotone" dataKey="price" stroke="currentColor" strokeWidth={4} dot={{r:6,strokeWidth:3,fill:'#07102d'}} activeDot={{r:8,strokeWidth:3}}/>
    </AreaChart></ResponsiveContainer></div>
    <div className="trajectory-day-grid">{trajectory.map(point=><article key={`${point.day}-${point.date}`} className={point.source==='interpolated'?'trajectory-day-card trajectory-day-estimated':'trajectory-day-card'}>
      <span>{point.day===0?'Current':`Day ${point.day}`}</span><strong>{money(point.price)}</strong><small>{shortDate(point.date)}</small>
      {point.day>0&&<div><b>{point.expected_move_pct>=0?'+':''}{Number(point.expected_move_pct).toFixed(2)}%</b><em>{point.confidence}% confidence</em></div>}
    </article>)}</div>
    <div className="trajectory-disclaimer"><Info size={17}/><span>This is a projected sequence of daily closing prices, not a guarantee of the exact path. A day marked “estimated” is interpolated between available production model horizons.</span></div>
  </section>
}
