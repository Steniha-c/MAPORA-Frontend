import * as THREE from 'three';
import { Component, Suspense, useCallback, useEffect, useMemo, useRef, useState, type ErrorInfo, type ReactNode } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Canvas, useThree } from '@react-three/fiber';
import { Grid, OrbitControls, useGLTF } from '@react-three/drei';
import { ArrowLeft, ArrowRight, Box, Compass, Eye, Grid2X2, Layers3, Move3D, Moon, RefreshCw, Sparkles, Sun } from 'lucide-react';
import { API_BASE, isApiConfigured, maporaApi } from '../services/api';
import { useAuth } from '../auth/AuthContext';
import { useProjects } from '../hooks/useProjects';
import type { MapProject } from '../types';

const rooms = [
  { id: 'living', name: 'Living Room', position: [-3.8, 0.008, 1.95] as [number, number, number], size: [3.8, 3.5] as [number, number], area: '13.3 m²', dims: '3.80 × 3.50 m' },
  { id: 'bedroom-1', name: 'Bedroom 01', position: [-3.8, 0.008, -1.85] as [number, number, number], size: [3.8, 3.7] as [number, number], area: '14.1 m²', dims: '3.80 × 3.70 m' },
  { id: 'bathroom', name: 'Bathroom Suite', position: [-0.5, 0.008, -2.5] as [number, number, number], size: [2.4, 2.4] as [number, number], area: '5.8 m²', dims: '2.40 × 2.40 m' },
  { id: 'hallway', name: 'Central Foyer', position: [-0.5, 0.008, 1.3] as [number, number, number], size: [2.4, 4.8] as [number, number], area: '11.5 m²', dims: '2.40 × 4.80 m' },
  { id: 'bedroom-2', name: 'Bedroom 02', position: [3.3, 0.008, 1.9] as [number, number, number], size: [4.8, 3.6] as [number, number], area: '17.3 m²', dims: '4.80 × 3.60 m' },
  { id: 'master', name: 'Master Suite & Terrace', position: [3.3, 0.008, -1.9] as [number, number, number], size: [4.8, 3.6] as [number, number], area: '17.3 m²', dims: '4.80 × 3.60 m' },
];

function SelectableRoom({ room, index, selected, onSelect }: { room: typeof rooms[number]; index: number; selected: boolean; onSelect: (index: number) => void }) {
  return (
    <mesh position={room.position} rotation={[-Math.PI / 2, 0, 0]} onClick={event => { event.stopPropagation(); onSelect(index); }}>
      <planeGeometry args={room.size} />
      <meshBasicMaterial color={selected ? '#ff6a00' : '#ffffff'} transparent opacity={selected ? 0.28 : 0.0} depthWrite={false} />
    </mesh>
  );
}

function ArchWall({ pos, size, rot = 0, wire = false, color = '#ffffff' }: { pos: [number, number, number]; size: [number, number, number]; rot?: number; wire?: boolean; color?: string }) {
  return (
    <mesh position={pos} rotation={[0, rot, 0]} castShadow receiveShadow>
      <boxGeometry args={size} />
      <meshStandardMaterial color={color} roughness={0.72} metalness={0.04} wireframe={wire} />
    </mesh>
  );
}

function ArchColumn({ pos, size = [0.38, 1.40, 0.38], wire = false }: { pos: [number, number, number]; size?: [number, number, number]; wire?: boolean }) {
  return (
    <mesh position={pos} castShadow receiveShadow>
      <boxGeometry args={size} />
      <meshStandardMaterial color="#ffffff" roughness={0.70} metalness={0.04} wireframe={wire} />
    </mesh>
  );
}

function OpenDoorLeaf({ hinge, size = [0.82, 1.18, 0.035], angle = 0.85, wire = false }: { hinge: [number, number, number]; size?: [number, number, number]; angle?: number; wire?: boolean }) {
  return (
    <group position={hinge} rotation={[0, angle, 0]}>
      <mesh position={[size[0] / 2, 0, 0]} castShadow receiveShadow>
        <boxGeometry args={size} />
        <meshStandardMaterial color="#fafbfc" roughness={0.65} metalness={0.05} wireframe={wire} />
      </mesh>
    </group>
  );
}

function DemoRoom3D({ wire, selectedRoom, onSelect }: { wire: boolean; selectedRoom: number; onSelect: (index: number) => void }) {
  return (
    <group>
      {/* 1. Ground Architectural Base Slab */}
      <mesh receiveShadow position={[0, -0.04, 0]}>
        <boxGeometry args={[11.8, 0.08, 7.8]} />
        <meshStandardMaterial color="#f2f4f7" roughness={0.88} metalness={0.01} wireframe={wire} />
      </mesh>

      {/* Interactive Room Picking Floor Zones */}
      {rooms.map((room, index) => (
        <SelectableRoom key={room.id} room={room} index={index} selected={selectedRoom === index} onSelect={onSelect} />
      ))}

      {/* 2. FRONT EXTERIOR WALLS (Z = 3.8) */}
      {/* Front-left corner post */}
      <ArchWall pos={[-5.5, 0.69, 3.8]} size={[0.6, 1.38, 0.2]} wire={wire} />
      {/* Living Room Window (Double-pane with center vertical mullion) */}
      <ArchWall pos={[-4.2, 0.19, 3.8]} size={[2.0, 0.38, 0.2]} wire={wire} />
      <ArchWall pos={[-4.2, 1.28, 3.8]} size={[2.0, 0.20, 0.2]} wire={wire} />
      <ArchWall pos={[-4.2, 0.73, 3.8]} size={[0.04, 0.90, 0.12]} wire={wire} color="#f4f5f7" />
      {/* Front-left wall section leading to open hallway entrance */}
      <ArchWall pos={[-2.5, 0.69, 3.8]} size={[1.4, 1.38, 0.2]} wire={wire} />

      {/* NOTE: Central entrance [X = -1.8 to 0.8] is completely open, giving direct unobstructed view of the corridor & iconic doors! */}

      {/* Front-right post leading into Bedroom 02 */}
      <ArchWall pos={[1.1, 0.69, 3.8]} size={[0.6, 1.38, 0.2]} wire={wire} />
      {/* Bedroom 2 Window (Double-pane with center vertical mullion) */}
      <ArchWall pos={[2.2, 0.19, 3.8]} size={[1.6, 0.38, 0.2]} wire={wire} />
      <ArchWall pos={[2.2, 1.28, 3.8]} size={[1.6, 0.20, 0.2]} wire={wire} />
      <ArchWall pos={[2.2, 0.73, 3.8]} size={[0.04, 0.90, 0.12]} wire={wire} color="#f4f5f7" />
      {/* Intermediate solid wall */}
      <ArchWall pos={[3.25, 0.69, 3.8]} size={[0.5, 1.38, 0.2]} wire={wire} />
      {/* Front-right Sliding Patio Doors (3 sliding panels with 2 vertical mullions) */}
      <ArchWall pos={[4.4, 0.05, 3.8]} size={[1.8, 0.10, 0.2]} wire={wire} color="#e5e7eb" />
      <ArchWall pos={[4.4, 1.29, 3.8]} size={[1.8, 0.18, 0.2]} wire={wire} />
      <ArchWall pos={[3.95, 0.68, 3.8]} size={[0.04, 1.12, 0.12]} wire={wire} color="#f4f5f7" />
      <ArchWall pos={[4.85, 0.68, 3.8]} size={[0.04, 1.12, 0.12]} wire={wire} color="#f4f5f7" />
      {/* Front-right corner post */}
      <ArchWall pos={[5.55, 0.69, 3.8]} size={[0.5, 1.38, 0.2]} wire={wire} />

      {/* 3. LEFT EXTERIOR WALLS (X = -5.8) */}
      {/* Front corner post */}
      <ArchWall pos={[-5.8, 0.69, 3.3]} size={[0.2, 1.38, 1.0]} wire={wire} />
      {/* Front-left side window opening */}
      <ArchWall pos={[-5.8, 0.21, 1.9]} size={[0.2, 0.42, 1.8]} wire={wire} />
      <ArchWall pos={[-5.8, 1.28, 1.9]} size={[0.2, 0.20, 1.8]} wire={wire} />
      <ArchWall pos={[-5.8, 0.74, 1.9]} size={[0.12, 0.88, 0.04]} wire={wire} color="#f4f5f7" />
      {/* Intermediate junction post */}
      <ArchWall pos={[-5.8, 0.69, 0.55]} size={[0.2, 1.38, 0.9]} wire={wire} />
      {/* Bedroom 01 Iconic Triple-Pane Ribbon Window */}
      <ArchWall pos={[-5.8, 0.21, -1.8]} size={[0.2, 0.42, 2.6]} wire={wire} />
      <ArchWall pos={[-5.8, 1.28, -1.8]} size={[0.2, 0.20, 2.6]} wire={wire} />
      <ArchWall pos={[-5.8, 0.74, -1.37]} size={[0.12, 0.88, 0.04]} wire={wire} color="#f4f5f7" />
      <ArchWall pos={[-5.8, 0.74, -2.23]} size={[0.12, 0.88, 0.04]} wire={wire} color="#f4f5f7" />
      {/* Rear-left corner post */}
      <ArchWall pos={[-5.8, 0.69, -3.45]} size={[0.2, 1.38, 0.7]} wire={wire} />

      {/* 4. BACK EXTERIOR WALLS (Z = -3.8) */}
      {/* Rear Bedroom 01 wall */}
      <ArchWall pos={[-3.8, 0.69, -3.8]} size={[4.0, 1.38, 0.2]} wire={wire} />
      {/* Bathroom Window */}
      <ArchWall pos={[-1.35, 0.69, -3.8]} size={[0.9, 1.38, 0.2]} wire={wire} />
      <ArchWall pos={[-0.4, 0.35, -3.8]} size={[1.0, 0.70, 0.2]} wire={wire} />
      <ArchWall pos={[-0.4, 1.28, -3.8]} size={[1.0, 0.20, 0.2]} wire={wire} />
      <ArchWall pos={[0.45, 0.69, -3.8]} size={[0.7, 1.38, 0.2]} wire={wire} />
      {/* Master Suite 3-Panel Sliding Patio Doors */}
      <ArchWall pos={[3.1, 0.05, -3.8]} size={[3.4, 0.10, 0.2]} wire={wire} color="#e5e7eb" />
      <ArchWall pos={[3.1, 1.29, -3.8]} size={[3.4, 0.18, 0.2]} wire={wire} />
      <ArchWall pos={[2.53, 0.69, -3.8]} size={[0.04, 1.18, 0.12]} wire={wire} color="#f4f5f7" />
      <ArchWall pos={[3.67, 0.69, -3.8]} size={[0.04, 1.18, 0.12]} wire={wire} color="#f4f5f7" />
      {/* Rear-right corner post */}
      <ArchWall pos={[5.3, 0.69, -3.8]} size={[1.0, 1.38, 0.2]} wire={wire} />

      {/* 5. RIGHT EXTERIOR WALLS (X = 5.8) */}
      <ArchWall pos={[5.8, 0.69, -3.5]} size={[0.2, 1.38, 0.6]} wire={wire} />
      {/* Master Suite right sliding glass doors */}
      <ArchWall pos={[5.8, 0.05, -1.9]} size={[0.2, 0.10, 2.6]} wire={wire} color="#e5e7eb" />
      <ArchWall pos={[5.8, 1.29, -1.9]} size={[0.2, 0.18, 2.6]} wire={wire} />
      <ArchWall pos={[5.8, 0.69, -1.9]} size={[0.12, 1.18, 0.04]} wire={wire} color="#f4f5f7" />
      {/* Middle right junction */}
      <ArchWall pos={[5.8, 0.69, -0.3]} size={[0.2, 1.38, 0.6]} wire={wire} />
      {/* Bedroom 02 Window Opening */}
      <ArchWall pos={[5.8, 0.20, 1.6]} size={[0.2, 0.40, 2.0]} wire={wire} />
      <ArchWall pos={[5.8, 1.28, 1.6]} size={[0.2, 0.20, 2.0]} wire={wire} />
      <ArchWall pos={[5.8, 0.74, 1.6]} size={[0.12, 0.88, 0.04]} wire={wire} color="#f4f5f7" />
      {/* Front-right corner post */}
      <ArchWall pos={[5.8, 0.69, 3.2]} size={[0.2, 1.38, 1.2]} wire={wire} />

      {/* 6. INTERIOR PARTITION WALLS & OPEN DOOR LEAFS */}
      {/* Partition between Bedroom 01 & Living Room (along Z = 0.1) */}
      <ArchWall pos={[-4.3, 0.69, 0.1]} size={[3.0, 1.38, 0.2]} wire={wire} />
      <ArchWall pos={[-2.35, 1.28, 0.1]} size={[0.9, 0.20, 0.2]} wire={wire} />
      <ArchWall pos={[-1.85, 0.69, 0.1]} size={[0.1, 1.38, 0.2]} wire={wire} />
      <OpenDoorLeaf hinge={[-2.8, 0.59, 0.1]} angle={Math.PI * 0.25} wire={wire} />

      {/* Vertical Partition 1 (Left wing to Central Hall, along X = -1.8) */}
      <ArchWall pos={[-1.8, 0.69, 3.4]} size={[0.2, 1.38, 0.8]} wire={wire} />
      <ArchWall pos={[-1.8, 1.28, 2.5]} size={[0.2, 0.20, 1.0]} wire={wire} />
      {/* THE ICONIC OPEN DOOR LEAF SWINGING WIDE INTO THE LIVING ROOM! */}
      <OpenDoorLeaf hinge={[-1.8, 0.59, 2.05]} angle={Math.PI * 0.22} wire={wire} />
      <ArchWall pos={[-1.8, 0.69, 1.05]} size={[0.2, 1.38, 1.9]} wire={wire} />
      <ArchWall pos={[-1.8, 0.69, -0.7]} size={[0.2, 1.38, 1.6]} wire={wire} />
      <ArchWall pos={[-1.8, 1.28, -1.95]} size={[0.2, 0.20, 0.9]} wire={wire} />
      <ArchWall pos={[-1.8, 0.69, -3.1]} size={[0.2, 1.38, 1.4]} wire={wire} />

      {/* Central Bathroom Partition (along Z = -0.6) */}
      <ArchWall pos={[-1.45, 0.69, -0.6]} size={[0.7, 1.38, 0.2]} wire={wire} />
      <ArchWall pos={[-0.65, 1.28, -0.6]} size={[0.9, 0.20, 0.2]} wire={wire} />
      <ArchWall pos={[0.3, 0.69, -0.6]} size={[1.0, 1.38, 0.2]} wire={wire} />
      {/* Central interior chase partition */}
      <ArchWall pos={[-0.3, 0.69, -2.2]} size={[0.2, 1.38, 3.2]} wire={wire} />

      {/* Vertical Partition 2 (Central Hall to Right wing, along X = 0.8) */}
      <ArchWall pos={[0.8, 0.69, 3.4]} size={[0.2, 1.38, 0.8]} wire={wire} />
      <ArchWall pos={[0.8, 1.28, 2.5]} size={[0.2, 0.20, 1.0]} wire={wire} />
      {/* THE ICONIC OPEN DOOR LEAF SWINGING WIDE INTO BEDROOM 02! */}
      <OpenDoorLeaf hinge={[0.8, 0.59, 2.05]} angle={-Math.PI * 0.22} wire={wire} />
      <ArchWall pos={[0.8, 0.69, 1.0]} size={[0.2, 1.38, 2.0]} wire={wire} />
      <ArchWall pos={[0.8, 0.69, -0.9]} size={[0.2, 1.38, 1.8]} wire={wire} />
      <ArchWall pos={[0.8, 1.28, -2.25]} size={[0.2, 0.20, 0.9]} wire={wire} />
      <ArchWall pos={[0.8, 0.69, -3.25]} size={[0.2, 1.38, 1.1]} wire={wire} />

      {/* Horizontal Partition 2 (Bedroom 02 & Master Suite, along Z = 0.0) */}
      <ArchWall pos={[3.3, 0.69, 0.0]} size={[5.0, 1.38, 0.2]} wire={wire} />

      {/* 7. ICONIC STRUCTURAL COLUMNS / PILLARS (Matching image exactly) */}
      {/* Column 1: Bedroom 01 corner column */}
      <ArchColumn pos={[-2.05, 0.70, 0.35]} size={[0.38, 1.40, 0.38]} wire={wire} />
      {/* Column 2: Central Bathroom service shaft pillar standing prominently in center room */}
      <ArchColumn pos={[-0.45, 0.70, -2.4]} size={[0.48, 1.40, 0.48]} wire={wire} />
      {/* Column 3: Bedroom 02 partition wall pilaster standing tall against the wall */}
      <ArchColumn pos={[2.2, 0.70, 0.24]} size={[0.42, 1.40, 0.42]} wire={wire} />
    </group>
  );
}

function BackendScene({
  url,
  wire,
  clay,
  selectedRoom,
  onReady,
  onSelect,
  onRooms,
}: {
  url: string;
  wire: boolean;
  clay: boolean;
  selectedRoom: string;
  onReady: () => void;
  onSelect: (name: string) => void;
  onRooms: (names: string[]) => void;
}) {
  const { scene } = useGLTF(url);
  const clone = useMemo(() => {
    const c = scene.clone(true);
    // 1. Ensure normals are computed on all geometries if absent
    c.traverse((object: any) => {
      if (object.isMesh && object.geometry) {
        if (!object.geometry.attributes.normal) {
          object.geometry.computeVertexNormals();
        }
        object.castShadow = true;
        object.receiveShadow = true;
      }
    });

    // 2. Center model at ground level (Y=0, centered in X and Z)
    const box = new THREE.Box3().setFromObject(c);
    const center = box.getCenter(new THREE.Vector3());
    c.position.set(-center.x, -box.min.y, -center.z);
    return c;
  }, [scene]);

  useEffect(() => {
    const names = new Set<string>();
    clone.traverse((object: any) => {
      if (object.isMesh) {
        const name = String(object.userData?.roomName || object.name || '').trim();
        if (name && !/^(wall|door|scene|camera|light|mesh|group|directional|ground|plinth)/i.test(name)) {
          names.add(name.replace(/_/g, ' '));
        }
      }
    });
    onRooms([...names]);

    // Auto-frame OrbitControls camera to model bounding box
    const box = new THREE.Box3().setFromObject(clone);
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.z, 5);
    const viewerControls = (window as any).__viewerControls;
    const viewerCamera = (window as any).__viewerCamera;
    if (viewerControls && viewerCamera) {
      viewerControls.target.set(0, size.y / 2, 0);
      viewerCamera.position.set(-maxDim * 1.15, maxDim * 1.05, maxDim * 1.25);
      viewerControls.update();
    }

    onReady();
  }, [clone, onReady, onRooms]);

  useEffect(() => {
    clone.traverse((object: any) => {
      if (object.isMesh && object.geometry) {
        if (!object.geometry.attributes.normal) {
          object.geometry.computeVertexNormals();
        }

        if (!object.geometry.boundingBox) {
          object.geometry.computeBoundingBox();
        }
        const gBox = object.geometry.boundingBox;
        const sizeY = gBox ? (gBox.max.y - gBox.min.y) : 1;
        const name = String(object.userData?.roomName || object.name || '').trim();

        const isPlinth = /plinth|ground|base slab/i.test(name);
        const isFloor = /floor|room|space|living|bedroom|kitchen|corridor|workspace|suite/i.test(name) || (!isPlinth && sizeY <= 0.12);
        const isDoor = /door|leaf|header/i.test(name);

        if (clay) {
          object.material = new THREE.MeshStandardMaterial({
            color: isPlinth ? '#e2e5eb' : isFloor ? '#edf0f5' : isDoor ? '#f5f6f8' : '#ffffff',
            roughness: isPlinth ? 0.90 : isFloor ? 0.85 : isDoor ? 0.65 : 0.72,
            metalness: 0.03,
            side: THREE.DoubleSide,
            wireframe: wire,
          });
        } else if (object.material) {
          if (Array.isArray(object.material)) {
            object.material.forEach((m: any) => {
              m.side = THREE.DoubleSide;
              m.wireframe = wire;
            });
          } else {
            object.material.side = THREE.DoubleSide;
            object.material.wireframe = wire;
          }
        }
      }
    });
  }, [clone, wire, clay]);

  useEffect(() => {
    const normSelected = (selectedRoom || '').toLowerCase().replace(/_/g, ' ').trim();
    clone.traverse((object: any) => {
      if (object.isMesh && object.material && !Array.isArray(object.material)) {
        const objName = String(object.userData?.roomName || object.name || '').toLowerCase().replace(/_/g, ' ').trim();
        const isMatch = normSelected && (objName === normSelected || objName.includes(normSelected) || normSelected.includes(objName));
        if (isMatch && !/wall|door|plinth|ground/i.test(objName)) {
          if (object.material.emissive) {
            object.material.emissive.set('#ff6a00');
            object.material.emissiveIntensity = 0.35;
          }
        } else if (object.material.emissive) {
          object.material.emissive.set('#000000');
          object.material.emissiveIntensity = 0;
        }
      }
    });
  }, [clone, selectedRoom]);

  return (
    <primitive
      object={clone}
      onClick={(event: { object: { name?: string; userData?: Record<string, unknown> } }) => {
        const name = String(event.object.userData?.roomName || event.object.name || '').trim();
        if (name && !/^(wall|door|plinth|ground)/i.test(name)) onSelect(name.replace(/_/g, ' '));
      }}
    />
  );
}

interface BoundaryProps { children: ReactNode; onError: (error: Error) => void }
class SceneErrorBoundary extends Component<BoundaryProps, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error: Error, _info: ErrorInfo) { this.props.onError(error); }
  render() { return this.state.failed ? null : this.props.children; }
}

function ControlsBridge() {
  const { controls, camera } = useThree();
  useEffect(() => {
    if (controls) {
      (window as any).__viewerControls = controls;
      (window as any).__viewerCamera = camera;
    }
  }, [controls, camera]);
  return null;
}

export default function Viewer3DPage() {
  const navigate = useNavigate();
  const { id = 'sample-apartment' } = useParams();
  const { session } = useAuth();
  const { projects } = useProjects();
  const [theme, setTheme] = useState<'clay' | 'dark'>('clay');
  const [viewModel, setViewModel] = useState<'dollhouse' | 'reconstructed'>('dollhouse');
  const [grid, setGrid] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [wire, setWire] = useState(false);
  const [selectedRoom, setSelectedRoom] = useState(0);
  const [backendRoom, setBackendRoom] = useState('');
  const [backendRooms, setBackendRooms] = useState<string[]>([]);
  const [sceneUrl, setSceneUrl] = useState('');
  const [project, setProject] = useState<MapProject | null>(null);
  const isSample = !id || id.startsWith('sample-') || id === 'sample-apartment' || id === 'sample-studio' || id === 'sample-loft';
  const [sceneState, setSceneState] = useState<'demo' | 'loading' | 'backend' | 'error'>((!isApiConfigured || isSample) ? 'demo' : 'loading');
  const [sceneError, setSceneError] = useState('');
  const controls = useRef<any>(null);
  useEffect(() => { if (controls.current) (window as any).__viewerControls = controls.current; });

  const loadScene = useCallback(async () => {
    if (!isApiConfigured || isSample) {
      setSceneState('demo');
      return;
    }
    setSceneState('loading');
    setSceneError('');
    setSceneUrl('');
    try {
      const [sceneResult, projectResult] = await Promise.all([
        maporaApi.getScene(id, session?.accessToken),
        maporaApi.getProject(id, session?.accessToken).catch(() => null),
      ]);
      if (!sceneResult.geometryUrl) throw new Error('The backend returned no authorized 3D geometry URL.');
      if (projectResult) setProject(projectResult);
      const fullUrl = sceneResult.geometryUrl.startsWith('http') || !API_BASE
        ? sceneResult.geometryUrl
        : (API_BASE + (sceneResult.geometryUrl.startsWith('/') ? '' : '/') + sceneResult.geometryUrl);
      setSceneUrl(fullUrl);
    } catch (cause) {
      setSceneState('error');
      setSceneError(cause instanceof Error ? cause.message : 'The 3D scene could not be loaded.');
    }
  }, [id, session, isSample]);

  useEffect(() => { void loadScene(); }, [loadScene]);

  const onModelReady = useCallback(() => setSceneState('backend'), []);
  const onModelRooms = useCallback((names: string[]) => {
    setBackendRooms(names);
    if (names.length > 0 && !backendRoom) setBackendRoom(names[0]);
  }, [backendRoom]);
  const onModelSelect = useCallback((name: string) => setBackendRoom(name), []);
  const retry = () => void loadScene();

  const resetToIsometric = () => {
    if ((window as any).__viewerControls && (window as any).__viewerCamera) {
      const c = (window as any).__viewerCamera;
      c.position.set(-11.8, 11.2, 13.0);
      (window as any).__viewerControls.target.set(0, 0.5, 0);
      (window as any).__viewerControls.update();
    } else if (controls.current) {
      controls.current.reset();
    }
  };

  const setTopDown = () => {
    if ((window as any).__viewerControls && (window as any).__viewerCamera) {
      const c = (window as any).__viewerCamera;
      c.position.set(0, 17.5, 0.01);
      (window as any).__viewerControls.target.set(0, 0, 0);
      (window as any).__viewerControls.update();
    }
  };

  const currentRoom = viewModel === 'reconstructed' && sceneState === 'backend'
    ? (backendRoom || backendRooms[0] || (project ? `${project.name} (3D model)` : '3D model loaded'))
    : rooms[selectedRoom].name;

  const currentDetails = viewModel === 'dollhouse' ? rooms[selectedRoom] : null;
  const latestReady = projects.find(p => p.status === 'Ready' && !p.id.startsWith('sample-'));

  return (
    <div className={`page three-page ${fullscreen ? 'three-fullscreen' : ''}`}>
      {isSample && latestReady && (
        <div className="demo-banner compact">
          <span className="demo-banner-icon"><Sparkles size={15} /></span>
          <span><b>Illustrative sample preview.</b> You have a reconstructed space ready: <b>{latestReady.name}</b>.</span>
          <button className="button button-small" onClick={() => navigate(`/projects/${latestReady.id}/3d`)}>
            Open real 3D model <ArrowRight size={13} />
          </button>
        </div>
      )}
      <div className="viewer-title">
        <div>
          <div className="page-back">
            <Link to={`/projects/${id}/floor-plan`}><ArrowLeft size={15} /> Floor plan</Link>
            <span className="demo-flag">
              <span className="status-dot" />
              {viewModel === 'dollhouse' ? 'ARCHITECTURAL DOLLHOUSE 3D' : sceneState === 'backend' ? 'REAL BACKEND MODEL' : '3D VIEWER'}
            </span>
          </div>
          <div className="viewer-heading">
            <h1>{viewModel === 'dollhouse' ? (isSample ? 'Northlight Apartment' : `${project?.name || 'Indoor Space'} · Dollhouse`) : (project?.name || 'Reconstructed Space')}</h1>
            <div className="model-mode-switch" role="group" aria-label="3D Model Visualization Mode">
              <button
                type="button"
                className={`model-mode-btn ${viewModel === 'dollhouse' ? 'active' : ''}`}
                onClick={() => setViewModel('dollhouse')}
                title="View Architectural Cutaway Dollhouse"
              >
                <Box size={14} /> Architectural Dollhouse
              </button>
              <button
                type="button"
                className={`model-mode-btn ${viewModel === 'reconstructed' ? 'active' : ''}`}
                onClick={() => setViewModel('reconstructed')}
                title={sceneUrl ? "View Reconstructed Spatial Model" : "Reconstructed scan model"}
              >
                <Move3D size={14} /> Reconstructed Model {sceneUrl ? '' : '(Demo)'}
              </button>
            </div>
          </div>
          <p className="muted">
            {viewModel === 'dollhouse'
              ? 'Isometric architectural cutaway · solid walls with open door leaves and window mullions'
              : sceneState === 'backend'
              ? `${project?.location || 'Indoor survey site'} · ${backendRooms.length || project?.rooms || 0} rooms detected · Authorized geometry from MAPORA backend`
              : sceneState === 'error'
              ? 'Reconstructed 3D geometry unavailable'
              : 'Loading authorized reconstruction…'}
          </p>
        </div>
        <div className="viewer-actions">
          <button className="button button-quiet" onClick={() => navigate(`/projects/${id}/floor-plan`)}>
            <Grid2X2 size={15} /> Floor plan
          </button>
        </div>
      </div>
      <div className="three-viewport">
        <Canvas
          shadows
          camera={{ position: [-11.8, 11.2, 13.0], fov: 36 }}
          dpr={[1, 1.8]}
          gl={{ antialias: true, alpha: false, preserveDrawingBuffer: true }}
        >
          <color attach="background" args={[theme === 'clay' ? '#ffffff' : '#101114']} />
          {theme === 'clay' ? (
            <>
              {/* Architectural White Studio Multi-Directional Lighting */}
              <ambientLight intensity={0.80} />
              <hemisphereLight args={['#ffffff', '#cbd5e1', 0.65]} />
              {/* Primary Sunlight casting crisp architectural shadows */}
              <directionalLight
                position={[-14, 22, 14]}
                intensity={1.85}
                castShadow
                shadow-mapSize-width={2048}
                shadow-mapSize-height={2048}
                shadow-camera-near={0.5}
                shadow-camera-far={45}
                shadow-camera-left={-12}
                shadow-camera-right={12}
                shadow-camera-top={12}
                shadow-camera-bottom={-12}
                shadow-bias={-0.0002}
              />
              {/* Secondary opposing fill light ensuring zero black silhouettes */}
              <directionalLight position={[14, 16, -12]} intensity={0.65} />
              {/* Top soft ambient downlight */}
              <directionalLight position={[0, 20, 0]} intensity={0.35} />
              {/* Ground contact shadow receiver plane */}
              <mesh receiveShadow position={[0, -0.05, 0]} rotation={[-Math.PI / 2, 0, 0]}>
                <planeGeometry args={[60, 60]} />
                <shadowMaterial opacity={0.12} />
              </mesh>
            </>
          ) : (
            <>
              <ambientLight intensity={1.1} />
              <directionalLight position={[5, 8, 4]} intensity={2.2} castShadow />
              <pointLight position={[-3, 2, 0]} color="#ff6a00" intensity={3} distance={8} />
            </>
          )}

          {viewModel === 'dollhouse' ? (
            <DemoRoom3D wire={wire} selectedRoom={selectedRoom} onSelect={setSelectedRoom} />
          ) : sceneUrl ? (
            <SceneErrorBoundary key={sceneUrl} onError={error => { setSceneError(error.message); setSceneState('error'); }}>
              <Suspense fallback={null}>
                <BackendScene
                  url={sceneUrl}
                  wire={wire}
                  clay={theme === 'clay'}
                  selectedRoom={backendRoom}
                  onReady={onModelReady}
                  onSelect={onModelSelect}
                  onRooms={onModelRooms}
                />
              </Suspense>
            </SceneErrorBoundary>
          ) : (
            <DemoRoom3D wire={wire} selectedRoom={selectedRoom} onSelect={setSelectedRoom} />
          )}

          <ControlsBridge />
          <OrbitControls
            ref={controls}
            makeDefault
            enableRotate
            enablePan
            enableZoom
            enableDamping
            dampingFactor={0.08}
            minDistance={3}
            maxDistance={40}
            maxPolarAngle={Math.PI * 0.48}
            mouseButtons={{ LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN }}
          />

          {grid && (
            <Grid
              position={[0, -0.035, 0]}
              args={[16, 16]}
              cellSize={0.5}
              cellThickness={0.45}
              cellColor={theme === 'clay' ? '#cbd5e1' : '#3a3b3f'}
              sectionSize={2}
              sectionThickness={0.8}
              sectionColor={theme === 'clay' ? '#94a3b8' : '#55565a'}
              fadeDistance={28}
              infiniteGrid={false}
            />
          )}
        </Canvas>

        {sceneState === 'loading' && (
          <div className="scene-state-overlay">
            <span className="scene-loading-mark"><RefreshCw size={16} className="spin" /></span>
            <b>Loading 3D geometry</b>
            <p>Waiting for the authorized model to become available.</p>
          </div>
        )}
        {sceneState === 'error' && (
          <div className="scene-state-overlay scene-error-overlay" role="status">
            <span className="scene-loading-mark"><Box size={16} /></span>
            <b>3D model unavailable</b>
            <p>{sceneError}</p>
            <button className="button button-quiet" onClick={retry}>
              <RefreshCw size={13} /> Retry model request
            </button>
          </div>
        )}

        <div className="three-toolbar">
          <button
            onClick={() => setTheme(theme === 'clay' ? 'dark' : 'clay')}
            className={theme === 'clay' ? 'selected' : ''}
            title={theme === 'clay' ? 'Switch to Dark Mode' : 'Switch to Clay Dollhouse'}
          >
            {theme === 'clay' ? <Sun size={15} /> : <Moon size={15} />}
            {theme === 'clay' ? 'Clay Studio' : 'Dark Mode'}
          </button>
          <button onClick={resetToIsometric} title="Reset to Architectural Isometric View">
            <Compass size={15} /> Isometric
          </button>
          <button onClick={setTopDown} title="Top-down Cutaway Plan View">
            <Eye size={15} /> Plan View
          </button>
          <button onClick={() => setGrid(!grid)} className={grid ? 'selected' : ''} aria-pressed={grid}>
            <Grid2X2 size={15} /> Grid
          </button>
          <button onClick={() => setWire(!wire)} className={wire ? 'selected' : ''} aria-pressed={wire}>
            <Layers3 size={15} /> {wire ? 'Solid' : 'Wireframe'}
          </button>
          <button onClick={() => setFullscreen(!fullscreen)}><Move3D size={15} /> {fullscreen ? 'Exit' : 'Fullscreen'}</button>
        </div>

        <div className="three-inspector">
          <span className="section-kicker">
            {viewModel === 'dollhouse' ? 'SPATIAL INSPECTOR' : sceneState === 'backend' ? 'SELECTED OBJECT' : 'MODEL STATUS'}
          </span>
          <h3>{viewModel === 'dollhouse' ? rooms[selectedRoom].name : (sceneState === 'error' ? 'No model loaded' : currentRoom)}</h3>
          <p>
            {viewModel === 'dollhouse'
              ? `${rooms[selectedRoom]?.dims || '4.00 × 3.70 m'} · ${rooms[selectedRoom]?.area || '14.8 m²'}`
              : sceneState === 'backend'
              ? `${project ? `${project.name} (${project.duration || 'Ready'})` : 'Reconstructed mesh'} · ${backendRooms.length} detected space(s)`
              : 'No reconstruction is shown as a substitute.'}
          </p>
          {viewModel === 'dollhouse' && (
            <div className="three-room-select" aria-label="Select sample room">
              {rooms.map((room, index) => (
                <button
                  key={room.id}
                  type="button"
                  className={selectedRoom === index ? 'active' : ''}
                  aria-label={`Select ${room.name}`}
                  aria-pressed={selectedRoom === index}
                  onClick={() => setSelectedRoom(index)}
                  title={room.name}
                >
                  {String(index + 1).padStart(2, '0')}
                </button>
              ))}
            </div>
          )}
          {viewModel === 'reconstructed' && sceneState === 'backend' && backendRooms.length > 0 && (
            <div className="three-room-select three-model-select" aria-label="Select model room">
              {backendRooms.map(name => (
                <button
                  key={name}
                  type="button"
                  className={backendRoom === name ? 'active' : ''}
                  aria-pressed={backendRoom === name}
                  onClick={() => setBackendRoom(name)}
                  title={name}
                >
                  {name.slice(0, 3).toUpperCase()}
                </button>
              ))}
            </div>
          )}
          <div className="three-room-keys">
            <button onClick={() => viewModel === 'dollhouse' ? setSelectedRoom(value => (value + rooms.length - 1) % rooms.length) : setBackendRoom(backendRooms[(Math.max(0, backendRooms.indexOf(backendRoom) - 1))] || '')} aria-label="Previous room">←</button>
            <button onClick={() => viewModel === 'dollhouse' ? setSelectedRoom(value => (value + 1) % rooms.length) : setBackendRoom(backendRooms[(backendRooms.indexOf(backendRoom) + 1) % Math.max(backendRooms.length, 1)] || '')} aria-label="Next room"><ArrowRight size={13} /></button>
          </div>
        </div>

        <div className="three-scene-tag">
          <span className="live-dot" /> {viewModel === 'dollhouse' ? 'ARCHITECTURAL DOLLHOUSE MODEL' : sceneState === 'backend' ? 'RECONSTRUCTED SPATIAL MODEL' : 'MODEL STATUS'}
        </div>
        <div className="axis-gizmo"><span>X</span><i /><span>Y</span><i /><span>Z</span></div>
        <div className="three-hint"><Move3D size={14} /> Drag to orbit · scroll to zoom · right-drag to pan</div>
      </div>
      <div className="three-bottom">
        <span><span className="live-dot" /> ARCHITECTURAL CLAY DOLLHOUSE VIEWPORT</span>
        <span>{viewModel === 'dollhouse' ? 'AXONOMETRIC CUTAWAY · OPEN DOOR LEAVES & WINDOW MULLIONS' : sceneState === 'backend' ? 'BACKEND GEOMETRY · RECONSTRUCTED FROM WALKTHROUGH VIDEO' : 'NO MODEL GEOMETRY AVAILABLE'}</span>
        <Link to={`/projects/${id}/floor-plan`}>Open floor plan <ArrowRight size={14} /></Link>
      </div>
    </div>
  );
}
