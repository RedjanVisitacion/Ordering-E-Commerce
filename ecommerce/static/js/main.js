document.addEventListener('DOMContentLoaded', function () {

  /* ── Auto-dismiss alerts ─────────────────────── */
  document.querySelectorAll('.alert.auto-dismiss').forEach(function (alert) {
    setTimeout(function () {
      bootstrap.Alert.getOrCreateInstance(alert).close();
    }, 4500);
  });

  /* ── Navbar shadow on scroll ─────────────────── */
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    window.addEventListener('scroll', () => {
      if (window.scrollY > 20) {
        navbar.style.boxShadow = '0 4px 20px rgba(0,0,0,.5)';
      } else {
        navbar.style.boxShadow = '0 2px 10px rgba(0,0,0,.3)';
      }
    }, { passive: true });
  }

  /* ── Qty decrease buttons ────────────────────── */
  document.querySelectorAll('.qty-decrease').forEach(btn => {
    btn.addEventListener('click', function () {
      const input = this.closest('.d-flex, .input-group').querySelector('.qty-input');
      const min = parseInt(input.getAttribute('min') || 1);
      if (parseInt(input.value) > min) {
        input.value = parseInt(input.value) - 1;
        input.dispatchEvent(new Event('change'));
        animateBounce(input);
      }
    });
  });

  /* ── Qty increase buttons ────────────────────── */
  document.querySelectorAll('.qty-increase').forEach(btn => {
    btn.addEventListener('click', function () {
      const input = this.closest('.d-flex, .input-group').querySelector('.qty-input');
      const max = parseInt(input.getAttribute('max') || 9999);
      if (parseInt(input.value) < max) {
        input.value = parseInt(input.value) + 1;
        input.dispatchEvent(new Event('change'));
        animateBounce(input);
      }
    });
  });

  function animateBounce(el) {
    el.style.transform = 'scale(1.15)';
    setTimeout(() => { el.style.transform = 'scale(1)'; }, 150);
  }

  /* ── Live cart total update ──────────────────── */
  document.querySelectorAll('.cart-qty-input').forEach(input => {
    input.addEventListener('change', function () {
      const price = parseFloat(this.getAttribute('data-price'));
      const qty = parseInt(this.value);
      const row = this.closest('tr, .cart-item');
      if (row) {
        const itemTotal = row.querySelector('.item-total');
        if (itemTotal) {
          itemTotal.textContent = '$' + (price * qty).toFixed(2);
          itemTotal.style.transition = 'color .2s';
          itemTotal.style.color = '#dc2626';
          setTimeout(() => itemTotal.style.color = '', 400);
        }
      }
      updateCartSubtotal();
    });
  });

  function updateCartSubtotal() {
    let subtotal = 0;
    document.querySelectorAll('.cart-qty-input').forEach(input => {
      subtotal += parseFloat(input.getAttribute('data-price')) * parseInt(input.value);
    });
    const el = document.getElementById('cart-subtotal');
    if (el) {
      el.textContent = '$' + subtotal.toFixed(2);
      el.style.transition = 'transform .2s';
      el.style.transform = 'scale(1.1)';
      setTimeout(() => el.style.transform = 'scale(1)', 200);
    }
  }

  /* ── Image fallback ──────────────────────────── */
  document.querySelectorAll('img.product-img').forEach(img => {
    img.addEventListener('error', function () {
      this.src = 'https://placehold.co/600x400/111111/dc2626?text=RPSV';
    });
  });

  /* ── Confirm delete ──────────────────────────── */
  document.querySelectorAll('.confirm-delete').forEach(form => {
    form.addEventListener('submit', function (e) {
      if (!confirm('Delete this product? This cannot be undone.')) {
        e.preventDefault();
      }
    });
  });

  /* ── Add to cart button feedback ─────────────── */
  document.querySelectorAll('form[action*="cart/add"]').forEach(form => {
    form.addEventListener('submit', function () {
      const btn = this.querySelector('button[type="submit"]');
      if (btn) {
        // Change text AFTER submit fires — don't disable until after submission
        const original = btn.innerHTML;
        btn.innerHTML = '<i class="bi bi-check-lg me-1"></i>Adding...';
        // Re-enable after a short time in case of navigation issues
        setTimeout(() => {
          btn.innerHTML = original;
        }, 2000);
      }
    });
  });

  /* ── Smooth reveal on scroll ─────────────────── */
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.product-card, .stat-card, .table-card').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity .4s ease, transform .4s ease';
    observer.observe(el);
  });

  /* ── Image preview for admin product form ────── */
  const urlInput = document.getElementById('imageUrlInput');
  if (urlInput) {
    const previewContainer = document.getElementById('imagePreviewContainer');
    const previewImg = document.getElementById('imagePreview');
    let debounceTimer;

    urlInput.addEventListener('input', function () {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        const url = this.value.trim();
        if (url) {
          previewImg.src = url;
          previewContainer.style.display = 'block';
          previewContainer.style.animation = 'pageFadeIn .3s ease';
        } else {
          previewContainer.style.display = 'none';
        }
      }, 400);
    });
  }

});
