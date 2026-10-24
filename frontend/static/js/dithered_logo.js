/**
 * Dithered Interactive Logo Component
 * Converts an image into an error-diffused dithered particle system
 * with interactive cursor repulsion and click shockwave ripples.
 */

(function (global) {
  'use strict';

  const DEFAULTS = {
    gridSize: 90,
    scale: 0.92,
    dotScale: 1.15,
    threshold: 210, // Pixels darker than threshold become particles
    contrast: 15,
    gamma: 1.0,
    blur: 0.8,
    diffusionStrength: 0.9,
    serpentine: true,
    particleColor: '#0d9488', // Brand turquoise
    preserveColors: true,     // Preserve real logo colors (teal, coral, navy)
    cursorRadius: 75,
    cursorForce: 35,
    rippleSpeed: 240,
    rippleWidth: 32,
    rippleForce: 24,
    rippleDuration: 650,
    lerpFactor: 0.14,
    snapThreshold: 0.01,
  };

  function toGrayscaleGrid(img, maxDim, contrast, gamma, blur) {
    const aspect = img.naturalWidth / img.naturalHeight;
    const outW = aspect >= 1 ? maxDim : Math.round(maxDim * aspect);
    const outH = aspect >= 1 ? Math.round(maxDim / aspect) : maxDim;

    const canvas = document.createElement('canvas');
    canvas.width = outW;
    canvas.height = outH;
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    if (!ctx) return null;

    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    ctx.drawImage(img, 0, 0, outW, outH);

    const imgData = ctx.getImageData(0, 0, outW, outH);
    const pixels = imgData.data;
    const grayscale = new Uint8Array(outW * outH);
    const alpha = new Uint8Array(outW * outH);
    const colors = [];

    const cFactor = (259 * (contrast + 255)) / (255 * (259 - contrast));

    for (let y = 0; y < outH; y++) {
      for (let x = 0; x < outW; x++) {
        const idx = (y * outW + x) * 4;
        const r = pixels[idx];
        const g = pixels[idx + 1];
        const b = pixels[idx + 2];
        const a = pixels[idx + 3];

        alpha[y * outW + x] = a;
        colors.push(`rgb(${r},${g},${b})`);

        // Compute perceived luminance
        let luma = 0.299 * r + 0.587 * g + 0.114 * b;
        if (contrast !== 0) luma = cFactor * (luma - 128) + 128;
        if (gamma !== 1) luma = 255 * Math.pow(Math.max(0, luma / 255), 1 / gamma);

        grayscale[y * outW + x] = Math.max(0, Math.min(255, Math.round(luma)));
      }
    }

    return { grayscale, alpha, colors, width: outW, height: outH };
  }

  function errorDiffusionDither(grid, config) {
    const { grayscale, alpha, width, height } = grid;
    const errors = new Float32Array(grayscale.length);
    for (let i = 0; i < grayscale.length; i++) {
      errors[i] = grayscale[i];
    }

    const positions = [];
    const colorIndices = [];
    const strength = config.diffusionStrength;

    for (let y = 0; y < height; y++) {
      const ltr = !config.serpentine || y % 2 === 0;
      const startX = ltr ? 0 : width - 1;
      const endX = ltr ? width : -1;
      const step = ltr ? 1 : -1;

      for (let x = startX; x !== endX; x += step) {
        const idx = y * width + x;
        // Skip purely transparent or near-white background pixels
        if (alpha[idx] < 64) continue;

        const oldVal = errors[idx];
        // Logo pixels are darker than background threshold
        const isEmblem = oldVal < config.threshold;
        const newVal = isEmblem ? 0 : 255;
        const err = (oldVal - newVal) * strength;

        if (isEmblem) {
          positions.push(x, y);
          colorIndices.push(idx);
        }

        const spread = (nx, ny, weight) => {
          if (nx < 0 || nx >= width || ny < 0 || ny >= height) return;
          const ni = ny * width + nx;
          if (alpha[ni] < 64) return;
          errors[ni] += err * weight;
        };

        spread(x + step, y, 7 / 16);
        spread(x - step, y + 1, 3 / 16);
        spread(x, y + 1, 5 / 16);
        spread(x + step, y + 1, 1 / 16);
      }
    }

    return {
      positions: new Float32Array(positions),
      colorIndices,
    };
  }

  function createDitheredLogo(canvas, imageSrc, options) {
    const config = Object.assign({}, DEFAULTS, options || {});
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    let sys = null;
    let ripples = [];
    let cursor = { x: -9999, y: -9999, active: false };
    let animId = null;
    let isRunning = false;

    function initSystem(positions, colorIndices, gridW, gridH, rawColors, rect) {
      const count = positions.length / 2;
      const scaleFactor = Math.max(
        0.5,
        (Math.min(rect.width, rect.height) * config.scale) / Math.max(gridW, gridH)
      );
      const originX = Math.round((rect.width - gridW * scaleFactor) / 2);
      const originY = Math.round((rect.height - gridH * scaleFactor) / 2);

      const baseX = new Float32Array(count);
      const baseY = new Float32Array(count);
      const offsetX = new Float32Array(count);
      const offsetY = new Float32Array(count);
      const particleColors = [];

      for (let i = 0; i < count; i++) {
        baseX[i] = originX + positions[i * 2] * scaleFactor;
        baseY[i] = originY + positions[i * 2 + 1] * scaleFactor;
        particleColors.push(
          config.preserveColors
            ? rawColors[colorIndices[i]] || config.particleColor
            : config.particleColor
        );
      }

      return {
        count,
        baseX,
        baseY,
        offsetX,
        offsetY,
        particleColors,
        size: Math.max(1, scaleFactor * config.dotScale),
      };
    }

    function step(now) {
      if (!sys) return false;
      const { count, baseX, baseY, offsetX, offsetY } = sys;

      // Filter expired ripples
      for (let k = ripples.length - 1; k >= 0; k--) {
        if (now - ripples[k].start >= config.rippleDuration) {
          ripples.splice(k, 1);
        }
      }

      const numRipples = ripples.length;
      let hasMotion = false;
      const curRadSq = config.cursorRadius * config.cursorRadius;

      for (let i = 0; i < count; i++) {
        let fx = 0;
        let fy = 0;

        // Cursor repulsion
        if (cursor.active) {
          const vx = baseX[i] + offsetX[i] - cursor.x;
          const vy = baseY[i] + offsetY[i] - cursor.y;
          const d2 = vx * vx + vy * vy;
          if (d2 > 0.1 && d2 < curRadSq) {
            const d = Math.sqrt(d2);
            const f = Math.pow(1 - d / config.cursorRadius, 3) * config.cursorForce;
            fx += (vx / d) * f;
            fy += (vy / d) * f;
          }
        }

        // Ripple shockwaves
        for (let k = 0; k < numRipples; k++) {
          const rip = ripples[k];
          const elapsed = now - rip.start;
          const radius = (elapsed / 1000) * config.rippleSpeed;
          const life = 1 - elapsed / config.rippleDuration;
          const sx = baseX[i] - rip.x;
          const sy = baseY[i] - rip.y;
          const d = Math.sqrt(sx * sx + sy * sy);
          if (d < 0.1) continue;
          const band = Math.abs(d - radius);
          if (band < config.rippleWidth) {
            const wf = (1 - band / config.rippleWidth) * life * config.rippleForce;
            fx += (sx / d) * wf;
            fy += (sy / d) * wf;
          }
        }

        // Spring / Lerp return
        offsetX[i] += (fx - offsetX[i]) * config.lerpFactor;
        offsetY[i] += (fy - offsetY[i]) * config.lerpFactor;

        if (Math.abs(offsetX[i]) < config.snapThreshold) offsetX[i] = 0;
        if (Math.abs(offsetY[i]) < config.snapThreshold) offsetY[i] = 0;
        if (offsetX[i] !== 0 || offsetY[i] !== 0) hasMotion = true;
      }

      return hasMotion || numRipples > 0 || cursor.active;
    }

    function render(dpr) {
      if (!sys) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const size = sys.size * dpr;
      const count = sys.count;

      for (let i = 0; i < count; i++) {
        const rx = (sys.baseX[i] + sys.offsetX[i]) * dpr;
        const ry = (sys.baseY[i] + sys.offsetY[i]) * dpr;

        ctx.fillStyle = sys.particleColors[i];
        ctx.fillRect(rx - 0.25 * dpr, ry - 0.25 * dpr, size, size);
      }
    }

    function loop(now) {
      const dpr = window.devicePixelRatio || 1;
      const needsMore = step(now);
      render(dpr);

      if (needsMore) {
        animId = requestAnimationFrame(loop);
        isRunning = true;
      } else {
        isRunning = false;
        animId = null;
      }
    }

    function wakeLoop() {
      if (!isRunning) {
        isRunning = true;
        animId = requestAnimationFrame(loop);
      }
    }

    // Load and build particles
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = function () {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.round(rect.width * dpr));
      canvas.height = Math.max(1, Math.round(rect.height * dpr));

      const grid = toGrayscaleGrid(img, config.gridSize, config.contrast, config.gamma, config.blur);
      if (!grid) return;

      const ditherResult = errorDiffusionDither(grid, config);
      sys = initSystem(
        ditherResult.positions,
        ditherResult.colorIndices,
        grid.width,
        grid.height,
        grid.colors,
        rect
      );

      wakeLoop();
    };
    img.src = imageSrc;

    // Interactive pointer events
    function onPointerMove(e) {
      const rect = canvas.getBoundingClientRect();
      cursor.x = e.clientX - rect.left;
      cursor.y = e.clientY - rect.top;
      cursor.active = true;
      wakeLoop();
    }

    function onPointerLeave() {
      cursor.active = false;
      wakeLoop();
    }

    function onPointerDown(e) {
      const rect = canvas.getBoundingClientRect();
      ripples.push({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        start: performance.now(),
      });
      wakeLoop();
    }

    canvas.addEventListener('pointermove', onPointerMove);
    canvas.addEventListener('pointerleave', onPointerLeave);
    canvas.addEventListener('pointerdown', onPointerDown);

    return {
      destroy: function () {
        if (animId) cancelAnimationFrame(animId);
        canvas.removeEventListener('pointermove', onPointerMove);
        canvas.removeEventListener('pointerleave', onPointerLeave);
        canvas.removeEventListener('pointerdown', onPointerDown);
      },
      triggerRipple: function (x, y) {
        const rect = canvas.getBoundingClientRect();
        ripples.push({
          x: x !== undefined ? x : rect.width / 2,
          y: y !== undefined ? y : rect.height / 2,
          start: performance.now(),
        });
        wakeLoop();
      },
    };
  }

  // Auto-initialize when DOM is ready
  document.addEventListener('DOMContentLoaded', function () {
    const canvas = document.getElementById('ditheredLogoCanvas');
    if (!canvas) return;

    const imgSrc = canvas.getAttribute('data-img-src') || '/static/images/yatrika_icon.png';
    global.yatrikaDitherLogo = createDitheredLogo(canvas, imgSrc, {
      gridSize: 85,
      scale: 0.95,
      dotScale: 1.25,
      threshold: 215,
      preserveColors: true,
      cursorRadius: 55,
      cursorForce: 30,
      rippleSpeed: 220,
      rippleForce: 25,
    });
  });

  global.createDitheredLogo = createDitheredLogo;
})(window);
