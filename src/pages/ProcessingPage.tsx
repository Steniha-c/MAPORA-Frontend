import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { Activity, AlertTriangle, ArrowLeft, ArrowRight, Check, Clock3, FileImage, FileVideo2, Grid2X2, Images, LoaderCircle, RefreshCw, Video, Box } from 'lucide-react';
import { isApiConfigured, maporaApi } from '../services/api';
import type { ProcessingStatus } from '../types';
import { useAuth } from '../auth/AuthContext';

const stages = [
  'Video preprocessing',
  'Frame extraction and keyframes',
  'Camera pose estimation',
  'Monocular depth estimation',
  'Semantic segmentation',
  'SLAM and point-cloud generation',
  'Floor-plan extraction',
  '3D reconstruction',
];

const STAGE_INDEX_MAP: Record<string, number> = {
  validating: 0,
  validating_images: 0,
  video_preprocessing: 0,
  preprocessing: 0,
  extracting_keyframes: 1,
  extracting_features: 1,
  feature_extraction: 1,
  keyframe_extraction: 1,
  estimating_geometry: 2,
  estimating_cameras: 2,
  camera_pose_estimation: 2,
  pose_estimation: 2,
  depth_estimation: 3,
  monocular_depth: 3,
  semantic_segmentation: 4,
  spatial_reconstruction: 5,
  point_cloud: 5,
  generating_floor_plan: 6,
  floor_plan_extraction: 6,
  generating_3d_model: 7,
  reconstruction_3d: 7,
  completed: 8,
};

const STAGE_DISPLAY_TITLES: Record<string, string> = {
  validating: 'Video preprocessing',
  validating_images: 'Photo validation & quality check',
  video_preprocessing: 'Video preprocessing',
  extracting_keyframes: 'Frame extraction and keyframes',
  extracting_features: 'Multi-view feature extraction',
  estimating_geometry: 'Camera pose estimation',
  estimating_cameras: 'Camera pose & epipolar estimation',
  camera_pose_estimation: 'Camera pose estimation',
  depth_estimation: 'Monocular depth estimation',
  semantic_segmentation: 'Semantic segmentation',
  spatial_reconstruction: 'SLAM and point-cloud generation',
  generating_floor_plan: 'Floor-plan extraction',
  generating_3d_model: '3D reconstruction',
  completed: 'All stages completed',
};

const stageOrder = (current: string): number => {
  if (!current) return -1;
  const normalized = current.trim().toLowerCase().replace(/[-\s]+/g, '_');
  if (normalized in STAGE_INDEX_MAP) {
    return STAGE_INDEX_MAP[normalized];
  }
  return stages.findIndex(stage =>
    normalized.includes(stage.toLowerCase().replace(/[-\s]+/g, '_')) ||
    stage.toLowerCase().includes(normalized) ||
    normalized.includes(stage.split(' ')[0].toLowerCase())
  );
};

const getDisplayStage = (currentStage?: string | null): string => {
  if (!currentStage) return 'Awaiting backend status';
  const normalized = currentStage.trim().toLowerCase().replace(/[-\s]+/g, '_');
  return STAGE_DISPLAY_TITLES[normalized] || currentStage;
};

export default function ProcessingPage() {
  const {id=''}=useParams();const location=useLocation() as {state?:{fileName?:string}};const {session}=useAuth();const [status,setStatus]=useState<ProcessingStatus|null>(null);const [error,setError]=useState('');const [loading,setLoading]=useState(false);const [retrying,setRetrying]=useState(false);
  const refresh=useCallback(async()=>{if(!isApiConfigured){setStatus(null);setError('Processing status is unknown because the MAPORA backend is not configured. No job was started by this page.');return;}setLoading(true);try{const result=await maporaApi.getProcessingStatus(id,session?.accessToken);setStatus(result);setError('');}catch(cause){setStatus(null);setError(cause instanceof Error?cause.message:'Could not read processing status.');}finally{setLoading(false);}},[id,session]);
  useEffect(()=>{void refresh();if(!isApiConfigured)return;const interval=window.setInterval(()=>void refresh(),5000);return()=>window.clearInterval(interval);},[refresh]);
  const retry=async()=>{if(!isApiConfigured)return;setRetrying(true);try{setStatus(await maporaApi.retryProcessing(id,session?.accessToken));setError('');}catch(cause){setError(cause instanceof Error?cause.message:'Retry request failed.');}finally{setRetrying(false);}};
  const active=stageOrder(status?.stage||'');const complete=status?.status==='completed';const failed=status?.status==='failed';
  return <div className="page processing-page"><div className="page-back"><Link to={`/projects/${id}/upload`}><ArrowLeft size={15}/> Back to upload</Link><span className={`demo-flag ${status?'':'unknown-flag'}`}><span className="status-dot"/>{status?'LIVE BACKEND STATUS':'STATUS UNKNOWN'}</span></div><div className="processing-header"><div><div className="eyebrow app-eyebrow">MAPPING WORKFLOW <span className="eyebrow-line"/></div><h1>{complete?'Mapping complete.':failed?'Mapping needs attention.':'Your space is taking shape.'}</h1><p className="muted">{status?.message||'Processing state is read from the MAPORA backend. No local progress is inferred.'}</p></div><div className="processing-orbit"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><span className="orbit-center">{loading?<LoaderCircle size={22}/>:<Activity size={20}/>}</span></div></div>{error&&<div className="processing-demo-warning" role="status"><AlertTriangle size={16}/><span><b>{isApiConfigured?'Status unavailable':'Status unknown'}:</b> {error}</span></div>}<div className="processing-layout"><section className="processing-card"><div className="processing-card-top"><div><span className="section-kicker">RECONSTRUCTION PIPELINE</span><h2>{failed?'Processing failed':complete?'All stages completed':getDisplayStage(status?.stage)}</h2></div><span className={`processing-status ${complete?'status-ready':failed?'status-error':''}`}><i/>{status?.status?.toUpperCase()||'UNKNOWN'}</span></div><div className="processing-progress"><div style={{width:`${complete?100:status?.progress!=null?Math.max(0,Math.min(status.progress,100)):0}%`}}/></div><div className="stage-list">{stages.map((stage,index)=>{const done=complete||(active>=0&&index<active&&status?.status==='processing');const current=index===active&&status?.status==='processing';return <div key={stage} className={`stage-row ${done?'complete':''} ${current?'current':''}`}><span className="stage-check">{done?<Check size={13}/>:current?<LoaderCircle size={13} className="spin"/>:<span>{String(index+1).padStart(2,'0')}</span>}</span><span>{stage}</span><span className="stage-meta">{done?'BACKEND COMPLETE':current?'BACKEND ACTIVE':'PENDING / UNKNOWN'}</span></div>;})}</div><div className="processing-card-foot"><span>{location.state?.fileName?.includes('photo')?<FileImage size={14}/>:<FileVideo2 size={14}/>}{location.state?.fileName||'Media associated with project'}</span><span>{status?.updatedAt?`UPDATED ${new Date(status.updatedAt).toLocaleTimeString()}`:'NO EVENT TIMESTAMP'}</span></div></section><aside className="processing-aside"><span className="section-kicker">PROCESSING SIGNAL</span><h3>{failed?'Review the failure.':complete?'Results are ready.':'Status from the source.'}</h3><p>{error?'The backend has not returned a readable job status. Check connection and try again.':'Stages, progress and completion are displayed only from responses returned by your backend.'}</p><div className="processing-mini"><div>{location.state?.fileName?.includes('photo')?<Images size={16}/>:<Video size={16}/>}</div><ArrowRight size={13}/><div><Grid2X2 size={16}/></div><ArrowRight size={13}/><div><Box size={16}/></div></div><span className="mono">{location.state?.fileName?.includes('photo')?'PHOTOS → 2D → 3D':'VIDEO → 2D → 3D'}</span></aside></div><div className="processing-actions">{failed&&<button className="button" disabled={retrying} onClick={()=>void retry()}>{retrying?<LoaderCircle size={15} className="spin"/>:<RefreshCw size={15}/>} Retry with backend</button>}{complete&&<><Link className="button" to={`/projects/${id}/3d`}><Box size={15}/> View 3D model <ArrowRight size={15}/></Link><Link className="button button-quiet" to={`/projects/${id}/floor-plan`}><Grid2X2 size={15}/> Open floor plan</Link></>}<button className="button button-quiet" onClick={()=>void refresh()} disabled={loading}><RefreshCw size={14} className={loading?'spin':''}/> Refresh status</button><Link className="button button-quiet" to="/dashboard">Return to dashboard</Link></div><div className="processing-footnote"><Clock3 size={13}/>{status?.progress!=null?`Progress ${status.progress}% was returned by the backend.`:'Progress remains unknown until the backend sends a processing status.'}</div></div>;
}
