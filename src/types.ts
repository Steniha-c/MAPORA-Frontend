export type UserRole = 'admin' | 'surveyor';
export type ProjectStatus = 'Ready' | 'Processing' | 'Needs attention';
export type JobStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'unknown';
export interface UserIdentity { id: string; email: string; role: UserRole; }
export interface AuthSession { accessToken: string; user: UserIdentity; }
export interface MapProject { id: string; name: string; location: string; createdAt: string; updatedAt?: string; status: ProjectStatus; rooms: number; duration: string; color: string; versionCount?: number; }
export interface ProcessingStatus { projectId: string; stage: string; status: JobStatus; progress?: number; message?: string; updatedAt?: string; }
export interface ProjectVersion { id: string; version: number; createdAt: string; description?: string; status: string; }
export interface AdminJob { id: string; projectId: string; projectName: string; stage: string; status: JobStatus; updatedAt: string; durationSeconds?: number; message?: string; }
export interface AdminAnalytics { projectCount: number; userCount: number; jobsRunning: number; jobsFailed: number; jobsCompleted?: number; averageProcessingSeconds?: number; reconstructionsCompleted?: number; roomsDetected?: number; averageGeometryConfidence?: number; updatedAt: string; recentJobs?: AdminJob[]; }
export interface FloorPlanRoom { id: string; name: string; bounds: { x: number; y: number; width: number; height: number }; areaSquareMeters?: number; }
export interface FloorPlanWall { id: string; start: { x: number; y: number }; end: { x: number; y: number }; kind: 'wall' | 'door'; }
export interface FloorPlanModel { coordinateSystem: string; units: string; measurementsAvailable: boolean; rooms: FloorPlanRoom[]; walls: FloorPlanWall[]; }

// Explicitly illustrative records; no backend or user data exists in this repository.
export const SAMPLE_PROJECTS: MapProject[] = [
  { id: 'sample-apartment', name: 'Northlight Apartment', location: '2 bed · sample space', createdAt: 'Oct 12, 2026', status: 'Ready', rooms: 6, duration: '02:14', color: 'sand', versionCount: 3 },
  { id: 'sample-studio', name: 'Studio 04', location: 'Creative studio · sample space', createdAt: 'Oct 08, 2026', status: 'Processing', rooms: 4, duration: '01:38', color: 'blue', versionCount: 1 },
  { id: 'sample-loft', name: 'The Corner Loft', location: 'Loft · sample space', createdAt: 'Oct 02, 2026', status: 'Needs attention', rooms: 5, duration: '03:06', color: 'plum', versionCount: 2 },
];
