/**
 * ═════════════════════════════════════════════════════════════════════
 * Neural Flow Field Background Engine (Vanilla JS implementation)
 * High-performance simplex-like flow field particles with cursor repulsion
 * and fading trail persistence.
 * ═════════════════════════════════════════════════════════════════════
 */

(function (global) {
  "use strict";

  class NeuralBackgroundInstance {
    constructor(container, options = {}) {
      this.container = container;
      this.options = options;
      this.color = options.color || "#00A896"; // Brand turquoise / indigo
      this.trailOpacity = options.trailOpacity !== undefined ? options.trailOpacity : 0.14;
      this.particleCount = options.particleCount || 450;
      this.speed = options.speed || 1;

      this.canvas = document.createElement("canvas");
      this.canvas.className = "neural-flow-canvas";
      this.canvas.style.display = "block";
      this.canvas.style.width = "100%";
      this.canvas.style.height = "100%";
      this.canvas.style.position = "absolute";
      this.canvas.style.top = "0";
      this.canvas.style.left = "0";
      this.canvas.style.pointerEvents = "none";
      this.canvas.style.zIndex = options.zIndex !== undefined ? options.zIndex : "0";

      this.container.style.position = this.container.style.position || "relative";
      this.container.appendChild(this.canvas);

      this.interactiveTarget = options.listenElement || this.container.parentElement || this.container;

      this.ctx = this.canvas.getContext("2d");
      this.mouse = { x: -1000, y: -1000 };
      this.running = true;

      this.init();
      this.bindEvents();
      this.animate = this.animate.bind(this);
      this.rafId = requestAnimationFrame(this.animate);
    }

    init() {
      const dpr = window.devicePixelRatio || 1;
      this.width = this.container.clientWidth || window.innerWidth;
      this.height = this.container.clientHeight || window.innerHeight;

      this.canvas.width = this.width * dpr;
      this.canvas.height = this.height * dpr;
      this.ctx.scale(dpr, dpr);

      const self = this;

      class Particle {
        constructor() {
          this.x = Math.random() * self.width;
          this.y = Math.random() * self.height;
          this.vx = 0;
          this.vy = 0;
          this.age = 0;
          this.life = Math.random() * 200 + 100;
        }

        update() {
          const angle = (Math.cos(this.x * 0.005) + Math.sin(this.y * 0.005)) * Math.PI;
          this.vx += Math.cos(angle) * 0.2 * self.speed;
          this.vy += Math.sin(angle) * 0.2 * self.speed;

          const dx = self.mouse.x - this.x;
          const dy = self.mouse.y - this.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          const radius = 140;

          if (dist < radius) {
            const force = (radius - dist) / radius;
            this.vx -= dx * force * 0.05;
            this.vy -= dy * force * 0.05;
          }

          this.x += this.vx;
          this.y += this.vy;
          this.vx *= 0.95;
          this.vy *= 0.95;

          this.age++;
          if (this.age > this.life) {
            this.reset();
          }

          if (this.x < 0) this.x = self.width;
          if (this.x > self.width) this.x = 0;
          if (this.y < 0) this.y = self.height;
          if (this.y > self.height) this.y = 0;
        }

        reset() {
          this.x = Math.random() * self.width;
          this.y = Math.random() * self.height;
          this.vx = 0;
          this.vy = 0;
          this.age = 0;
          this.life = Math.random() * 200 + 100;
        }

        draw(ctx) {
          ctx.fillStyle = self.color;
          const alpha = 1 - Math.abs(this.age / this.life - 0.5) * 2;
          ctx.globalAlpha = Math.max(0, Math.min(1, alpha));
          ctx.fillRect(this.x, this.y, 1.6, 1.6);
        }
      }

      this.particles = [];
      for (let i = 0; i < this.particleCount; i++) {
        this.particles.push(new Particle());
      }
    }

    animate() {
      if (!this.running) return;
      this.rafId = requestAnimationFrame(this.animate);

      this.ctx.fillStyle = `rgba(11, 31, 51, ${this.trailOpacity})`;
      this.ctx.fillRect(0, 0, this.width, this.height);

      this.particles.forEach((p) => {
        p.update();
        p.draw(this.ctx);
      });
    }

    bindEvents() {
      this.onResize = () => {
        if (!this.container) return;
        this.init();
      };

      this.onMouseMove = (e) => {
        const rect = this.canvas.getBoundingClientRect();
        this.mouse.x = e.clientX - rect.left;
        this.mouse.y = e.clientY - rect.top;
      };

      this.onMouseLeave = () => {
        this.mouse.x = -1000;
        this.mouse.y = -1000;
      };

      window.addEventListener("resize", this.onResize);
      if (this.interactiveTarget) {
        this.interactiveTarget.addEventListener("mousemove", this.onMouseMove);
        this.interactiveTarget.addEventListener("mouseleave", this.onMouseLeave);
      }
    }

    destroy() {
      this.running = false;
      if (this.rafId) cancelAnimationFrame(this.rafId);
      window.removeEventListener("resize", this.onResize);
      if (this.interactiveTarget) {
        this.interactiveTarget.removeEventListener("mousemove", this.onMouseMove);
        this.interactiveTarget.removeEventListener("mouseleave", this.onMouseLeave);
      }
      this.canvas.remove();
    }
  }

  global.NeuralBackground = {
    mount: function (container, options) {
      if (!container) return null;
      return new NeuralBackgroundInstance(container, options);
    }
  };

})(window);
