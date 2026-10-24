/**
 * Sticky Reveal Footer Engine
 * Under-page sticky footer that fades, scales, and unblurs as scroll uncovers it.
 * Implements the signature Motion for React scroll-reveal effect with 60fps rAF.
 */

(function (global) {
  "use strict";

  function initStickyRevealFooter() {
    const footer = document.getElementById("stickyRevealFooter");
    const spacer = document.getElementById("footerRevealSpacer");
    const inner = document.getElementById("footerRevealInner");

    if (!footer || !spacer || !inner) return;

    const prefersReduced =
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const isMobile = window.innerWidth <= 768;

    if (prefersReduced || isMobile) {
      spacer.style.height = "0px";
      spacer.style.display = "none";
      inner.style.opacity = "1";
      inner.style.transform = "none";
      inner.style.filter = "none";
      if (isMobile) return;
    }

    let footerHeight = footer.offsetHeight || 380;
    let rafId = null;

    function updateSpacerHeight() {
      footerHeight = footer.offsetHeight || 380;
      spacer.style.height = footerHeight + "px";
    }

    // Observe footer height on DOM updates or resize
    if (window.ResizeObserver) {
      const ro = new ResizeObserver(() => {
        updateSpacerHeight();
        onScroll();
      });
      ro.observe(footer);
    } else {
      window.addEventListener("resize", () => {
        updateSpacerHeight();
        onScroll();
      });
    }

    updateSpacerHeight();

    function onScroll() {
      if (rafId) return;
      rafId = requestAnimationFrame(updateRevealState);
    }

    function updateRevealState() {
      rafId = null;

      const scrollY = window.pageYOffset || document.documentElement.scrollTop || 0;
      const windowHeight = window.innerHeight || 800;
      const docHeight = document.documentElement.scrollHeight || 1000;

      // Distance from the bottom of viewport to the end of the document
      const remainingDist = docHeight - (scrollY + windowHeight);

      // If document is shorter than viewport or at bottom
      if (docHeight - footerHeight <= windowHeight) {
        inner.style.opacity = "1";
        inner.style.transform = "scale(1) translateY(0px)";
        inner.style.filter = "blur(0px)";
        return;
      }

      // Compute progress 0.0 -> 1.0 as the footer is uncovered
      let progress = 0;
      if (remainingDist <= footerHeight) {
        progress = Math.max(0, Math.min(1, 1.0 - remainingDist / Math.max(1, footerHeight)));
      } else {
        progress = 0;
      }

      // Smooth easing curve (cubic-bezier out)
      const eased = Math.pow(progress, 0.85);

      const scale = 0.92 + 0.08 * eased;
      const opacity = 0.4 + 0.6 * eased;
      const translateY = -24 * (1.0 - eased);
      const blur = (1.0 - eased) * 4;

      inner.style.transform = `scale(${scale.toFixed(4)}) translateY(${translateY.toFixed(2)}px)`;
      inner.style.opacity = opacity.toFixed(3);
      inner.style.filter = `blur(${blur.toFixed(2)}px)`;
    }

    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });

    // Initial tick
    updateRevealState();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initStickyRevealFooter);
  } else {
    initStickyRevealFooter();
  }
})(window);
