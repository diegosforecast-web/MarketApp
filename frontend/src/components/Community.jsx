import { useCallback, useEffect, useState } from 'react'
import {
  CheckCircle2, CircleAlert, HeartHandshake, Lightbulb,
  LoaderCircle, Map, MessageSquareText, Send, Sparkles,
  Star, ThumbsUp,
} from 'lucide-react'
import { supabase } from '../lib/supabase'
import './Community.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'
const STATUS = {submitted:'Submitted',planned:'Planned',in_progress:'In progress',completed:'Completed',declined:'Declined'}

async function headers(json=false){
  const {data:{session}}=await supabase.auth.getSession()
  if(!session?.access_token) throw new Error('Your session has expired. Please sign in again.')
  return {Authorization:`Bearer ${session.access_token}`,...(json?{'Content-Type':'application/json'}:{})}
}

function Stars({value,onChange,readOnly=false}){
  return <div className="community-stars">{[1,2,3,4,5].map(star=><button key={star} type="button" disabled={readOnly} className={star<=value?'community-star-active':''} onClick={()=>onChange?.(star)} aria-label={`${star} stars`}><Star size={22} fill={star<=value?'currentColor':'none'}/></button>)}</div>
}

export default function Community(){
  const [summary,setSummary]=useState(null),[loading,setLoading]=useState(true),[busy,setBusy]=useState(''),[error,setError]=useState(''),[message,setMessage]=useState('')
  const [rating,setRating]=useState(5),[reviewTitle,setReviewTitle]=useState(''),[reviewBody,setReviewBody]=useState(''),[publishConsent,setPublishConsent]=useState(false),[publishName,setPublishName]=useState(false),[displayName,setDisplayName]=useState('')
  const [featureTitle,setFeatureTitle]=useState(''),[featureDescription,setFeatureDescription]=useState('')

  const load=useCallback(async()=>{
    setLoading(true);setError('')
    try{
      const response=await fetch(`${API_URL}/community/summary`,{headers:await headers()})
      const payload=await response.json().catch(()=>null)
      if(!response.ok) throw new Error(payload?.detail||`Unable to load community (${response.status}).`)
      setSummary(payload)
    }catch(err){setError(err.message||'Unable to load community.')}finally{setLoading(false)}
  },[])
  useEffect(()=>{load()},[load])

  async function submitReview(event){
    event.preventDefault();setBusy('review');setError('');setMessage('')
    try{
      const response=await fetch(`${API_URL}/community/reviews`,{method:'POST',headers:await headers(true),body:JSON.stringify({rating,title:reviewTitle,body:reviewBody,publish_consent:publishConsent,publish_name:publishConsent&&publishName,display_name:publishConsent&&publishName?displayName:null})})
      const payload=await response.json().catch(()=>null)
      if(!response.ok) throw new Error(payload?.detail||`Unable to save review (${response.status}).`)
      setMessage(publishConsent?'Your review was saved and approved for public display.':'Your private review was saved.')
      setReviewTitle('');setReviewBody('');await load()
    }catch(err){setError(err.message||'Unable to save review.')}finally{setBusy('')}
  }

  async function submitFeature(event){
    event.preventDefault();setBusy('feature');setError('');setMessage('')
    try{
      const response=await fetch(`${API_URL}/community/features`,{method:'POST',headers:await headers(true),body:JSON.stringify({title:featureTitle,description:featureDescription})})
      const payload=await response.json().catch(()=>null)
      if(!response.ok) throw new Error(payload?.detail||`Unable to save feature request (${response.status}).`)
      setMessage('Your feature request was submitted.');setFeatureTitle('');setFeatureDescription('');await load()
    }catch(err){setError(err.message||'Unable to save feature request.')}finally{setBusy('')}
  }

  async function vote(id){
    setBusy(`vote-${id}`);setError('')
    try{
      const response=await fetch(`${API_URL}/community/features/${id}/vote`,{method:'POST',headers:await headers()})
      const payload=await response.json().catch(()=>null)
      if(!response.ok) throw new Error(payload?.detail||`Unable to update vote (${response.status}).`)
      await load()
    }catch(err){setError(err.message||'Unable to update vote.')}finally{setBusy('')}
  }

  return <section id="community" className="community-section">
    <div className="section-heading community-heading"><div><span className="dashboard-eyebrow">DIMARKET COMMUNITY</span><h2>Help shape what DiMarket becomes next.</h2><p>Share a review, submit a feature request, vote on ideas, and follow the public roadmap.</p></div><HeartHandshake size={32}/></div>
    {loading&&<div className="community-state"><LoaderCircle className="community-spinner" size={26}/>Loading the community...</div>}
    {error&&<div className="community-message community-message-error"><CircleAlert size={19}/>{error}</div>}
    {message&&<div className="community-message community-message-success"><CheckCircle2 size={19}/>{message}</div>}
    {!loading&&summary&&<>
      <div className="community-overview-grid">
        <article className="community-rating-card"><span className="dashboard-eyebrow">COMMUNITY RATING</span><strong>{summary.published_review_count?Number(summary.rating_average).toFixed(1):'Not rated yet'}</strong><Stars value={Math.round(summary.rating_average||0)} readOnly/><p>{summary.published_review_count?`${summary.published_review_count} published review${summary.published_review_count===1?'':'s'}`:'The rating appears only after explicit publication consent.'}</p></article>
        <article className="community-mission-card"><Sparkles size={25}/><div><span className="dashboard-eyebrow">OUR MISSION</span><h3>Trust is earned through accountability.</h3><p>Investors deserve transparent AI. Every forecast should explain itself, preserve its original prediction, and eventually be measured against reality.</p></div></article>
      </div>

      <div className="community-form-grid">
        <form className="community-form-card" onSubmit={submitReview}><div className="community-form-heading"><MessageSquareText size={23}/><div><h3>Review DiMarket</h3><p>Your review stays private unless you consent.</p></div></div><label>Rating<Stars value={rating} onChange={setRating}/></label><label>Review title<input value={reviewTitle} onChange={e=>setReviewTitle(e.target.value)} minLength={3} maxLength={120} required/></label><label>Review<textarea value={reviewBody} onChange={e=>setReviewBody(e.target.value)} minLength={10} maxLength={1500} rows={5} required/></label><label className="community-consent-row"><input type="checkbox" checked={publishConsent} onChange={e=>{setPublishConsent(e.target.checked);if(!e.target.checked)setPublishName(false)}}/>I consent to publishing this review.</label>{publishConsent&&<><label className="community-consent-row"><input type="checkbox" checked={publishName} onChange={e=>setPublishName(e.target.checked)}/>Publish using my chosen first name.</label>{publishName&&<label>Public first name<input value={displayName} onChange={e=>setDisplayName(e.target.value)} maxLength={80} required/></label>}</>}<button disabled={busy==='review'}><Send size={18}/>{busy==='review'?'Saving review...':'Save review'}</button></form>
        <form className="community-form-card" onSubmit={submitFeature}><div className="community-form-heading"><Lightbulb size={23}/><div><h3>Request a feature</h3><p>Submit one focused improvement at a time.</p></div></div><label>Feature title<input value={featureTitle} onChange={e=>setFeatureTitle(e.target.value)} minLength={3} maxLength={140} required/></label><label>Why would this help?<textarea value={featureDescription} onChange={e=>setFeatureDescription(e.target.value)} minLength={10} maxLength={1200} rows={8} required/></label><button disabled={busy==='feature'}><Send size={18}/>{busy==='feature'?'Submitting request...':'Submit feature request'}</button></form>
      </div>

      <section className="community-list-section"><div className="community-subheading"><div><span className="dashboard-eyebrow">FEATURE REQUESTS</span><h3>Vote on what matters most.</h3></div><Lightbulb size={25}/></div><div className="feature-request-list">{summary.feature_requests.length?summary.feature_requests.map(feature=><article key={feature.id}><div><span className={`community-status community-status-${feature.status}`}>{STATUS[feature.status]||feature.status}</span><h4>{feature.title}</h4><p>{feature.description}</p></div><button type="button" className={feature.user_voted?'feature-vote-button feature-vote-active':'feature-vote-button'} disabled={busy===`vote-${feature.id}`} onClick={()=>vote(feature.id)}><ThumbsUp size={18} fill={feature.user_voted?'currentColor':'none'}/>{feature.votes}</button></article>):<div className="community-empty">No feature requests yet.</div>}</div></section>

      <section className="community-list-section"><div className="community-subheading"><div><span className="dashboard-eyebrow">PUBLIC ROADMAP</span><h3>Simple, visible progress.</h3></div><Map size={25}/></div><div className="community-roadmap-grid">{summary.roadmap.map(item=><article key={item.id}><span className={`community-status community-status-${item.status}`}>{STATUS[item.status]||item.status}</span><h4>{item.title}</h4><p>{item.description}</p></article>)}</div></section>

      <section className="community-list-section"><div className="community-subheading"><div><span className="dashboard-eyebrow">PUBLISHED REVIEWS</span><h3>Shared only with explicit consent.</h3></div><MessageSquareText size={25}/></div><div className="community-review-grid">{summary.reviews.length?summary.reviews.map(review=><article key={review.id}><Stars value={Number(review.rating)} readOnly/><h4>{review.title}</h4><p>{review.body}</p><span>{review.author}</span></article>):<div className="community-empty">No public reviews yet.</div>}</div></section>
    </>}
  </section>
}
