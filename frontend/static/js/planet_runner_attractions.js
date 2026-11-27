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

  function buildDefaultStages(destination) {
    const dest = destination || "your destination";
    return [
      { name: `Checking stays in ${dest}`, category: "Accommodation", icon: "🏨" },
      { name: "Resolving local distances", category: "Routing", icon: "🗺️" },
      { name: "Comparing nightly rates", category: "Pricing", icon: "💳" },
      { name: `Mapping routes around ${dest}`, category: "Navigation", icon: "🧭" },
      { name: "Loading transit connections", category: "Transport", icon: "🚆" },
      { name: "Preparing trip summary", category: "Itinerary", icon: "📋" }
    ];
  }

  class PlanetRunnerInstance {
    constructor(container, options = {}) {
      this.container = container;
      this.destination = options.destination || "your destination";
      this.attractionsList = (options.attractions && options.attractions.length > 0)
        ? options.attractions.map(a => typeof a === 'string' ? { name: a, category: 'Explore', icon: '📍' } : a)
        : buildDefaultStages(this.destination);
      this.onComplete = options.onComplete || null;

      this.running = true;
      this.time = 0;
      this.selectedCount = 0;
      this.targetSelectTotal = Math.min(this.attractionsList.length, 8);
      this.lastPinSelectTime = 0;
      this.onWindowResize = this.onWindowResize.bind(this);

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
            <span>Exploring ${this.destination}</span>
          </div>
        </div>
        <div class="planet-runner-toast" id="prToast">
          <div class="planet-runner-toast-icon" id="prToastIcon">🧭</div>
          <div class="planet-runner-toast-content">
            <div class="planet-runner-toast-label">Finding local options</div>
            <div class="planet-runner-toast-name" id="prToastName">Scanning stays &amp; routes in ${this.destination}…</div>
          </div>
        </div>
        <div class="planet-runner-hint">Drag to rotate</div>
      `;
    }

    initThree() {
      const W = this.container.clientWidth || 640;
      const H = this.container.clientHeight || 380;

      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(42, W / H, 0.1, 100);
      // 3/4 side-front angle so the running stride, backpack & oncoming pins read clearly
      this.camera.position.set(1.85, 1.32, 4.85);
      this.camera.lookAt(0, 0.14, 0);

      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
      this.renderer.setSize(W, H);
      this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      this.renderer.domElement.className = "planet-runner-canvas";
      this.container.appendChild(this.renderer.domElement);

      // Balanced studio-style lighting for natural 3D depth
      const hemiLight = new THREE.HemisphereLight(0xe0f2fe, 0x0f172a, 0.95);
      this.scene.add(hemiLight);

      const sunLight = new THREE.DirectionalLight(0xfff7ed, 1.85);
      sunLight.position.set(4, 6, 5);
      this.scene.add(sunLight);

      const rimLight = new THREE.DirectionalLight(0x38bdf8, 0.85);
      rimLight.position.set(-4, -1, -4);
      this.scene.add(rimLight);

      // Subtle starfield
      const starGeo = new THREE.BufferGeometry();
      const starCount = 70;
      const starPos = new Float32Array(starCount * 3);
      for (let i = 0; i < starCount * 3; i += 3) {
        starPos[i] = (Math.random() - 0.5) * 16;
        starPos[i + 1] = (Math.random() - 0.5) * 12;
        starPos[i + 2] = -4 - Math.random() * 8;
      }
      starGeo.setAttribute("position", new THREE.BufferAttribute(starPos, 3));
      const starMat = new THREE.PointsMaterial({ color: 0xcbd5e1, size: 0.035, transparent: true, opacity: 0.45 });
      this.stars = new THREE.Points(starGeo, starMat);
      this.scene.add(this.stars);

      window.addEventListener("resize", this.onWindowResize);
    }

    createPlanetTexture() {
      const c = document.createElement("canvas");
      c.width = 1024;
      c.height = 512;
      const ctx = c.getContext("2d");

      // Rich deep ocean gradient
      const oceanGrad = ctx.createLinearGradient(0, 0, 0, c.height);
      oceanGrad.addColorStop(0, "#0b1d36");
      oceanGrad.addColorStop(0.5, "#13345e");
      oceanGrad.addColorStop(1, "#0b1d36");
      ctx.fillStyle = oceanGrad;
      ctx.fillRect(0, 0, c.width, c.height);

      // Soft organic landmass silhouettes with subtle coastal shelf
      const drawLandBlob = (cx, cy, rx, ry, rot, color) => {
        ctx.save();
        ctx.translate(cx, cy);
        ctx.rotate(rot);
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      };

      for (let i = 0; i < 20; i++) {
        const x = (i * 53 + 20) % c.width;
        const y = 90 + ((i * 37) % (c.height - 180));
        const rx = 48 + (i % 4) * 20;
        const ry = 25 + (i % 3) * 12;
        drawLandBlob(x, y, rx + 8, ry + 5, (i * 0.6) % Math.PI, "rgba(56, 189, 248, 0.14)");
        drawLandBlob(x, y, rx, ry, (i * 0.6) % Math.PI, "rgba(30, 88, 102, 0.78)");
      }

      // Warm sage / emerald terrain highlights
      for (let i = 0; i < 18; i++) {
        const x = (i * 61 + 40) % c.width;
        const y = 105 + ((i * 29) % (c.height - 210));
        const rx = 24 + (i % 4) * 10;
        const ry = 13 + (i % 3) * 6;
        drawLandBlob(x, y, rx, ry, (i * 0.9) % Math.PI, "rgba(45, 138, 110, 0.82)");
      }

      // Faint subtle latitude lines
      ctx.strokeStyle = "rgba(255, 255, 255, 0.035)";
      ctx.lineWidth = 1;
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

    createCloudTexture() {
      const c = document.createElement("canvas");
      c.width = 512;
      c.height = 256;
      const ctx = c.getContext("2d");
      ctx.clearRect(0, 0, c.width, c.height);

      for (let i = 0; i < 28; i++) {
        const x = (i * 41 + 15) % c.width;
        const y = 30 + ((i * 29) % (c.height - 60));
        const rx = 22 + (i % 4) * 12;
        const ry = 7 + (i % 3) * 4;
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate((i * 0.4) % Math.PI);
        ctx.fillStyle = "rgba(255, 255, 255, 0.28)";
        ctx.beginPath();
        ctx.ellipse(0, 0, rx, ry, 0, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }

      const tex = new THREE.CanvasTexture(c);
      tex.wrapS = THREE.RepeatWrapping;
      tex.wrapT = THREE.ClampToEdgeWrapping;
      return tex;
    }

    initPlanet() {
      this.planetGroup = new THREE.Group();
      this.planetRadius = 1.85;

      const planetGeo = new THREE.SphereGeometry(this.planetRadius, 56, 42);
      const planetMat = new THREE.MeshStandardMaterial({
        map: this.createPlanetTexture(),
        roughness: 0.78,
        metalness: 0.08
      });
      this.planetMesh = new THREE.Mesh(planetGeo, planetMat);
      this.planetGroup.add(this.planetMesh);

      // Drifting translucent cloud layer
      const cloudGeo = new THREE.SphereGeometry(this.planetRadius * 1.016, 40, 28);
      const cloudMat = new THREE.MeshStandardMaterial({
        map: this.createCloudTexture(),
        transparent: true,
        opacity: 0.5,
        depthWrite: false,
        roughness: 0.9
      });
      this.cloudMesh = new THREE.Mesh(cloudGeo, cloudMat);
      this.planetGroup.add(this.cloudMesh);

      // Smooth translucent atmospheric halo (no harsh wireframe grid)
      const atmoGeo = new THREE.SphereGeometry(this.planetRadius * 1.032, 40, 28);
      const atmoMat = new THREE.MeshBasicMaterial({
        color: 0x38bdf8,
        transparent: true,
        opacity: 0.08,
        side: THREE.BackSide
      });
      const atmoMesh = new THREE.Mesh(atmoGeo, atmoMat);
      this.planetGroup.add(atmoMesh);

      // Position planet so the top curve sits right below the runner
      this.planetGroup.position.set(0, -this.planetRadius + 0.15, 0);
      this.scene.add(this.planetGroup);
    }

    initCharacter() {
      // Build a smooth, two-segment jointed 3D Traveler Character
      this.runner = new THREE.Group();

      const skinMat = new THREE.MeshStandardMaterial({ color: 0xf3c6a5, roughness: 0.55 });
      const jacketMat = new THREE.MeshStandardMaterial({ color: 0x1e4e79, roughness: 0.48 });
      const pantsMat = new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.65 });
      const shoeMat = new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.4 });
      const bagMat = new THREE.MeshStandardMaterial({ color: 0xe07a5f, roughness: 0.42 });
      const hatMat = new THREE.MeshStandardMaterial({ color: 0x0f2942, roughness: 0.5 });

      // Soft ground contact shadow on the globe surface
      const shadowGeo = new THREE.CircleGeometry(0.16, 20);
      const shadowMat = new THREE.MeshBasicMaterial({
        color: 0x020617,
        transparent: true,
        opacity: 0.35,
        depthWrite: false
      });
      const shadowDisc = new THREE.Mesh(shadowGeo, shadowMat);
      shadowDisc.rotation.x = -Math.PI / 2;
      shadowDisc.position.y = -0.05;
      this.runner.add(shadowDisc);

      // Rounded Torso (tapered cylinder + spherical shoulder/hip caps)
      this.torso = new THREE.Group();
      const torsoCore = new THREE.Mesh(new THREE.CylinderGeometry(0.085, 0.072, 0.22, 16), jacketMat);
      const shoulderCap = new THREE.Mesh(new THREE.SphereGeometry(0.086, 16, 12), jacketMat);
      shoulderCap.position.y = 0.11;
      const hipCap = new THREE.Mesh(new THREE.SphereGeometry(0.072, 14, 10), jacketMat);
      hipCap.position.y = -0.11;
      this.torso.add(torsoCore, shoulderCap, hipCap);
      this.torso.position.y = 0.28;
      this.runner.add(this.torso);

      // Head + Visor Cap
      this.head = new THREE.Group();
      const headSphere = new THREE.Mesh(new THREE.SphereGeometry(0.082, 18, 14), skinMat);
      const capCrown = new THREE.Mesh(
        new THREE.SphereGeometry(0.086, 16, 10, 0, Math.PI * 2, 0, Math.PI * 0.52),
        hatMat
      );
      capCrown.position.y = 0.01;
      const capVisor = new THREE.Mesh(new THREE.CylinderGeometry(0.082, 0.082, 0.015, 14, 1, false, -0.7, 1.4), hatMat);
      capVisor.position.set(0, 0.012, 0.035);
      this.head.add(headSphere, capCrown, capVisor);
      this.head.position.y = 0.49;
      this.runner.add(this.head);

      // Rounded Backpack
      this.bag = new THREE.Group();
      const bagBody = new THREE.Mesh(new THREE.CylinderGeometry(0.068, 0.072, 0.16, 14), bagMat);
      bagBody.scale.set(1.1, 1, 0.72);
      const bagTop = new THREE.Mesh(new THREE.SphereGeometry(0.068, 14, 10), bagMat);
      bagTop.scale.set(1.1, 0.7, 0.72);
      bagTop.position.y = 0.08;
      this.bag.add(bagBody, bagTop);
      this.bag.position.set(0, 0.29, -0.105);
      this.runner.add(this.bag);

      // Two-segment leg (hip -> thigh -> knee -> shin -> shoe)
      const buildLeg = (xOffset) => {
        const legGroup = new THREE.Group();
        const thigh = new THREE.Mesh(new THREE.CylinderGeometry(0.033, 0.028, 0.105, 12), pantsMat);
        thigh.position.y = -0.052;

        const kneeGroup = new THREE.Group();
        kneeGroup.position.y = -0.105;
        const kneeJoint = new THREE.Mesh(new THREE.SphereGeometry(0.027, 10, 10), pantsMat);
        const shin = new THREE.Mesh(new THREE.CylinderGeometry(0.027, 0.022, 0.095, 12), pantsMat);
        shin.position.y = -0.048;
        const shoe = new THREE.Mesh(new THREE.SphereGeometry(0.033, 12, 10), shoeMat);
        shoe.scale.set(0.95, 0.72, 1.35);
        shoe.position.set(0, -0.102, 0.012);

        kneeGroup.add(kneeJoint, shin, shoe);
        legGroup.add(thigh, kneeGroup);
        legGroup.position.set(xOffset, 0.165, 0);
        legGroup.userData.knee = kneeGroup;
        return legGroup;
      };

      // Two-segment arm (shoulder -> upperArm -> elbow -> forearm -> hand)
      const buildArm = (xOffset) => {
        const armGroup = new THREE.Group();
        const shoulder = new THREE.Mesh(new THREE.SphereGeometry(0.028, 10, 10), jacketMat);
        const upperArm = new THREE.Mesh(new THREE.CylinderGeometry(0.026, 0.022, 0.088, 12), jacketMat);
        upperArm.position.y = -0.044;

        const elbowGroup = new THREE.Group();
        elbowGroup.position.y = -0.088;
        const elbowJoint = new THREE.Mesh(new THREE.SphereGeometry(0.022, 10, 10), jacketMat);
        const forearm = new THREE.Mesh(new THREE.CylinderGeometry(0.021, 0.018, 0.082, 12), jacketMat);
        forearm.position.y = -0.041;
        const hand = new THREE.Mesh(new THREE.SphereGeometry(0.022, 10, 10), skinMat);
        hand.position.y = -0.086;

        elbowGroup.add(elbowJoint, forearm, hand);
        armGroup.add(shoulder, upperArm, elbowGroup);
        armGroup.position.set(xOffset, 0.37, 0);
        armGroup.userData.elbow = elbowGroup;
        return armGroup;
      };

      this.leftLeg = buildLeg(-0.048);
      this.rightLeg = buildLeg(0.048);
      this.leftArm = buildArm(-0.112);
      this.rightArm = buildArm(0.112);

      this.runner.add(this.leftLeg, this.rightLeg, this.leftArm, this.rightArm);

      // Face along +X (running direction) with a slight forward lean
      this.runner.rotation.order = "YXZ";
      this.runner.rotation.y = Math.PI / 2;
      this.runner.rotation.x = 0.13;
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

        // Distribute pins along the XY great circle so they rise from the right horizon
        // and pass directly under the runner at the north pole
        const angle = (i / count) * Math.PI * 2;
        const lateral = Math.sin(i * 1.7) * 0.22;
        const rOrbit = Math.sqrt(Math.max(0.1, this.planetRadius * this.planetRadius - lateral * lateral));
        const x = rOrbit * Math.cos(angle);
        const y = rOrbit * Math.sin(angle);
        const z = lateral;

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

      // Pulse pin colors to warm amber
      pin.userData.headMat.color.setHex(0xf59e0b);
      pin.userData.headMat.emissive.setHex(0xf59e0b);
      pin.userData.ring.scale.set(2.4, 2.4, 2.4);

      // Show toast
      const toast = document.getElementById("prToast");
      const icon = document.getElementById("prToastIcon");
      const name = document.getElementById("prToastName");

      if (toast && name) {
        const item = pin.userData.attraction;
        if (icon) icon.textContent = item.icon || "📍";
        const cat = item.category ? ` <span style="color:#94a3b8;font-weight:500;">(${item.category})</span>` : "";
        name.innerHTML = `<strong>${item.name}</strong>${cat}`;
        toast.style.transform = "translateX(-50%) translateY(-4px)";
        setTimeout(() => {
          if (toast) toast.style.transform = "translateX(-50%) translateY(0px)";
        }, 280);
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

      // 1. Spin planet under the runner's feet (+Y moves toward -X while runner faces +X)
      this.planetMesh.rotation.z += this.planetSpinVelocity;
      if (this.cloudMesh) {
        this.cloudMesh.rotation.z += this.planetSpinVelocity * 0.45;
        this.cloudMesh.rotation.y += 0.0012;
      }
      this.stars.rotation.y += 0.00035;

      // 2. Two-segment running stride (hips, knees, shoulders, elbows)
      const strideFreq = 7.5;
      const stride = Math.sin(this.time * strideFreq);
      const strideCos = Math.cos(this.time * strideFreq);

      this.leftLeg.rotation.x = stride * 0.68;
      this.rightLeg.rotation.x = -stride * 0.68;
      if (this.leftLeg.userData.knee) {
        this.leftLeg.userData.knee.rotation.x = Math.max(0.12, -strideCos * 0.85 + 0.25);
      }
      if (this.rightLeg.userData.knee) {
        this.rightLeg.userData.knee.rotation.x = Math.max(0.12, strideCos * 0.85 + 0.25);
      }

      this.leftArm.rotation.x = -stride * 0.58;
      this.rightArm.rotation.x = stride * 0.58;
      if (this.leftArm.userData.elbow) {
        this.leftArm.userData.elbow.rotation.x = -0.85 - Math.abs(stride) * 0.22;
      }
      if (this.rightArm.userData.elbow) {
        this.rightArm.userData.elbow.rotation.x = -0.85 - Math.abs(stride) * 0.22;
      }

      // Torso bobs vertically and slightly rolls
      this.runner.position.y = 0.22 + Math.abs(strideCos) * 0.032;
      this.torso.rotation.z = stride * 0.04;
      this.head.rotation.y = Math.sin(this.time * 2.0) * 0.1;

      // Bag jiggles slightly with stride
      this.bag.rotation.x = stride * 0.15;
      this.bag.rotation.y = stride * 0.08;

      // 3. Check proximity of pins to the north pole runner position and loop cleanly
      const worldPinPos = new THREE.Vector3();
      const runnerPos = new THREE.Vector3(0, 0.25, 0);

      this.pins.forEach((pin) => {
        pin.getWorldPosition(worldPinPos);
        const dist = worldPinPos.distanceTo(runnerPos);

        // Reset pins once they pass below the horizon so long searches keep looping
        if (pin.userData.selected && worldPinPos.y < -0.6) {
          pin.userData.selected = false;
          pin.userData.headMat.color.setHex(0xffffff);
          pin.userData.headMat.emissive.setHex(0x00A896);
        }

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

      if (this.scene) {
        this.scene.traverse((obj) => {
          if (obj.geometry) obj.geometry.dispose();
          if (obj.material) {
            const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
            mats.forEach((mat) => {
              if (mat.map) mat.map.dispose();
              mat.dispose();
            });
          }
        });
      }

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
      modal.setAttribute("aria-label", "Route and stay search progress");
      modal.innerHTML = `
        <div class="planet-runner-modal-card">
          <button type="button" class="planet-runner-modal-close" id="globalPlanetRunnerClose" title="Dismiss loading preview">&times;</button>
          <div class="planet-runner-modal-stage" id="globalPlanetRunnerStage"></div>
          <div class="planet-runner-modal-footer">
            <div style="flex-grow: 1;">
              <div class="planet-runner-modal-msg">
                <span class="planet-runner-pulse-dot"></span>
                <span id="globalPlanetRunnerTitle">Searching stays &amp; routes...</span>
              </div>
              <div class="planet-runner-modal-sub" id="globalPlanetRunnerSub">
                Loading local stays, route distances &amp; transit options
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
      if (subEl) subEl.textContent = subtitle || "Smart itinerary engine actively resolving stay-first route & attractions";

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

  // Only show loading modal for slow AI/network trip generation POST requests (never on PDF downloads or navigation)
  document.addEventListener("DOMContentLoaded", () => {
    document.addEventListener("submit", (e) => {
      const form = e.target;
      if (!form || !form.tagName || form.tagName.toLowerCase() !== "form") return;
      if (form.method && form.method.toUpperCase() === "GET") return;
      if (e.defaultPrevented) return;
      if (form.id === "plannerForm" || form.dataset.hasCustomLoader === "true") return;

      const action = (form.getAttribute("action") || "").toLowerCase();
      if (action.includes("/planner/new") || action.includes("/planner/wizard") || form.dataset.planetLoader === "true") {
        const dest = form.querySelector("input[name='destination']")?.value || "India";
        global.PlanetRunner.showModal(
          `Preparing Itinerary for ${dest}...`,
          dest,
          "Waiting for route, stay & schedule response"
        );
      }
    });
  });

})(window);
