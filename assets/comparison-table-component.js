/**
 * Comparison Table Component
 * Copyright © RoarTheme
 */

// CSS Class Constants
const CSS_CLASSES = {
  // Main containers
  TABLE: 'comparison-table',
  WRAPPER: 'comparison-table-wrapper',
  STICKY_COLUMN: 'comparison-table__sticky-column',
  SCROLLABLE_CONTENT: 'comparison-table__scrollable-content',
  
  // Headers
  CRITERIA_HEADER: 'comparison-table__criteria-header',
  PRODUCTS_HEADER: 'comparison-table__products-header',
  
  // Rows and cells
  CRITERIA: 'comparison-table__criteria',
  DATA_ROW: 'comparison-table__data-row',
  PRODUCT: 'comparison-table__product',
  CELL: 'comparison-table__cell',
  
  // Product elements
  PRODUCT_IMAGE: 'comparison-table__product-image',
  PRODUCT_IMG: 'comparison-table__product-img',
  PRODUCT_TITLE: 'comparison-table__product-title',
  PRODUCT_DESCRIPTION: 'comparison-table__product-description',
  PRODUCT_BUTTON: 'comparison-table__product-button',
  PRODUCT_ICON: 'comparison-table__product-icon',
  PRODUCT_TEXT: 'comparison-table__product-text',
  
  // Criteria elements
  CRITERIA_ICON: 'comparison-table__criteria-icon',
  CRITERIA_NAME: 'comparison-table__criteria-name',
  WARNING_ICON: 'comparison-table__warning-icon',
  CUSTOM_ICON: 'comparison-table__custom-icon',
  
  // Inline criteria
  INLINE_CRITERIA: 'comparison-table__inline-criteria',
  
  // Modifiers
  AUTO_FIT: 'comparison-table--auto-fit',
  SCROLL: 'comparison-table--scroll',
  WITH_CRITERIA: 'comparison-table--with-criteria',
  INLINE_CRITERIA_MODIFIER: 'comparison-table--inline-criteria',
  NO_SHADOW: 'comparison-table--no-shadow',
  PLACEHOLDER: 'comparison-table__product--placeholder'
};

class ComparisonTableComponent extends HTMLElement {
  constructor() {
    super();
    this.resizeTimeout = null;
    this.syncTimeout = null;
    this.observer = null;
    this.isInitialized = false;
  }

  connectedCallback() {
    this.init();
  }

  disconnectedCallback() {
    this.cleanup();
  }

  init() {
    if (this.isInitialized) return;
    
    const table = this.querySelector(`.${CSS_CLASSES.TABLE}`);
    if (!table) return;
    
    this.setupTable(table);
    this.setupResizeListener();
    this.setupMutationObserver();
    this.isInitialized = true;
  }

  setupTable(table) {
    const wrapper = table.closest(`.${CSS_CLASSES.WRAPPER}`);
    if (!wrapper) return;
    
    const productColumns = table.querySelectorAll(`.${CSS_CLASSES.PRODUCT}`);
    if (productColumns.length === 0) return;
    
    table.dataset.productCount = productColumns.length;
    this.updateTableMode(table);
    
    const images = table.querySelectorAll('img');
    images.forEach(img => {
      if (img.complete) return;
      img.addEventListener('load', () => this.syncHeights(table));
      img.addEventListener('error', () => this.syncHeights(table));
    });
  }

  setupResizeListener() {
    const handleResize = () => {
      clearTimeout(this.resizeTimeout);
      this.resizeTimeout = setTimeout(() => {
        const table = this.querySelector(`.${CSS_CLASSES.TABLE}`);
        if (table) this.updateTableMode(table);
      }, 100);
    };

    window.addEventListener('resize', handleResize);
    this.resizeHandler = handleResize;
  }

  setupMutationObserver() {
    this.observer = new MutationObserver((mutations) => {
      let shouldUpdate = false;
      
      mutations.forEach((mutation) => {
        // Only update when product columns or data rows are added/removed/changed
        if (mutation.type === 'childList') {
          const addedNodes = Array.from(mutation.addedNodes);
          const removedNodes = Array.from(mutation.removedNodes);
          
          const hasRelevantChanges = addedNodes.some(node => 
            node.nodeType === Node.ELEMENT_NODE && 
            (node.classList?.contains(CSS_CLASSES.PRODUCT) || 
             node.classList?.contains(CSS_CLASSES.DATA_ROW) ||
             node.querySelector?.(`.${CSS_CLASSES.PRODUCT}`) ||
             node.querySelector?.(`.${CSS_CLASSES.DATA_ROW}`))
          ) || removedNodes.some(node => 
            node.nodeType === Node.ELEMENT_NODE && 
            (node.classList?.contains(CSS_CLASSES.PRODUCT) || 
             node.classList?.contains(CSS_CLASSES.DATA_ROW) ||
             node.querySelector?.(`.${CSS_CLASSES.PRODUCT}`) ||
             node.querySelector?.(`.${CSS_CLASSES.DATA_ROW}`))
          );
          
          if (hasRelevantChanges) {
            shouldUpdate = true;
          }
        }
      });
      
      if (shouldUpdate) {
        clearTimeout(this.syncTimeout);
        this.syncTimeout = setTimeout(() => {
          const table = this.querySelector(`.${CSS_CLASSES.TABLE}`);
          if (table) {
            this.updateTableMode(table);
          }
        }, 150);
      }
    });

    this.observer.observe(this, {
      childList: true,
      subtree: true
    });
  }

  updateTableMode(table) {
    const wrapper = table.closest(`.${CSS_CLASSES.WRAPPER}`);
    if (!wrapper) return;
    
    const productCount = parseInt(table.dataset.productCount) || 0;
    if (productCount === 0) return;
    
    const stickyColumn = table.querySelector(`.${CSS_CLASSES.STICKY_COLUMN}`);
    const scrollableContent = table.querySelector(`.${CSS_CLASSES.SCROLLABLE_CONTENT}`);
    if (!scrollableContent) return;
    
    const wrapperWidth = wrapper.offsetWidth;
    let availableWidth;
    
    if (stickyColumn) {
      const stickyWidth = stickyColumn.offsetWidth;
      availableWidth = wrapperWidth - stickyWidth - 2;
    } else {
      availableWidth = wrapperWidth;
    }
    
    let columnWidth;
    if (window.innerWidth <= 480) {
      columnWidth = 120;
    } else if (window.innerWidth <= 768) {
      columnWidth = 150;
    } else {
      columnWidth = 200;
    }
    
    const requiredWidth = productCount * columnWidth;
    const minColumnWidth = window.innerWidth <= 480 ? 100 : (window.innerWidth <= 768 ? 120 : 150);
    const shouldAutoFit = (requiredWidth <= availableWidth) && (availableWidth / productCount >= minColumnWidth);
    
    table.classList.remove(CSS_CLASSES.AUTO_FIT, CSS_CLASSES.SCROLL);
    
    if (shouldAutoFit) {
      table.classList.add(CSS_CLASSES.AUTO_FIT);
      scrollableContent.style.overflowX = 'visible';
      
      const equalColumnWidth = Math.ceil(availableWidth / productCount);
      const productColumns = table.querySelectorAll(`.${CSS_CLASSES.PRODUCT}`);
      const dataCells = table.querySelectorAll(`.${CSS_CLASSES.CELL}`);
      
      productColumns.forEach(column => {
        column.style.minWidth = `${equalColumnWidth}px`;
        column.style.width = `${equalColumnWidth}px`;
      });
      
      dataCells.forEach(cell => {
        cell.style.minWidth = `${equalColumnWidth}px`;
        cell.style.width = `${equalColumnWidth}px`;
      });
    } else {
      table.classList.add(CSS_CLASSES.SCROLL);
      scrollableContent.style.overflowX = 'auto';
      
      const productColumns = table.querySelectorAll(`.${CSS_CLASSES.PRODUCT}`);
      const dataCells = table.querySelectorAll(`.${CSS_CLASSES.CELL}`);
      
      productColumns.forEach(column => {
        column.style.minWidth = '';
        column.style.width = '';
      });
      
      dataCells.forEach(cell => {
        cell.style.minWidth = '';
        cell.style.width = '';
      });
    }
    
    this.syncHeights(table);
  }

  syncHeights(table) {
    const criteriaHeader = table.querySelector(`.${CSS_CLASSES.CRITERIA_HEADER}`);
    const productsHeader = table.querySelector(`.${CSS_CLASSES.PRODUCTS_HEADER}`);
    const criteriaRows = table.querySelectorAll(`.${CSS_CLASSES.CRITERIA}`);
    const dataRows = table.querySelectorAll(`.${CSS_CLASSES.DATA_ROW}`);
    
    // Sync heights only when necessary to avoid layout shift
    const needsSync = this.checkIfHeightsNeedSync(criteriaHeader, productsHeader, criteriaRows, dataRows);
    if (!needsSync) return;
    
    // Use a short CSS transition for smoother visual change
    const elements = [criteriaHeader, productsHeader, ...criteriaRows, ...dataRows].filter(Boolean);
    elements.forEach(el => {
      el.style.transition = 'height 0.2s ease-out';
    });
    
    requestAnimationFrame(() => {
      if (criteriaHeader && productsHeader) {
        const headerHeight = Math.max(criteriaHeader.offsetHeight, productsHeader.offsetHeight);
        criteriaHeader.style.height = headerHeight + 'px';
        productsHeader.style.height = headerHeight + 'px';
      }
      
      requestAnimationFrame(() => {
        const rowCount = Math.min(criteriaRows.length, dataRows.length);
        for (let i = 0; i < rowCount; i++) {
          const crit = criteriaRows[i];
          const row = dataRows[i];
          const maxH = Math.max(crit.offsetHeight, row.offsetHeight);
          crit.style.height = maxH + 'px';
          row.style.height = maxH + 'px';
        }
        
        // Remove transition after completion
        setTimeout(() => {
          elements.forEach(el => {
            el.style.transition = '';
          });
        }, 200);
      });
    });
  }
  
  checkIfHeightsNeedSync(criteriaHeader, productsHeader, criteriaRows, dataRows) {
    // Determine whether heights need to be synchronized
    if (criteriaHeader && productsHeader) {
      const heightDiff = Math.abs(criteriaHeader.offsetHeight - productsHeader.offsetHeight);
      if (heightDiff > 5) return true; // Only sync if the difference is greater than 5px
    }
    
    const rowCount = Math.min(criteriaRows.length, dataRows.length);
    for (let i = 0; i < rowCount; i++) {
      const crit = criteriaRows[i];
      const row = dataRows[i];
      const heightDiff = Math.abs(crit.offsetHeight - row.offsetHeight);
      if (heightDiff > 5) return true;
    }
    
    return false;
  }

  cleanup() {
    if (this.resizeHandler) {
      window.removeEventListener('resize', this.resizeHandler);
    }
    
    if (this.observer) {
      this.observer.disconnect();
    }
    
    if (this.resizeTimeout) {
      clearTimeout(this.resizeTimeout);
    }
    
    if (this.syncTimeout) {
      clearTimeout(this.syncTimeout);
    }
    
    this.isInitialized = false;
  }

  // Public API methods for dynamic updates
  refresh() {
    const table = this.querySelector(`.${CSS_CLASSES.TABLE}`);
    if (table) {
      this.setupTable(table);
    }
  }

  updateProductCount() {
    const table = this.querySelector(`.${CSS_CLASSES.TABLE}`);
    if (table) {
      const productColumns = table.querySelectorAll(`.${CSS_CLASSES.PRODUCT}`);
      table.dataset.productCount = productColumns.length;
      this.updateTableMode(table);
    }
  }

  // Method to handle dynamic content changes
  handleContentChange() {
    this.refresh();
  }
}

// Register the custom element
if (!customElements.get("comparison-table-component")) {
  customElements.define("comparison-table-component", ComparisonTableComponent);
}
