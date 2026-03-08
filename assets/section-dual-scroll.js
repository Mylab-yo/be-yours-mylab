if (!customElements.get('dual-scroll-component')) {
  // Helper function: Parse hex color to RGB (outside class for performance)
  const hexToRgb = (hex) => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : null;
  };

  class DualScrollComponent extends HTMLDivElement {
    constructor() {
      super();
      this.currentActiveKey = null;
      this.currentActiveImage = null;
      this.ticking = false;
      this.cachedRotation = null;
      this.cachedScale = null;
      this.onScroll = this.onScroll.bind(this);
      this.onResize = this.onResize.bind(this);
      this.updateMediaWithScrollProgress = this.updateMediaWithScrollProgress.bind(this);
    }

    connectedCallback() {
      // Initialize only once
      if (this.initialized) return;
      this.initialized = true;

      this.panels = Array.from(this.querySelectorAll('.dual-scroll-panel'));
      this.mediaViewport = this.querySelector('.dual-scroll-media-viewport');
      this.mediaImages = Array.from(this.querySelectorAll('.dual-scroll-media-image'));
      this.keyToImage = new Map(
        this.mediaImages.map((img) => [img.getAttribute('data-key'), img])
      );
      
      // Cache CSS variables for performance
      this.cacheMediaStyles();

      // Set initial background color for first panel
      if (this.mediaViewport && this.panels.length > 0) {
        const firstPanel = this.panels[0];
        const initialBgColor = firstPanel.getAttribute('data-media-bg-color');
        if (initialBgColor) {
          this.mediaViewport.style.backgroundColor = initialBgColor;
        }
      }

      this.setupScrollListeners();
      window.addEventListener('resize', this.onResize, { passive: true });
      
      // Delay initial update to ensure scroll position is restored after page reload
      // Chrome/Safari restore scroll position before JavaScript runs
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          this.updateMediaWithScrollProgress();
        });
      });
      
      this.setupMobileAnimations();
    }

    disconnectedCallback() {
      // Cleanup when component is removed
      this.cleanup();
    }

    cleanup() {
      window.removeEventListener('scroll', this.onScroll);
      window.removeEventListener('resize', this.onResize);
      
      if (this.mobileObserver) {
        this.mobileObserver.disconnect();
        this.mobileObserver = null;
      }

      this.initialized = false;
      this.currentActiveKey = null;
      this.currentActiveImage = null;
      this.cachedRotation = null;
      this.cachedScale = null;
    }
    
    cacheMediaStyles() {
      // Cache CSS variables to avoid repeated getComputedStyle calls
      const styles = getComputedStyle(this);
      this.cachedRotation = styles.getPropertyValue('--media-rotation').trim() || '-6deg';
      this.cachedScale = styles.getPropertyValue('--media-scale').trim() || '1.02';
    }
    
    setupMobileAnimations() {
      const isMobile = window.innerWidth <= 860;
      if (!isMobile) return;
      
      // Use IntersectionObserver to trigger animation when panel has scrolled 30% past bottom of viewport
      if ('IntersectionObserver' in window) {
        this.mobileObserver = new IntersectionObserver((entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add('is-in-view');
            }
          });
        }, {
          rootMargin: '0px 0px -30% 0px', // Trigger when panel has scrolled 30% past bottom of viewport
          threshold: 0
        });
        
        this.panels.forEach((panel) => {
          this.mobileObserver.observe(panel);
          // Check if panel is already scrolled past 30% on initial load
          const rect = panel.getBoundingClientRect();
          const viewportHeight = window.innerHeight;
          const scrollPastBottom = viewportHeight - rect.top;
          const triggerPoint = viewportHeight * 0.3;
          if (scrollPastBottom >= triggerPoint && rect.bottom > 0) {
            panel.classList.add('is-in-view');
          }
        });
      }
    }

    updateMediaWithScrollProgress() {
      const isMobile = window.innerWidth <= 860;
      
      // On mobile, no animation needed - images are already in their panels
      if (isMobile) {
        return;
      }

      let activePanel = null;
      let nextPanel = null;
      let progress = 0;

      for (let i = 0; i < this.panels.length; i++) {
        const panel = this.panels[i];
        const rect = panel.getBoundingClientRect();
        const panelTop = rect.top;
        const panelBottom = rect.bottom;

        if (panelTop <= 0 && panelBottom > 0) {
          activePanel = panel;
          nextPanel = this.panels[i + 1] || null;
          progress = Math.max(0, Math.min(1, -panelTop / rect.height));
          break;
        } else if (panelTop > 0) {
          activePanel = panel;
          nextPanel = this.panels[i + 1] || null;
          // Calculate negative progress when panel is above viewport
          progress = -Math.min(1, panelTop / rect.height);
          break;
        }
      }

      if (!activePanel && this.panels.length > 0) {
        activePanel = this.panels[this.panels.length - 1];
        progress = 1;
      }

      if (!activePanel) return;

      // Fade background color from 30% viewport
      if (this.mediaViewport) {
        const bgColor = activePanel.getAttribute('data-media-bg-color');
        const nextBgColor = nextPanel ? nextPanel.getAttribute('data-media-bg-color') : null;
        
        if (nextPanel && nextBgColor && progress >= 0.3) {
          const fadeProgress = Math.max(0, Math.min(1, (progress - 0.3) / 0.7)); // 0.3-1 range
          const currentRgb = hexToRgb(bgColor);
          const nextRgb = hexToRgb(nextBgColor);
          
          if (currentRgb && nextRgb) {
            // Interpolate between colors
            const r = Math.round(currentRgb.r + (nextRgb.r - currentRgb.r) * fadeProgress);
            const g = Math.round(currentRgb.g + (nextRgb.g - currentRgb.g) * fadeProgress);
            const b = Math.round(currentRgb.b + (nextRgb.b - currentRgb.b) * fadeProgress);
            this.mediaViewport.style.backgroundColor = `rgb(${r}, ${g}, ${b})`;
          }
        } else if (bgColor) {
          // Before 30% or no next panel: use current color
          this.mediaViewport.style.backgroundColor = bgColor;
        }
      }

      const activeKey = activePanel.getAttribute('data-key');
      const nextKey = nextPanel ? nextPanel.getAttribute('data-key') : null;
      const transitionType = this.getAttribute('data-transition-type') || 'fade';
      const rotation = this.cachedRotation;
      const scale = this.cachedScale;

      if (activeKey !== this.currentActiveKey) {
        // Previous image is becoming inactive
        if (this.currentActiveImage) {
          this.currentActiveImage.classList.remove('is-active', 'is-transitioning');
          if (transitionType === 'scroll') {
            // Scroll down when becoming inactive
            this.currentActiveImage.style.transform = `translateY(100%) rotate(${rotation}) scale(${scale})`;
          }
        }
        this.currentActiveKey = activeKey;
        this.currentActiveImage = this.keyToImage.get(activeKey);
        if (this.currentActiveImage) {
          this.currentActiveImage.classList.add('is-active');
        }
      }

      // Different threshold for different transition types
      const threshold = transitionType === 'scroll' ? 0 : 0.3;
      
      if (nextKey && progress > threshold) {
        const nextImage = this.keyToImage.get(nextKey);
        if (nextImage && this.currentActiveImage) {
          const transitionProgress = transitionType === 'scroll' 
            ? Math.max(0, Math.min(1, progress / 1.0))  // Full range 0-1 for scroll
            : Math.max(0, Math.min(1, (progress - 0.3) / 0.7));  // 0.3-1 range for fade
          
          if (transitionType === 'fade') {
            // Fade transition: current image fades out, next image fades in from top
            const pullDistance = (1 - transitionProgress) * 100;
            
            // Current image fades out
            this.currentActiveImage.style.transform = `translateY(0) rotate(${rotation}) scale(${scale})`;
            this.currentActiveImage.style.opacity = 1 - transitionProgress;
            
            // Next image fades in and moves down
            nextImage.style.transform = `translateY(-${pullDistance}%) rotate(${rotation}) scale(${scale})`;
            nextImage.style.opacity = transitionProgress;
            nextImage.classList.add('is-transitioning');
          } else if (transitionType === 'scroll') {
            // Scroll transition: current image scrolls down, next image comes from top
            const scrollDownDistance = transitionProgress * 100;
            this.currentActiveImage.style.transform = `translateY(${scrollDownDistance}%) rotate(${rotation}) scale(${scale})`;
            const pullUpDistance = (1 - transitionProgress) * 100;
            nextImage.style.transform = `translateY(-${pullUpDistance}%) rotate(${rotation}) scale(${scale})`;
            nextImage.classList.add('is-transitioning');
          }
        }
      } else if (this.currentActiveImage) {
        // Reset non-active images
        const resetTransform = `translateY(-100%) rotate(${rotation}) scale(${scale})`;
        for (const img of this.mediaImages) {
          if (img !== this.currentActiveImage) {
            img.classList.remove('is-transitioning');
            img.style.transform = resetTransform;
            if (transitionType === 'fade') {
              img.style.opacity = '0';
            }
          }
        }
        this.currentActiveImage.style.transform = `translateY(0) rotate(${rotation}) scale(${scale})`;
        if (transitionType === 'fade') {
          this.currentActiveImage.style.opacity = '1';
        }
      }
    }

    onScroll() {
      if (!this.ticking) {
        this.ticking = true;
        requestAnimationFrame(() => {
          this.updateMediaWithScrollProgress();
          this.ticking = false;
        });
      }
    }

    setupScrollListeners() {
      // Remove existing listeners before adding new ones
      window.removeEventListener('scroll', this.onScroll);

      const isMobile = window.innerWidth <= 860;
      // On mobile, no scroll listeners needed - simple layout
      if (!isMobile) {
        window.addEventListener('scroll', this.onScroll, { passive: true });
      }
    }

    onResize() {
      // Cleanup mobile observer if exists
      if (this.mobileObserver) {
        this.mobileObserver.disconnect();
        this.mobileObserver = null;
      }
      
      // Recache media styles on resize
      this.cacheMediaStyles();
      
      this.setupScrollListeners();
      this.setupMobileAnimations();
      this.onScroll();
    }
  }

  customElements.define('dual-scroll-component', DualScrollComponent, { extends: 'div' });
}

