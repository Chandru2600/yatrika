/**
 * WebGL Ripple Transition Engine (Three.js & GSAP)
 * Implements concentric water shockwave distortion, pinch effect,
 * and auto-play randomized origin transitions between 50 Indian destination images.
 */

(function (global) {
  "use strict";

  const RIPPLE_VERTEX = `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = vec4(position.xy, 0.0, 1.0);
    }
  `;

  const RIPPLE_FRAGMENT = `
    precision highp float;
    varying vec2 vUv;
    uniform sampler2D uTexCurrent;
    uniform sampler2D uTexNext;
    uniform float uProgress;
    uniform vec2 uOrigin;
    uniform float uAspect;
    uniform float uPinch;

    void main() {
      vec2 uv = vUv;
      vec2 p = uv - uOrigin;
      p.x *= uAspect;
      float dist = length(p);

      // Expanding wave radius
      float maxRadius = 2.2;
      float currentRadius = uProgress * maxRadius;
      float waveWidth = 0.35;
      float waveDist = abs(dist - currentRadius);
      float waveFactor = smoothstep(waveWidth, 0.0, waveDist);

      vec2 dir = normalize(p + 1e-5);

      // Harmonic wave displacement
      float freq = 32.0;
      float ripple = sin(waveDist * freq - uProgress * 16.0) * waveFactor * (1.0 - uProgress);

      // Pinch distortion (radial pulling towards origin)
      float pinchDist = 1.0 - smoothstep(0.0, 0.95, dist);
      float pinchVal = sin(uProgress * 3.14159265) * 0.15 * uPinch;
      vec2 pinchOffset = dir * pinchDist * pinchVal;

      vec2 disp = dir * ripple * 0.10 + pinchOffset;

      // Displaced UV coordinates
      vec2 uvCurrent = clamp(uv + disp * (1.0 - uProgress), 0.001, 0.999);
      vec2 uvNext    = clamp(uv - disp * uProgress, 0.001, 0.999);

      vec4 colCurrent = texture2D(uTexCurrent, uvCurrent);
      vec4 colNext    = texture2D(uTexNext, uvNext);

      // Smooth step blend along the wave front
      float blend = smoothstep(currentRadius - waveWidth * 0.75, currentRadius + 0.08, dist);
      vec4 finalColor = mix(colNext, colCurrent, blend);

      // Specular water gleam along ripple crest
      float spec = pow(clamp(ripple * 5.5, 0.0, 1.0), 3.0) * 0.45 * (1.0 - uProgress);
      finalColor.rgb += vec3(spec);

      gl_FragColor = finalColor;
    }
  `;

  function createRippleTransition(container, options) {
    if (!container) return null;
    const items = options.items || [];
    if (items.length === 0) return null;

    const autoPlay = options.autoPlay !== false;
    const autoPlayInterval = options.autoPlayInterval || 3200;
    const duration = options.duration || 1.4;
    const pinch = options.pinch !== false;
    const autoPlayOrigin = options.autoPlayOrigin || "random";
    const onIndexChange = options.onIndexChange || null;

    let width = container.clientWidth || window.innerWidth;
    let height = container.clientHeight || 520;

    let renderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    } catch (e) {
      console.warn("WebGL not supported for RippleTransition:", e);
      return null;
    }

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    renderer.setPixelRatio(dpr);
    renderer.setSize(width, height);
    renderer.domElement.style.width = "100%";
    renderer.domElement.style.height = "100%";
    renderer.domElement.style.display = "block";
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    // Texture cache
    const textures = new Array(items.length).fill(null);
    const textureLoader = new THREE.TextureLoader();
    textureLoader.setCrossOrigin("anonymous");

    // Warm scenic fallback texture while images load or if an offline link fails
    const placeholderCanvas = document.createElement("canvas");
    placeholderCanvas.width = 128;
    placeholderCanvas.height = 128;
    const pctx = placeholderCanvas.getContext("2d");
    const bgGrad = pctx.createLinearGradient(0, 0, 128, 128);
    bgGrad.addColorStop(0, "#0E4D54");
    bgGrad.addColorStop(0.5, "#0D3349");
    bgGrad.addColorStop(1, "#081A2D");
    pctx.fillStyle = bgGrad;
    pctx.fillRect(0, 0, 128, 128);
    const fallbackTex = new THREE.CanvasTexture(placeholderCanvas);

    function loadTexture(idx) {
      if (textures[idx]) return textures[idx];
      const item = items[idx];
      const url = typeof item === "string" ? item : item.image;
      const tex = textureLoader.load(
        url,
        (loaded) => {
          loaded.minFilter = THREE.LinearFilter;
          loaded.magFilter = THREE.LinearFilter;
          loaded.generateMipmaps = false;
          if (THREE.SRGBColorSpace) loaded.colorSpace = THREE.SRGBColorSpace;
          else if (THREE.sRGBEncoding) loaded.encoding = THREE.sRGBEncoding;
        },
        undefined,
        () => {
          // If a photo fails, fall back to the first loaded valid photo or scenic gradient
          textures[idx] = textures.find(t => t && t !== fallbackTex) || fallbackTex;
        }
      );
      textures[idx] = tex;
      return tex;
    }

    // Preload first 4 textures immediately
    for (let i = 0; i < Math.min(4, items.length); i++) {
      loadTexture(i);
    }

    let currentIndex = 0;
    let nextIndex = 1;
    let isTransitioning = false;
    let autoPlayTimer = null;

    const uniforms = {
      uTexCurrent: { value: loadTexture(0) },
      uTexNext: { value: loadTexture(1) },
      uProgress: { value: 0.0 },
      uOrigin: { value: new THREE.Vector2(0.5, 0.5) },
      uAspect: { value: width / height },
      uPinch: { value: pinch ? 1.0 : 0.0 },
    };

    const material = new THREE.ShaderMaterial({
      vertexShader: RIPPLE_VERTEX,
      fragmentShader: RIPPLE_FRAGMENT,
      uniforms: uniforms,
      depthTest: false,
      depthWrite: false,
    });

    const geometry = new THREE.PlaneGeometry(2, 2);
    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);

    function getOrigin(customOrigin) {
      if (customOrigin) return customOrigin;
      if (autoPlayOrigin === "random") {
        return new THREE.Vector2(
          0.2 + Math.random() * 0.6,
          0.2 + Math.random() * 0.6
        );
      }
      return new THREE.Vector2(0.5, 0.5);
    }

    function transitionTo(targetIdx, origin) {
      if (isTransitioning || targetIdx === currentIndex) return;
      isTransitioning = true;
      nextIndex = (targetIdx + items.length) % items.length;

      // Lazy load surrounding textures
      loadTexture(nextIndex);
      loadTexture((nextIndex + 1) % items.length);

      uniforms.uTexCurrent.value = textures[currentIndex] || fallbackTex;
      uniforms.uTexNext.value = textures[nextIndex] || fallbackTex;
      uniforms.uProgress.value = 0.0;

      const pt = getOrigin(origin);
      uniforms.uOrigin.value.set(pt.x, pt.y);

      if (window.gsap) {
        window.gsap.to(uniforms.uProgress, {
          value: 1.0,
          duration: duration,
          ease: "power2.inOut",
          onComplete: () => {
            currentIndex = nextIndex;
            uniforms.uTexCurrent.value = textures[currentIndex] || fallbackTex;
            uniforms.uProgress.value = 0.0;
            isTransitioning = false;
            if (onIndexChange) onIndexChange(currentIndex, items[currentIndex]);
          },
        });
      } else {
        currentIndex = nextIndex;
        uniforms.uTexCurrent.value = textures[currentIndex] || fallbackTex;
        uniforms.uProgress.value = 0.0;
        isTransitioning = false;
        if (onIndexChange) onIndexChange(currentIndex, items[currentIndex]);
      }
    }

    function next(origin) {
      transitionTo((currentIndex + 1) % items.length, origin);
    }

    function previous(origin) {
      transitionTo((currentIndex - 1 + items.length) % items.length, origin);
    }

    function startAutoPlay() {
      if (!autoPlay || autoPlayTimer) return;
      autoPlayTimer = setInterval(() => {
        if (!document.hidden) {
          next();
        }
      }, autoPlayInterval);
    }

    function stopAutoPlay() {
      if (autoPlayTimer) {
        clearInterval(autoPlayTimer);
        autoPlayTimer = null;
      }
    }

    // Click to ripple at exact pointer position
    renderer.domElement.addEventListener("click", (e) => {
      const rect = renderer.domElement.getBoundingClientRect();
      const x = (e.clientX - rect.left) / rect.width;
      const y = 1.0 - (e.clientY - rect.top) / rect.height; // invert for WebGL UV
      stopAutoPlay();
      next(new THREE.Vector2(x, y));
      startAutoPlay();
    });

    let rafId = 0;
    let running = true;

    function renderLoop() {
      if (!running) return;
      renderer.render(scene, camera);
      rafId = requestAnimationFrame(renderLoop);
    }
    renderLoop();
    startAutoPlay();

    function onResize() {
      width = container.clientWidth || window.innerWidth;
      height = container.clientHeight || 520;
      renderer.setSize(width, height);
      uniforms.uAspect.value = width / height;
    }

    const resizeObserver = new ResizeObserver(onResize);
    resizeObserver.observe(container);

    function destroy() {
      running = false;
      stopAutoPlay();
      cancelAnimationFrame(rafId);
      resizeObserver.disconnect();
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      textures.forEach((t) => t && t.dispose && t.dispose());
      if (renderer.domElement.parentNode) {
        renderer.domElement.parentNode.removeChild(renderer.domElement);
      }
    }

    if (onIndexChange) {
      onIndexChange(0, items[0]);
    }

    return {
      next,
      previous,
      transitionTo,
      pause: stopAutoPlay,
      play: startAutoPlay,
      destroy,
      getCurrentIndex: () => currentIndex,
    };
  }

  global.createRippleTransition = createRippleTransition;
})(window);
