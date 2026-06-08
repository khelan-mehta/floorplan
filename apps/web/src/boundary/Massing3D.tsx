import { Grid, OrbitControls } from '@react-three/drei';
import { Canvas } from '@react-three/fiber';
import { useMemo } from 'react';
import * as THREE from 'three';
import { type EditorLevel } from './boundary-model';

const MM_TO_M = 0.001;

function LevelMass({ level }: { level: EditorLevel }) {
  const geometry = useMemo(() => {
    if (level.outline.length < 3) return null;
    const shape = new THREE.Shape();
    level.outline.forEach((p, i) =>
      i === 0
        ? shape.moveTo(p[0] * MM_TO_M, p[1] * MM_TO_M)
        : shape.lineTo(p[0] * MM_TO_M, p[1] * MM_TO_M),
    );
    return new THREE.ExtrudeGeometry(shape, {
      depth: level.floor_to_floor_mm * MM_TO_M,
      bevelEnabled: false,
    });
  }, [level.outline, level.floor_to_floor_mm]);

  if (!geometry) return null;
  return (
    <mesh
      geometry={geometry}
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, level.elevation_mm * MM_TO_M, 0]}
    >
      <meshStandardMaterial color="#3b82f6" transparent opacity={0.4} />
    </mesh>
  );
}

export function Massing3D({ levels }: { levels: EditorLevel[] }) {
  return (
    <Canvas camera={{ position: [18, 16, 18], fov: 50 }}>
      <ambientLight intensity={0.7} />
      <directionalLight position={[12, 20, 8]} intensity={1} />
      <Grid
        args={[60, 60]}
        infiniteGrid
        cellColor="#2a2f3a"
        sectionColor="#3b4252"
        fadeDistance={80}
      />
      {levels.map((l) => (
        <LevelMass key={l.index} level={l} />
      ))}
      <OrbitControls makeDefault />
    </Canvas>
  );
}
