/**
 * ═════════════════════════════════════════════════════════════════════
 * Interactive Dot-Grid Radar Canvas Background (from Quordix Hero)
 * - Interactive proximity radar that magnifies and lights dots on cursor hover
 * - Floating ambient particles drifting across the grid
 * - Automated mobile vertical laser scanline
 * ═════════════════════════════════════════════════════════════════════
 */

(function (global) {
  "use strict";

  class DotGridRadarInstance {
    constructor(canvas, container, options = {}) {
      this.canvas = canvas;
      this.container = container || canvas.parentElement || document.body;
      this.ctx = canvas.getContext("2d");
      if (!this.ctx) return;

      this.spacing = options.spacing || 30;
      this.baseR = options.baseR || 1.5;
      this.hoverR = options.hoverR || 105;
      this.scanDur = options.scanDur || 2500;
      this.scanPause = options.scanPause || 4000;
      this.defaultColor = options.defaultColor || "rgba(148, 163, 184, 0.42)";
      this.activeColor = options.activeColor || "#ff5500";
      this.particleColor = options.particleColor || "rgba(249, 115, 22, 0.16)";

      this.mouseX = -1000;
      this.mouseY = -1000;
      this.isMobile = false;
      this.particles = [];
      this.running = true;

      const self = this;
      class Particle {
        constructor(w, h) { this.reset(w, h); }
        reset(w, h) {
          this.x = Math.random() * w;
          this.y = Math.random() * h;
          this.vx = (Math.random() - 0.5) * 0.5;
          this.vy = (Math.random() - 0.5) * 0.5;
          this.size = Math.random() * 2.2;
        }
        update(w, h) {
          this.x += this.vx; this.y += this.vy;
          if (this.x < 0 || this.x > w) this.vx *= -1;
          if (this.y < 0 || this.y > h) this.vy *= -1;
        }
        draw(c) {
          c.beginPath();
          c.arc(this.x, this.y, this.size, 0, Math.PI * 2);
          c.fillStyle = self.particleColor;
          c.fill();
        }
      }
      this.Particle = Particle;

      this.init();
      this.bindEvents();
      this.draw = this.draw.bind(this);
      this.raf = requestAnimationFrame(this.draw);
    }

    init() {
      const rect = this.container.getBoundingClientRect();
      const w = this.container.clientWidth || window.innerWidth;
      const h = this.container.clientHeight || rect.height || 600;

      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      this.canvas.width = w * dpr;
      this.canvas.height = h * dpr;
      this.canvas.style.width = w + "px";
      this.canvas.style.height = h + "px";
      this.ctx.scale(dpr, dpr);

      this.w = w;
      this.h = h;
      this.isMobile = w < 768;

      this.particles = [];
      const n = this.isMobile ? 12 : 36;
      for (let i = 0; i < n; i++) {
        this.particles.push(new this.Particle(w, h));
      }
    }

    bindEvents() {
      this.onResize = () => {
        if (!this.running) return;
        this.init();
      };

      this.onMouseMove = (e) => {
        if (this.isMobile) return;
        const r = this.canvas.getBoundingClientRect();
        this.mouseX = e.clientX - r.left;
        this.mouseY = e.clientY - r.top;
      };

      this.onMouseLeave = () => {
        this.mouseX = -1000;
        this.mouseY = -1000;
      };

      window.addEventListener("resize", this.onResize);
      this.container.addEventListener("mousemove", this.onMouseMove);
      this.container.addEventListener("mouseleave", this.onMouseLeave);
    }

    draw() {
      if (!this.running) return;
      this.raf = requestAnimationFrame(this.draw);

      const ctx = this.ctx;
      const w = this.w;
      const h = this.h;

      ctx.clearRect(0, 0, w, h);

      // Draw floating particles
      this.particles.forEach(p => {
        p.update(w, h);
        p.draw(ctx);
      });

      // Scanline timer for mobile
      const loopTime = performance.now() % (this.scanDur + this.scanPause);
      const scanY = this.isMobile
        ? (Math.min(loopTime / this.scanDur, 1)) * (h + this.hoverR * 2) - this.hoverR
        : 0;

      // Draw interactive dot grid
      for (let x = 0; x < w; x += this.spacing) {
        for (let y = 0; y < h; y += this.spacing) {
          const dx = x - this.mouseX;
          const dy = y - this.mouseY;
          const dist = this.isMobile ? Math.abs(y - scanY) : Math.sqrt(dx * dx + dy * dy);

          if (dist < this.hoverR) {
            const scale = 1 - dist / this.hoverR;
            ctx.fillStyle = this.activeColor;
            ctx.shadowBlur = this.isMobile ? 0 : 14;
            ctx.shadowColor = this.isMobile ? "transparent" : "rgba(255, 85, 0, 0.45)";
            ctx.beginPath();
            ctx.arc(x, y, this.baseR + scale * (this.isMobile ? 2 : 3), 0, Math.PI * 2);
            ctx.fill();
          } else {
            ctx.fillStyle = this.defaultColor;
            ctx.shadowBlur = 0;
            ctx.shadowColor = "transparent";
            ctx.beginPath();
            ctx.arc(x, y, this.baseR, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }
    }

    destroy() {
      this.running = false;
      if (this.raf) cancelAnimationFrame(this.raf);
      window.removeEventListener("resize", this.onResize);
      this.container.removeEventListener("mousemove", this.onMouseMove);
      this.container.removeEventListener("mouseleave", this.onMouseLeave);
      this.canvas.remove();
    }
  }

  global.DotGridRadar = {
    mount: function (canvas, container, options) {
      if (!canvas) return null;
      return new DotGridRadarInstance(canvas, container, options);
    }
  };

})(window);
