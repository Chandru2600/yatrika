/**
 * ═════════════════════════════════════════════════════════════════════
 * 3D Orbit Planet Runner & Autonomous Attraction Scout
 * 
 * Self-contained WebGL (Three.js) engine featuring:
 * - 3D Rotating Globe with terrain, latitude rings & atmospheric rim
 * - Animated 3D Traveler / Courier character running on the planet surface
 * - Dynamic gait animation: pumping legs, swinging arms, bobbing torso & swaying backpack
 * - Attraction pins rising and being "Selected" with pulse waves as the runner reaches them
 * - Live HUD showing discovered attractions & scouting progress
 * ═════════════════════════════════════════════════════════════════════
 */

(function (global) {
  "use strict";

  if (global.PlanetRunnerEngineActive) return;
  global.PlanetRunnerEngineActive = true;

  const DEFAULT_ATTRACTIONS_POOL = [
    { name: "Abbey Falls & Mist Valleys", category: "Waterfalls & Nature", icon: "🌊" },
    { name: "Raja's Seat Sunset Pavilion", category: "Scenic Viewpoint", icon: "🌅" },
    { name: "Dubare Elephant Camp & River", category: "Wildlife Sanctuary", icon: "🐘" },
    { name: "Golden Temple (Namdroling)", category: "Spiritual & Heritage", icon: "🛕" },
    { name: "Talacauvery Sacred River Origin", category: "Sacred Pilgrimage", icon: "⛰️" },
    { name: "Mandalpatti Peak 4x4 Trail", category: "High Altitude Adventure", icon: "🚙" },
    { name: "Coffee Plantation Heritage Walk", category: "Agro-Tourism", icon: "☕" },
    { name: "Madikeri Fort & Palace Museum", category: "Historic Landmark", icon: "🏰" },
    { name: "Iruppu Cascades & Brahmagiri", category: "Trekking Trail", icon: "🌿" },
    { name: "Nagarhole Tiger Reserve", category: "National Park Safari", icon: "🐅" },
    { name: "Om Beach Cliff Trails", category: "Coastal Wonder", icon: "🏖️" },
    { name: "Hampi Stone Chariot Complex", category: "UNESCO World Heritage", icon: "🏛️" }
  ];

  class PlanetRunnerInstance {
    constructor(container, options = {}) {
      this.container = container;
      this.destination = options.destination || "Karnataka";
      this.attractionsList = (options.attractions && options.attractions.length > 0) 
        ? options.attractions.map(a => typeof a === 'string' ? { name: a, category: 'Attraction', icon: '📍' } : a)
        : DEFAULT_ATTRACTIONS_POOL;
      this.onComplete = options.onComplete || null;

      this.running = true;
      this.time = 0;
      this.selectedCount = 0;
      this.targetSelectTotal = Math.min(this.attractionsList.length, 8);
      this.lastPinSelectTime = 0;

      this.initDOM();
      this.initThree();
      this.initCharacter();
      this.initPlanet();
      this.initAttractionPins();
      this.initControls();
      this.animate = this.animate.bind(this);
      this.rafId = requestAnimationFrame(this.animate);
    }

    initDOM() {
      this.container.classList.add("planet-runner-container");
      this.container.innerHTML = `
        <div class="planet-runner-glow"></div>
        <div class="planet-runner-hud-top">
          <div class="planet-runner-badge">
            <span class="planet-runner-pulse-dot"></span>
            <span>Scouting ${this.destination}</span>
          </div>
          <div class="planet-runner-counter" id="prCounter">
            Selected: <span id="prSelCount">0</span> / ${this.targetSelectTotal}
          </div>
        </div>
        <div class="planet-runner-toast" id="prToast">
          <div class="planet-runner-toast-icon" id="prToastIcon">🏃</div>
          <div class="planet-runner-toast-content">
            <div class="planet-runner-toast-label">Autonomous Scout Running</div>
            <div class="planet-runner-toast-name" id="prToastName">Exploring ${this.destination} landscape…</div>
          </div>
        </div>
        <div class="planet-runner-hint">Drag to rotate the world</div>
      `;
    }

    initThree() {
      const W = this.container.clientWidth || 640;
      const H = this.container.clientHeight || 380;

      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(45, W / H, 0.1, 100);
      this.camera.position.set(0, 1.2, 5.8);
      this.camera.lookAt(0, 0.1, 0);

      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      this.renderer.setSize(W, H);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.renderer.domElement.className = "planet-runner-canvas";
      this.container.appendChild(this.renderer.domElement);

      // Lights
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
      this.scene.add(ambientLight);

      const sunLight = new THREE.DirectionalLight(0xfff5e6, 2.2);
      sunLight.position.set(4, 6, 5);
      this.scene.add(sunLight);

      const rimLight = new THREE.DirectionalLight(0x00A896, 1.4);
      rimLight.position.set(-4, -2, -4);
      this.scene.add(rimLight);

      // Star particles in background
      const starGeo = new THREE.BufferGeometry();
      const starCount = 80;
      const starPos = new Float32Array(starCount * 3);
      for (let i = 0; i < starCount * 3; i += 3) {
        starPos[i] = (Math.random() - 0.5) * 16;
        starPos[i + 1] = (Math.random() - 0.5) * 12;
        starPos[i + 2] = -4 - Math.random() * 8;
      }
      starGeo.setAttribute("position", new THREE.BufferAttribute(starPos, 3));
      const starMat = new THREE.PointsMaterial({ color: 0x93c5fd, size: 0.04, transparent: true, opacity: 0.6 });
      this.stars = new THREE.Points(starGeo, starMat);
      this.scene.add(this.stars);

      window.addEventListener("resize", this.onWindowResize.bind(this));
    }

    createPlanetTexture() {
      const c = document.createElement("canvas");
      c.width = 1024;
      c.height = 512;
      const ctx = c.getContext("2d");

      // Deep stylized ocean
      const oceanGrad = ctx.createLinearGradient(0, 0, 0, c.height);
      oceanGrad.addColorStop(0, "#0b2545");
      oceanGrad.addColorStop(0.5, "#134074");
      oceanGrad.addColorStop(1, "#0b2545");
      ctx.fillStyle = oceanGrad;
      ctx.fillRect(0, 0, c.width, c.height);

      // Continents & landmass islands
      ctx.fillStyle = "#1e5f74";
      for (let i = 0; i < 22; i++) {
        const x = (i * 47) % c.width;
        const y = 80 + ((i * 31) % (c.height - 160));
        const r = 35 + (i % 5) * 18;
        ctx.beginPath();
        ctx.arc(x, y, r, 0, Math.PI * 2);
        ctx.fill();
      }

      // Emerald vibrant Karnataka / India greenery patches
      ctx.fillStyle = "#00A896";
      for (let i = 0; i < 18; i++) {
        const x = (i * 59 + 30) % c.width;
        const y = 100 + ((i * 27) % (c.height - 200));
        ctx.beginPath();
        ctx.arc(x, y, 16 + (i % 4) * 8, 0, Math.PI * 2);
        ctx.fill();
      }

      // Latitude grid lines
      ctx.strokeStyle = "rgba(255, 255, 255, 0.08)";
      ctx.lineWidth = 1.5;
      for (let y = 64; y < c.height; y += 64) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(c.width, y);
        ctx.stroke();
      }

      const tex = new THREE.CanvasTexture(c);
      tex.wrapS = THREE.RepeatWrapping;
      tex.wrapT = THREE.ClampToEdgeWrapping;
      return tex;
    }

    initPlanet() {
      this.planetGroup = new THREE.Group();
      this.planetRadius = 1.85;

      const planetGeo = new THREE.SphereGeometry(this.planetRadius, 48, 36);
      const planetMat = new THREE.MeshStandardMaterial({
        map: this.createPlanetTexture(),
        roughness: 0.72,
        metalness: 0.1
      });
      this.planetMesh = new THREE.Mesh(planetGeo, planetMat);
      this.planetGroup.add(this.planetMesh);

      // Atmosphere rim glow mesh
      const atmoGeo = new THREE.SphereGeometry(this.planetRadius * 1.025, 36, 24);
      const atmoMat = new THREE.MeshBasicMaterial({
        color: 0x02c39a,
        transparent: true,
        opacity: 0.15,
        wireframe: true
      });
      const atmoMesh = new THREE.Mesh(atmoGeo, atmoMat);
      this.planetGroup.add(atmoMesh);

      // Position planet so the top curve sits right below the runner
      this.planetGroup.position.set(0, -this.planetRadius + 0.15, 0);
      this.scene.add(this.planetGroup);
    }

    initCharacter() {
      // Build a 3D stylized Courier / Explorer Character
      this.runner = new THREE.Group();

      const skinMat = new THREE.MeshStandardMaterial({ color: 0xffd1b3, roughness: 0.5 });
      const outfitMat = new THREE.MeshStandardMaterial({ color: 0x00A896, roughness: 0.4 }); // Turquoise jacket
      const darkMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.6 }); // Pants & boots
      const bagMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.3 }); // Orange/Gold courier bag
      const hatMat = new THREE.MeshStandardMaterial({ color: 0x0B1F33, roughness: 0.5 });

      // Torso
      this.torso = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.08, 0.28, 8), outfitMat);
      this.torso.position.y = 0.28;
      this.runner.add(this.torso);

      // Head
      this.head = new THREE.Mesh(new THREE.SphereGeometry(0.09, 12, 10), skinMat);
      this.head.position.y = 0.48;
      this.runner.add(this.head);

      // Explorer Cap
      const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.04, 8), hatMat);
      cap.position.y = 0.54;
      this.runner.add(cap);

      // Courier Bag / Backpack
      this.bag = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.18, 0.12), bagMat);
      this.bag.position.set(0, 0.28, -0.12);
      this.runner.add(this.bag);

      // Left Leg
      this.leftLeg = new THREE.Group();
      const leftLegMesh = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.22, 0.06), darkMat);
      leftLegMesh.position.y = -0.11;
      this.leftLeg.add(leftLegMesh);
      this.leftLeg.position.set(-0.06, 0.16, 0);
      this.runner.add(this.leftLeg);

      // Right Leg
      this.rightLeg = new THREE.Group();
      const rightLegMesh = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.22, 0.06), darkMat);
      rightLegMesh.position.y = -0.11;
      this.rightLeg.add(rightLegMesh);
      this.rightLeg.position.set(0.06, 0.16, 0);
      this.runner.add(this.rightLeg);

      // Left Arm
      this.leftArm = new THREE.Group();
      const leftArmMesh = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.2, 0.05), outfitMat);
      leftArmMesh.position.y = -0.1;
      this.leftArm.add(leftArmMesh);
      this.leftArm.position.set(-0.13, 0.38, 0);
      this.runner.add(this.leftArm);

      // Right Arm
      this.rightArm = new THREE.Group();
      const rightArmMesh = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.2, 0.05), outfitMat);
      rightArmMesh.position.y = -0.1;
      this.rightArm.add(rightArmMesh);
      this.rightArm.position.set(0.13, 0.38, 0);
      this.runner.add(this.rightArm);

      // Position runner right on the north pole top of the planet sphere
      this.runner.position.set(0, 0.22, 0);
      this.scene.add(this.runner);
    }

    initAttractionPins() {
      this.pins = [];
      const count = Math.min(this.attractionsList.length, 12);

      const pinStemGeo = new THREE.CylinderGeometry(0.015, 0.015, 0.24, 6);
      const pinHeadGeo = new THREE.SphereGeometry(0.065, 8, 8);

      for (let i = 0; i < count; i++) {
        const pinGroup = new THREE.Group();

        // Pin materials
        const stemMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.6, roughness: 0.3 });
        const headMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0x00A896, roughness: 0.2 });

        const stem = new THREE.Mesh(pinStemGeo, stemMat);
        stem.position.y = 0.12;
        pinGroup.add(stem);

        const head = new THREE.Mesh(pinHeadGeo, headMat);
        head.position.y = 0.24;
        pinGroup.add(head);

        // Pulse wave ring
        const ringGeo = new THREE.RingGeometry(0.04, 0.07, 16);
        const ringMat = new THREE.MeshBasicMaterial({ color: 0x5eead4, side: THREE.DoubleSide, transparent: true, opacity: 0.7 });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = Math.PI / 2;
        ring.position.y = 0.02;
        pinGroup.add(ring);

        // Distribute pins along equator & mid-latitudes around the sphere
        const angle = (i / count) * Math.PI * 2;
        const lat = (Math.sin(i * 1.8) * 0.45); // slight latitude variance
        const phi = Math.PI / 2 - lat;
        const theta = angle;

        const r = this.planetRadius;
        const x = r * Math.sin(phi) * Math.cos(theta);
        const y = r * Math.cos(phi);
        const z = r * Math.sin(phi) * Math.sin(theta);

        pinGroup.position.set(x, y, z);
        pinGroup.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(x, y, z).normalize());

        pinGroup.userData = {
          attraction: this.attractionsList[i],
          selected: false,
          ring: ring,
          headMat: headMat,
          angle: angle
        };

        this.planetMesh.add(pinGroup);
        this.pins.push(pinGroup);
      }
    }

    initControls() {
      this.isDragging = false;
      this.prevPointerX = 0;
      this.dragSpeed = 0.006;
      this.planetSpinVelocity = 0.016; // constant walking rotation

      const canvas = this.renderer.domElement;

      canvas.addEventListener("pointerdown", (e) => {
        this.isDragging = true;
        this.prevPointerX = e.clientX;
        canvas.setPointerCapture(e.pointerId);
      });

      canvas.addEventListener("pointermove", (e) => {
        if (!this.isDragging) return;
        const dx = e.clientX - this.prevPointerX;
        this.planetGroup.rotation.y += dx * this.dragSpeed;
        this.prevPointerX = e.clientX;
      });

      const stopDrag = (e) => {
        this.isDragging = false;
        try { canvas.releasePointerCapture(e.pointerId); } catch (_) {}
      };

      canvas.addEventListener("pointerup", stopDrag);
      canvas.addEventListener("pointercancel", stopDrag);
    }

    onWindowResize() {
      if (!this.container || !this.renderer || !this.camera) return;
      const W = this.container.clientWidth;
      const H = this.container.clientHeight;
      if (W === 0 || H === 0) return;
      this.camera.aspect = W / H;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(W, H);
    }

    triggerSelect(pin) {
      if (pin.userData.selected) return;
      pin.userData.selected = true;
      this.selectedCount++;

      // Pulse pin colors to golden turquoise
      pin.userData.headMat.color.setHex(0xf59e0b);
      pin.userData.headMat.emissive.setHex(0xf59e0b);
      pin.userData.ring.scale.set(2.4, 2.4, 2.4);

      // Update counter UI
      const selEl = document.getElementById("prSelCount");
      if (selEl) selEl.textContent = this.selectedCount;

      // Show toast
      const toast = document.getElementById("prToast");
      const icon = document.getElementById("prToastIcon");
      const name = document.getElementById("prToastName");

      if (toast && name) {
        const item = pin.userData.attraction;
        if (icon) icon.textContent = item.icon || "📍";
        name.innerHTML = `<strong>${item.name}</strong> <span class="text-white-50">(${item.category || 'Must-Visit'})</span>`;
        toast.style.transform = "translateX(-50%) translateY(-6px)";
        toast.style.borderColor = "#00A896";
        setTimeout(() => {
          if (toast) toast.style.transform = "translateX(-50%) translateY(0px)";
        }, 300);
      }

      if (this.selectedCount >= this.targetSelectTotal && this.onComplete) {
        setTimeout(() => {
          if (this.running && this.onComplete) this.onComplete();
        }, 800);
      }
    }

    animate() {
      if (!this.running) return;
      this.rafId = requestAnimationFrame(this.animate);

      this.time += 0.05;

      // 1. Rotate Planet to simulate runner moving forward across the globe
      this.planetGroup.rotation.y += this.planetSpinVelocity;
      this.stars.rotation.y += 0.0004;

      // 2. Character Running Stride Animation (legs pumping, arms swinging, torso bobbing)
      const strideFreq = 7.5;
      const stride = Math.sin(this.time * strideFreq);
      const strideCos = Math.cos(this.time * strideFreq);

      // Legs swing back and forth
      this.leftLeg.rotation.x = stride * 0.72;
      this.rightLeg.rotation.x = -stride * 0.72;

      // Arms swing opposite to legs
      this.leftArm.rotation.x = -stride * 0.65;
      this.rightArm.rotation.x = stride * 0.65;

      // Torso bobs vertically and slightly rolls
      this.runner.position.y = 0.22 + Math.abs(strideCos) * 0.035;
      this.torso.rotation.z = stride * 0.05;
      this.head.rotation.y = Math.sin(this.time * 2.0) * 0.12;

      // Bag jiggles with delay
      this.bag.rotation.x = stride * 0.2;
      this.bag.rotation.y = stride * 0.1;

      // 3. Check proximity of pins to the north pole runner position
      const worldPinPos = new THREE.Vector3();
      const runnerPos = new THREE.Vector3(0, 0.25, 0);

      this.pins.forEach((pin) => {
        pin.getWorldPosition(worldPinPos);
        const dist = worldPinPos.distanceTo(runnerPos);

        // When pin passes close under/near the runner
        if (dist < 1.15 && !pin.userData.selected) {
          this.triggerSelect(pin);
        }

        // Animate ring pulse
        if (pin.userData.ring) {
          const pulse = 1.0 + Math.sin(this.time * 6.0 + pin.userData.angle) * 0.25;
          pin.userData.ring.scale.set(pulse, pulse, pulse);
        }
      });

      this.renderer.render(this.scene, this.camera);
    }

    destroy() {
      this.running = false;
      if (this.rafId) cancelAnimationFrame(this.rafId);
      window.removeEventListener("resize", this.onWindowResize);
      if (this.renderer && this.renderer.domElement) {
        this.renderer.domElement.remove();
        this.renderer.dispose();
      }
      this.container.innerHTML = "";
    }
  }

  let modalRunner = null;
  let showTimer = null;
  let modalShownTimestamp = 0;

  function ensureModalElement() {
    let modal = document.getElementById("globalPlanetRunnerModal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "globalPlanetRunnerModal";
      modal.className = "planet-runner-global-modal";
      modal.setAttribute("role", "dialog");
      modal.setAttribute("aria-modal", "true");
      modal.setAttribute("aria-label", "AI Scout Loading");
      modal.innerHTML = `
        <div class="planet-runner-modal-card">
          <button type="button" class="planet-runner-modal-close" id="globalPlanetRunnerClose" title="Dismiss loading preview">&times;</button>
          <div class="planet-runner-modal-stage" id="globalPlanetRunnerStage"></div>
          <div class="planet-runner-modal-footer">
            <div style="flex-grow: 1;">
              <div class="planet-runner-modal-msg">
                <span class="planet-runner-pulse-dot"></span>
                <span id="globalPlanetRunnerTitle">Scouting Karnataka &amp; All-India Journey...</span>
              </div>
              <div class="planet-runner-modal-sub" id="globalPlanetRunnerSub">
                4-Agent Cooperative ML synthesizing stay-first routes &amp; attractions
              </div>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(modal);

      const closeBtn = document.getElementById("globalPlanetRunnerClose");
      if (closeBtn) {
        closeBtn.addEventListener("click", () => {
          global.PlanetRunner.hideModal(true);
        });
      }
    }
    return modal;
  }

  // Global namespace API
  global.PlanetRunner = {
    mount: function (container, options) {
      if (!container) return null;
      return new PlanetRunnerInstance(container, options);
    },

    renderMicro: function (label) {
      return `
        <span class="planet-runner-micro">
          <span class="planet-runner-micro-orb" title="Scout Running Across Earth">
            <span class="planet-runner-micro-earth"></span>
            <span class="planet-runner-micro-figure">🏃</span>
          </span>
          <span class="planet-runner-micro-label">${label !== undefined ? label : "Loading…"}</span>
        </span>
      `;
    },

    mountInline: function (container, message, destination) {
      if (!container) return null;
      if (typeof container === "string") container = document.querySelector(container);
      if (!container) return null;
      container.innerHTML = `
        <div class="planet-loader-inline">
          <div style="width: 100%; height: 180px;" class="planet-inline-canvas-box"></div>
          <div class="planet-loader-inline-text">${message || "Scouting & Resolving…"}</div>
        </div>
      `;
      const box = container.querySelector(".planet-inline-canvas-box");
      if (box && global.THREE) {
        return new PlanetRunnerInstance(box, { destination: destination || "Karnataka" });
      }
      return null;
    },

    showModal: function (title, destination, subtitle) {
      if (showTimer) {
        clearTimeout(showTimer);
        showTimer = null;
      }

      const modal = ensureModalElement();
      const stage = document.getElementById("globalPlanetRunnerStage");
      const titleEl = document.getElementById("globalPlanetRunnerTitle");
      const subEl = document.getElementById("globalPlanetRunnerSub");

      const destName = destination || "Karnataka";
      if (titleEl) titleEl.textContent = title || `Scouting ${destName} & All-India Journey...`;
      if (subEl) subEl.textContent = subtitle || "4-Agent Cooperative Engine actively resolving stay-first route & attractions";

      modal.classList.add("is-active");
      modalShownTimestamp = Date.now();

      if (stage) {
        if (modalRunner) {
          try { modalRunner.destroy(); } catch (_) {}
          modalRunner = null;
        }
        modalRunner = new PlanetRunnerInstance(stage, {
          destination: destName,
          attractions: [
            { name: `${destName} Scenic Peak & Lookouts`, category: "Scenic Viewpoint", icon: "🌅" },
            { name: "Ancient Heritage Citadel & Fort", category: "Historic Landmark", icon: "🏰" },
            { name: "Cascading Waterfalls & Nature Loop", category: "Waterfalls & Nature", icon: "🌊" },
            { name: "Wildlife & National Forest Trails", category: "Wildlife Reserve", icon: "🐅" },
            { name: "Coffee & Agro-Tourism Plantations", category: "Agro-Tourism", icon: "☕" },
            { name: "Sacred Temple & Spiritual Sanctuary", category: "Spiritual", icon: "🛕" }
          ]
        });
        setTimeout(() => {
          if (modalRunner && modalRunner.onWindowResize) modalRunner.onWindowResize();
        }, 80);
      }
    },

    hideModal: function (force = false) {
      if (showTimer) {
        clearTimeout(showTimer);
        showTimer = null;
      }

      const modal = document.getElementById("globalPlanetRunnerModal");
      if (!modal || !modal.classList.contains("is-active")) return;

      const elapsed = Date.now() - modalShownTimestamp;
      // Allow user to see the running motion smoothly if it just popped up (min 450ms), unless force-dismissed
      const delay = force ? 0 : Math.max(0, 450 - elapsed);

      setTimeout(() => {
        if (modal) modal.classList.remove("is-active");
        if (modalRunner) {
          try { modalRunner.destroy(); } catch (_) {}
          modalRunner = null;
        }
      }, delay);
    },

    /**
     * Smart latency-aware loader:
     * Only displays the 3D globe runner if the operation takes LONGER than delayMs (default 280ms).
     * If the operation is instant or fast, the loader is NEVER shown!
     */
    startLoading: function (options = {}) {
      const delay = options.delayMs !== undefined ? options.delayMs : 280;
      let isShown = false;

      if (showTimer) {
        clearTimeout(showTimer);
        showTimer = null;
      }

      showTimer = setTimeout(() => {
        isShown = true;
        global.PlanetRunner.showModal(options.title, options.destination, options.subtitle);
      }, delay);

      return {
        done: function (force = false) {
          if (showTimer) {
            clearTimeout(showTimer);
            showTimer = null;
          }
          if (isShown) {
            global.PlanetRunner.hideModal(force);
          }
        },
        update: function (title, subtitle) {
          const titleEl = document.getElementById("globalPlanetRunnerTitle");
          const subEl = document.getElementById("globalPlanetRunnerSub");
          if (titleEl && title) titleEl.textContent = title;
          if (subEl && subtitle) subEl.textContent = subtitle;
        }
      };
    },

    withLoading: async function (asyncPromise, options = {}) {
      const loader = global.PlanetRunner.startLoading(options);
      try {
        const result = await asyncPromise;
        loader.done();
        return result;
      } catch (err) {
        loader.done(true);
        throw err;
      }
    }
  };

  // Window global aliases
  global.showGlobalScoutLoader = global.PlanetRunner.showModal;
  global.hideGlobalScoutLoader = global.PlanetRunner.hideModal;
  global.withGlobalScoutLoader = global.PlanetRunner.withLoading;

  // Auto-intercept PDF downloads and long-running trip generation actions site-wide
  document.addEventListener("DOMContentLoaded", () => {
    // 1. Intercept PDF download clicks (anchor links & buttons)
    document.addEventListener("click", (e) => {
      const trigger = e.target.closest("a[href*='/pdf'], a[href*='download_pdf'], button[onclick*='download_pdf'], button[onclick*='/pdf'], .btn-pdf-download");
      if (!trigger) return;

      const destEl = document.querySelector("#dest-name-title, #tripDestination, .trip-title-dest, [data-destination]");
      const dest = destEl ? (destEl.textContent || destEl.value || "").trim() : "Karnataka & All-India";

      global.PlanetRunner.showModal(
        "Generating Verified PDF Itinerary...",
        dest,
        "Assembling offline booking tables, weather tips & QR code voucher"
      );

      // Safe dismiss window after download dispatch
      setTimeout(() => global.PlanetRunner.hideModal(), 4200);
    });

    // 2. Intercept forms that trigger real backend trip generation (ONLY POST methods, never GET search)
    document.addEventListener("submit", (e) => {
      const form = e.target;
      if (!form || !form.tagName || form.tagName.toLowerCase() !== "form") return;

      // DO NOT show loader on GET navigation (e.g., search box on home page)
      if (form.method && form.method.toUpperCase() === "GET") return;

      // DO NOT show global loader if page script prevents default to handle AJAX/inline preview
      if (e.defaultPrevented) return;
      if (form.id === "plannerForm" || form.dataset.hasCustomLoader === "true") return;

      const action = (form.getAttribute("action") || "").toLowerCase();
      if (action.includes("/planner/new") || action.includes("/planner/wizard") || form.dataset.planetLoader === "true") {
        const dest = form.querySelector("input[name='destination']")?.value || "India";
        global.PlanetRunner.showModal(
          `Scouting & Generating Itinerary for ${dest}...`,
          dest,
          "4-Agent Cooperative ML synthesizing stay-first anchors & verified transit"
        );
      }
    });
  });

})(window);
