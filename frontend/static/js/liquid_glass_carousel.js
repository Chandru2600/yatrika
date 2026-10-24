/**
 * Liquid Glass WebGL Carousel
 * Ported & adapted from React/Three.js/GSAP component for Yatrika Travel Planner.
 * Features:
 * - Fluid rim refraction shader with chromatic dispersion
 * - Shimmer, nova bloom & glowing blue ring aura
 * - Infinite horizontal plane pooling with inertia scrolling
 * - Card focus zoom with GSAP staggered card drop physics
 * - Smooth pointer drag, wheel control & keyboard navigation
 * - Dynamic card canvas generation for crisp destination typography & badges
 */

(function (global) {
  "use strict";

  const PORTRAIT_ASPECT = 3 / 4;

  const LENS = {
    sizeX: 0.565,
    sizeY: 1,
    posX: 0.5,
    posY: 0.5,
    rotation: 65,
    spin: 0,
    zoom: 0,
    dispersion: 11,
    blur: 0,
    glow: 4.2,
    whiteGlow: 0.24,
    novaSize: 12,
    blueRing: 6,
    ringRadius: 0.49,
    ringWidth: 0.014,
    shimmer: true,
    shimmerFreq: 12,
    shimmerSpeed: 3.5,
    shimmerDepth: 0.12,
    rimStart: 0.578,
    rimTangential: 0.6,
    rimInward: 0,
    rimFreq1: 2,
    rimFreq2: 1,
    blueColor: "#009dff",
    rimLine: 1.4,
    rimLinePos: 0.488,
    rimLineWidth: 0.003,
    vignette: 0,
    vignetteSize: 0.3,
    samples: 16,
  };

  const FOCUS = {
    cardDuration: 0.7,
    focusDuration: 0.9,
    cardEase: "power4.out",
    focusEase: "power3.out",
    stagger: 0.06,
    dropDist: 1.4,
    centerScale: 1.18,
    lensFade: 0.85,
  };

  const ENTRY = {
    delay: 0.3,
    startH: 80,
    riseDuration: 1.0,
    stagger: 0.07,
    riseEase: "power3.out",
    fromBelow: 0.9,
    growDelay: 0.2,
    growDuration: 1.8,
    growEase: "expo.inOut",
    growStagger: 0.08,
    lensBloom: 1.4,
    lensBloomEase: "power2.inOut",
  };

  const LENS_VERTEX = `
    varying vec2 vUv;
    void main(){
      vUv = uv;
      gl_Position = vec4(position.xy, 0.0, 1.0);
    }
  `;

  const LENS_FRAGMENT = `
    #define PI 3.14159265359
    precision highp float;
    varying vec2 vUv;
    uniform sampler2D uTex;
    uniform vec2 uRes;
    uniform vec2 uCenter;
    uniform float uSizeX;
    uniform float uSizeY;
    uniform float uAspect;
    uniform float uZoom;
    uniform float uDispersion;
    uniform float uBlur;
    uniform float uGlow;
    uniform float uWhiteGlow;
    uniform float uNovaSize;
    uniform float uBlueRing;
    uniform float uRingRadius;
    uniform float uRingWidth;
    uniform float uShimmer;
    uniform float uShimmerFreq;
    uniform float uShimmerSpeed;
    uniform float uShimmerDepth;
    uniform float uTime;
    uniform float uRimStart;
    uniform float uRimTangential;
    uniform float uRimInward;
    uniform float uRimFreq1;
    uniform float uRimFreq2;
    uniform vec3 uBlueColor;
    uniform float uRimLine;
    uniform float uRimLinePos;
    uniform float uRimLineWidth;
    uniform float uVignette;
    uniform float uVignetteSize;
    uniform float uShape;
    uniform float uSquareRound;
    uniform float uRotation;
    uniform int uSamples;

    const int MAX_SAMPLES = 16;

    float sdRoundBox(vec2 p, vec2 b, float r){
      vec2 q = abs(p) - b + r;
      return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
    }

    vec3 discLens(vec2 center, float aspectCorrect, out float outA) {
      vec2 p = (vUv - center);
      p.x *= aspectCorrect;
      float ca = cos(uRotation), sa = sin(uRotation);
      p = mat2(ca, -sa, sa, ca) * p;
      vec2 halfSize = vec2(uSizeX, uSizeY);
      float dist = length(p / halfSize);
      outA = 0.0;

      float maskND;
      if (uShape > 0.5) {
        float corner = min(uSizeX, uSizeY) * clamp(uSquareRound, 0.0, 1.0);
        float sd = sdRoundBox(p, halfSize, corner);
        maskND = 1.0 + sd / min(uSizeX, uSizeY);
      } else {
        maskND = dist;
      }
      if (maskND > 1.0) return vec3(0.0);

      float shapeND = clamp(maskND, 0.0, 1.0);
      float nd = clamp(dist, 0.0, 1.0);
      vec2 offset = vUv - center;
      vec2 radialDir = normalize(offset + 1e-6);
      vec2 tangentDir = vec2(-radialDir.y, radialDir.x);
      float angle = atan(p.y, p.x);

      float pull = uZoom * 0.30 * (nd * nd);
      float rimStrength = smoothstep(uRimStart, 1.0, nd);
      float fluidWave = sin(angle * uRimFreq1) * 0.55 + sin(angle * uRimFreq2) * 0.25;
      float rScreen = (uSizeX + uSizeY) * 0.5;
      vec2 rimOff = tangentDir * fluidWave * rimStrength * rScreen * uRimTangential;
      vec2 rimPull = -radialDir * rimStrength * rScreen * uRimInward;

      vec2 baseUV = center + offset * (1.0 - pull) + rimOff + rimPull;

      float rimMask = smoothstep(0.55, 1.0, nd);
      vec2 dispDir = offset * uDispersion * 0.004 * rimMask;
      int N = uSamples;
      if (N < 2) N = 2;
      if (N > MAX_SAMPLES) N = MAX_SAMPLES;
      vec3 col = vec3(0.0);
      vec3 caW = vec3(0.0);
      for (int i = 0; i < MAX_SAMPLES; i++) {
        if (i >= N) break;
        float t = float(i) / float(N - 1);
        vec2 sUV = baseUV + dispDir * (t - 0.5);
        vec3 s = texture2D(uTex, sUV).rgb;
        
        float dt0 = (t - 0.0) / 0.38;
        float dt1 = (t - 0.5) / 0.38;
        float dt2 = (t - 1.0) / 0.38;
        vec3 w = vec3(
          exp(-dt0 * dt0),
          exp(-dt1 * dt1),
          exp(-dt2 * dt2)
        );
        col += s * w;
        caW += w;
      }
      col /= max(caW, vec3(0.001));

      float blurFade = 1.0 - smoothstep(0.72, 0.98, nd);
      if (uBlur > 0.01 && blurFade > 0.01) {
        vec2 blurRad = vec2(uBlur) / uRes * blurFade;
        vec3 bcol = vec3(0.0);
        float btw = 0.0;
        for (float a = 0.0; a < PI * 2.0; a += PI * 2.0 / 6.0) {
          for (float rr = 0.4; rr <= 1.001; rr += 0.3) {
            vec2 o = vec2(cos(a), sin(a)) * blurRad * rr;
            float w = 1.0 - rr * 0.38;
            bcol += texture2D(uTex, baseUV + o).rgb * w;
            btw += w;
          }
        }
        col = mix(bcol / btw, col, rimMask);
      }

      col *= mix(0.91, 1.0, smoothstep(0.0, 0.38, shapeND));

      float r2 = shapeND * shapeND * 0.25;
      float gs = max(uNovaSize * uGlow * 0.003, 0.004);
      float nova = exp(-r2 / gs) + exp(-r2 / (gs * 7.0)) * 0.18;
      nova *= uWhiteGlow * (uGlow / 17.0) * 1.15;
      col += vec3(nova);

      float dC = shapeND * 0.5;
      float tR = clamp(uRingRadius, 0.1, 0.49);
      float rW = max(uRingWidth, 0.003);
      float ringDiff = (dC - tR) / rW;
      float ring = exp(-ringDiff * ringDiff);
      ring *= uBlueRing * (uGlow / 17.0) * 1.8;
      if (uShimmer > 0.5) {
        ring *= sin(angle * uShimmerFreq + uTime * uShimmerSpeed) * uShimmerDepth + (1.0 - uShimmerDepth);
      }
      float auraDiff = (dC - tR) / (rW * 6.0);
      float ringAura = exp(-auraDiff * auraDiff) * 0.28 * uBlueRing * (uGlow / 17.0);
      col += uBlueColor * (ring + ringAura);

      float lineDiff = (dC - uRimLinePos) / max(uRimLineWidth, 0.0001);
      col += vec3(exp(-lineDiff * lineDiff) * uRimLine);

      outA = smoothstep(1.0, 0.93, maskND);
      return col;
    }

    void main(){
      vec3 base = texture2D(uTex, vUv).rgb;
      vec3 outc = base;
      float a = 0.0;
      vec3 c = discLens(uCenter, uAspect, a);
      outc = mix(outc, c, a);
      if (uVignette > 0.001) {
        vec2 vc = vUv - 0.5;
        vc.x *= uAspect;
        float d = length(vc) / max(uVignetteSize, 0.0001);
        float vig = 1.0 - uVignette * smoothstep(0.5, 1.0, d);
        outc *= clamp(vig, 0.0, 1.0);
      }
      gl_FragColor = vec4(outc, 1.0);
    }
  `;

  const LENS_FX_KEYS = [
    "uDispersion",
    "uBlueRing",
    "uRimLine",
    "uVignette",
    "uZoom",
    "uRimTangential",
    "uRimInward",
  ];

  let REPEATS = 4;
  const CLICK_SLOP = 8;
  const TOUCH_CLICK_SLOP = 14;
  const FLICK_IDLE_MS = 90;

  function prefersReducedMotion() {
    return (
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  function hexToNumber(background) {
    if (!background) return 0xeef4f7;
    const value = background.trim();
    if (value.startsWith("#") && (value.length === 7 || value.length === 4)) {
      const hex =
        value.length === 4
          ? `#${value[1]}${value[1]}${value[2]}${value[2]}${value[3]}${value[3]}`
          : value;
      const parsed = Number.parseInt(hex.slice(1), 16);
      return Number.isFinite(parsed) ? parsed : 0xeef4f7;
    }
    return 0xeef4f7;
  }

  function pad(value) {
    return String(value).padStart(2, "0");
  }

  /**
   * Helper: create a high-DPI HTML5 canvas texture representing the destination card
   * with image, gradient, rating pill, title, subtitle, and footer price bar.
   */
  function createCardCanvas(img, item) {
    const canvas = document.createElement("canvas");
    const cw = 600;
    const ch = 800;
    canvas.width = cw;
    canvas.height = ch;
    const ctx = canvas.getContext("2d");

    // Rounded card mask
    const r = 36;
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(r, 0);
    ctx.lineTo(cw - r, 0);
    ctx.quadraticCurveTo(cw, 0, cw, r);
    ctx.lineTo(cw, ch - r);
    ctx.quadraticCurveTo(cw, ch, cw - r, ch);
    ctx.lineTo(r, ch);
    ctx.quadraticCurveTo(0, ch, 0, ch - r);
    ctx.lineTo(0, r);
    ctx.quadraticCurveTo(0, 0, r, 0);
    ctx.closePath();
    ctx.clip();

    // Fill background
    ctx.fillStyle = "#0B1F33";
    ctx.fillRect(0, 0, cw, ch);

    // Draw Image
    if (img && img.width > 0) {
      const imgAspect = img.width / img.height;
      const targetAspect = cw / ch;
      let sx = 0,
        sy = 0,
        sw = img.width,
        sh = img.height;
      if (imgAspect > targetAspect) {
        sw = img.height * targetAspect;
        sx = (img.width - sw) / 2;
      } else {
        sh = img.width / targetAspect;
        sy = (img.height - sh) / 2;
      }
      ctx.drawImage(img, sx, sy, sw, sh, 0, 0, cw, ch);
    } else {
      // Fallback gradient if image is loading or offline (warm teal-to-navy with ambient glow)
      const g = ctx.createLinearGradient(0, 0, cw, ch);
      g.addColorStop(0, "#0E4D54");
      g.addColorStop(0.5, "#0D3349");
      g.addColorStop(1, "#081A2D");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, cw, ch);

      // Ambient radial soft light in center
      const rad = ctx.createRadialGradient(cw / 2, ch * 0.42, 20, cw / 2, ch * 0.42, cw * 0.55);
      rad.addColorStop(0, "rgba(0, 168, 150, 0.42)");
      rad.addColorStop(1, "rgba(0, 168, 150, 0.0)");
      ctx.fillStyle = rad;
      ctx.fillRect(0, 0, cw, ch);
    }

    // Vignette / dark overlay on lower section for high text contrast
    const grad = ctx.createLinearGradient(0, ch * 0.35, 0, ch - 110);
    grad.addColorStop(0, "rgba(11, 31, 51, 0.0)");
    grad.addColorStop(0.4, "rgba(11, 31, 51, 0.35)");
    grad.addColorStop(1, "rgba(11, 31, 51, 0.88)");
    ctx.fillStyle = grad;
    ctx.fillRect(0, ch * 0.35, cw, ch - 110 - ch * 0.35);

    // Top-right Rating Badge
    const ratingText = item.rating || "⭐ 4.8";
    ctx.save();
    ctx.font = "bold 24px 'Plus Jakarta Sans', sans-serif";
    const badgeW = ctx.measureText(ratingText).width + 30;
    const badgeH = 46;
    const bx = cw - badgeW - 24;
    const by = 24;
    ctx.fillStyle = "rgba(11, 31, 51, 0.65)";
    ctx.strokeStyle = "rgba(255, 255, 255, 0.28)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    if (ctx.roundRect) {
      ctx.roundRect(bx, by, badgeW, badgeH, 23);
    } else {
      ctx.rect(bx, by, badgeW, badgeH);
    }
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = "#ffffff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(ratingText, bx + badgeW / 2, by + badgeH / 2 + 1);
    ctx.restore();

    // Bottom destination info
    ctx.save();
    ctx.fillStyle = "#ffffff";
    ctx.font = "800 48px 'Plus Jakarta Sans', sans-serif";
    ctx.shadowColor = "rgba(0, 0, 0, 0.55)";
    ctx.shadowBlur = 12;
    ctx.fillText(item.title, 32, ch - 180);

    ctx.fillStyle = "rgba(255, 255, 255, 0.9)";
    ctx.font = "500 22px 'Plus Jakarta Sans', sans-serif";
    ctx.shadowBlur = 6;
    ctx.fillText(item.subtitle || "Authentic Indian Destination", 32, ch - 140);
    ctx.restore();

    // Bottom white footer bar (110px)
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, ch - 110, cw, 110);
    ctx.strokeStyle = "rgba(226, 232, 240, 0.85)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, ch - 110);
    ctx.lineTo(cw, ch - 110);
    ctx.stroke();

    // Price on Left
    ctx.save();
    ctx.fillStyle = "#64748b";
    ctx.font = "500 22px 'Plus Jakarta Sans', sans-serif";
    ctx.textBaseline = "middle";
    ctx.fillText(item.price || "From ₹8,500 / person", 32, ch - 55);

    // "Plan Trip →" on Right
    ctx.fillStyle = "#00A896";
    ctx.font = "700 24px 'Plus Jakarta Sans', sans-serif";
    ctx.textAlign = "right";
    ctx.fillText("Plan Trip →", cw - 32, ch - 55);
    ctx.restore();

    ctx.restore();
    return canvas;
  }

  /**
   * Main Engine Initializer
   */
  function createLiquidGlassCarousel(container, options) {
    if (!container) return null;
    const reduced = prefersReducedMotion();
    const items = options.items || [];
    if (items.length === 0) return null;

    const mount = container.querySelector(".lgc-mount") || container;
    const cursorElement = container.querySelector(".lgc-cursor");
    const activeTitleEl = container.querySelector("#lgcActiveTitle");
    const activeSubtitleEl = container.querySelector("#lgcActiveSubtitle");
    const activePlanBtn = container.querySelector("#lgcActivePlanBtn");
    const counterEl = container.querySelector("#lgcCounter");
    const closeBtn = container.querySelector("#lgcCloseFocusBtn");
    const prevBtn = container.querySelector("#lgcPrevBtn");
    const nextBtn = container.querySelector("#lgcNextBtn");

    const entryOn = options.entry !== false && !reduced;
    let W = Math.max(1, mount.clientWidth);
    let H = Math.max(1, mount.clientHeight);

    const targetHeight = options.panelHeight || 440;
    const panelHFor = () =>
      Math.max(140, Math.min(targetHeight, Math.round(H * 0.72)));
    let PANEL_H = panelHFor();
    const GAP = options.gap || 18;
    REPEATS = items.length >= 40 ? 2 : (items.length >= 20 ? 3 : 4);
    const EASE = reduced ? 0.28 : (options.ease || 0.055);
    const SNAP_EASE = reduced ? 0.22 : (options.snapEase || 0.032);
    const WHEEL = options.wheelSpeed !== undefined ? options.wheelSpeed : 0.38;
    const DRAG = options.dragSpeed !== undefined ? options.dragSpeed : 0.75;
    const TOUCH_DRAG = options.touchDragSpeed !== undefined ? options.touchDragSpeed : 0.60;
    const TOUCH_EASE = options.touchEase || 0.16;
    const FRICTION = options.friction || 0.91;
    const SNAP_IDLE_MS = options.snapIdleMs || 280;
    const SHRINK_MAX = 60;
    const SHRINK_ATTACK = 0.25;
    const SHRINK_DECAY = 0.06;

    // Ambient slow continuous auto-scroll
    const autoScrollEnabled = options.autoScroll !== false && !reduced;
    const AUTO_SCROLL_SPEED = options.autoScrollSpeed !== undefined ? options.autoScrollSpeed : 0.38;
    const AUTO_SCROLL_RESUME_MS = options.autoScrollResumeMs || 1400;

    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    } catch (e) {
      console.warn("WebGL not supported for LiquidGlassCarousel:", e);
      return null;
    }

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    renderer.setPixelRatio(dpr);
    renderer.setSize(W, H);
    renderer.setClearColor(hexToNumber(options.background || "#EEF4F7"), 1);
    if (renderer.capabilities && renderer.capabilities.isWebGL2) {
      renderer.outputEncoding = THREE.sRGBEncoding || 3001;
    }
    renderer.domElement.style.display = "block";
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.touchAction = "pan-y";
    renderer.domElement.style.userSelect = "none";
    renderer.domElement.setAttribute("aria-hidden", "true");
    mount.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(
      -W / 2,
      W / 2,
      H / 2,
      -H / 2,
      -100,
      100
    );
    camera.position.z = 10;

    // Load Sources and build dynamic textures
    const sources = items.map((item) => {
      const s = {
        tex: null,
        aspect: item.aspect || PORTRAIT_ASPECT,
        locked: true,
        item: item,
      };

      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => {
        const canvas = createCardCanvas(img, item);
        const tex = new THREE.CanvasTexture(canvas);
        tex.minFilter = THREE.LinearMipmapLinearFilter;
        tex.magFilter = THREE.LinearFilter;
        tex.generateMipmaps = true;
        if (renderer.capabilities.getMaxAnisotropy) {
          tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
        }
        if (THREE.SRGBColorSpace) {
          tex.colorSpace = THREE.SRGBColorSpace;
        } else if (THREE.sRGBEncoding) {
          tex.encoding = THREE.sRGBEncoding;
        }
        s.tex = tex;
        recomputeTotal();
        if (!userInteracted) {
          scroll = centerForIndex(0);
          target = scroll;
        }
      };
      img.onerror = () => {
        const canvas = createCardCanvas(null, item);
        const tex = new THREE.CanvasTexture(canvas);
        s.tex = tex;
        recomputeTotal();
      };
      img.src = item.src;
      return s;
    });

    function slotWidth(srcIndex) {
      const s = sources[srcIndex];
      return (s ? s.aspect : PORTRAIT_ASPECT) * PANEL_H + GAP;
    }

    let offsets = [];
    let totalWidth = 0;
    function recomputeTotal() {
      offsets = [];
      let acc = 0;
      for (let i = 0; i < sources.length; i++) {
        offsets.push(acc);
        acc += slotWidth(i);
      }
      totalWidth = acc;
    }
    recomputeTotal();

    function centerForIndex(idx) {
      const N = sources.length;
      if (N === 0) return 0;
      const loop = Math.floor(idx / N);
      const s = ((idx % N) + N) % N;
      return (offsets[s] || 0) + slotWidth(s) / 2 - GAP / 2 + loop * totalWidth;
    }

    function nearestIndex(value) {
      if (!totalWidth) return 0;
      const N = sources.length;
      let best = 0;
      let bestDist = Infinity;
      for (let i = 0; i < N; i++) {
        const center = (offsets[i] || 0) + slotWidth(i) / 2 - GAP / 2;
        const k = Math.round((value - center) / totalWidth);
        const dist = Math.abs(center + k * totalWidth - value);
        if (dist < bestDist) {
          bestDist = dist;
          best = i + k * N;
        }
      }
      return best;
    }

    function centerIndex(value) {
      if (!totalWidth) return 0;
      let bestI = 0;
      let bestDist = Infinity;
      for (let i = 0; i < sources.length; i++) {
        const center = (offsets[i] || 0) + slotWidth(i) / 2 - GAP / 2;
        const k = Math.round((value - center) / totalWidth);
        const dist = Math.abs(center + k * totalWidth - value);
        if (dist < bestDist) {
          bestDist = dist;
          bestI = i;
        }
      }
      return bestI;
    }

    let lastCenter = -1;
    const pool = [];
    for (let r = 0; r < REPEATS; r++) {
      for (let i = 0; i < sources.length; i++) {
        const mat = new THREE.MeshBasicMaterial({
          color: 0xffffff,
          transparent: true,
        });
        const mesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1, 1, 1), mat);
        mesh.visible = false;
        scene.add(mesh);
        pool.push({ mesh, mat, srcIndex: i, bound: false });
      }
    }

    let scroll = centerForIndex(0);
    let target = scroll;
    let userInteracted = false;
    let velocity = 0;
    let prevScroll = 0;
    let scrollEnergy = 0;
    let pendingFocus = null;
    let lastInput = performance.now();
    let snapped = false;

    // Render target and shader setup
    const rt = new THREE.WebGLRenderTarget(W * dpr, H * dpr);
    const lensScene = new THREE.Scene();
    const lensCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const lensUniforms = {
      uTex: { value: rt.texture },
      uRes: { value: new THREE.Vector2(W * dpr, H * dpr) },
      uCenter: { value: new THREE.Vector2(0.5, 0.5) },
      uSizeX: { value: LENS.sizeX },
      uSizeY: { value: LENS.sizeY },
      uShape: { value: 0 },
      uSquareRound: { value: 0 },
      uRotation: { value: 0 },
      uAspect: { value: W / H },
      uZoom: { value: LENS.zoom },
      uDispersion: { value: LENS.dispersion },
      uBlur: { value: LENS.blur },
      uGlow: { value: LENS.glow },
      uWhiteGlow: { value: LENS.whiteGlow },
      uNovaSize: { value: LENS.novaSize },
      uBlueRing: { value: LENS.blueRing },
      uRingRadius: { value: LENS.ringRadius },
      uRingWidth: { value: LENS.ringWidth },
      uShimmer: { value: reduced || !LENS.shimmer ? 0 : 1 },
      uShimmerFreq: { value: LENS.shimmerFreq },
      uShimmerSpeed: { value: LENS.shimmerSpeed },
      uShimmerDepth: { value: LENS.shimmerDepth },
      uTime: { value: 0 },
      uRimStart: { value: LENS.rimStart },
      uRimTangential: { value: LENS.rimTangential },
      uRimInward: { value: LENS.rimInward },
      uRimFreq1: { value: LENS.rimFreq1 },
      uRimFreq2: { value: LENS.rimFreq2 },
      uBlueColor: { value: new THREE.Color(LENS.blueColor) },
      uRimLine: { value: LENS.rimLine },
      uRimLinePos: { value: LENS.rimLinePos },
      uRimLineWidth: { value: LENS.rimLineWidth },
      uVignette: { value: LENS.vignette },
      uVignetteSize: { value: LENS.vignetteSize },
      uSamples: { value: LENS.samples },
    };

    const lensMat = new THREE.ShaderMaterial({
      uniforms: lensUniforms,
      vertexShader: LENS_VERTEX,
      fragmentShader: LENS_FRAGMENT,
      depthTest: false,
      depthWrite: false,
    });
    const lensQuad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), lensMat);
    lensScene.add(lensQuad);

    const focusState = {
      active: false,
      srcIndex: -1,
      poolIdx: -1,
      lensFx: entryOn ? 0 : 1,
      anim: null,
    };
    const drop = new Array(REPEATS * sources.length).fill(0);
    let focusScale = 1;
    const lastCenterX = new Array(REPEATS * sources.length);
    const pEntry = new Array(REPEATS * sources.length).fill(entryOn ? 0 : 1);
    let entryActive = entryOn;
    let entrySettled = false;
    const growArr = new Array(REPEATS * sources.length).fill(entryOn ? 0 : 1);
    let entryAnim = null;

    const lensFxFull = {};
    LENS_FX_KEYS.forEach((key) => {
      lensFxFull[key] = lensUniforms[key].value;
    });

    let panelRects = [];
    let centeredPanel = null;

    function layout() {
      panelRects = [];
      centeredPanel = null;
      let centeredDist = Infinity;
      const half = W / 2;
      const buffer = PANEL_H;

      pool.forEach((p, poolIdx) => {
        const rep = Math.floor(poolIdx / sources.length);
        const i = p.srcIndex;
        const src = sources[i];
        if (!src) return;

        const slotCenterInLoop =
          (offsets[i] || 0) + slotWidth(i) / 2 - GAP / 2;
        let x = slotCenterInLoop - scroll;
        x = ((x % totalWidth) + totalWidth) % totalWidth;
        x += (rep - Math.floor(REPEATS / 2)) * totalWidth;
        if (x > half + totalWidth) x -= totalWidth * REPEATS;

        const centerX = x;
        const inEntry = entryActive || entrySettled;
        if (!inEntry && (centerX < -half - buffer || centerX > half + buffer)) {
          p.mesh.visible = false;
          lastCenterX[poolIdx] = undefined;
          return;
        }
        lastCenterX[poolIdx] = centerX;

        const shrink = 1 - 0.25 * scrollEnergy;
        const h = PANEL_H * shrink;
        const wPx = src.aspect * PANEL_H * shrink;

        if (src.tex && !p.bound) {
          p.mat.map = src.tex;
          p.mat.color.set(0xffffff);
          p.mat.needsUpdate = true;
          p.bound = true;
        }

        let y = 0;
        const isFocused = focusState.active && focusState.poolIdx === poolIdx;
        const d = drop[poolIdx] || 0;
        let drawW = wPx;
        let drawH = h;
        if (isFocused) {
          drawW = wPx * focusScale;
          drawH = h * focusScale;
        } else if (d > 0) {
          y = -d * H * FOCUS.dropDist;
        }

        p.mesh.visible = true;
        let finalX = centerX;
        let finalY = y;
        let finalW = drawW;
        let finalH = drawH;

        if (entryActive || entrySettled) {
          const pe = pEntry[poolIdx] || 0;
          const g = growArr[poolIdx] || 0;
          const curH = ENTRY.startH + (drawH - ENTRY.startH) * g;
          finalH = curH;
          finalW = curH * src.aspect;

          const cSrc = centerIndex(scroll);
          let di = i - cSrc;
          if (di > sources.length / 2) di -= sources.length;
          if (di < -sources.length / 2) di += sources.length;
          const N = sources.length;
          const midRep = Math.floor(REPEATS / 2);
          if (rep !== midRep) {
            p.mesh.visible = false;
            lastCenterX[poolIdx] = undefined;
            return;
          }
          const slotH = (s) => {
            const gg = growArr[midRep * N + s] || 0;
            return ENTRY.startH + (PANEL_H - ENTRY.startH) * gg;
          };
          let off = 0;
          if (di > 0) {
            for (let k = 0; k < di; k++) {
              const sa = (((cSrc + k) % N) + N) % N;
              const sb = (((cSrc + k + 1) % N) + N) % N;
              off +=
                ((sources[sa].aspect * slotH(sa) +
                  sources[sb].aspect * slotH(sb)) /
                  2 +
                  GAP);
            }
          } else if (di < 0) {
            for (let k = 0; k < -di; k++) {
              const sa = (((cSrc - k) % N) + N) % N;
              const sb = (((cSrc - k - 1) % N) + N) % N;
              off -=
                ((sources[sa].aspect * slotH(sa) +
                  sources[sb].aspect * slotH(sb)) /
                  2 +
                  GAP);
            }
          }
          finalX = off;
          if (finalX < -half - buffer || finalX > half + buffer) {
            p.mesh.visible = false;
            lastCenterX[poolIdx] = undefined;
            return;
          }
          const below = -H * ENTRY.fromBelow;
          finalY = below + (y - below) * pe;
        }

        p.mesh.position.set(finalX, finalY, 0);
        p.mesh.scale.set(finalW, finalH, 1);

        const sx = centerX + W / 2;
        const sy = H / 2 - y;
        panelRects.push({
          left: sx - drawW / 2,
          right: sx + drawW / 2,
          top: sy - drawH / 2,
          bottom: sy + drawH / 2,
          poolIdx,
          srcIndex: i,
          centerX,
        });

        if (Math.abs(centerX) < centeredDist) {
          centeredDist = Math.abs(centerX);
          centeredPanel = { srcIndex: i, centerX, wPx, h, poolIdx };
        }
      });
    }

    function panelAtPointer(px, py) {
      for (let i = 0; i < panelRects.length; i++) {
        const r = panelRects[i];
        if (px >= r.left && px <= r.right && py >= r.top && py <= r.bottom) {
          return r;
        }
      }
      return null;
    }

    function localPoint(e) {
      const rect = renderer.domElement.getBoundingClientRect();
      return { x: e.clientX - rect.left, y: e.clientY - rect.top };
    }

    const el = renderer.domElement;
    let dragging = false;
    let dragPointerId = null;
    let dragLastX = 0;
    let dragDist = 0;
    let dragVel = 0;
    let dragMoveT = 0;
    let suppressClick = false;
    let dragPointerType = "mouse";
    let lastPointerX = Number.NaN;
    let lastPointerY = Number.NaN;
    let pointerInside = false;
    let lastPointerType = "mouse";

    if (cursorElement && window.gsap) {
      window.gsap.set(cursorElement, {
        xPercent: 20,
        yPercent: 30,
        scale: 0,
        autoAlpha: 0,
      });
    }
    const moveX =
      cursorElement && window.gsap
        ? window.gsap.quickTo(cursorElement, "x", {
            duration: 0.4,
            ease: "power3.out",
          })
        : null;
    const moveY =
      cursorElement && window.gsap
        ? window.gsap.quickTo(cursorElement, "y", {
            duration: 0.4,
            ease: "power3.out",
          })
        : null;

    let overPanel = false;
    let hoverPanel = false;
    let cursorNow = "";
    function setCursor(v) {
      if (v === cursorNow) return;
      cursorNow = v;
      el.style.cursor = v;
    }

    function updateCursor() {
      if (focusState.active || entryActive || entrySettled)
        return setCursor("");
      if (dragging) return setCursor("grabbing");
      if (!hoverPanel) return setCursor("");
      return setCursor("grab");
    }

    function setHover(on) {
      hoverPanel = on;
      setView(on);
    }

    function refreshHover() {
      if (!pointerInside || lastPointerType !== "mouse") return;
      if (!Number.isFinite(lastPointerX)) return;
      if (focusState.active) {
        setHover(false);
        return;
      }
      setHover(panelAtPointer(lastPointerX, lastPointerY) !== null);
    }

    function setView(on) {
      if (entryActive || entrySettled) on = false;
      if (dragging) on = false;
      if (on === overPanel) {
        updateCursor();
        return;
      }
      overPanel = on;
      updateCursor();
      if (!cursorElement || !window.gsap) return;
      window.gsap.killTweensOf(cursorElement, "scale,autoAlpha,opacity,visibility");
      window.gsap.to(cursorElement, {
        scale: on ? 1 : 0,
        autoAlpha: on ? 1 : 0,
        duration: on ? 0.35 : 0.25,
        ease: on ? "power3.out" : "power3.in",
      });
    }

    function inputLocked() {
      return focusState.active || entryActive || entrySettled;
    }

    let touchStartX = 0;
    let touchStartY = 0;
    let touchDirectionDecided = false;
    let isHorizontalSwipe = false;

    function onWheel(e) {
      const absX = Math.abs(e.deltaX);
      const absY = Math.abs(e.deltaY);
      // If user is scrolling vertically up/down and not holding Shift, let the page scroll naturally!
      if (absY >= absX && !e.shiftKey) {
        return;
      }
      e.preventDefault();
      if (inputLocked()) return;
      userInteracted = true;
      pendingFocus = null;
      target += (e.deltaX || (e.shiftKey ? e.deltaY : 0)) * WHEEL;
      lastInput = performance.now();
      snapped = false;
    }

    function onPointerDown(e) {
      suppressClick = false;
      if (inputLocked()) return;
      if (dragging) return;
      if (e.button !== 0 && e.pointerType === "mouse") return;
      
      dragPointerType = e.pointerType || "mouse";
      dragPointerId = e.pointerId;
      const p = localPoint(e);
      touchStartX = p.x;
      touchStartY = p.y;
      dragLastX = p.x;
      lastPointerX = p.x;
      lastPointerY = p.y;

      if (dragPointerType === "mouse") {
        dragging = true;
        touchDirectionDecided = true;
        isHorizontalSwipe = true;
        try { el.setPointerCapture(e.pointerId); } catch (_) {}
      } else {
        // Touch device: start in tentative state to detect vertical vs horizontal gesture
        dragging = true;
        touchDirectionDecided = false;
        isHorizontalSwipe = false;
      }

      dragDist = 0;
      dragVel = 0;
      dragMoveT = performance.now();
      setView(false);
      velocity = 0;
      pendingFocus = null;
      userInteracted = true;
      snapped = false;
      lastInput = dragMoveT;
    }

    function onPointerMove(e) {
      const p = localPoint(e);
      if (dragging && e.pointerId === dragPointerId) {
        if (!touchDirectionDecided && dragPointerType !== "mouse") {
          const dx = Math.abs(p.x - touchStartX);
          const dy = Math.abs(p.y - touchStartY);
          if (dx > 7 || dy > 7) {
            touchDirectionDecided = true;
            if (dy >= dx) {
              // User is scrolling vertically up or down — release drag so browser scrolls the page!
              dragging = false;
              isHorizontalSwipe = false;
              return;
            } else {
              // User is swiping horizontally — lock horizontal carousel drag
              isHorizontalSwipe = true;
              try { el.setPointerCapture(e.pointerId); } catch (_) {}
            }
          }
        }

        if (isHorizontalSwipe || dragPointerType === "mouse") {
          const sens = dragPointerType === "mouse" ? DRAG : TOUCH_DRAG;
          const dx = p.x - dragLastX;
          dragLastX = p.x;
          dragDist += Math.abs(dx);
          target -= dx * sens;
          dragVel = dragVel * 0.6 + -dx * sens * 0.4;
          dragMoveT = performance.now();
          lastInput = dragMoveT;
          snapped = false;
        }
      }
      lastPointerX = p.x;
      lastPointerY = p.y;
      lastPointerType = e.pointerType || "mouse";
      pointerInside = true;
      if (e.pointerType !== "mouse") return;
      if (moveX) moveX(p.x);
      if (moveY) moveY(p.y);
      if (focusState.active) {
        setHover(false);
        return;
      }
      setHover(panelAtPointer(p.x, p.y) !== null);
    }

    function onPointerUp(e) {
      touchDirectionDecided = false;
      isHorizontalSwipe = false;
      if (!dragging) return;
      if (e && dragPointerId !== null && e.pointerId !== dragPointerId) return;
      dragging = false;
      if (dragPointerId !== null) {
        try {
          el.releasePointerCapture(dragPointerId);
        } catch (err) {
          /* already released */
        }
        dragPointerId = null;
      }
      velocity =
        performance.now() - dragMoveT > FLICK_IDLE_MS ? 0 : dragVel;
      dragVel = 0;
      lastInput = performance.now();
      snapped = false;
      suppressClick =
        dragDist >
        (dragPointerType === "mouse" ? CLICK_SLOP : TOUCH_CLICK_SLOP);
      if (dragPointerType === "mouse") {
        setHover(panelAtPointer(lastPointerX, lastPointerY) !== null);
      } else {
        updateCursor();
      }
    }

    function onEnter(e) {
      pointerInside = true;
      lastPointerType = e.pointerType || "mouse";
    }
    function onLeave() {
      pointerInside = false;
      lastInput = performance.now();
      setHover(false);
    }

    function onClick(e) {
      if (suppressClick) {
        suppressClick = false;
        return;
      }
      if (inputLocked()) return;
      const p = localPoint(e);
      const hit = panelAtPointer(p.x, p.y);
      if (!hit) return;
      if (centeredPanel && hit.poolIdx === centeredPanel.poolIdx) {
        pendingFocus = null;
        if (focusState.active) {
          const item = items[centeredPanel.srcIndex];
          if (options.onCardAction) {
            options.onCardAction(item);
          } else if (typeof window.quickGo === 'function' && item) {
            window.quickGo(item.title);
          } else if (typeof window.openPlanModal === 'function' && item) {
            window.openPlanModal(item.title);
          }
          return;
        }
        openFocus();
        return;
      }
      userInteracted = true;
      velocity = 0;
      target = centerForIndex(nearestIndex(scroll + hit.centerX));
      snapped = true;
      pendingFocus = { srcIndex: hit.srcIndex };
      setView(false);
    }

    function openFocus() {
      if (focusState.active || !centeredPanel) return;
      const src = sources[centeredPanel.srcIndex];
      if (!src || !src.tex) return;

      focusState.active = true;
      focusState.srcIndex = centeredPanel.srcIndex;
      const focusPoolIdx = centeredPanel.poolIdx;
      focusState.poolIdx = focusPoolIdx;
      target = centerForIndex(nearestIndex(scroll));

      const focusX = lastCenterX[focusPoolIdx] || 0;
      const others = pool
        .map((_, idx) => ({ idx, x: lastCenterX[idx] }))
        .filter((o) => o.idx !== focusPoolIdx && o.x !== undefined)
        .map((o) => ({ idx: o.idx, dist: Math.abs((o.x || 0) - focusX) }))
        .sort((a, b) => a.dist - b.dist);

      let rank = 0;
      let prevDist = -1;
      const ranked = others.map((o) => {
        if (prevDist >= 0 && o.dist - prevDist > 1) rank += 1;
        prevDist = o.dist;
        return { idx: o.idx, rank };
      });

      for (const key of LENS_FX_KEYS) {
        lensFxFull[key] = lensUniforms[key].value;
      }

      if (focusState.anim) focusState.anim.kill();
      const scaleProxy = { v: focusScale };
      const tl = window.gsap ? window.gsap.timeline() : null;

      if (tl) {
        tl.to(
          focusState,
          { lensFx: 0, duration: FOCUS.lensFade, ease: "power3.out" },
          0
        );
        tl.to(
          scaleProxy,
          {
            v: FOCUS.centerScale,
            duration: FOCUS.focusDuration,
            ease: FOCUS.focusEase,
            onUpdate() {
              focusScale = scaleProxy.v;
            },
          },
          0
        );
        ranked.forEach((o) => {
          tl.to(
            drop,
            { [o.idx]: 1, duration: FOCUS.cardDuration, ease: FOCUS.cardEase },
            o.rank * FOCUS.stagger
          );
        });
        focusState.anim = tl;
      } else {
        focusScale = FOCUS.centerScale;
        focusState.lensFx = 0;
        ranked.forEach((o) => {
          drop[o.idx] = 1;
        });
      }

      setView(false);
      if (closeBtn) closeBtn.classList.add("is-visible");
      if (options.onFocusChange) options.onFocusChange(true);
    }

    function closeFocus() {
      if (!focusState.active) return;
      if (focusState.anim) focusState.anim.kill();

      const focusX = lastCenterX[focusState.poolIdx] || 0;
      const others = pool
        .map((_, idx) => ({ idx, x: lastCenterX[idx] }))
        .filter((o) => o.x !== undefined && (drop[o.idx] || 0) > 0)
        .map((o) => ({ idx: o.idx, dist: Math.abs((o.x || 0) - focusX) }))
        .sort((a, b) => b.dist - a.dist);

      let rank = 0;
      let prevDist = -1;
      const ranked = others.map((o) => {
        if (prevDist >= 0 && prevDist - o.dist > 1) rank += 1;
        prevDist = o.dist;
        return { idx: o.idx, rank };
      });

      if (closeBtn) closeBtn.classList.remove("is-visible");
      if (options.onFocusChange) options.onFocusChange(false);

      const scaleProxy = { v: focusScale };
      if (window.gsap) {
        const tl = window.gsap.timeline({
          onComplete: () => {
            focusState.active = false;
            focusState.srcIndex = -1;
            updateCursor();
          },
        });
        tl.to(
          focusState,
          { lensFx: 1, duration: FOCUS.lensFade * 0.8, ease: "power3.inOut" },
          0
        );
        tl.to(
          scaleProxy,
          {
            v: 1,
            duration: FOCUS.focusDuration * 0.85,
            ease: FOCUS.focusEase,
            onUpdate() {
              focusScale = scaleProxy.v;
            },
          },
          0
        );
        ranked.forEach((o) => {
          tl.to(
            drop,
            {
              [o.idx]: 0,
              duration: FOCUS.cardDuration * 0.85,
              ease: FOCUS.cardEase,
            },
            o.rank * FOCUS.stagger * 0.7
          );
        });
        focusState.anim = tl;
      } else {
        focusScale = 1;
        focusState.lensFx = 1;
        for (let k = 0; k < drop.length; k++) drop[k] = 0;
        focusState.active = false;
        focusState.srcIndex = -1;
      }
    }

    function playEntry() {
      if (!entryOn || !window.gsap) {
        return;
      }
      if (entryAnim) entryAnim.kill();
      for (let k = 0; k < pEntry.length; k++) pEntry[k] = 0;
      entryActive = true;
      entrySettled = false;
      for (let k = 0; k < growArr.length; k++) growArr[k] = 0;
      focusState.lensFx = 0;
      target = centerForIndex(nearestIndex(scroll));
      scroll = target;
      velocity = 0;
      snapped = true;
      layout();

      const visible = [];
      for (let k = 0; k < lastCenterX.length; k++) {
        if (lastCenterX[k] !== undefined) visible.push(k);
      }
      const tl = window.gsap.timeline({ delay: ENTRY.delay });
      const spread = ENTRY.stagger * Math.max(visible.length - 1, 1);
      let lastRiseEnd = 0;
      visible.forEach((idx) => {
        const at = Math.random() * spread;
        lastRiseEnd = Math.max(lastRiseEnd, at + ENTRY.riseDuration);
        tl.to(
          pEntry,
          { [idx]: 1, duration: ENTRY.riseDuration, ease: ENTRY.riseEase },
          at
        );
      });
      tl.call(
        () => {
          entryActive = false;
          entrySettled = true;
        },
        [],
        lastRiseEnd
      );
      const cSrcG = centerIndex(scroll);
      const Ng = sources.length;
      const midRepG = Math.floor(REPEATS / 2);
      const growList = [];
      let maxRank = 0;
      for (let k = 0; k < lastCenterX.length; k++) {
        if (lastCenterX[k] === undefined) continue;
        if (Math.floor(k / Ng) !== midRepG) continue;
        let di = (k % Ng) - cSrcG;
        if (di > Ng / 2) di -= Ng;
        if (di < -Ng / 2) di += Ng;
        const r = Math.abs(di);
        maxRank = Math.max(maxRank, r);
        growList.push({ idx: k, rank: r });
      }
      const growRanked = growList.map((v) => ({
        idx: v.idx,
        rank: maxRank - v.rank,
      }));
      const growStart = lastRiseEnd + ENTRY.growDelay;
      let growEnd = growStart;
      tl.to(
        focusState,
        { lensFx: 1, duration: ENTRY.lensBloom, ease: ENTRY.lensBloomEase },
        growStart
      );
      growRanked.forEach((o) => {
        const at = growStart + o.rank * ENTRY.growStagger;
        growEnd = Math.max(growEnd, at + ENTRY.growDuration);
        tl.to(
          growArr,
          { [o.idx]: 1, duration: ENTRY.growDuration, ease: ENTRY.growEase },
          at
        );
      });
      tl.call(
        () => {
          entrySettled = false;
          for (let k = 0; k < growArr.length; k++) growArr[k] = 1;
          updateCursor();
        },
        [],
        growEnd
      );
      entryAnim = tl;
    }

    function step(direction) {
      if (inputLocked()) return;
      userInteracted = true;
      velocity = 0;
      pendingFocus = null;
      target = centerForIndex(nearestIndex(scroll) + direction);
      snapped = true;
      lastInput = performance.now();
    }

    // Attach listeners
    el.addEventListener("wheel", onWheel, { passive: false });
    el.addEventListener("pointerdown", onPointerDown);
    el.addEventListener("pointermove", onPointerMove);
    el.addEventListener("pointerup", onPointerUp);
    el.addEventListener("pointercancel", onPointerUp);
    el.addEventListener("pointerenter", onEnter);
    el.addEventListener("pointerleave", onLeave);
    el.addEventListener("click", onClick);

    // Container listeners for whole-component hover and accessibility pause
    container.addEventListener("pointerenter", onEnter);
    container.addEventListener("pointerleave", onLeave);
    container.addEventListener("focusin", onEnter);
    container.addEventListener("focusout", onLeave);

    if (closeBtn) {
      closeBtn.addEventListener("click", () => closeFocus());
    }
    if (prevBtn) {
      prevBtn.addEventListener("click", () => step(-1));
    }
    if (nextBtn) {
      nextBtn.addEventListener("click", () => step(1));
    }

    // Keyboard navigation
    container.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") {
        e.preventDefault();
        step(1);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        step(-1);
      } else if (e.key === "Escape") {
        e.preventDefault();
        closeFocus();
      }
    });

    let raf = 0;
    let running = true;
    let visible = true;

    function tick() {
      if (!running) return;
      if (!visible || document.hidden) {
        raf = 0;
        return;
      }

      const now = performance.now();
      const isInteracting =
        dragging ||
        pointerInside ||
        focusState.active ||
        pendingFocus ||
        entryActive ||
        entrySettled;

      const canAutoScroll =
        autoScrollEnabled &&
        !isInteracting &&
        now - lastInput > AUTO_SCROLL_RESUME_MS;

      if (!dragging) {
        if (canAutoScroll) {
          // Slow ambient cruise: advance target smoothly without snap friction
          target += AUTO_SCROLL_SPEED;
          snapped = false;
        } else {
          target += velocity;
          velocity *= FRICTION;
          if (Math.abs(velocity) < 0.05) velocity = 0;
          if (
            !snapped &&
            !focusState.active &&
            now - lastInput > SNAP_IDLE_MS
          ) {
            target = centerForIndex(nearestIndex(scroll));
            snapped = true;
          }
        }
      }
      const follow =
        dragging && dragPointerType !== "mouse"
          ? TOUCH_EASE
          : snapped && !pendingFocus
          ? SNAP_EASE
          : EASE;
      scroll += (target - scroll) * follow;

      const ci = centerIndex(scroll);
      if (ci !== lastCenter) {
        lastCenter = ci;
        onActiveChange(ci);
      }

      const rawSpeed = scroll - prevScroll;
      prevScroll = scroll;
      const norm = Math.min(1, Math.abs(rawSpeed) / Math.max(1, SHRINK_MAX));
      const k = norm > scrollEnergy ? SHRINK_ATTACK : SHRINK_DECAY;
      scrollEnergy += (norm - scrollEnergy) * k;

      layout();
      refreshHover();

      if (pendingFocus && !focusState.active) {
        if (Math.abs(target - scroll) < 0.5) {
          const pf = pendingFocus;
          pendingFocus = null;
          if (centeredPanel && centeredPanel.srcIndex === pf.srcIndex) {
            openFocus();
          }
        }
      }

      lensUniforms.uCenter.value.set(LENS.posX, LENS.posY);
      lensUniforms.uAspect.value = W / H;
      lensUniforms.uTime.value = performance.now() * 0.001;
      const rad = (a) => (a * Math.PI) / 180;
      lensUniforms.uRotation.value =
        rad(LENS.rotation) + rad(LENS.spin) * (performance.now() * 0.001);
      const fx = focusState.lensFx;
      for (let i = 0; i < LENS_FX_KEYS.length; i++) {
        const key = LENS_FX_KEYS[i];
        lensUniforms[key].value = (lensFxFull[key] || 0) * fx;
      }

      renderer.setRenderTarget(rt);
      renderer.render(scene, camera);
      renderer.setRenderTarget(null);
      renderer.render(lensScene, lensCam);
      raf = requestAnimationFrame(tick);
    }

    function onActiveChange(idx) {
      const activeItem = items[idx];
      if (!activeItem) return;

      if (counterEl) {
        counterEl.textContent = `${pad(idx + 1)} / ${pad(items.length)}`;
      }

      if (activeTitleEl) {
        if (window.gsap) {
          window.gsap.fromTo(
            activeTitleEl,
            { opacity: 0.3, y: -4 },
            { opacity: 1, y: 0, duration: 0.3, ease: "power2.out" }
          );
        }
        activeTitleEl.textContent = activeItem.title;
      }

      if (activeSubtitleEl) {
        activeSubtitleEl.textContent = `${activeItem.subtitle || ""} · ${
          activeItem.price || ""
        }`;
      }

      if (activePlanBtn) {
        activePlanBtn.href =
          activeItem.planUrl ||
          `/planner/new?destination=${encodeURIComponent(
            activeItem.title
          )}&source=Bengaluru`;
        activePlanBtn.innerHTML = `<i class="bi bi-compass me-1"></i>Plan Trip to ${activeItem.title} →`;
      }

      if (options.onActiveChange) {
        options.onActiveChange(idx);
      }
    }

    function startLoop() {
      if (!running || raf) return;
      raf = requestAnimationFrame(tick);
    }

    startLoop();
    if (entryOn) playEntry();
    onActiveChange(0);

    function onResize() {
      W = Math.max(1, mount.clientWidth);
      H = Math.max(1, mount.clientHeight);
      PANEL_H = panelHFor();
      recomputeTotal();
      renderer.setSize(W, H);
      camera.left = -W / 2;
      camera.right = W / 2;
      camera.top = H / 2;
      camera.bottom = -H / 2;
      camera.updateProjectionMatrix();
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      renderer.setPixelRatio(ratio);
      rt.setSize(W * ratio, H * ratio);
      lensUniforms.uRes.value.set(W * ratio, H * ratio);
      if (!userInteracted) {
        scroll = centerForIndex(0);
        target = scroll;
      }
    }

    const resizeObserver = new ResizeObserver(onResize);
    resizeObserver.observe(mount);
    const intersection = new IntersectionObserver(([entry]) => {
      const box = entry?.boundingClientRect;
      if (!box || (box.width === 0 && box.height === 0)) return;
      visible = entry?.isIntersecting ?? true;
      if (visible) startLoop();
    });
    intersection.observe(mount);

    const onVisibility = () => {
      if (!document.hidden) startLoop();
    };
    document.addEventListener("visibilitychange", onVisibility);

    function destroy() {
      running = false;
      cancelAnimationFrame(raf);
      resizeObserver.disconnect();
      intersection.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
      el.removeEventListener("wheel", onWheel);
      el.removeEventListener("pointerdown", onPointerDown);
      el.removeEventListener("pointermove", onPointerMove);
      el.removeEventListener("pointerup", onPointerUp);
      el.removeEventListener("pointercancel", onPointerUp);
      el.removeEventListener("pointerenter", onEnter);
      el.removeEventListener("pointerleave", onLeave);
      el.removeEventListener("click", onClick);
      container.removeEventListener("pointerenter", onEnter);
      container.removeEventListener("pointerleave", onLeave);
      container.removeEventListener("focusin", onEnter);
      container.removeEventListener("focusout", onLeave);
      if (focusState.anim) focusState.anim.kill();
      if (entryAnim) entryAnim.kill();
      if (cursorElement && window.gsap) window.gsap.killTweensOf(cursorElement);
      renderer.dispose();
      rt.dispose();
      lensQuad.geometry.dispose();
      lensMat.dispose();
      pool.forEach((p) => {
        p.mesh.geometry.dispose();
        p.mat.dispose();
      });
      sources.forEach((s) => {
        s.tex?.dispose();
      });
      if (renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
    }

    return {
      closeFocus,
      next: () => step(1),
      previous: () => step(-1),
      destroy,
    };
  }

  global.createLiquidGlassCarousel = createLiquidGlassCarousel;
})(window);
