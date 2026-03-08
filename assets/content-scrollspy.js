/**
 * Content ScrollSpy Web Component
 * Handles scroll-based navigation and animations for content detail sections
 * 
 * @author RoarTheme - https://roartheme.co/
 */

// Prevent duplicate class declaration
if (typeof window.ContentScrollSpy === 'undefined') {

window.ContentScrollSpy = class ContentScrollSpy extends HTMLElement {
  // Selectors and class names constants
  static SELECTORS = {
    MENU: '[data-scrollspy-menu]',
    MENU_ITEM_LINK: '[data-scrollspy-link]',
    SCROLL_INDICATOR: '.content-scrollspy__scroll-indicator',
    POSSIBLE_HEADERS: ['header', '.header', '.sticky-header', '.fixed-header']
  };

  static CLASSES = {
    MENU_HIDDEN: 'content-scrollspy__menu--hidden',
    MENU_ITEM: 'content-scrollspy__menu-item',
    VISIBLE: 'visible',
    ACTIVE: 'active'
  };

  constructor() {
    super();
    this.sections = [];
    this.menuItems = [];
    this.observer = null;
    this.currentActive = null;
    this.isInitialized = false;
    this.settings = {
      threshold: 0.6,
      rootMargin: '-10% 0px -10% 0px',
      animationThreshold: 0.6,
      headingSelector: ''
    };
    
    this.cachedElements = new Map();
    
    this.boundScrollHandler = this.handleScroll.bind(this);
    this.boundResizeHandler = this.handleResize.bind(this);
    
    this.scrollTicking = false;
    this.resizeTicking = false;
    this.lastScrollY = 0;
    this.scrollDirection = null;
  }

  init() {
    // Clear any cached elements from previous init
    this.cachedElements.clear();
    
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.setup());
    } else {
      // Use requestAnimationFrame to ensure DOM is fully ready
      requestAnimationFrame(() => this.setup());
    }
  }

  setup() {
    if (this.isInitialized) return;
    this.loadSettings();
    this.detectHeadings();

    if (this.sections.length === 0) {
      return;
    }

    this.initScrollSpy();
    this.initMenuBehavior();
    this.initAnimations();
    this.isInitialized = true;
    
    this.dispatchEvent('scrollspy:ready');
  }

  getCachedElement(selector) {
    if (!this.cachedElements.has(selector)) {
      const element = this.querySelector(selector);
      this.cachedElements.set(selector, element);
    }
    return this.cachedElements.get(selector);
  }

  loadSettings() {
    const { dataset } = this;
    const enableAnimations = dataset.enableAnimations !== 'false';
    const animationThreshold = parseFloat(dataset.animationThreshold) || 0.6;
    const headingSelector = dataset.headingSelector;
    const hideOnScrollUp = dataset.hideOnScrollUp === 'true';
    const showScrollIndicator = dataset.showScrollIndicator === 'true';
    const explicitThreshold = dataset.threshold ? parseFloat(dataset.threshold) : undefined;
    const contentScope = dataset.contentScope; // Selector for the container to scan headings

    this.settings = {
      ...this.settings,
      enableAnimations,
      animationThreshold,
      headingSelector,
      hideOnScrollUp,
      showScrollIndicator,
      contentScope,
      // If a dedicated data-threshold is provided, use it; otherwise map animationThreshold
      threshold: Number.isFinite(explicitThreshold) ? explicitThreshold : animationThreshold
    };

    // Always query menu fresh (don't use cache here as it might be stale)
    const menu = this.querySelector(ContentScrollSpy.SELECTORS.MENU);
    if (menu) {
      menu.classList.add(ContentScrollSpy.CLASSES.MENU_HIDDEN);
    }
  }

  detectHeadings() {
    const { headingSelector, contentScope } = this.settings;
    if (!headingSelector) return;
    
    const selectors = headingSelector.split(',')
      .map(s => s.trim())
      .filter(Boolean);
    
    if (selectors.length === 0) return;
    
    const combinedSelector = selectors.join(', ');
    
    // Determine the scope to query headings from
    let scopeElement = this.getScopeElement(contentScope);
    
    const headingsNodeList = scopeElement.querySelectorAll(combinedSelector);
    
    const headings = [...new Set(headingsNodeList)];
    
    headings.sort((a, b) => {
      const position = a.compareDocumentPosition(b);
      return position & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1;
    });
    
    // Filter to headings with actual (non-whitespace) text content
    const filteredHeadings = headings.filter(h => (h.textContent || '').trim().length > 0);
    if (filteredHeadings.length === 0) return;

    this.generateMenuItems(filteredHeadings);
    
    this.ensureHeadingIds(filteredHeadings);
    
    this.setupScrollHandling();
  }

  getScopeElement(contentScope) {
    // 1. If explicit scope is provided, use it
    if (contentScope) {
      // Try to find a specific element by selector
      const customScope = document.querySelector(contentScope);
      if (customScope) {
        return customScope;
      }
      // Try finding closest parent matching the scope
      const closestScope = this.closest(contentScope);
      if (closestScope) {
        return closestScope;
      }
    }
    
    // 2. Try to find the closest main
    const parentSection = this.closest('main');
    if (parentSection) {
      return parentSection;
    }
    
    // 3. Fallback to the component itself (most restrictive)
    return this;
  }

  generateMenuItems(headings) {
    const menu = this.getCachedElement(ContentScrollSpy.SELECTORS.MENU);
    if (!menu) return;

    const fragment = document.createDocumentFragment();
    
    this.menuItems = new Array(headings.length);

    headings.forEach((heading, index) => {
      const menuItem = document.createElement('a');
      const headingId = heading.id || `scrollspy-heading-${index}`;
      
      menuItem.href = `#${headingId}`;
      menuItem.className = ContentScrollSpy.CLASSES.MENU_ITEM;
      menuItem.setAttribute('data-scrollspy-link', '');
      menuItem.textContent = heading.textContent.trim();
      
      fragment.appendChild(menuItem);
      this.menuItems[index] = menuItem;
    });


    menu.innerHTML = '';
    menu.appendChild(fragment);
  }

  hasOnlyDirectTextContent(element) {
    // Check if element has any child elements
    if (element.children.length > 0) {
      return false;
    }
    
    // Check if element has only text nodes (no other node types)
    const childNodes = element.childNodes;
    for (let i = 0; i < childNodes.length; i++) {
      const node = childNodes[i];
      // Allow only text nodes (nodeType 3) and comment nodes (nodeType 8)
      if (node.nodeType !== 3 && node.nodeType !== 8) {
        return false;
      }
    }
    
    // Check if there's actual text content (not just whitespace)
    const textContent = element.textContent.trim();
    return textContent.length > 0;
  }

  ensureHeadingIds(headings) {
    headings.forEach((heading, index) => {
      if (!heading.id) {
        heading.id = `scrollspy-heading-${index}`;
      }
    });


    this.sections = headings;
  }

  setupScrollHandling() {
    if (this.sections.length === 0) return;

    // Query menu and scroll indicator fresh (important for AJAX reloads)
    this.menu = this.querySelector(ContentScrollSpy.SELECTORS.MENU);
    this.scrollIndicator = this.querySelector(ContentScrollSpy.SELECTORS.SCROLL_INDICATOR);
    this.firstSection = this.sections[0];
    this.lastScrollY = window.scrollY;
    
    // Remove existing listeners before adding new ones to prevent duplicates
    window.removeEventListener('scroll', this.boundScrollHandler);
    window.removeEventListener('resize', this.boundResizeHandler);
    
    window.addEventListener('scroll', this.boundScrollHandler, { passive: true });
    window.addEventListener('resize', this.boundResizeHandler, { passive: true });
    
    this.handleScroll();
  }

  handleScroll() {
    if (this.scrollTicking) return;
    
    this.scrollTicking = true;
    requestAnimationFrame(() => {
      this.updateScrollState();
      this.scrollTicking = false;
    });
  }

  handleResize() {
    if (this.resizeTicking) return;
    
    this.resizeTicking = true;
    requestAnimationFrame(() => {
      this.updateScrollIndicator();
      this.resizeTicking = false;
    });
  }

  updateScrollState() {
    const currentScrollY = window.scrollY;
    
    if (currentScrollY > this.lastScrollY) {
      this.scrollDirection = 'down';
    } else if (currentScrollY < this.lastScrollY) {
      this.scrollDirection = 'up';
    }
    
    this.updateFixedMenu(currentScrollY);
    
    this.updateScrollIndicator();
    
    // Always prefer the section nearest to the top of the viewport when multiple are visible
    const topMostIndex = this.getTopMostVisibleSectionIndex();
    if (topMostIndex !== null && topMostIndex !== undefined) {
      this.setActiveSection(topMostIndex);
    } else if (!this.observer) {
      // Fallback legacy behavior when IO is not available
      this.updateActiveSectionFallback(currentScrollY);
    }
    
    this.lastScrollY = currentScrollY;
  }

  updateFixedMenu(currentScrollY) {
    // Re-check menu element if it's not available (may happen after AJAX reload)
    if (!this.menu) {
      this.menu = this.querySelector(ContentScrollSpy.SELECTORS.MENU);
      if (!this.menu) return;
    }
    
    if (!this.firstSection) return;

    const rect = this.firstSection.getBoundingClientRect();
    const isFirstSectionPassed = rect.top < 0;
    const { hideOnScrollUp } = this.settings;

    if (isFirstSectionPassed) {
      if (hideOnScrollUp && this.scrollDirection === 'up') {
        this.menu.classList.add(ContentScrollSpy.CLASSES.MENU_HIDDEN);
      } else if (!hideOnScrollUp || this.scrollDirection === 'down' || this.scrollDirection === null) {
        this.menu.classList.remove(ContentScrollSpy.CLASSES.MENU_HIDDEN);
      }
    } else {
      this.menu.classList.add(ContentScrollSpy.CLASSES.MENU_HIDDEN);
    }
  }

  initScrollSpy() {
    if ('IntersectionObserver' in window) {
      this.initIntersectionObserver();
    } else {
      this.initScrollFallback();
    }
  }

  initIntersectionObserver() {
    this.observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          this.handleSectionIntersection(entry);
        });
      },
      {
        threshold: this.settings.threshold,
        rootMargin: this.settings.rootMargin
      }
    );

    this.sections.forEach(section => {
      this.observer.observe(section);
    });
  }

  initScrollFallback() {
    this.useScrollFallback = true;
  }

  updateActiveSectionFallback(scrollTop) {
    if (!this.useScrollFallback) return;
    
    const windowHeight = window.innerHeight;
    const threshold = this.settings.threshold;
    
    for (let i = 0; i < this.sections.length; i++) {
      const section = this.sections[i];
      const rect = section.getBoundingClientRect();
      const sectionTop = rect.top + scrollTop;
      const sectionBottom = sectionTop + rect.height;
      
      if (scrollTop >= sectionTop - windowHeight * threshold && 
          scrollTop < sectionBottom - windowHeight * threshold) {
        this.setActiveSection(i);
        break;
      }
    }
  }

  handleSectionIntersection(entry) {
    if (entry.isIntersecting) {
      const sectionIndex = this.sections.indexOf(entry.target);
      if (sectionIndex !== -1) {
        // Defer to scroll tick which selects the top-most visible section
        if (!CSS.supports('view-timeline-name', '--scroll')) {
          entry.target.classList.add(ContentScrollSpy.CLASSES.VISIBLE);
        }
      }
    }
  }

  setActiveSection(index) {
    if (this.currentActive === index) return;
    
    this.menuItems.forEach(item => item.classList.remove(ContentScrollSpy.CLASSES.ACTIVE));
    
    if (this.menuItems[index]) {
      this.menuItems[index].classList.add(ContentScrollSpy.CLASSES.ACTIVE);
      this.currentActive = index;
      
      const menuItem = this.menuItems[index];
      const targetId = menuItem.getAttribute('href').substring(1);
      const targetElement = document.getElementById(targetId);
      
      this.dispatchEvent('scrollspy:section-changed', {
        sectionIndex: index,
        sectionId: targetId,
        sectionElement: targetElement
      });
    }
  }

  initMenuBehavior() {
    this.menuItems.forEach((item, index) => {
      item.addEventListener('click', (e) => {
        e.preventDefault();
        this.scrollToSection(index);
      });
      
      item.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          this.scrollToSection(index);
        }
      });
    });
  }

  scrollToSection(index) {
    if (!this.menuItems[index]) return;
    
    const menuItem = this.menuItems[index];
    const targetId = menuItem.getAttribute('href').substring(1);
    const targetElement = document.getElementById(targetId);
    
    if (!targetElement) return;
    
    const offsets = this.calculateScrollOffsets();
    const targetRect = targetElement.getBoundingClientRect();
    const currentScrollTop = window.scrollY;
    const targetTop = currentScrollTop + targetRect.top;
    
    const finalScrollTop = Math.max(0, targetTop - offsets.total - 20);
    
    window.scrollTo({
      top: finalScrollTop,
      behavior: 'smooth'
    });
    
    this.dispatchEvent('scrollspy:section-clicked', {
      sectionIndex: index,
      sectionId: targetId,
      sectionElement: targetElement
    });
  }

  calculateScrollOffsets() {
    if (!this.cachedOffsets || this.offsetsCacheTime < Date.now() - 1000) {
      const menuHeight = this.getMenuHeight();
      
      let additionalOffset = 0;
      
      for (const selector of ContentScrollSpy.SELECTORS.POSSIBLE_HEADERS) {
        const element = document.querySelector(selector);
        if (element) {
          const style = getComputedStyle(element);
          if (style.position === 'fixed' || style.position === 'sticky') {
            const rect = element.getBoundingClientRect();
            if (rect.top <= 0 && rect.height > 0) {
              additionalOffset = Math.max(additionalOffset, rect.height);
            }
          }
        }
      }
      
      this.cachedOffsets = {
        menu: menuHeight,
        additional: additionalOffset,
        total: menuHeight + additionalOffset
      };
      this.offsetsCacheTime = Date.now();
    }
    
    return this.cachedOffsets;
  }

  getMenuHeight() {
    // Re-query menu if not available
    if (!this.menu) {
      this.menu = this.querySelector(ContentScrollSpy.SELECTORS.MENU);
      if (!this.menu) return 0;
    }
    
    const isVisible = !this.menu.classList.contains(ContentScrollSpy.CLASSES.MENU_HIDDEN);
    
    if (!isVisible) {
      // Fallback to configured CSS variable when hidden
      const cssVar = getComputedStyle(this).getPropertyValue('--menu-height').trim();
      const parsed = parseFloat(cssVar);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
      return 0;
    }
    
    if (!this.cachedMenuHeight || this.menuHeightCacheTime < Date.now() - 500) {
      const rect = this.menu.getBoundingClientRect();
      this.cachedMenuHeight = rect.height;
      this.menuHeightCacheTime = Date.now();
    }
    
    return this.cachedMenuHeight;
  }

  getTopMostVisibleSectionIndex() {
    if (!this.sections || this.sections.length === 0) return null;
    const viewportHeight = window.innerHeight;
    let bestIndex = null;
    let bestTop = Number.POSITIVE_INFINITY;
    let bestNegativeTop = -Number.POSITIVE_INFINITY;
    let bestNegativeIndex = null;
    
    for (let i = 0; i < this.sections.length; i++) {
      const rect = this.sections[i].getBoundingClientRect();
      const isVisible = rect.bottom > 0 && rect.top < viewportHeight;
      if (!isVisible) continue;
      // Prefer the section whose top is closest to the top of the viewport (>= 0)
      if (rect.top >= 0 && rect.top < bestTop) {
        bestTop = rect.top;
        bestIndex = i;
      }
      // If none are with top >= 0 (all above), choose the one closest above (max negative top)
      if (rect.top < 0 && rect.top > bestNegativeTop) {
        bestNegativeTop = rect.top;
        bestNegativeIndex = i;
      }
    }
    if (bestIndex !== null) return bestIndex;
    if (bestNegativeIndex !== null) return bestNegativeIndex;
    return null;
  }

  initAnimations() {
    if (!this.settings.enableAnimations) return;
    
    // Initialize animations for sections that are already visible
    this.sections.forEach(section => {
      const rect = section.getBoundingClientRect();
      const isVisible = rect.top < window.innerHeight && rect.bottom > 0;
      
      if (isVisible && !CSS.supports('view-timeline-name', '--scroll')) {
        section.classList.add(ContentScrollSpy.CLASSES.VISIBLE);
      }
    });
  }

  updateScrollIndicator() {
    // Re-query scroll indicator if not available
    if (!this.scrollIndicator) {
      this.scrollIndicator = this.querySelector(ContentScrollSpy.SELECTORS.SCROLL_INDICATOR);
      if (!this.scrollIndicator) return;
    }
    
    const scrollTop = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    
    if (docHeight > 0) {
      const percent = (scrollTop / docHeight) * 100;
      this.scrollIndicator.style.width = `${percent}%`;
    }
  }

  goToSection(index) {
    if (index >= 0 && index < this.sections.length) {
      this.scrollToSection(index);
    }
  }

  getCurrentSection() {
    return this.currentActive;
  }

  getSections() {
    return this.sections;
  }

  getMenuItems() {
    return this.menuItems;
  }

  destroy() {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
    
    window.removeEventListener('scroll', this.boundScrollHandler);
    window.removeEventListener('resize', this.boundResizeHandler);
    
    this.cachedElements.clear();
    this.menu = null;
    this.scrollIndicator = null;
    this.firstSection = null;
    this.cachedOffsets = null;
    this.cachedMenuHeight = null;
    
    this.sections = [];
    this.menuItems = [];
    this.currentActive = null;
    this.isInitialized = false;
    this.useScrollFallback = false;
    
    this.scrollTicking = false;
    this.resizeTicking = false;
    this.lastScrollY = 0;
    this.scrollDirection = null;
  }

  dispatchEvent(eventName, detail = {}) {
    const event = new CustomEvent(eventName, {
      detail: {
        scrollspy: this,
        ...detail
      }
    });
    document.dispatchEvent(event);
  }

  refresh() {
    this.destroy();
    this.init();
  }

  connectedCallback() {
    this.init();
  }

  disconnectedCallback() {
    this.destroy();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue !== newValue) {
      this.refresh();
    }
  }

  static get observedAttributes() {
    return [
      'data-enable-animations',
      'data-animation-threshold',
      'data-heading-selector',
      'data-hide-on-scroll-up',
      'data-show-scroll-indicator',
      'data-threshold',
      'data-content-scope'
    ];
  }
};

} // End of ContentScrollSpy class definition guard

// Only define the custom element if it hasn't been defined yet
if (!customElements.get('content-scrollspy')) {
  customElements.define('content-scrollspy', window.ContentScrollSpy);
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = window.ContentScrollSpy;
} 