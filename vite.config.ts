import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    allowedHosts: ['.manus.computer', 'workspace-qrog47xd.v0.build', 'sb-55n1dkrtkbpv.vercel.run'],
    watch: {
      ignored: [
        '**/backend/**',
        '**/.git/**',
        '**/dist/**',
        '**/node_modules/**',
        '**/*.py',
        '**/*.pyc',
        '**/*.db',
        '**/*.onnx',
        '**/*.mp4',
        '**/*.webm',
      ],
    },
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-dom/client',
      'react-router-dom',
      'lucide-react',
      'framer-motion',
      'three',
      '@react-three/fiber',
      '@react-three/drei',
    ],
  },
});
