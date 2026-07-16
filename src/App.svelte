<script lang="ts">
  import { onMount } from 'svelte';
  import * as THREE from 'three';

  // Game state
  let score = 0;
  let highscore = 0;
  let level = 1;
  let gemsCollected = 0;
  let totalGems = 0;
  let lives = 3;
  let gameOver = false;
  let gameWon = false;
  let started = false;
  let activeLevelTime = 0;
  let portalActive = false;

  let canvas: HTMLCanvasElement;

  const isDeviceBuild = import.meta.env.VITE_KAIOS_DEVICE === 'true';

  // Web Audio retro-synthesizer and High-Quality OGG Player
  let audioCtx: AudioContext | null = null;
  let audioBuffers: Record<string, AudioBuffer> = {};
  let compressor: DynamicsCompressorNode | null = null;
  let masterGainNode: GainNode | null = null;
  
  let useStaticOgg = true;
  let masterVolumeBoost = 1.8; // 180% volume boost for ultra loudness
  let showAudioLab = false;

  const soundUrls = {
    start: '/audio/start.ogg',
    bounce: '/audio/bounce.ogg',
    gem: '/audio/gem.ogg',
    fall: '/audio/fall.ogg',
    portal: '/audio/portal.ogg',
    win: '/audio/win.ogg'
  };

  function initAudio() {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
  }

  async function preloadSounds() {
    initAudio();
    if (!audioCtx) return;
    for (const [key, url] of Object.entries(soundUrls)) {
      try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP status ${response.status}`);
        const arrayBuffer = await response.arrayBuffer();
        
        // Use promise-based decodeAudioData if possible, with callback fallback
        const decodePromise = audioCtx.decodeAudioData(
          arrayBuffer,
          (decoded) => {
            audioBuffers[key] = decoded;
          },
          (err) => {
            console.warn(`Error decoding OGG file "${key}":`, err);
          }
        );
        if (decodePromise && typeof decodePromise.then === 'function') {
          const decoded = await decodePromise;
          if (decoded) audioBuffers[key] = decoded;
        }
      } catch (e) {
        console.warn(`Failed to preload OGG sound "${key}":`, e);
      }
    }
  }

  function playSound(type: 'bounce' | 'gem' | 'fall' | 'portal' | 'win' | 'start') {
    initAudio();
    if (!audioCtx) return;
    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }

    const now = audioCtx.currentTime;

    // Initialize professional master effects chain (Compressor + Gain Boost)
    if (!compressor) {
      compressor = audioCtx.createDynamicsCompressor();
      // Brickwall limiting style compression to pack maximum energy safely (ULTRA LOUD)
      compressor.threshold.setValueAtTime(-14, now); // Starts compressing early
      compressor.knee.setValueAtTime(15, now);       // Tight knee
      compressor.ratio.setValueAtTime(16, now);      // High compression ratio
      compressor.attack.setValueAtTime(0.003, now);  // Instant punch
      compressor.release.setValueAtTime(0.06, now);  // Fast release

      masterGainNode = audioCtx.createGain();
      masterGainNode.gain.setValueAtTime(masterVolumeBoost, now);

      compressor.connect(masterGainNode);
      masterGainNode.connect(audioCtx.destination);
    } else {
      masterGainNode.gain.setValueAtTime(masterVolumeBoost, now);
    }

    // Play high-quality mastered OGG if available and selected
    if (useStaticOgg && audioBuffers[type]) {
      const source = audioCtx.createBufferSource();
      source.buffer = audioBuffers[type];
      source.connect(compressor);
      source.start(now);
      return;
    }

    // High-volume Svelte synthesizer fallback
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(compressor);

    if (type === 'start') {
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(330, now); // E4
      osc.frequency.exponentialRampToValueAtTime(660, now + 0.3);
      gain.gain.setValueAtTime(0.85, now); // Ultra loud start sweep
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.3);
      osc.start(now);
      osc.stop(now + 0.3);
    } else if (type === 'bounce') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(120, now);
      osc.frequency.exponentialRampToValueAtTime(60, now + 0.1);
      gain.gain.setValueAtTime(1.0, now); // Maximum impact bounce
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.1);
      osc.start(now);
      osc.stop(now + 0.1);
    } else if (type === 'gem') {
      // High frequency diamond sparkle
      const scale = [523.25, 659.25, 783.99, 1046.50];
      scale.forEach((freq, idx) => {
        const o = audioCtx!.createOscillator();
        const g = audioCtx!.createGain();
        o.type = 'triangle';
        o.frequency.setValueAtTime(freq, now + idx * 0.05);
        g.gain.setValueAtTime(0.55, now + idx * 0.05); // High volume
        g.gain.exponentialRampToValueAtTime(0.01, now + idx * 0.05 + 0.12);
        o.connect(g);
        g.connect(compressor!);
        o.start(now + idx * 0.05);
        o.stop(now + idx * 0.05 + 0.15);
      });
    } else if (type === 'fall') {
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(220, now);
      osc.frequency.exponentialRampToValueAtTime(30, now + 0.5);
      gain.gain.setValueAtTime(0.9, now); // Heavy drop void
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.5);
      osc.start(now);
      osc.stop(now + 0.5);
    } else if (type === 'portal') {
      osc.type = 'square';
      osc.frequency.setValueAtTime(440, now);
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.25);
      gain.gain.setValueAtTime(0.65, now); // Piercing portal resonance
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.25);
      osc.start(now);
      osc.stop(now + 0.25);
    } else if (type === 'win') {
      const chord = [261.63, 329.63, 392.00, 523.25, 659.25];
      chord.forEach((freq, idx) => {
        const o = audioCtx!.createOscillator();
        const g = audioCtx!.createGain();
        o.type = 'sine';
        o.frequency.setValueAtTime(freq, now + idx * 0.06);
        g.gain.setValueAtTime(0.5, now + idx * 0.06); // Rich thick master chord
        g.gain.exponentialRampToValueAtTime(0.01, now + idx * 0.06 + 0.2);
        o.connect(g);
        g.connect(compressor!);
        o.start(now + idx * 0.06);
        o.stop(now + idx * 0.06 + 0.25);
      });
    }
  }

  // Beautiful 7x7 Maze Plateau Level Layouts
  // '#' = neon glass wall
  // '.' = solid cyber floor
  // 'O' = deadly open void hole
  // 'S' = initial spawn spot
  // '*' = glow cyber crystal
  // 'E' = dimension escape portal
  const LEVELS = [
    [
      "#######",
      "#E..*##",
      "#.#.###",
      "#*..S.#",
      "#.###.#",
      "#*...*#",
      "#######"
    ],
    [
      "#######",
      "#E..*##",
      "##.#..#",
      "#*..S.#",
      "#..#..#",
      "#*..O*#",
      "#######"
    ],
    [
      "#######",
      "#E.O.*#",
      "#O.#.O#",
      "#*..S.#",
      "#O.#.O#",
      "#*.O.*#",
      "#######"
    ],
    [
      "#######",
      "#E.O.*#",
      "##...##",
      "#*.S.*#",
      "##...##",
      "#*.O.*#",
      "#######"
    ]
  ];

  onMount(() => {
    const saved = localStorage.getItem('kaios_cybertilt_highscore');
    if (saved) {
      highscore = parseInt(saved, 10);
    }
    preloadSounds();
  });

  onMount(() => {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x03030c);
    scene.fog = new THREE.FogExp2(0x03030c, 0.06);

    const width = isDeviceBuild ? window.innerWidth : 240;
    const height = isDeviceBuild ? window.innerHeight : 320;

    // Dynamic isometric camera looking down at the tilting board
    const camera = new THREE.PerspectiveCamera(46, width / height, 0.1, 100);
    camera.position.set(0, 7.8, 6.8);
    camera.lookAt(new THREE.Vector3(0, -0.4, 0));

    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    renderer.setSize(width, height);
    renderer.shadowMap.enabled = true;

    // Cyan / Magenta Cyber Light theme
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
    scene.add(ambientLight);

    const pinkLight = new THREE.DirectionalLight(0xff00ff, 0.9);
    pinkLight.position.set(4, 9, 3);
    scene.add(pinkLight);

    const cyanLight = new THREE.DirectionalLight(0x00ffff, 0.7);
    cyanLight.position.set(-4, 9, -3);
    scene.add(cyanLight);

    // Nebula lighting follows the ball
    const ballGlowLight = new THREE.PointLight(0x00ffff, 1.4, 4);
    scene.add(ballGlowLight);

    // Rotating 3D Starfield background
    const starCount = 80;
    const starGeometry = new THREE.BufferGeometry();
    const starPositions = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
      starPositions[i * 3] = (Math.random() - 0.5) * 16;
      starPositions[i * 3 + 1] = (Math.random() - 0.5) * 12;
      starPositions[i * 3 + 2] = -Math.random() * 20;
    }
    const starBufferAttr = new THREE.BufferAttribute(starPositions, 3);
    if ((starGeometry as any).setAttribute) {
      (starGeometry as any).setAttribute('position', starBufferAttr);
    } else {
      (starGeometry as any).addAttribute('position', starBufferAttr);
    }
    const starMaterial = new THREE.PointsMaterial({
      color: 0xffffff,
      size: 0.04,
      transparent: true,
      opacity: 0.5
    });
    const starfield = new THREE.Points(starGeometry, starMaterial);
    scene.add(starfield);

    // Group that represents the entire tilting board structure
    const boardGroup = new THREE.Group();
    scene.add(boardGroup);

    // Dimensions
    const GRID_SIZE = 7;
    const CELL_SIZE = 0.94;
    const halfGrid = (GRID_SIZE * CELL_SIZE) / 2;

    // Platform elements
    interface Tile {
      mesh: THREE.Mesh;
      wire: THREE.LineSegments;
    }
    let tiles: Tile[] = [];

    interface Wall {
      mesh: THREE.Mesh;
      wire: THREE.LineSegments;
      gridX: number;
      gridZ: number;
    }
    let walls: Wall[] = [];

    interface Gem {
      mesh: THREE.Mesh;
      gridX: number;
      gridZ: number;
      collected: boolean;
    }
    let gems: Gem[] = [];

    interface Hole {
      gridX: number;
      gridZ: number;
    }
    let holes: Hole[] = [];

    let portalMesh: THREE.Mesh | null = null;
    let portalLight: THREE.PointLight | null = null;
    let portalGridPos = { x: 0, z: 0 };

    // Player Ball Sphere
    const ballRadius = 0.18;
    const ballGeo = new THREE.SphereGeometry(ballRadius, 20, 20);
    const ballMat = new THREE.MeshStandardMaterial({
      color: 0x00ffff,
      emissive: 0x003333,
      roughness: 0.08,
      metalness: 0.95
    });
    const ball = new THREE.Mesh(ballGeo, ballMat);
    boardGroup.add(ball); // Ball belongs to the board group locally to roll smoothly!

    let ballLocalPos = new THREE.Vector3(0, ballRadius, 0);
    let ballLocalVel = new THREE.Vector3(0, 0, 0);
    let isFallingInHole = false;
    let fallScale = 1.0;

    // Controls tilt parameters
    let targetTiltX = 0; // Pitch
    let targetTiltZ = 0; // Roll
    let currentTiltX = 0;
    let currentTiltZ = 0;

    const TILT_MAX = 0.24; // Maximum pitch/roll rotation (about 14 degrees)
    const TILT_ACCEL = 0.016;
    const TILT_FRICTION = 0.88;

    // Ball physics constants
    const GRAVITY_CONSTANT = 0.018;
    const BALL_FRICTION = 0.985;
    const BOUNCE_DAMPING = 0.55;

    // Key input matrix
    let keysPressed = {
      up: false,
      down: false,
      left: false,
      right: false
    };

    function buildLevel() {
      // Clear past visual assets
      tiles.forEach(t => {
        boardGroup.remove(t.mesh);
        boardGroup.remove(t.wire);
      });
      tiles = [];

      walls.forEach(w => {
        boardGroup.remove(w.mesh);
        boardGroup.remove(w.wire);
      });
      walls = [];

      gems.forEach(g => boardGroup.remove(g.mesh));
      gems = [];

      holes = [];

      if (portalMesh) {
        boardGroup.remove(portalMesh);
        portalMesh = null;
      }
      if (portalLight) {
        boardGroup.remove(portalLight);
        portalLight = null;
      }

      const map = LEVELS[(level - 1) % LEVELS.length];
      gemsCollected = 0;
      totalGems = 0;
      portalActive = false;

      // Build 7x7 grid elements
      for (let r = 0; r < GRID_SIZE; r++) {
        for (let c = 0; c < GRID_SIZE; c++) {
          const char = map[r][c];

          // Calculate local position of cell relative to boardGroup center
          const lx = (c - GRID_SIZE / 2 + 0.5) * CELL_SIZE;
          const lz = (r - GRID_SIZE / 2 + 0.5) * CELL_SIZE;

          if (char === 'O') {
            // Register Hole coordinate
            holes.push({ gridX: c, gridZ: r });
            continue; // Do not draw solid ground
          }

          // Ground Floor tile
          const tileGeo = new THREE.BoxGeometry(CELL_SIZE * 0.96, 0.12, CELL_SIZE * 0.96);
          const tileMat = new THREE.MeshStandardMaterial({
            color: 0x070718,
            roughness: 0.4,
            metalness: 0.2
          });
          const tileMesh = new THREE.Mesh(tileGeo, tileMat);
          tileMesh.position.set(lx, -0.06, lz);
          boardGroup.add(tileMesh);

          // Grid wire lines
          const edges = new THREE.EdgesGeometry(tileGeo);
          const wireMat = new THREE.LineBasicMaterial({ color: 0x111133 });
          const wire = new THREE.LineSegments(edges, wireMat);
          wire.position.copy(tileMesh.position);
          boardGroup.add(wire);

          tiles.push({ mesh: tileMesh, wire });

          if (char === '#') {
            // Glass Cyber-Wall
            const wallGeo = new THREE.BoxGeometry(CELL_SIZE * 0.95, 0.5, CELL_SIZE * 0.95);
            const wallMat = new THREE.MeshStandardMaterial({
              color: 0x110022,
              roughness: 0.1,
              metalness: 0.8,
              transparent: true,
              opacity: 0.75
            });
            const wallMesh = new THREE.Mesh(wallGeo, wallMat);
            wallMesh.position.set(lx, 0.25, lz);
            boardGroup.add(wallMesh);

            const wallEdges = new THREE.EdgesGeometry(wallGeo);
            const wallWireMat = new THREE.LineBasicMaterial({ color: 0xff00ff });
            const wallWire = new THREE.LineSegments(wallEdges, wallWireMat);
            wallWire.position.copy(wallMesh.position);
            boardGroup.add(wallWire);

            walls.push({ mesh: wallMesh, wire: wallWire, gridX: c, gridZ: r });

          } else if (char === 'S') {
            // Initial spawn coordinates
            ballLocalPos.set(lx, ballRadius, lz);
            ballLocalVel.set(0, 0, 0);
            ball.position.copy(ballLocalPos);
            ball.scale.set(1, 1, 1);
            isFallingInHole = false;
            fallScale = 1.0;

          } else if (char === '*') {
            // Cyber Crystal
            const gemGeo = new THREE.OctahedronGeometry(0.15);
            const gemMat = new THREE.MeshStandardMaterial({
              color: 0x00ffcc,
              emissive: 0x003322,
              roughness: 0.1,
              metalness: 0.9
            });
            const gemMesh = new THREE.Mesh(gemGeo, gemMat);
            gemMesh.position.set(lx, 0.28, lz);
            boardGroup.add(gemMesh);

            gems.push({ mesh: gemMesh, gridX: c, gridZ: r, collected: false });
            totalGems++;

          } else if (char === 'E') {
            // Golden Escape Hole/Portal
            const portalGeo = new THREE.TorusGeometry(0.24, 0.05, 8, 16);
            portalGeo.rotateX(Math.PI / 2);
            const portalMat = new THREE.MeshStandardMaterial({
              color: 0xffcc00,
              emissive: 0x442200,
              roughness: 0.1,
              metalness: 0.9
            });
            portalMesh = new THREE.Mesh(portalGeo, portalMat);
            portalMesh.position.set(lx, 0.02, lz);
            boardGroup.add(portalMesh);

            portalLight = new THREE.PointLight(0xffaa00, 0, 2);
            portalLight.position.set(lx, 0.4, lz);
            boardGroup.add(portalLight);

            portalGridPos = { x: c, z: r };
          }
        }
      }

      // Reset Board angles
      targetTiltX = 0;
      targetTiltZ = 0;
      currentTiltX = 0;
      currentTiltZ = 0;
      boardGroup.rotation.set(0, 0, 0);
    }

    // Handle fall respawn
    function handleFall() {
      playSound('fall');
      lives--;
      if (lives <= 0) {
        gameOver = true;
      } else {
        // Find spawn coordinate
        const map = LEVELS[(level - 1) % LEVELS.length];
        for (let r = 0; r < GRID_SIZE; r++) {
          for (let c = 0; c < GRID_SIZE; c++) {
            if (map[r][c] === 'S') {
              const lx = (c - GRID_SIZE / 2 + 0.5) * CELL_SIZE;
              const lz = (r - GRID_SIZE / 2 + 0.5) * CELL_SIZE;
              ballLocalPos.set(lx, ballRadius, lz);
              ballLocalVel.set(0, 0, 0);
              ball.position.copy(ballLocalPos);
              ball.scale.set(1, 1, 1);
              isFallingInHole = false;
              fallScale = 1.0;
            }
          }
        }
      }
    }

    // Set interactive keys on/off
    (window as any).setKeyState = (dir: 'up' | 'down' | 'left' | 'right', isPressed: boolean) => {
      initAudio();
      keysPressed[dir] = isPressed;
    };

    (window as any).triggerEnter = () => {
      initAudio();
      if (!started || gameOver || gameWon) {
        started = true;
        gameOver = false;
        gameWon = false;
        level = 1;
        score = 0;
        lives = 3;
        buildLevel();
        playSound('start');
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === '5') (window as any).triggerEnter();
      if (e.key === 'ArrowUp' || e.key === '2') keysPressed.up = true;
      if (e.key === 'ArrowDown' || e.key === '8') keysPressed.down = true;
      if (e.key === 'ArrowLeft' || e.key === '4') keysPressed.left = true;
      if (e.key === 'ArrowRight' || e.key === '6') keysPressed.right = true;
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.key === 'ArrowUp' || e.key === '2') keysPressed.up = false;
      if (e.key === 'ArrowDown' || e.key === '8') keysPressed.down = false;
      if (e.key === 'ArrowLeft' || e.key === '4') keysPressed.left = false;
      if (e.key === 'ArrowRight' || e.key === '6') keysPressed.right = false;
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    let animationId: number;

    function animate(time: number) {
      animationId = requestAnimationFrame(animate);

      // Starfield background visual drift
      starfield.rotation.y += 0.001;

      if (!started || gameOver || gameWon) {
        renderer.render(scene, camera);
        return;
      }

      // 1. Compute board tilting angles based on keys
      if (keysPressed.up) targetTiltX = Math.max(-TILT_MAX, targetTiltX - TILT_ACCEL);
      if (keysPressed.down) targetTiltX = Math.min(TILT_MAX, targetTiltX + TILT_ACCEL);
      if (keysPressed.left) targetTiltZ = Math.min(TILT_MAX, targetTiltZ + TILT_ACCEL);
      if (keysPressed.right) targetTiltZ = Math.max(-TILT_MAX, targetTiltZ - TILT_ACCEL);

      // Decay / return to horizontal gently when keys are released
      if (!keysPressed.up && !keysPressed.down) targetTiltX *= TILT_FRICTION;
      if (!keysPressed.left && !keysPressed.right) targetTiltZ *= TILT_FRICTION;

      // Elastic rotation interpolation for ultra-organic physical response
      currentTiltX += (targetTiltX - currentTiltX) * 0.16;
      currentTiltZ += (targetTiltZ - currentTiltZ) * 0.16;

      boardGroup.rotation.x = currentTiltX;
      boardGroup.rotation.z = currentTiltZ;

      // 2. Local physical model of the rolling ball inside the board coordinate space
      if (!isFallingInHole) {
        // Gravity pulls ball along board gradients!
        // Tilting left/right (rot Z) creates slide forces on X
        // Tilting forward/backward (rot X) creates slide forces on Z
        const accelX = -Math.sin(currentTiltZ) * GRAVITY_CONSTANT;
        const accelZ = Math.sin(currentTiltX) * GRAVITY_CONSTANT;

        ballLocalVel.x += accelX;
        ballLocalVel.z += accelZ;

        ballLocalVel.x *= BALL_FRICTION;
        ballLocalVel.z *= BALL_FRICTION;

        ballLocalPos.x += ballLocalVel.x;
        ballLocalPos.z += ballLocalVel.z;

        // 3. Robust grid-based wall bounding-box collision checks
        const cellMin = -halfGrid;
        const cellMax = halfGrid;

        // Check each wall block collision
        walls.forEach(wall => {
          const wx = (wall.gridX - GRID_SIZE / 2 + 0.5) * CELL_SIZE;
          const wz = (wall.gridZ - GRID_SIZE / 2 + 0.5) * CELL_SIZE;

          const dx = ballLocalPos.x - wx;
          const dz = ballLocalPos.z - wz;

          const overlapX = (CELL_SIZE / 2 + ballRadius) - Math.abs(dx);
          const overlapY = (CELL_SIZE / 2 + ballRadius) - Math.abs(dz);

          if (overlapX > 0 && overlapY > 0) {
            // Push out in the direction of shallowest overlap
            if (overlapX < overlapY) {
              const sign = dx > 0 ? 1 : -1;
              ballLocalPos.x = wx + sign * (CELL_SIZE / 2 + ballRadius);
              ballLocalVel.x *= -BOUNCE_DAMPING;
              if (Math.abs(ballLocalVel.x) > 0.015) playSound('bounce');
            } else {
              const sign = dz > 0 ? 1 : -1;
              ballLocalPos.z = wz + sign * (CELL_SIZE / 2 + ballRadius);
              ballLocalVel.z *= -BOUNCE_DAMPING;
              if (Math.abs(ballLocalVel.z) > 0.015) playSound('bounce');
            }
          }
        });

        // Board outer perimeter limits (prevent flying off completely unless a hole)
        const boundLimit = halfGrid - ballRadius;
        if (ballLocalPos.x < -boundLimit) {
          ballLocalPos.x = -boundLimit;
          ballLocalVel.x *= -BOUNCE_DAMPING;
          playSound('bounce');
        } else if (ballLocalPos.x > boundLimit) {
          ballLocalPos.x = boundLimit;
          ballLocalVel.x *= -BOUNCE_DAMPING;
          playSound('bounce');
        }

        if (ballLocalPos.z < -boundLimit) {
          ballLocalPos.z = -boundLimit;
          ballLocalVel.z *= -BOUNCE_DAMPING;
          playSound('bounce');
        } else if (ballLocalPos.z > boundLimit) {
          ballLocalPos.z = boundLimit;
          ballLocalVel.z *= -BOUNCE_DAMPING;
          playSound('bounce');
        }

        // 4. Abyss / Hole fall-through detection
        // Convert current local position back to map cell index
        const currentGridX = Math.floor((ballLocalPos.x + halfGrid) / CELL_SIZE);
        const currentGridZ = Math.floor((ballLocalPos.z + halfGrid) / CELL_SIZE);

        const fallenInHole = holes.some(h => h.gridX === currentGridX && h.gridZ === currentGridZ);
        if (fallenInHole) {
          // Verify if it is close enough to the center of the void hole to start dropping down
          const hx = (currentGridX - GRID_SIZE / 2 + 0.5) * CELL_SIZE;
          const hz = (currentGridZ - GRID_SIZE / 2 + 0.5) * CELL_SIZE;
          const dist = Math.sqrt((ballLocalPos.x - hx) * (ballLocalPos.x - hx) + (ballLocalPos.z - hz) * (ballLocalPos.z - hz));

          if (dist < CELL_SIZE * 0.45) {
            isFallingInHole = true;
            ballLocalVel.set(0, 0, 0);
          }
        }

        // Apply physical rolling sphere rotation mirroring actual travel
        ball.rotation.z -= ballLocalVel.x * 2.2;
        ball.rotation.x += ballLocalVel.z * 2.2;

        ball.position.copy(ballLocalPos);

      } else {
        // Fall-in-hole graphic shrinking sequence
        fallScale -= 0.05;
        ballLocalPos.y -= 0.04;
        ball.scale.set(Math.max(0.001, fallScale), Math.max(0.001, fallScale), Math.max(0.001, fallScale));
        ball.position.copy(ballLocalPos);

        if (fallScale <= 0.05) {
          handleFall();
        }
      }

      // Animate Cyber Crystals
      gems.forEach(gem => {
        if (!gem.collected) {
          gem.mesh.rotation.y += 0.04;
          gem.mesh.rotation.x += 0.015;

          // Collect diamond crystal detection
          const dist = ball.position.distanceTo(gem.mesh.position);
          if (dist < 0.44) {
            gem.collected = true;
            boardGroup.remove(gem.mesh);
            gemsCollected++;
            score += 150;
            playSound('gem');

            // Activate portal escapes once all crystals are extracted
            if (gemsCollected >= totalGems) {
              portalActive = true;
              playSound('portal');
              if (portalLight) portalLight.intensity = 2.5;
            }
          }
        }
      });

      // Animate golden exit Portal
      if (portalMesh) {
        portalMesh.rotation.y += 0.05;

        // Pulse the portal glow when active
        if (portalActive) {
          portalMesh.scale.set(
            1 + Math.sin(time * 0.008) * 0.1,
            1 + Math.sin(time * 0.008) * 0.1,
            1 + Math.sin(time * 0.008) * 0.1
          );

          // Success extraction portal collision
          const dist = ball.position.distanceTo(portalMesh.position);
          if (dist < 0.42) {
            level++;
            score += 1000;
            playSound('win');
            if (level > LEVELS.length) {
              gameWon = true;
            } else {
              buildLevel();
            }
          }
        } else {
          portalMesh.scale.set(0.8, 0.8, 0.8);
        }
      }

      // PointLight follows ball player
      ballGlowLight.position.set(ball.position.x, 1.2, ball.position.z);

      // Highscore saving
      if (score > highscore) {
        highscore = score;
        localStorage.setItem('kaios_cybertilt_highscore', highscore.toString());
      }

      renderer.render(scene, camera);
    }

    animate(0);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
      cancelAnimationFrame(animationId);
      renderer.dispose();
      delete (window as any).setKeyState;
      delete (window as any).triggerEnter;
    };
  });
</script>

{#if isDeviceBuild}
  <main class="screen device-full">
    <canvas bind:this={canvas}></canvas>
    <div class="ui">
      <div class="top-bar">
        <div class="level">LVL:{level}</div>
        <div class="crystals">
          {#if portalActive}
            <span class="escape-ready">ESCAPE NOW!</span>
          {:else}
            CRYS:{gemsCollected}/{totalGems}
          {/if}
        </div>
        <div class="lives">
          {#each Array(Math.max(0, lives)) as _}&hearts;{/each}
        </div>
      </div>
      
      {#if !started}
        <div class="overlay">
          <h1>CYBERTILT</h1>
          <p class="subtitle">3D BALANCE LABYRINTH</p>
          <button class="menu-btn" on:click={() => (window as any).triggerEnter()}>POWER UP</button>
          <div class="controls-guide">
            <p>D-Pad: Tilt Cyber Board</p>
            <p>Extract all crystals to escape</p>
            <p>Avoid deadly void holes!</p>
          </div>
        </div>
      {:else if gameOver}
        <div class="overlay red-alert">
          <h1>VOID DROP</h1>
          <p>Score: {score}</p>
          <button class="menu-btn" on:click={() => (window as any).triggerEnter()}>RETRY</button>
        </div>
      {:else if gameWon}
        <div class="overlay gold-alert">
          <h1>GRAND MASTER</h1>
          <p>Perfect Extraction!</p>
          <p>Score: {score}</p>
          <button class="menu-btn" on:click={() => (window as any).triggerEnter()}>EXTRACT AGAIN</button>
        </div>
      {/if}
    </div>
  </main>
{:else}
  <div class="cyber-workspace">
    <!-- GameBoy Hardware Console -->
    <div class="device-container">
      <div class="gameboy-top-label">KAI-3D CYBERTILT</div>
      <main class="screen">
        <canvas bind:this={canvas}></canvas>
        <div class="ui">
          <div class="top-bar">
            <div class="level">LVL:{level}</div>
            <div class="crystals">
              {#if portalActive}
                <span class="escape-ready">ESCAPE NOW!</span>
              {:else}
                CRYS:{gemsCollected}/{totalGems}
              {/if}
            </div>
            <div class="lives">
              {#each Array(Math.max(0, lives)) as _}&hearts;{/each}
            </div>
          </div>
          
          {#if !started}
            <div class="overlay">
              <h1>CYBERTILT</h1>
              <p class="subtitle">3D BALANCE LABYRINTH</p>
              <button class="menu-btn" on:click={() => (window as any).triggerEnter()}>POWER UP</button>
              <div class="controls-guide">
                <p>D-Pad: Tilt Cyber Board</p>
                <p>Extract all crystals to escape</p>
                <p>Avoid deadly void holes!</p>
              </div>
            </div>
          {:else if gameOver}
            <div class="overlay red-alert">
              <h1>VOID DROP</h1>
              <p>Score: {score}</p>
              <button class="menu-btn" on:click={() => (window as any).triggerEnter()}>RETRY</button>
            </div>
          {:else if gameWon}
            <div class="overlay gold-alert">
              <h1>GRAND MASTER</h1>
              <p>Perfect Extraction!</p>
              <p>Score: {score}</p>
              <button class="menu-btn" on:click={() => (window as any).triggerEnter()}>EXTRACT AGAIN</button>
            </div>
          {/if}
        </div>
      </main>
      
      <div class="virtual-controller">
        <div class="d-pad-section">
          <div class="d-pad">
            <!-- Up Button -->
            <button class="btn up" 
              on:mousedown={() => (window as any).setKeyState('up', true)}
              on:mouseup={() => (window as any).setKeyState('up', false)}
              on:mouseleave={() => (window as any).setKeyState('up', false)}
              on:touchstart={(e) => { e.preventDefault(); (window as any).setKeyState('up', true); }}
              on:touchend={(e) => { e.preventDefault(); (window as any).setKeyState('up', false); }}
            >&#9650;</button>

            <!-- Left Button -->
            <button class="btn left" 
              on:mousedown={() => (window as any).setKeyState('left', true)}
              on:mouseup={() => (window as any).setKeyState('left', false)}
              on:mouseleave={() => (window as any).setKeyState('left', false)}
              on:touchstart={(e) => { e.preventDefault(); (window as any).setKeyState('left', true); }}
              on:touchend={(e) => { e.preventDefault(); (window as any).setKeyState('left', false); }}
            >&#9664;</button>

            <!-- Center Reset Button -->
            <button class="btn enter" on:click={() => (window as any).triggerEnter()}>OK</button>

            <!-- Right Button -->
            <button class="btn right" 
              on:mousedown={() => (window as any).setKeyState('right', true)}
              on:mouseup={() => (window as any).setKeyState('right', false)}
              on:mouseleave={() => (window as any).setKeyState('right', false)}
              on:touchstart={(e) => { e.preventDefault(); (window as any).setKeyState('right', true); }}
              on:touchend={(e) => { e.preventDefault(); (window as any).setKeyState('right', false); }}
            >&#9654;</button>

            <!-- Down Button -->
            <button class="btn down" 
              on:mousedown={() => (window as any).setKeyState('down', true)}
              on:mouseup={() => (window as any).setKeyState('down', false)}
              on:mouseleave={() => (window as any).setKeyState('down', false)}
              on:touchstart={(e) => { e.preventDefault(); (window as any).setKeyState('down', true); }}
              on:touchend={(e) => { e.preventDefault(); (window as any).setKeyState('down', false); }}
            >&#9660;</button>
          </div>
        </div>
        <div class="console-decor">
          <div class="speaker-slits">
            <div class="slit"></div>
            <div class="slit"></div>
            <div class="slit"></div>
          </div>
          <div class="buttons-badge">KAIOS TILT-ENGINE</div>
        </div>
      </div>
    </div>

    <!-- Cyber Sound FX Lab & Mastery Equalizer Panel -->
    <div class="audio-lab-panel">
      <div class="lab-header">
        <div class="header-logo">
          <span class="logo-icon">&#127914;</span>
          <div class="logo-texts">
            <span class="title">CYBER SYNTH LABS</span>
            <span class="subtitle">HIGH POWER SOUND INTEGRATION</span>
          </div>
        </div>
        <span class="status-indicator">● ONLINE</span>
      </div>

      <div class="lab-body">
        <!-- Section 1: Playback engine selection -->
        <div class="lab-section">
          <div class="section-header">
            <span class="num">01</span>
            <span class="label">PLAYBACK ENGINE MODE</span>
          </div>
          <div class="engine-selector">
            <button class="engine-btn" class:active={useStaticOgg} on:click={() => useStaticOgg = true}>
              <div class="bullet"></div>
              <div class="btn-text">
                <span class="main-label">MASTERED OGG VORBIS</span>
                <span class="sub-label">High quality audio file playback</span>
              </div>
            </button>
            <button class="engine-btn" class:active={!useStaticOgg} on:click={() => useStaticOgg = false}>
              <div class="bullet"></div>
              <div class="btn-text">
                <span class="main-label">LIVE PROCEDURAL SYNTH</span>
                <span class="sub-label">Real-time oscillator synthesis</span>
              </div>
            </button>
          </div>
        </div>

        <!-- Section 2: Loudness boost slider -->
        <div class="lab-section">
          <div class="section-header">
            <span class="num">02</span>
            <span class="label">LOUDNESS BOOST (MASTER GAIN)</span>
          </div>
          <div class="slider-container">
            <div class="slider-numeric">
              <span class="text-cyan-400">GAIN MULTIPLIER:</span>
              <span class="boost-badge text-pink-500 font-bold font-mono">{(masterVolumeBoost * 100).toFixed(0)}%</span>
            </div>
            <input 
              type="range" 
              min="0.5" 
              max="3.0" 
              step="0.1" 
              bind:value={masterVolumeBoost} 
              class="volume-slider" 
            />
            <div class="slider-labels">
              <span>0.5x</span>
              <span>1.0x (Normal)</span>
              <span>2.0x (Very Loud)</span>
              <span>3.0x (Max Power)</span>
            </div>
          </div>
        </div>

        <!-- Section 3: Retro Soundboard & Archive -->
        <div class="lab-section">
          <div class="section-header">
            <span class="num">03</span>
            <span class="label">FX SOUNDBOARD & AUDIO DOWNLOADS</span>
          </div>
          <div class="soundboard-grid">
            {#each Object.keys(soundUrls) as soundName}
              <div class="soundboard-row">
                <div class="sound-info">
                  <span class="icon">&#9836;</span>
                  <span class="name">{soundName.toUpperCase()}</span>
                </div>
                <div class="sound-actions">
                  <button class="action-btn play" on:click={() => playSound(soundName)}>
                    PLAY
                  </button>
                  <a class="action-btn download" href="/audio/{soundName}.ogg" download="{soundName}.ogg" target="_blank" rel="noreferrer">
                    GET OGG
                  </a>
                </div>
              </div>
            {/each}
          </div>
        </div>
      </div>

      <div class="lab-footer">
        <span class="footer-spec">44.1 KHZ / STEREO / Q8 256KBPS DIGITAL MASTERS</span>
      </div>
    </div>
  </div>
{/if}

<style>
  :global(body) {
    margin: 0;
    overflow: hidden;
    background-color: #020205;
    font-family: 'Courier New', Courier, monospace;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    box-sizing: border-box;
  }
  .cyber-workspace {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: center;
    align-items: stretch;
    gap: 30px;
    max-width: 900px;
    width: 100%;
    margin: auto;
    padding: 20px;
    box-sizing: border-box;
  }
  
  /* Cyber Synth Labs Panel Styling */
  .audio-lab-panel {
    flex: 1;
    min-width: 280px;
    max-width: 440px;
    background: linear-gradient(135deg, #090915, #04040a);
    border: 3px solid #ff00ff;
    border-radius: 20px;
    box-shadow: 0 10px 30px rgba(255, 0, 255, 0.15), inset 0 1px 3px rgba(255,255,255,0.05);
    padding: 20px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    gap: 15px;
    color: #ffffff;
    box-sizing: border-box;
  }

  .lab-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #ff00ff;
    padding-bottom: 12px;
  }
  
  .header-logo {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  
  .logo-icon {
    font-size: 24px;
    text-shadow: 0 0 10px #ff00ff;
  }
  
  .logo-texts {
    display: flex;
    flex-direction: column;
  }
  
  .logo-texts .title {
    font-size: 14px;
    font-weight: 900;
    letter-spacing: 1.5px;
    color: #ff00ff;
    text-shadow: 0 0 5px rgba(255, 0, 255, 0.5);
  }
  
  .logo-texts .subtitle {
    font-size: 8px;
    color: #00ffff;
    letter-spacing: 1px;
  }
  
  .status-indicator {
    font-size: 10px;
    font-weight: bold;
    color: #00ff66;
    text-shadow: 0 0 8px rgba(0, 255, 102, 0.6);
    animation: pulse-glow 2s infinite alternate;
  }

  @keyframes pulse-glow {
    from { opacity: 0.6; text-shadow: 0 0 4px rgba(0, 255, 102, 0.4); }
    to { opacity: 1; text-shadow: 0 0 12px rgba(0, 255, 102, 0.8); }
  }

  .lab-body {
    display: flex;
    flex-direction: column;
    gap: 16px;
    flex-grow: 1;
  }

  .lab-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 10px;
    font-weight: bold;
    letter-spacing: 1px;
    color: #00ffff;
  }
  
  .section-header .num {
    background: rgba(0, 255, 255, 0.15);
    padding: 1px 4px;
    border-radius: 3px;
    border: 1px solid #00ffff;
  }

  .engine-selector {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .engine-btn {
    background: #0d0d22;
    border: 1px solid #333355;
    border-radius: 8px;
    padding: 10px;
    color: #8888aa;
    text-align: left;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 10px;
    transition: all 0.15s ease;
  }

  .engine-btn:hover {
    border-color: #00ffff;
    background: #0f0f2b;
  }

  .engine-btn.active {
    border-color: #00ffff;
    background: rgba(0, 255, 255, 0.08);
    color: #ffffff;
    box-shadow: 0 0 10px rgba(0, 255, 255, 0.1);
  }

  .engine-btn .bullet {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    border: 2px solid #333355;
    background: transparent;
    transition: all 0.15s ease;
  }

  .engine-btn.active .bullet {
    border-color: #00ffff;
    background: #00ffff;
    box-shadow: 0 0 8px #00ffff;
  }

  .btn-text {
    display: flex;
    flex-direction: column;
  }

  .btn-text .main-label {
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
  }

  .btn-text .sub-label {
    font-size: 8px;
    opacity: 0.7;
  }

  .slider-container {
    background: #0a0a18;
    border: 1px solid #1e1e3f;
    border-radius: 8px;
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .slider-numeric {
    display: flex;
    justify-content: space-between;
    font-size: 9px;
    font-weight: bold;
    letter-spacing: 1px;
  }

  .volume-slider {
    -webkit-appearance: none;
    appearance: none;
    width: 100%;
    height: 6px;
    border-radius: 3px;
    background: #1e1e3f;
    outline: none;
  }

  .volume-slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #ff00ff;
    cursor: pointer;
    box-shadow: 0 0 10px #ff00ff;
    border: 2px solid #ffffff;
  }

  .slider-labels {
    display: flex;
    justify-content: space-between;
    font-size: 7.5px;
    color: #555577;
    font-weight: bold;
  }

  .soundboard-grid {
    display: flex;
    flex-direction: column;
    gap: 6px;
    background: #070712;
    border: 1px solid #1e1e38;
    border-radius: 10px;
    padding: 8px;
    max-height: 180px;
    overflow-y: auto;
  }

  .soundboard-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px;
    background: #0d0d22;
    border-radius: 6px;
    border: 1px solid #1a1a3a;
  }

  .sound-info {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .sound-info .icon {
    font-size: 11px;
    color: #00ffff;
  }

  .sound-info .name {
    font-size: 9px;
    font-weight: bold;
    font-family: monospace;
    color: #e2e2e2;
  }

  .sound-actions {
    display: flex;
    gap: 6px;
  }

  .action-btn {
    font-size: 8px;
    font-weight: bold;
    font-family: inherit;
    padding: 4px 8px;
    border-radius: 4px;
    cursor: pointer;
    text-decoration: none;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .action-btn.play {
    background: #00ffff;
    color: #03030c;
    border: none;
    box-shadow: 0 1.5px 0 #008888;
  }

  .action-btn.play:active {
    transform: translateY(1px);
    box-shadow: none;
  }

  .action-btn.download {
    background: rgba(255, 0, 255, 0.15);
    color: #ff00ff;
    border: 1px solid #ff00ff;
  }

  .action-btn.download:hover {
    background: #ff00ff;
    color: #ffffff;
    box-shadow: 0 0 6px rgba(255,0,255,0.4);
  }

  .lab-footer {
    border-top: 1px solid #111126;
    padding-top: 10px;
    text-align: center;
  }

  .footer-spec {
    font-size: 7px;
    color: #444466;
    letter-spacing: 1px;
    font-weight: bold;
  }

  .device-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    background: linear-gradient(145deg, #11111d, #05050b);
    padding: 25px 15px 15px 15px;
    border-radius: 28px;
    box-shadow: 0 15px 40px rgba(0,0,0,0.95), inset 0 2px 5px rgba(255,255,255,0.08);
    gap: 15px;
    border: 3px solid #00ffff;
    position: relative;
  }
  .device-container::before {
    content: '';
    position: absolute;
    top: 6px;
    left: 50%;
    transform: translateX(-50%);
    width: 60px;
    height: 4px;
    background: #00ffff;
    border-radius: 2px;
    opacity: 0.8;
  }
  .gameboy-top-label {
    color: #ff00ff;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 2px;
    text-shadow: 0 0 5px #ff00ff;
    margin-bottom: -5px;
  }
  .screen {
    position: relative;
    width: 240px;
    height: 320px;
    background-color: #03030c;
    overflow: hidden;
    border: 3px solid #ff00ff;
    border-radius: 8px;
    box-shadow: 0 0 15px rgba(255,0,255,0.35);
  }
  .screen.device-full {
    width: 100vw;
    height: 100vh;
    border: none;
    border-radius: 0;
    box-shadow: none;
  }
  .virtual-controller {
    width: 240px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }
  .d-pad-section {
    display: flex;
    justify-content: center;
    width: 100%;
  }
  .d-pad {
    display: grid;
    grid-template-areas:
      ". up ."
      "left enter right"
      ". down .";
    gap: 6px;
  }
  .btn {
    background: #111122;
    border: 2px solid #00ffff;
    color: #00ffff;
    font-weight: bold;
    border-radius: 8px;
    cursor: pointer;
    box-shadow: 0 3px 0 #008888;
    transition: transform 0.05s, box-shadow 0.05s;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    font-size: 16px;
    text-shadow: 0 0 3px #00ffff;
  }
  .btn:active {
    transform: translateY(3px);
    box-shadow: 0 0 0 #008888;
  }
  .btn.up { grid-area: up; }
  .btn.down { grid-area: down; }
  .btn.left { grid-area: left; }
  .btn.right { grid-area: right; }
  .btn.enter {
    grid-area: enter;
    border-radius: 50%;
    background: #ff00ff;
    border: 2px solid #ffffff;
    color: #03030c;
    box-shadow: 0 3px 0 #aa00aa;
    font-size: 12px;
    font-weight: 900;
    text-shadow: none;
    letter-spacing: 0.5px;
    width: 48px;
    height: 48px;
  }
  .btn.enter:active {
    box-shadow: 0 0 0 #aa00aa;
  }
  .console-decor {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
    padding: 0 10px;
  }
  .speaker-slits {
    display: flex;
    gap: 4px;
    transform: rotate(-25deg);
  }
  .slit {
    width: 4px;
    height: 18px;
    background: #030308;
    border-radius: 2px;
  }
  .buttons-badge {
    font-size: 8px;
    color: #555566;
    font-weight: bold;
    letter-spacing: 1px;
    border: 1px solid #333344;
    padding: 2px 6px;
    border-radius: 10px;
  }
  canvas {
    display: block;
    width: 100%;
    height: 100%;
  }
  .ui {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    display: flex;
    flex-direction: column;
  }
  .top-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 10px;
    background: rgba(3,3,12,0.85);
    border-bottom: 1px solid #ff00ff;
    color: #ff00ff;
    font-weight: bold;
    font-size: 11px;
    text-shadow: 0 0 3px #ff00ff;
  }
  .crystals {
    color: #00ffff;
    text-shadow: 0 0 3px #00ffff;
  }
  .escape-ready {
    color: #ffff00;
    text-shadow: 0 0 5px #ffff00;
    animation: flash 0.8s infinite alternate;
  }
  @keyframes flash {
    from { opacity: 0.5; }
    to { opacity: 1; }
  }
  .lives {
    color: #ff0055;
    text-shadow: 0 0 3px #ff0055;
    font-size: 12px;
  }
  .overlay {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    color: white;
    background: rgba(3, 3, 12, 0.94);
    padding: 14px;
    border: 2px solid #00ffff;
    box-shadow: 0 0 15px #00ffff;
    border-radius: 8px;
    width: 85%;
    max-width: 200px;
    pointer-events: auto;
  }
  .red-alert {
    border-color: #ff0055;
    box-shadow: 0 0 15px #ff0055;
  }
  .gold-alert {
    border-color: #ffff00;
    box-shadow: 0 0 15px #ffff00;
  }
  h1 {
    margin: 0 0 4px 0;
    font-size: 18px;
    color: #00ffff;
    text-shadow: 0 0 5px #00ffff;
    letter-spacing: 1px;
  }
  .red-alert h1 {
    color: #ff0055;
    text-shadow: 0 0 5px #ff0055;
  }
  .gold-alert h1 {
    color: #ffff00;
    text-shadow: 0 0 5px #ffff00;
  }
  .subtitle {
    font-size: 8px;
    color: #ff00ff;
    margin-top: -2px;
    margin-bottom: 12px;
    letter-spacing: 1.5px;
    font-weight: bold;
  }
  p {
    margin: 4px 0;
    font-size: 11px;
  }
  .controls-guide {
    margin-top: 12px;
    border-top: 1px dashed #333344;
    padding-top: 8px;
    color: #888899;
  }
  .controls-guide p {
    font-size: 9px;
    margin: 2px 0;
  }
  .menu-btn {
    background: #00ffff;
    color: #03030c;
    border: none;
    padding: 6px 12px;
    border-radius: 4px;
    font-weight: bold;
    font-size: 11px;
    cursor: pointer;
    margin-top: 10px;
    box-shadow: 0 3px 0 #008888;
    font-family: inherit;
    transition: transform 0.05s;
  }
  .menu-btn:active {
    transform: translateY(2px);
    box-shadow: 0 1px 0 #008888;
  }
  .red-alert .menu-btn {
    background: #ff0055;
    color: #fff;
    box-shadow: 0 3px 0 #8a0022;
  }
  .red-alert .menu-btn:active {
    box-shadow: 0 1px 0 #8a0022;
  }
  .gold-alert .menu-btn {
    background: #ffff00;
    color: #03030c;
    box-shadow: 0 3px 0 #8a8a00;
  }
  .gold-alert .menu-btn:active {
    box-shadow: 0 1px 0 #8a8a00;
  }
</style>
