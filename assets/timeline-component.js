/**
 * Timeline Component
 * Copyright © RoarTheme
 */
class TimelineComponent extends HTMLElement {
  // ---------- Lifecycle ----------
  constructor() {
    super();

    // Config (data-* with sensible defaults)
    const ds = this.dataset;
    this.animationSpeed = parseInt(ds.animationSpeed || "", 10) || 800;
    this.sectionHeight  = parseInt(ds.height || "", 10) || 500;
    this.showDots       = ds.showDots === "true";
    this.timelineBg     = ds.timelineBg || "#1a1a1a";
    this.contentBg      = ds.contentBg || "#ffffff";
    this.accentColor    = ds.accentColor || "#ff6b35";
    this.dateColor      = ds.dateColor || "#cccccc";
    this.textColor      = ds.textColor || "#ffffff";

    // State
    this.slides = [];
    this.timelineItems = [];
    this.timelineDot = null;
    this.currentSlideIndex = -1;
    this.totalSlides = 0;
    this.windowHeight = 0;
    this.isInViewport = false;

    // Touch
    this.touchStartY = 0;
    this.touchEndY = 0;

    // Misc
    this._raf = null;           // scroll rAF lock
    this._abort = new AbortController(); // for listeners/observers
    this._resizeObserver = null;
    this._io = null;            // single IntersectionObserver
    this._manualSlideChange = false; // flag to prevent scroll interference
  }

  connectedCallback() {
    this._init();
  }

  disconnectedCallback() {
    this._cleanup();
  }

  // ---------- Init / Cleanup ----------
  _init() {
    this._setupElements();
    this._applyCustomStyles();
    this._setupObservers();
    this._setupEventListeners();

    this._updateDimensions();
    this._updateActiveSlide(0);
  }

  _cleanup() {
    // Abort all DOM listeners bound with this._abort.signal
    this._abort.abort();

    // Disconnect observers
    this._resizeObserver?.disconnect();
    this._io?.disconnect();

    // Cancel any scheduled frame
    if (this._raf) cancelAnimationFrame(this._raf);
  }

  // ---------- Setup ----------
  _setupElements() {
    this.timelineSection = this.closest(".timeline-section") || this;

    this.slides = Array.from(this.querySelectorAll(".slide"));
    this.timelineItems = Array.from(this.querySelectorAll(".timeline-item"));
    this.timelineDot = this.querySelector(".timeline-dot");
    this.totalSlides = this.slides.length;

    if (this.timelineSection) {
      this.timelineSection.style.height = `${this.sectionHeight}vh`;
    }
  }

  _applyCustomStyles() {
    const timelinePanel = this.querySelector(".timeline-panel");
    const contentPanel  = this.querySelector(".content-panel");

    if (timelinePanel) timelinePanel.style.backgroundColor = this.timelineBg;
    if (contentPanel)  contentPanel.style.backgroundColor = this.contentBg;

    this.querySelectorAll(".source-link").forEach(a => (a.style.color = this.accentColor));

    // CSS custom props
    this.style.setProperty("--timeline-accent-color", this.accentColor);
    this.style.setProperty("--timeline-animation-speed", `${this.animationSpeed}ms`);
    this.style.setProperty("--timeline-date-color", this.dateColor);
    this.style.setProperty("--timeline-text-color", this.textColor);
  }

  _setupObservers() {
    // ResizeObserver to keep windowHeight in sync
    this._resizeObserver = new ResizeObserver(() => this._handleResize());
    this._resizeObserver.observe(document.documentElement);

    // Single IntersectionObserver for:
    // 1) section visibility (activates slide updates)
    // 2) lazy image preloading (inside this component)
    this._io = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        const target = entry.target;

        // Section visibility
        if (target === this.timelineSection) {
          this.isInViewport = entry.isIntersecting;
          if (this.isInViewport) {
            this._updateActiveSlide(this._getCurrentSlideIndex());
          }
          continue;
        }

        // Image preloading
        if (entry.isIntersecting && target.tagName === "IMG") {
          const img = target;
          const src = img.dataset.src;
          if (src) {
            img.src = src;
            img.removeAttribute("data-src");
            img.decoding = "async";
            img.loading = "eager";
          }
          this._io.unobserve(img);
        }
      }
    }, { root: null, rootMargin: "50px", threshold: 0.1 });

    // Observe section
    this._io.observe(this.timelineSection);

    // Observe lazy images within this component
    this.querySelectorAll('img[loading="lazy"]').forEach(img => this._io.observe(img));
  }

  _setupEventListeners() {
    const { signal } = this._abort;

    window.addEventListener("scroll", () => this._handleScroll(), { passive: true, signal });
    window.addEventListener("resize", () => this._handleResize(), { passive: true, signal });

    document.addEventListener("keydown", (e) => this._handleKeydown(e), { signal });

    this.addEventListener("touchstart", (e) => {
      this.touchStartY = e.touches[0].clientY;
    }, { passive: true, signal });

    this.addEventListener("touchend", (e) => {
      this.touchEndY = e.changedTouches[0].clientY;
      this._handleSwipe();
    }, { passive: true, signal });
  }

  // ---------- Measurements ----------
  _updateDimensions() {
    this.windowHeight = window.innerHeight || document.documentElement.clientHeight;
  }

  // More stable than offsetTop math; avoids forced reflow chains.
  _getCurrentSlideIndex() {
    if (!this.isInViewport || this.totalSlides <= 1) return Math.max(0, this.currentSlideIndex);

    const rect = this.timelineSection.getBoundingClientRect();
    const sectionPx = Math.max(1, rect.height - this.windowHeight); // avoid /0
    const progress = this._clamp((0 - rect.top) / sectionPx, 0, 1);  // 0..1
    const idx = Math.round(progress * (this.totalSlides - 1));
    return this._clamp(idx, 0, this.totalSlides - 1);
    // Note: using clamp prevents jitter at edges
  }

  // ---------- Updates ----------
  _updateActiveSlide(slideIndex) {
    if (slideIndex === this.currentSlideIndex) return;

    this.currentSlideIndex = slideIndex;

    // Toggle active classes
    this.slides.forEach(el => el.classList.remove("active"));
    this.timelineItems.forEach(el => el.classList.remove("active"));
    this.timelineDot?.classList.remove("active");

    const activeSlide = this.querySelector(`.slide[data-slide="${slideIndex}"]`);
    const activeItem  = this.querySelector(`.timeline-item[data-slide="${slideIndex}"]`);

    activeSlide?.classList.add("active");
    activeItem?.classList.add("active");
    this.timelineDot?.classList.add("active");

    // Positioning via transforms—batch in a single rAF to avoid multiple layouts
    requestAnimationFrame(() => {
      this.slides.forEach((slide) => {
        const i = parseInt(slide.dataset.slide || "0", 10);
        if (i < slideIndex) {
          slide.style.transform = "translateY(-10%)";
          slide.style.opacity = "0";
        } else if (i === slideIndex) {
          slide.style.transform = "translateY(-1px)";
          slide.style.opacity = "1";
        } else {
          slide.style.transform = "translateY(100%)";
          slide.style.opacity = "0";
        }
      });

      this.timelineItems.forEach((item) => {
        const i = parseInt(item.dataset.slide || "0", 10);
        if (i < slideIndex) {
          item.style.transform = "translateY(100%)";
          item.style.opacity = "0";
        } else if (i === slideIndex) {
          item.style.transform = "translateY(-50%)";
          item.style.opacity = "1";
        } else {
          item.style.transform = "translateY(-100%)";
          item.style.opacity = "0";
        }
      });
    });

    // Notify listeners
    this.dispatchEvent(new CustomEvent("slidechange", {
      detail: { slideIndex, totalSlides: this.totalSlides },
      bubbles: true
    }));
  }

  // ---------- Handlers ----------
  _handleScroll() {
    if (!this.isInViewport) return;
    if (this._raf) return; // throttle via rAF
    
    // Skip scroll-based slide updates if we just made a manual change
    if (this._manualSlideChange) return;

    this._raf = requestAnimationFrame(() => {
      this._raf = null;
      this._updateActiveSlide(this._getCurrentSlideIndex());
    });
  }

  _handleResize() {
    this._updateDimensions();
    this._updateActiveSlide(this._getCurrentSlideIndex());
  }

  _handleKeydown(e) {
    if (!this.isInViewport) return;

    const idx = this.currentSlideIndex;
    switch (e.key) {
      case "ArrowUp":
      case "ArrowLeft":
        e.preventDefault();
        if (idx > 0) this.scrollToSlide(idx - 1);
        break;
      case "ArrowDown":
      case "ArrowRight":
        e.preventDefault();
        if (idx < this.totalSlides - 1) this.scrollToSlide(idx + 1);
        break;
      case " ":
      case "Spacebar":
        e.preventDefault();
        this.scrollToSlide((idx + 1) % this.totalSlides);
        break;
      default:
        break;
    }
  }

  _handleSwipe() {
    const threshold = 50;
    const idx = this.currentSlideIndex;

    if (this.touchEndY < this.touchStartY - threshold && idx < this.totalSlides - 1) {
      this.scrollToSlide(idx + 1);
    } else if (this.touchEndY > this.touchStartY + threshold && idx > 0) {
      this.scrollToSlide(idx - 1);
    }
  }

  // ---------- Scrolling ----------
  scrollToSlide(slideIndex) {
    if (!this.timelineSection || this.totalSlides <= 1) return;

    const rect = this.timelineSection.getBoundingClientRect();
    const sectionTopAbs = window.scrollY + rect.top; // absolute top
    const sectionScrollSpan = Math.max(1, this.timelineSection.scrollHeight - this.windowHeight);

    const ratio = slideIndex / (this.totalSlides - 1);
    const target = sectionTopAbs + sectionScrollSpan * ratio;

    window.scrollTo({ top: target, behavior: "smooth" });
  }

  // ---------- Public API ----------
  goToSlide(i)      { if (i >= 0 && i < this.totalSlides) this.scrollToSlide(i); }
  
  // Method specifically for Theme Editor - immediately updates slide state and scrolls
  goToSlideImmediate(i) {
    if (i >= 0 && i < this.totalSlides) {
      // Set flag to prevent scroll handler interference
      this._manualSlideChange = true;
      
      // Immediately update the slide state
      this._updateActiveSlide(i);
      
      // Then scroll to bring timeline into view
      if (this.timelineSection) {
        const rect = this.timelineSection.getBoundingClientRect();
        const targetScrollTop = window.scrollY + rect.top - 100; // 100px offset from top
        
        window.scrollTo({ 
          top: targetScrollTop, 
          behavior: 'smooth' 
        });
        
        // Clear the flag after scroll animation completes
        setTimeout(() => {
          this._manualSlideChange = false;
        }, 1000); // Give scroll animation time to complete
      } else {
        // Clear flag immediately if no scrolling
        this._manualSlideChange = false;
      }
    }
  }
  
  nextSlide()       { this.goToSlide(Math.min(this.currentSlideIndex + 1, this.totalSlides - 1)); }
  previousSlide()   { this.goToSlide(Math.max(this.currentSlideIndex - 1, 0)); }
  getCurrentSlide() { return this.currentSlideIndex; }
  getTotalSlides()  { return this.totalSlides; }

  // ---------- Utils ----------
  _clamp(n, a, b) { return Math.min(b, Math.max(a, n)); }
}

// Define once
if (!customElements.get("timeline-component")) {
  customElements.define("timeline-component", TimelineComponent);
}