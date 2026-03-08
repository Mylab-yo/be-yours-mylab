class CartRemoveButton extends HTMLElement {
  constructor() {
    super();

    this.addEventListener('click', (event) => {
      event.preventDefault();
      this.closest('cart-items').updateQuantity(this.dataset.index, 0);
    });
  }
}
customElements.define('cart-remove-button', CartRemoveButton);
if (!customElements.get('cart-items')) {
  customElements.define('cart-items', class CartItems extends HTMLElement {
    cartUpdateUnsubscriber = undefined;
    
    constructor() {
      super();

      this.lineItemStatusElement = document.getElementById('shopping-cart-line-item-status');
      this.cartErrors = document.getElementById('cart-errors');

      this.currentItemCount = Array.from(this.querySelectorAll('[name="updates[]"]'))
        .reduce((total, quantityInput) => total + parseInt(quantityInput.value), 0);

      this.debouncedOnChange = debounce((event) => {
        this.onChange(event);
      }, 300);

      this.addEventListener('change', this.debouncedOnChange.bind(this));
      this.cartUpdateUnsubscriber = subscribe(PUB_SUB_EVENTS.cartUpdate, this.onCartUpdate.bind(this));
    }

    disconnectedCallback() {
      if (this.cartUpdateUnsubscriber) {
        this.cartUpdateUnsubscriber();
      }
    }

    onCartUpdate(event) {
      const sections = event.sections; 
      const parsedState = event.cart; 
      
      this.classList.toggle('is-empty', parsedState.item_count === 0);
      const cartFooter = document.getElementById('main-cart-footer');

      if (cartFooter) cartFooter.classList.toggle('is-empty', parsedState.item_count === 0);
      if (parsedState.errors) {
        this.updateErrorLiveRegions(event.line, parsedState.errors);
      }
      this.getSectionsToRender().forEach((section => {
        const element = document.getElementById(section.id);
        
        if (element) {
          const elementToReplace = element.querySelector(section.selector) || element;
          if (elementToReplace && parsedState.sections[section.section]) {
            elementToReplace.innerHTML =
              this.getSectionInnerHTML(parsedState.sections[section.section], section.selector);
          }
        }
      }));
      
      this.updateQuantityLiveRegions(event.line, parsedState.item_count);
      
      const lineItem = document.getElementById(`CartItem-${event.line}`);
      if (lineItem && event.name) lineItem.querySelector(`[name="${event.name}"]`).focus();
      this.disableLoading();

      document.dispatchEvent(new CustomEvent('cart:updated', {
        detail: {
          cart: parsedState
        }
      }));
    }

    updateQuantity(line, quantity, name, target) {
      const sections = this.getSectionsToRender().map((section) => section.section);
      const body = JSON.stringify({
        line,
        quantity,
        sections: sections,
        sections_url: window.location.pathname
      });

      fetch(`${theme.routes.cart_change_url}`, {...fetchConfig(), ...{ body }})
        .then((response) => {
          return response.text();
        })
        .then((state) => {
          const parsedState = JSON.parse(state);
          publish(PUB_SUB_EVENTS.cartUpdate, { source: 'cart-items', cart: parsedState,  target, line, name, sections  });
        })
        .catch(() => {
          this.querySelectorAll('.loading-overlay').forEach((overlay) => overlay.classList.add('hidden'));
          this.disableLoading();
          if (this.cartErrors) {
            this.cartErrors.textContent = theme.cartStrings.error;
          }
        });
    }

    onChange(event) {
      if (event.target === null) return;
      this.updateQuantity(event.target.dataset.index, event.target.value, document.activeElement.getAttribute('name'));
    }

    getSectionsToRender() {
      let sections = [
        {
          id: 'mini-cart',
          section: document.getElementById('mini-cart')?.id,
          selector: '.shopify-section',
        },
        {
          id: 'main-cart-items',
          section: document.getElementById('main-cart-items')?.dataset.id,
          selector: '.js-contents',
        },
        {
          id: 'cart-icon-bubble',
          section: 'cart-icon-bubble',
          selector: '.shopify-section'
        },
        {
          id: 'mobile-cart-icon-bubble',
          section: 'mobile-cart-icon-bubble',
          selector: '.shopify-section'
        },
        {
          id: 'cart-live-region-text',
          section: 'cart-live-region-text',
          selector: '.shopify-section'
        },
        {
          id: 'main-cart-footer',
          section: document.getElementById('main-cart-footer')?.dataset.id,
          selector: '.js-contents',
        }
      ];
      if (document.querySelector('#main-cart-footer .free-shipping')) {
        sections.push({
          id: 'main-cart-footer',
          section: document.getElementById('main-cart-footer')?.dataset.id,
          selector: '.free-shipping',
        });
      }
      return sections;
    }

    updateErrorLiveRegions(line, message) {
      const lineItemError =
        document.getElementById(`Line-item-error-${line}`) || document.getElementById(`CartDrawer-LineItemError-${line}`);
      if (lineItemError) lineItemError.querySelector('.cart-item__error-text').innerHTML = message;
    
      this.lineItemStatusElement.setAttribute('aria-hidden', true);
    
      const cartStatus =
        document.getElementById('cart-live-region-text') || document.getElementById('CartDrawer-LiveRegionText');
      cartStatus.setAttribute('aria-hidden', false);
    
      setTimeout(() => {
        cartStatus.setAttribute('aria-hidden', true);
      }, 1000);
    }
    
    updateQuantityLiveRegions(line, itemCount) {
      if (this.currentItemCount === itemCount) {
        const quantityError = document.getElementById(`Line-item-error-${line}`);
        if (quantityError) {
          quantityError.querySelector('.cart-item__error-text')
            .innerHTML = theme.cartStrings.quantityError.replace(
              '[quantity]',
              document.getElementById(`Quantity-${line}`).value
            ); 
        }
      }

      this.currentItemCount = itemCount;
      
      if (this.lineItemStatusElement) this.lineItemStatusElement.setAttribute('aria-hidden', true);

      const cartStatus = document.getElementById('cart-live-region-text');
      if (cartStatus) {
        cartStatus.setAttribute('aria-hidden', false);

        setTimeout(() => {
          cartStatus.setAttribute('aria-hidden', true);
        }, 1e3);
      }
    }

    getSectionInnerHTML(html, selector) {
      return new DOMParser()
        .parseFromString(html, 'text/html')
        .querySelector(selector)?.innerHTML;
    }

    enableLoading(line) {
      const cartItems = document.getElementById('main-cart-items');
      if (cartItems) cartItems.classList.add('cart__items--disabled');

      const loadingOverlay = this.querySelectorAll('.loading-overlay')[line - 1];
      if (loadingOverlay) loadingOverlay.classList.remove('hidden');
      
      document.activeElement.blur();
      if (this.lineItemStatusElement) this.lineItemStatusElement.setAttribute('aria-hidden', false);
    }

    disableLoading() {
      const cartItems = document.getElementById('main-cart-items');
      if (cartItems) cartItems.classList.remove('cart__items--disabled');
    }

    renderContents(parsedState) {
      this.getSectionsToRender().forEach((section => {
        const element = document.getElementById(section.id);

        if (element) {
          element.innerHTML = this.getSectionInnerHTML(parsedState.sections[section.id], section.selector);
        }
      }));
    }
  });
}

class CartNote extends HTMLElement {
  constructor() {
    super();

    this.addEventListener('change', debounce((event) => {
      const body = JSON.stringify({ note: event.target.value });
      fetch(`${theme.routes.cart_update_url}`, {...fetchConfig(), ...{ body }});
    }, 300));
  }
}
customElements.define('cart-note', CartNote);

if (!customElements.get('cart-discount')) {
  customElements.define('cart-discount', class CartDiscount extends HTMLElement {
    constructor() {
      super();
      this.onApplyDiscount = this.applyDiscount.bind(this);
    }

    get sectionId() {
      return this.getAttribute('data-section-id');
    }
    
    connectedCallback() {
      this.submitButton = this.querySelector('[data-discount-btn]');
      this.resultsElement = this.lastElementChild;
      this.submitButton.addEventListener('click', this.onApplyDiscount);
    }

    disconnectedCallback() {
      this.abortController?.abort();
      this.submitButton.removeEventListener('click', this.onApplyDiscount);
    }

    getSectionsToRender() {
      let sections = [
        {
          id: 'mini-cart',
          section: document.getElementById('mini-cart')?.id,
          selector: '.shopify-section',
        },
        {
          id: 'main-cart-items',
          section: document.getElementById('main-cart-items')?.dataset.id,
          selector: '.js-contents',
        },
        {
          id: 'cart-icon-bubble',
          section: 'cart-icon-bubble',
          selector: '.shopify-section'
        },
        {
          id: 'mobile-cart-icon-bubble',
          section: 'mobile-cart-icon-bubble',
          selector: '.shopify-section'
        },
        {
          id: 'cart-live-region-text',
          section: 'cart-live-region-text',
          selector: '.shopify-section'
        },
        {
          id: 'main-cart-footer',
          section: document.getElementById('main-cart-footer')?.dataset.id,
          selector: '.js-contents',
        }
      ];
      if (document.querySelector('#main-cart-footer .free-shipping')) {
        sections.push({
          id: 'main-cart-footer',
          section: document.getElementById('main-cart-footer')?.dataset.id,
          selector: '.free-shipping',
        });
      }
      return sections;
    }

    applyDiscount(event) {
      event.preventDefault();

      const discountCode = this.querySelector('[name="discount"]');
      if (!(discountCode instanceof HTMLInputElement) || typeof this.getAttribute('data-section-id') !== 'string') return;

      this.abortController?.abort();
      this.abortController = new AbortController();

      const discountCodeValue = discountCode.value.trim();
      if (discountCodeValue === '') return;

      const existingDiscounts = this.existingDiscounts();
      if (existingDiscounts.includes(discountCodeValue)) return;

      this.setDiscountError('');
      this.submitButton.setAttribute('aria-busy', 'true');
      
      const sections = this.getSectionsToRender().map((section) => section.section);
      const body = JSON.stringify({
        discount: [...existingDiscounts, discountCodeValue].join(','),
        sections: sections,
        sections_url: window.location.pathname
      });

      fetch(`${theme.routes.cart_update_url}`, {...fetchConfig('json'), ...{ body }, signal: this.abortController.signal })
        .then((response) => response.json())
        .then((parsedState) => {
          if (
            parsedState.discount_codes.find((discount) => {
              return discount.code === discountCodeValue && discount.applicable === false;
            })
          ) {
            discountCode.value = '';
            this.setDiscountError(theme.discountStrings.error);
            return;
          }
          
          const newHtml = parsedState.sections[this.sectionId];
          const parsedHtml = new DOMParser().parseFromString(newHtml, 'text/html');
          const section = parsedHtml.getElementById(`shopify-section-${this.sectionId}`);

          if (section) {
            const discountCodes = section?.querySelectorAll('button[is="discount-remove"]') || [];
            const codes = Array.from(discountCodes)
              .map((element) => (element instanceof HTMLButtonElement ? element.getAttribute('data-discount') : null))
              .filter(Boolean);

            if (
              codes.length === existingDiscounts.length &&
              codes.every((code) => existingDiscounts.includes(code)) &&
              parsedState.discount_codes.find((discount) => {
                return discount.code === discountCodeValue && discount.applicable === true;
              })
            ) {
              discountCode.value = '';
              this.setDiscountError(theme.discountStrings.shippingError);
              return;
            }
          }

          publish(PUB_SUB_EVENTS.cartUpdate, { source: 'cart-discount', cart: parsedState });
        })
        .catch((error) => {
          if (error.name === 'AbortError') {
            console.log('Fetch aborted by user');
          }
          else {
            console.error(error);
          }
        })
        .finally(() => {
          this.submitButton.removeAttribute('aria-busy');
        });
    }

    removeDiscount(event) {
      if ((event instanceof KeyboardEvent && event.key !== 'Enter') || !(event instanceof MouseEvent)) {
        return;
      }

      const discountCode = event.currentTarget.getAttribute('data-discount');
      
      if (!discountCode) return;

      const existingDiscounts = this.existingDiscounts();
      const index = existingDiscounts.indexOf(discountCode);
      if (index === -1) return;

      existingDiscounts.splice(index, 1);

      this.abortController?.abort();
      this.abortController = new AbortController();

      this.setDiscountError('');
      event.currentTarget.setAttribute('loading', '');

      const sections = this.getSectionsToRender().map((section) => section.section);
      const body = JSON.stringify({
        discount: existingDiscounts.join(','),
        sections: sections,
        sections_url: window.location.pathname
      });
      
      fetch(theme.routes.cart_update_url, { ...fetchConfig(), ...{ body }, signal: this.abortController.signal })
        .then((response) => response.json())
        .then((parsedState) => {
          publish(PUB_SUB_EVENTS.cartUpdate, { source: 'cart-discount', cart: parsedState });
        })
        .catch((error) => {
          if (error.name === 'AbortError') {
            console.log('Fetch aborted by user');
          }
          else {
            console.error(error);
          }
        })
        .finally(() => {
          event.target.removeAttribute('loading');
        });
    }

    existingDiscounts() {
      const discountCodes = [];
      const discountPills = this.querySelectorAll('button[is="discount-remove"]');
      for (const pill of discountPills) {
        if (pill.hasAttribute('data-discount')) {
          discountCodes.push(pill.getAttribute('data-discount'));
        }
      }
      return discountCodes;
    }

    setDiscountError(error) {
      this.resultsElement.lastElementChild.textContent = error;
      if(error.length === 0) {
        this.resultsElement.classList.add('hidden');
      } else {
        this.resultsElement.classList.remove('hidden');
      }
    }
  });
}

class DiscountRemove extends HTMLButtonElement {
  constructor() {
    super();
     this.addEventListener('click', (event) => {
        const cartDiscount = this.closest('cart-discount') || document.querySelector('cart-discount');
        if (cartDiscount) {
          event.preventDefault();
          cartDiscount.removeDiscount(event);
        }
      });
  }
}
customElements.define('discount-remove', DiscountRemove, { extends: 'button' });

class ShippingCalculator extends HTMLElement {
  constructor() {
    super();

    this.setupCountries();
    
    this.errors = this.querySelector('#ShippingCalculatorErrors');
    this.success = this.querySelector('#ShippingCalculatorSuccess');
    this.zip = this.querySelector('#ShippingCalculatorZip');
    this.country = this.querySelector('#ShippingCalculatorCountry');
    this.province = this.querySelector('#ShippingCalculatorProvince');
    this.button = this.querySelector('button');
    this.button.addEventListener('click', this.onSubmitHandler.bind(this));
  }

  setupCountries() {
    if (Shopify && Shopify.CountryProvinceSelector) {
      // eslint-disable-next-line no-new
      new Shopify.CountryProvinceSelector('ShippingCalculatorCountry', 'ShippingCalculatorProvince', {
        hideElement: 'ShippingCalculatorProvinceContainer'
      });
    }
  }

  onSubmitHandler(event) {
    event.preventDefault();
    
    this.errors.classList.add('hidden');
    this.success.classList.add('hidden');
    this.zip.classList.remove('invalid');
    this.country.classList.remove('invalid');
    this.province.classList.remove('invalid');
    this.button.classList.add('loading');
    this.button.setAttribute('disabled', true);

    const body = JSON.stringify({
      shipping_address: {
        zip: this.zip.value,
        country: this.country.value,
        province: this.province.value
      }
    });
    let sectionUrl = `${theme.routes.cart_url}/shipping_rates.json`;

    // remove double `/` in case shop might have /en or language in URL
    sectionUrl = sectionUrl.replace('//', '/');

    fetch(sectionUrl, { ...fetchConfig('javascript'), body })
      .then((response) => response.json())
      .then((parsedState) => {
        if (parsedState.shipping_rates) {
          this.success.classList.remove('hidden');
          this.success.innerHTML = '';
          
          parsedState.shipping_rates.forEach((rate) => {
            const child = document.createElement('p');
            child.innerHTML = `${rate.name}: ${rate.price} ${Shopify.currency.active}`;
            this.success.appendChild(child);
          });
        }
        else {
          let errors = [];
          Object.entries(parsedState).forEach(([attribute, messages]) => {
            errors.push(`${attribute.charAt(0).toUpperCase() + attribute.slice(1)} ${messages[0]}`);
          });

          this.errors.classList.remove('hidden');
          this.errors.querySelector('.errors').innerHTML = errors.join('; ');
        }
      })
      .catch((e) => {
        console.error(e);
      })
      .finally(() => {
        this.button.classList.remove('loading');
        this.button.removeAttribute('disabled');
      });
  }
}

customElements.define('shipping-calculator', ShippingCalculator);
