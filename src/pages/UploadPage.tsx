import { useEffect, useRef, useState, type DragEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  CloudUpload,
  FileImage,
  FileVideo2,
  Images,
  Info,
  LockKeyhole,
  Plus,
  Sparkles,
  Trash2,
  Upload,
  Video,
  WandSparkles,
  X,
} from 'lucide-react';
import { getValidAccessToken, isApiConfigured, maporaApi } from '../services/api';
import { useAuth } from '../auth/AuthContext';

function DemoFlag({ children }: { children: string }) {
  return (
    <span className="demo-flag">
      <span className="status-dot" />
      {children}
    </span>
  );
}

export default function UploadPage() {
  const [mode, setMode] = useState<'video' | 'photos'>('video');

  // Video state
  const [file, setFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState('');

  // Photos state
  const [photos, setPhotos] = useState<File[]>([]);
  const [photoPreviews, setPhotoPreviews] = useState<string[]>([]);

  // Common UI state
  const [error, setError] = useState('');
  const [drag, setDrag] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const videoInput = useRef<HTMLInputElement>(null);
  const photoInput = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { id } = useParams();
  const { session } = useAuth();

  // Manage video URL object lifecycle
  useEffect(() => {
    if (!file) {
      setVideoUrl('');
      return;
    }
    const next = URL.createObjectURL(file);
    setVideoUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [file]);

  // Manage photo URL objects lifecycle
  useEffect(() => {
    const urls = photos.map((p) => URL.createObjectURL(p));
    setPhotoPreviews(urls);
    return () => {
      urls.forEach((u) => URL.revokeObjectURL(u));
    };
  }, [photos]);

  const sizeLabel = (bytes: number) =>
    bytes > 1024 ** 3
      ? `${(bytes / 1024 ** 3).toFixed(2)} GB`
      : `${(bytes / 1024 ** 2).toFixed(1)} MB`;

  const totalPhotosSize = photos.reduce((acc, p) => acc + p.size, 0);

  // Accept single video
  const acceptVideo = (next?: File) => {
    if (!next) return;
    setError('');
    const isVideo =
      next.type.startsWith('video/') ||
      /\.(mp4|mov|webm|m4v|avi)$/i.test(next.name);
    if (!isVideo) {
      setFile(null);
      setError('Choose a video file. This file type is not recognized as video.');
      return;
    }
    setFile(next);
  };

  // Accept multiple photos
  const acceptPhotos = (incoming: FileList | File[]) => {
    setError('');
    const valid: File[] = [];
    const filesArray = Array.from(incoming);

    for (const f of filesArray) {
      const isImg =
        f.type.startsWith('image/') ||
        /\.(jpe?g|png|webp)$/i.test(f.name);
      if (isImg) {
        valid.push(f);
      }
    }

    if (valid.length === 0) {
      setError('Please select valid photograph files (.jpg, .jpeg, .png, .webp).');
      return;
    }

    // Append to existing list avoiding exact duplicate names & sizes
    setPhotos((prev) => {
      const existingSignatures = new Set(prev.map((p) => `${p.name}_${p.size}`));
      const newItems = valid.filter((v) => !existingSignatures.has(`${v.name}_${v.size}`));
      return [...prev, ...newItems];
    });
  };

  const removePhoto = (index: number) => {
    setPhotos((prev) => prev.filter((_, i) => i !== index));
  };

  const clearAllPhotos = () => {
    setPhotos([]);
    setError('');
    if (photoInput.current) photoInput.current.value = '';
  };

  const onDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDrag(false);
    if (mode === 'video') {
      acceptVideo(event.dataTransfer.files[0]);
    } else {
      acceptPhotos(event.dataTransfer.files);
    }
  };

  const submit = async () => {
    setError('');
    if (!isApiConfigured) {
      setError('The MAPORA upload service is not connected. Files remain on this device.');
      return;
    }
    const token = await getValidAccessToken(session?.accessToken);
    if (!token) {
      setError('Your session has expired. Please sign in again to upload spatial data.');
      return;
    }

    if (mode === 'video') {
      if (!file) return;
      setSubmitting(true);
      try {
        const result = await maporaApi.createMapping(file, token);
        navigate(`/projects/${encodeURIComponent(result.id)}/processing`, {
          state: { fileName: file.name },
        });
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : 'The video could not be submitted.');
      } finally {
        setSubmitting(false);
      }
    } else {
      if (photos.length === 0) return;
      setSubmitting(true);
      try {
        let projId = id;
        if (id) {
          // Uploading photos to existing project
          await maporaApi.uploadProjectImages(id, photos, token);
          await maporaApi.triggerImageReconstruction(id, token);
        } else {
          // Creating new project with photos
          const result = await maporaApi.createPhotoMapping(photos, undefined, token);
          projId = result.id;
        }
        navigate(`/projects/${encodeURIComponent(projId!)}/processing`, {
          state: { fileName: `${photos.length} indoor photographs` },
        });
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : 'The photographs could not be submitted.');
      } finally {
        setSubmitting(false);
      }
    }
  };

  return (
    <div className="page upload-page">
      <div className="page-back">
        <Link to={id ? `/projects/${id}` : '/projects'}>
          <ArrowLeft size={15} /> Back to project
        </Link>
        <DemoFlag>{isApiConfigured ? 'BACKEND CONNECTED' : 'UPLOAD PREVIEW'}</DemoFlag>
      </div>

      <div className="upload-heading">
        <div>
          <div className="eyebrow app-eyebrow">
            NEW SPATIAL MAP <span className="eyebrow-line" />
          </div>
          <h1>
            Start with {mode === 'video' ? <em>walkthrough video.</em> : <em>indoor photos.</em>}
          </h1>
          <p className="muted">
            {mode === 'video'
              ? 'Add an indoor walkthrough video to reconstruct real 2D floor plans and interactive 3D spatial models.'
              : 'Upload multiple overlapping photographs of your space. MAPORA correlates camera positions to extract architectural layouts.'}
          </p>
        </div>
        <div className="upload-steps">
          <span className="active">
            <i>1</i> Upload
          </span>
          <b />
          <span>
            <i>2</i> Process
          </span>
          <b />
          <span>
            <i>3</i> Explore
          </span>
        </div>
      </div>

      {/* Mode Switcher Tabs */}
      <div className="upload-mode-tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'video'}
          className={`upload-mode-tab ${mode === 'video' ? 'active' : ''}`}
          onClick={() => {
            setMode('video');
            setError('');
          }}
        >
          <Video size={14} /> Walkthrough Video
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'photos'}
          className={`upload-mode-tab ${mode === 'photos' ? 'active' : ''}`}
          onClick={() => {
            setMode('photos');
            setError('');
          }}
        >
          <Images size={14} /> Indoor Photographs
          {photos.length > 0 && <span className="tab-badge">{photos.length}</span>}
        </button>
      </div>

      <div className="upload-layout">
        <div className="upload-main">
          {mode === 'video' ? (
            /* Video Upload UI */
            <div
              className={`drop-zone ${drag ? 'is-dragging' : ''} ${file ? 'has-file' : ''}`}
              onDragOver={(e) => {
                e.preventDefault();
                setDrag(true);
              }}
              onDragLeave={() => setDrag(false)}
              onDrop={onDrop}
              onClick={() => !file && videoInput.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if ((e.key === 'Enter' || e.key === ' ') && !file) {
                  e.preventDefault();
                  videoInput.current?.click();
                }
              }}
            >
              <input
                ref={videoInput}
                type="file"
                accept="video/*,.mp4,.mov,.webm,.m4v,.avi"
                hidden
                onChange={(e) => acceptVideo(e.target.files?.[0])}
              />
              {!file ? (
                <>
                  <div className="upload-orb">
                    <CloudUpload size={25} />
                  </div>
                  <h2>Drop your video here</h2>
                  <p>
                    or{' '}
                    <button
                      className="inline-browse"
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        videoInput.current?.click();
                      }}
                    >
                      browse files
                    </button>{' '}
                    from your device
                  </p>
                  <span className="format-chip">
                    <FileVideo2 size={13} /> MP4, MOV, WEBM · up to 500 MB
                  </span>
                  <span className="limit-note">Continuous room walkthroughs produce the most cohesive spatial models.</span>
                </>
              ) : (
                <div className="selected-file" onClick={(e) => e.stopPropagation()}>
                  <div className="file-preview">
                    {videoUrl && <video src={videoUrl} controls playsInline />}
                  </div>
                  <div className="selected-file-info">
                    <span className="section-kicker">VIDEO SELECTED</span>
                    <b>{file.name}</b>
                    <small>{sizeLabel(file.size)} · local preview</small>
                    <div className="file-actions">
                      <button onClick={() => videoInput.current?.click()}>
                        <Upload size={13} /> Replace
                      </button>
                      <button
                        onClick={() => {
                          setFile(null);
                          setError('');
                          if (videoInput.current) videoInput.current.value = '';
                        }}
                      >
                        <X size={13} /> Remove
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Photo Upload UI */
            <div>
              <input
                ref={photoInput}
                type="file"
                accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
                multiple
                hidden
                onChange={(e) => e.target.files && acceptPhotos(e.target.files)}
              />

              {photos.length === 0 ? (
                <div
                  className={`drop-zone ${drag ? 'is-dragging' : ''}`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDrag(true);
                  }}
                  onDragLeave={() => setDrag(false)}
                  onDrop={onDrop}
                  onClick={() => photoInput.current?.click()}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      photoInput.current?.click();
                    }
                  }}
                >
                  <div className="upload-orb">
                    <Images size={25} />
                  </div>
                  <h2>Drop your indoor photos here</h2>
                  <p>
                    or{' '}
                    <button
                      className="inline-browse"
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        photoInput.current?.click();
                      }}
                    >
                      browse photos
                    </button>{' '}
                    from your device
                  </p>
                  <span className="format-chip">
                    <FileImage size={13} /> JPG, PNG, WEBP · Select multiple photos
                  </span>
                  <span className="limit-note">
                    Min 4 photos recommended for full 3D metric reconstruction (30–50% visual overlap).
                  </span>
                </div>
              ) : (
                <div className="photo-selection-container">
                  <div className="photo-batch-header">
                    <div className="photo-batch-info">
                      <b>{photos.length} photographs selected</b>
                      <small>({sizeLabel(totalPhotosSize)})</small>
                    </div>
                    <div className="photo-batch-actions">
                      <button type="button" onClick={() => photoInput.current?.click()}>
                        <Plus size={13} /> Add more photos
                      </button>
                      <button type="button" onClick={clearAllPhotos}>
                        <Trash2 size={13} /> Clear all
                      </button>
                    </div>
                  </div>

                  <div className="photo-preview-grid">
                    {photos.map((p, idx) => (
                      <div key={`${p.name}_${idx}`} className="photo-card">
                        <div className="photo-card-thumb">
                          {photoPreviews[idx] && (
                            <img src={photoPreviews[idx]} alt={p.name} loading="lazy" />
                          )}
                          <span className="photo-card-badge">#{idx + 1}</span>
                          <button
                            type="button"
                            className="photo-card-remove"
                            title="Remove this photo"
                            onClick={(e) => {
                              e.stopPropagation();
                              removePhoto(idx);
                            }}
                          >
                            <X size={12} />
                          </button>
                        </div>
                        <div className="photo-card-meta">
                          <b title={p.name}>{p.name}</b>
                          <small>{sizeLabel(p.size)}</small>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Coverage Guidance Banner */}
                  {photos.length === 1 ? (
                    <div className="photo-guidance-banner warning" role="status">
                      <AlertCircle size={16} />
                      <div>
                        <b>Single Photo Mode:</b> MAPORA will generate a 2.5D spatial estimation. For a complete 3D metric reconstruction and multi-room floor plan, upload 4 or more photos with overlapping viewpoints.
                      </div>
                    </div>
                  ) : photos.length < 4 ? (
                    <div className="photo-guidance-banner info" role="status">
                      <Info size={16} />
                      <div>
                        <b>Coverage Advisory:</b> {photos.length} photos selected. For optimal SLAM camera tracking and accurate floor plan walls, 4+ photos with 30–50% visual overlap across room corners are recommended.
                      </div>
                    </div>
                  ) : (
                    <div className="photo-guidance-banner success" role="status">
                      <CheckCircle2 size={16} />
                      <div>
                        <b>Good Coverage:</b> {photos.length} photos selected. Sufficient photographic views to correlate 3D camera geometry and generate complete spatial floor plans.
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="form-error" role="alert" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertCircle size={15} />
                <span>{error}</span>
              </div>
              {(error.toLowerCase().includes('expired') || error.toLowerCase().includes('sign in') || error.toLowerCase().includes('unauthorized')) && (
                <Link
                  to={`/login?next=${encodeURIComponent(id ? `/projects/${id}/upload` : '/projects/new')}&expired=1`}
                  className="button button-small"
                  style={{ padding: '4px 10px', fontSize: '12px', height: 'auto', borderRadius: '4px' }}
                >
                  Sign in again
                </Link>
              )}
            </div>
          )}

          <div className="upload-privacy">
            <LockKeyhole size={14} />
            <span>
              <b>No hidden upload.</b> Selecting {mode === 'video' ? 'a video' : 'photographs'} keeps them in this browser. Media is sent only when you explicitly submit to the configured backend.
            </span>
          </div>

          <button
            className="button button-block start-process"
            disabled={mode === 'video' ? !file || submitting : photos.length === 0 || submitting}
            onClick={() => void submit()}
          >
            {submitting ? (
              <>
                <span className="button-spinner" />{' '}
                {mode === 'video' ? 'Sending video to MAPORA…' : `Uploading ${photos.length} photos to MAPORA…`}
              </>
            ) : (
              <>
                {mode === 'video' ? 'Upload video and start mapping' : `Upload ${photos.length} photo${photos.length === 1 ? '' : 's'} and start mapping`}{' '}
                <ArrowRight size={16} />
              </>
            )}
          </button>

          <p className="upload-disclaimer">
            Processing stages, point cloud fusion, and 3D GLB export are executed on the MAPORA backend.
          </p>
        </div>

        {/* Sidebar with dynamic tips based on selected mode */}
        <aside className="upload-side">
          <div className="upload-side-card">
            <span className="section-kicker">CAPTURE TIPS</span>
            <h3>
              A few helpful
              <br />
              <em>{mode === 'video' ? 'frames go far.' : 'angles go far.'}</em>
            </h3>
            {mode === 'video' ? (
              <div className="tip-list">
                <div>
                  <span>01</span>
                  <p>Move slowly through each room, keeping walls and corners in view.</p>
                </div>
                <div>
                  <span>02</span>
                  <p>Use steady lighting and avoid fast turns or abrupt camera movement.</p>
                </div>
                <div>
                  <span>03</span>
                  <p>Capture connecting doorways to help reveal how spaces relate.</p>
                </div>
              </div>
            ) : (
              <div className="tip-list">
                <div>
                  <span>01</span>
                  <p>Stand in room corners to capture wide perspectives showing walls and floor.</p>
                </div>
                <div>
                  <span>02</span>
                  <p>Maintain 30–50% visual overlap between adjacent photos so features align.</p>
                </div>
                <div>
                  <span>03</span>
                  <p>Capture connecting doors and hallways to stitch separate spaces together.</p>
                </div>
              </div>
            )}
            <div className="tip-foot">
              <WandSparkles size={14} /> Reconstruction capabilities depend on your processing service.
            </div>
          </div>

          <div className="upload-help">
            <span className="help-icon">
              <Sparkles size={16} />
            </span>
            <div>
              <b>Project association</b>
              <p>
                {id
                  ? `These ${mode === 'video' ? 'files' : 'photos'} will be submitted for project ${id}.`
                  : 'A new project will be created by the backend after successful submission.'}
              </p>
            </div>
            {mode === 'video' ? <Video size={15} /> : <Images size={15} />}
          </div>
        </aside>
      </div>
    </div>
  );
}
