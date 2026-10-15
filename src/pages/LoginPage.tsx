import { useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Eye, EyeOff, LockKeyhole, Mail, ShieldCheck } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { ApiUnavailableError } from '../services/api';

function BrandMark() {
  return <span className="brand"><svg className="brand-mark" viewBox="0 0 38 38" aria-hidden="true"><path d="M6 30V8h12v10h14v12H20V19H6" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinejoin="round"/><circle cx="6" cy="8" r="3" fill="currentColor"/><circle cx="32" cy="30" r="3" fill="currentColor"/><circle cx="20" cy="18" r="2.4" fill="currentColor"/></svg><span>MAPORA</span></span>;
}

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { signIn } = useAuth();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const next = searchParams.get('next');

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setError('Enter a valid email address.'); return; }
    if (!password) { setError('Enter your password.'); return; }
    setSubmitting(true);
    try {
      const session = await signIn(email.trim(), password);
      navigate(next?.startsWith('/') ? next : session.user.role === 'admin' ? '/admin' : '/dashboard', { replace: true });
    } catch (cause) {
      setError(cause instanceof ApiUnavailableError ? 'Authentication is not connected yet. No sign-in was attempted because the MAPORA backend URL is not configured.' : cause instanceof Error ? cause.message : 'Sign-in failed. Please try again.');
    } finally { setSubmitting(false); }
  };

  return <main className="auth-screen"><div className="auth-atmosphere" aria-hidden="true"><div className="auth-grid"/><span className="auth-coordinate">MAPORA / AUTH / 01</span><div className="auth-orbit"><i/><i/><i/></div></div><header className="auth-top"><Link to="/"><BrandMark/></Link><Link to="/" className="auth-back"><ArrowLeft size={14}/> Back to site</Link></header><div className="auth-layout"><section className="auth-story"><span className="eyebrow"><i className="eyebrow-line"/> SPATIAL INTELLIGENCE, IN YOUR HANDS</span><h1>See space<br/>with <em>clarity.</em></h1><p>Sign in to your MAPORA workspace to continue mapping, review your spaces, and explore your spatial projects.</p><div className="auth-story-bottom"><span><ShieldCheck size={14}/> Secure access requires a connected MAPORA authentication service.</span><span className="mono">01 / ACCESS WORKSPACE</span></div></section><section className="auth-form-wrap"><div className="auth-form-heading"><span className="auth-icon"><LockKeyhole size={18}/></span><span className="section-kicker">WORKSPACE ACCESS</span><h2>Welcome <em>back.</em></h2><p>Use your MAPORA account credentials to sign in.</p></div><form className="auth-form" onSubmit={onSubmit} noValidate><label htmlFor="login-email">Email address</label><div className="auth-input"><Mail size={15}/><input id="login-email" type="email" autoComplete="username" placeholder="you@example.com" value={email} onChange={e=>setEmail(e.target.value)} aria-describedby={error?'login-error':undefined}/></div><div className="auth-password-row"><label htmlFor="login-password">Password</label><button type="button" className="quiet-action" disabled title="Password recovery will be available when the backend supports it">Forgot password?</button></div><div className="auth-input"><LockKeyhole size={15}/><input id="login-password" type={showPassword?'text':'password'} autoComplete="current-password" placeholder="Enter your password" value={password} onChange={e=>setPassword(e.target.value)}/><button type="button" className="password-toggle" onClick={()=>setShowPassword(!showPassword)} aria-label={showPassword?'Hide password':'Show password'}>{showPassword?<EyeOff size={15}/>:<Eye size={15}/>}</button></div>{error&&<div className="auth-error" id="login-error" role="alert">{error}</div>}<button className="button button-block auth-submit" type="submit" disabled={submitting}>{submitting?'Connecting…':<>Sign in to MAPORA <ArrowRight size={15}/></>}</button></form><div className="auth-backend-note"><span className="status-dot"/> Authentication requires a configured backend. Credentials are never stored in this demo.</div></section></div><footer className="auth-footer"><span>© 2026 MAPORA · PROJECT PREVIEW</span><span>PRECISION BEGINS WITH ACCESS</span></footer></main>;
}
