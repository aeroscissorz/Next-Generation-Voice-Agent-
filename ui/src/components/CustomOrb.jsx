import { useEffect, useRef } from 'react'
import * as THREE from 'three'

const vertexShader = `
uniform float u_time;
uniform float u_frequency;
varying vec2 vUv;
varying float vPerlin;
varying vec3 vNormal;
varying vec3 vViewPosition;

// Simplex Noise
vec3 mod289(vec3 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 mod289(vec4 x) { return x - floor(x * (1.0 / 289.0)) * 289.0; }
vec4 permute(vec4 x) { return mod289(((x * 34.0) + 1.0) * x); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }
vec3 fade(vec3 t) { return t * t * t * (t * (t * 6.0 - 15.0) + 10.0); }

float cnoise(vec3 P) {
  vec3 Pi0 = floor(P); vec3 Pi1 = Pi0 + vec3(1.0);
  Pi0 = mod289(Pi0); Pi1 = mod289(Pi1);
  vec3 Pf0 = fract(P); vec3 Pf1 = Pf0 - vec3(1.0);
  vec4 ix = vec4(Pi0.x, Pi1.x, Pi0.x, Pi1.x);
  vec4 iy = vec4(Pi0.y, Pi0.y, Pi1.y, Pi1.y);
  vec4 iz0 = Pi0.zzzz; vec4 iz1 = Pi1.zzzz;
  vec4 ixy = permute(permute(ix) + iy);
  vec4 ixy0 = permute(ixy + iz0); vec4 ixy1 = permute(ixy + iz1);
  vec4 gx0 = ixy0 * (1.0 / 7.0); vec4 gy0 = fract(floor(gx0) * (1.0 / 7.0)) - 0.5;
  gx0 = fract(gx0); vec4 gz0 = vec4(0.5) - abs(gx0) - abs(gy0);
  vec4 sz0 = step(gz0, vec4(0.0)); gx0 -= sz0 * (step(0.0, gx0) - 0.5); gy0 -= sz0 * (step(0.0, gy0) - 0.5);
  vec4 gx1 = ixy1 * (1.0 / 7.0); vec4 gy1 = fract(floor(gx1) * (1.0 / 7.0)) - 0.5;
  gx1 = fract(gx1); vec4 gz1 = vec4(0.5) - abs(gx1) - abs(gy1);
  vec4 sz1 = step(gz1, vec4(0.0)); gx1 -= sz1 * (step(0.0, gx1) - 0.5); gy1 -= sz1 * (step(0.0, gy1) - 0.5);
  vec3 g000 = vec3(gx0.x, gy0.x, gz0.x); vec3 g100 = vec3(gx0.y, gy0.y, gz0.y);
  vec3 g010 = vec3(gx0.z, gy0.z, gz0.z); vec3 g110 = vec3(gx0.w, gy0.w, gz0.w);
  vec3 g001 = vec3(gx1.x, gy1.x, gz1.x); vec3 g101 = vec3(gx1.y, gy1.y, gz1.y);
  vec3 g011 = vec3(gx1.z, gy1.z, gz1.z); vec3 g111 = vec3(gx1.w, gy1.w, gz1.w);
  vec4 norm0 = taylorInvSqrt(vec4(dot(g000, g000), dot(g100, g100), dot(g010, g010), dot(g110, g110)));
  g000 *= norm0.x; g100 *= norm0.y; g010 *= norm0.z; g110 *= norm0.w;
  vec4 norm1 = taylorInvSqrt(vec4(dot(g001, g001), dot(g101, g101), dot(g011, g011), dot(g111, g111)));
  g001 *= norm1.x; g101 *= norm1.y; g011 *= norm1.z; g111 *= norm1.w;
  float n000 = dot(g000, Pf0); float n100 = dot(g100, vec3(Pf1.x, Pf0.yz));
  float n010 = dot(g010, vec3(Pf0.x, Pf1.y, Pf0.z)); float n110 = dot(g110, vec3(Pf1.xy, Pf0.z));
  float n001 = dot(g001, vec3(Pf0.xy, Pf1.z)); float n101 = dot(g101, vec3(Pf1.x, Pf0.y, Pf1.z));
  float n011 = dot(g011, vec3(Pf0.x, Pf1.yz)); float n111 = dot(g111, Pf1);
  vec3 fade_xyz = fade(Pf0);
  vec4 n_z = mix(vec4(n000, n100, n010, n110), vec4(n001, n101, n011, n111), fade_xyz.z);
  vec2 n_yz = mix(n_z.xy, n_z.zw, fade_xyz.y);
  float n_xyz = mix(n_yz.x, n_yz.y, fade_xyz.x);
  return 2.2 * n_xyz;
}

void main() {
  vUv = uv;
  vNormal = normalize(normalMatrix * normal);
  vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
  vViewPosition = -mvPosition.xyz;
  
  float noise = cnoise(vec3(position.x * 1.5, position.y * 1.5, u_time * 0.5));
  vPerlin = noise;
  float displacement = noise * (0.15 + (u_frequency * 0.5));
  vec3 newPos = position + (normal * displacement);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(newPos, 1.0);
}
`

const fragmentShader = `
uniform float u_frequency;
varying float vPerlin;
varying vec3 vNormal;
varying vec3 vViewPosition;

void main() {
  // Cyan, Violet, Pink colors
  vec3 cCyan = vec3(0.0, 0.9, 1.0);
  vec3 cViolet = vec3(0.6, 0.2, 1.0);
  vec3 cPink = vec3(1.0, 0.1, 0.6);
  
  // Color mixing
  vec3 color = mix(cCyan, cViolet, smoothstep(-0.5, 0.2, vPerlin));
  color = mix(color, cPink, smoothstep(0.2, 1.0, vPerlin));
  
  // Fresnel rim lighting
  vec3 normal = normalize(vNormal);
  vec3 viewDir = normalize(vViewPosition);
  float rim = 1.0 - max(dot(normal, viewDir), 0.0);
  float rimPower = pow(rim, 2.0);
  color += vec3(0.2, 0.8, 1.0) * rimPower * 1.0;
  
  // Brightness boost when talking
  float brightness = 1.0 + (u_frequency * 0.5);
  gl_FragColor = vec4(color * brightness, 1.0);
}
`

export default function CustomOrb({ agentState = null, getInputVolume, getOutputVolume, className }) {
    const containerRef = useRef(null)
    const glowRef = useRef(null)
    const sceneRef = useRef(null)
    const rendererRef = useRef(null)
    const blobRef = useRef(null)
    const uniformsRef = useRef(null)
    const currentVolRef = useRef(0)
    const targetVolRef = useRef(0)
    const animationFrameRef = useRef(null)

    useEffect(() => {
        if (!containerRef.current) return

        const width = containerRef.current.clientWidth
        const height = containerRef.current.clientHeight

        // Scene setup
        const scene = new THREE.Scene()
        scene.background = null
        sceneRef.current = scene

        const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100)
        camera.position.z = 5.5

        const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
        renderer.setSize(width, height)
        renderer.setPixelRatio(window.devicePixelRatio)
        renderer.setClearColor(0x000000, 0)
        rendererRef.current = renderer
        containerRef.current.appendChild(renderer.domElement)

        // Create blob
        const geo = new THREE.IcosahedronGeometry(1.0, 128)
        const uniforms = {
            u_time: { value: 0.0 },
            u_frequency: { value: 0.0 }
        }
        uniformsRef.current = uniforms

        const mat = new THREE.ShaderMaterial({
            uniforms,
            vertexShader,
            fragmentShader,
            transparent: true
        })

        const blob = new THREE.Mesh(geo, mat)
        blobRef.current = blob
        scene.add(blob)

        // Animation loop
        const animate = () => {
            animationFrameRef.current = requestAnimationFrame(animate)

            // Get volume based on agent state
            let volume = 0
            if (agentState === 'talking' && getOutputVolume) {
                volume = getOutputVolume()
            } else if (agentState === 'listening' && getInputVolume) {
                volume = getInputVolume()
            }

            targetVolRef.current = volume
            currentVolRef.current += (targetVolRef.current - currentVolRef.current) * 0.1
            uniforms.u_frequency.value = currentVolRef.current

            // Dynamic speed
            const dynamicSpeed = 0.005 + (currentVolRef.current * 0.06)
            uniforms.u_time.value += dynamicSpeed

            // Rotation
            blob.rotation.y += 0.003
            blob.rotation.z -= 0.002

            // Update glow
            if (glowRef.current) {
                const opacity = 0.5 + (currentVolRef.current * 0.5)
                const scale = 1.0 + (currentVolRef.current * 0.5)
                glowRef.current.style.opacity = opacity
                glowRef.current.style.transform = `translate(-50%, -50%) rotate(${uniforms.u_time.value * 30}deg) scale(${scale})`
            }

            renderer.render(scene, camera)
        }

        animate()

        // Cleanup
        return () => {
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current)
            }
            if (rendererRef.current && containerRef.current) {
                containerRef.current.removeChild(rendererRef.current.domElement)
            }
            geo.dispose()
            mat.dispose()
            renderer.dispose()
        }
    }, [agentState, getInputVolume, getOutputVolume])

    return (
        <div className={`relative ${className || 'w-full h-full'}`}>
            {/* Volumetric glow backdrop */}
            <div
                ref={glowRef}
                className="absolute top-1/2 left-1/2 w-[180px] h-[180px] rounded-full pointer-events-none"
                style={{
                    background: `conic-gradient(
            from 0deg,
            rgba(0, 255, 255, 0.8),
            rgba(130, 50, 255, 0.8),
            rgba(255, 0, 150, 0.8),
            rgba(0, 100, 255, 0.8),
            rgba(0, 255, 255, 0.8)
          )`,
                    filter: 'blur(50px)',
                    opacity: 0.5,
                    mixBlendMode: 'screen',
                    transform: 'translate(-50%, -50%)',
                    transition: 'opacity 0.1s'
                }}
            />
            {/* Canvas container */}
            <div
                ref={containerRef}
                className="absolute inset-0"
                style={{
                    WebkitMaskImage: 'radial-gradient(circle, black 0%, black 40%, transparent 70%)',
                    maskImage: 'radial-gradient(circle, black 0%, black 40%, transparent 70%)'
                }}
            />
        </div>
    )
}
