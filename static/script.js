// Mobile menu toggle with overlay
const menuToggle = document.getElementById('menu-toggle');
const navUl = document.querySelector('nav ul');
let overlay = document.getElementById('nav-overlay');
if (!overlay) {
  overlay = document.createElement('div');
  overlay.id = 'nav-overlay';
  overlay.style.position = 'fixed';
  overlay.style.top = 0;
  overlay.style.left = 0;
  overlay.style.width = '100vw';
  overlay.style.height = '100vh';
  overlay.style.background = 'rgba(60,16,120,0.18)';
  overlay.style.zIndex = 150;
  overlay.style.display = 'none';
  document.body.appendChild(overlay);
}
if (menuToggle && navUl) {
  menuToggle.addEventListener('click', () => {
    navUl.classList.toggle('active');
    overlay.style.display = navUl.classList.contains('active') ? 'block' : 'none';
  });
}
overlay.addEventListener('click', () => {
  navUl.classList.remove('active');
  overlay.style.display = 'none';
});
// Smooth scroll for nav links
const navLinks = document.querySelectorAll('nav a');
navLinks.forEach(link => {
  link.addEventListener('click', function(e) {
    const targetId = this.getAttribute('href');
    if (targetId && targetId.startsWith('#')) {
      e.preventDefault();
      const target = document.querySelector(targetId);
      if (target) target.scrollIntoView({ behavior: 'smooth' });
      navUl.classList.remove('active');
      overlay.style.display = 'none';
    }
  });
});
// Fade-in animation for sections on scroll
const faders = document.querySelectorAll('section, .portfolio-item, .service, .testimonial, .job-card, .step');
const appearOptions = { threshold: 0.12, rootMargin: '0px 0px -40px 0px' };
const appearOnScroll = new IntersectionObserver(function(entries, appearOnScroll) {
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    entry.target.classList.add('fade-in');
    appearOnScroll.unobserve(entry.target);
  });
}, appearOptions);
faders.forEach(fader => {
  fader.classList.add('pre-fade');
  appearOnScroll.observe(fader);
});
// Ripple effect for buttons
function createRipple(event) {
  const button = event.currentTarget;
  const circle = document.createElement('span');
  const diameter = Math.max(button.clientWidth, button.clientHeight);
  const radius = diameter / 2;
  circle.style.width = circle.style.height = `${diameter}px`;
  circle.style.left = `${event.clientX - button.getBoundingClientRect().left - radius}px`;
  circle.style.top = `${event.clientY - button.getBoundingClientRect().top - radius}px`;
  circle.classList.add('ripple');
  const ripple = button.getElementsByClassName('ripple')[0];
  if (ripple) { ripple.remove(); }
  button.appendChild(circle);
}
document.querySelectorAll('.btn, button').forEach(btn => {
  btn.addEventListener('click', createRipple);
});

// --- Typing animation for search input placeholders ---
const searchInput = document.getElementById('search-title');
const locationInput = document.getElementById('search-location');
const placeholderTexts = [ 'Job title or keyword', 'e.g. Frontend Developer', 'e.g. UI/UX Designer', 'e.g. Remote, Marketing' ];
const locationPlaceholders = [ 'Location', 'e.g. Remote', 'e.g. Bangalore', 'e.g. San Francisco' ];
let phIndex = 0, charIndex = 0, typing, erasing;
let locIndex = 0, locCharIndex = 0, locTyping, locErasing;
function typePlaceholder() {
  if (!searchInput) return;
  if (charIndex < placeholderTexts[phIndex].length) {
    searchInput.setAttribute('placeholder', placeholderTexts[phIndex].slice(0, charIndex + 1));
    charIndex++;
    typing = setTimeout(typePlaceholder, 60);
  } else { setTimeout(erasePlaceholder, 1200); }
}
function erasePlaceholder() {
  if (!searchInput) return;
  if (charIndex > 0) {
    searchInput.setAttribute('placeholder', placeholderTexts[phIndex].slice(0, charIndex - 1));
    charIndex--;
    erasing = setTimeout(erasePlaceholder, 30);
  } else { phIndex = (phIndex + 1) % placeholderTexts.length; setTimeout(typePlaceholder, 400); }
}
function typeLocationPlaceholder() {
  if (!locationInput) return;
  if (locCharIndex < locationPlaceholders[locIndex].length) {
    locationInput.setAttribute('placeholder', locationPlaceholders[locIndex].slice(0, locCharIndex + 1));
    locCharIndex++;
    locTyping = setTimeout(typeLocationPlaceholder, 60);
  } else { setTimeout(eraseLocationPlaceholder, 1200); }
}
function eraseLocationPlaceholder() {
  if (!locationInput) return;
  if (locCharIndex > 0) {
    locationInput.setAttribute('placeholder', locationPlaceholders[locIndex].slice(0, locCharIndex - 1));
    locCharIndex--;
    locErasing = setTimeout(eraseLocationPlaceholder, 30);
  } else { locIndex = (locIndex + 1) % locationPlaceholders.length; setTimeout(typeLocationPlaceholder, 400); }
}
if (searchInput) typePlaceholder();
if (locationInput) typeLocationPlaceholder();

// --- Typing animation for hero heading and subheading ---
const heroTitle = document.querySelector('.hero h1');
const heroSubtitle = document.querySelector('.hero p');
const heroTitleText = 'Find Your Dream Job';
const heroSubtitleText = 'Connecting talent with opportunity. Search thousands of jobs and take the next step in your career.';
let heroTitleIndex = 0, heroSubtitleIndex = 0;
function typeHeroTitle() {
  if (heroTitle && heroTitleIndex <= heroTitleText.length) {
    heroTitle.textContent = heroTitleText.slice(0, heroTitleIndex);
    heroTitleIndex++;
    setTimeout(typeHeroTitle, 60);
  } else { setTimeout(typeHeroSubtitle, 400); }
}
function typeHeroSubtitle() {
  if (heroSubtitle && heroSubtitleIndex <= heroSubtitleText.length) {
    heroSubtitle.textContent = heroSubtitleText.slice(0, heroSubtitleIndex);
    heroSubtitleIndex++;
    setTimeout(typeHeroSubtitle, 30);
  }
}
if (heroTitle && heroSubtitle) {
  heroTitle.textContent = '';
  heroSubtitle.textContent = '';
  setTimeout(typeHeroTitle, 400);
}

// --- Expandable job cards ---
const jobCards = document.querySelectorAll('.job-card');
jobCards.forEach(card => {
  card.addEventListener('click', function(e) {
    if (e.target.classList.contains('btn')) return; // Prevent expand on button click
    this.classList.toggle('expanded');
  });
});

// --- Scroll-to-top button ---
let scrollBtn = document.getElementById('scroll-to-top');
if (!scrollBtn) {
  scrollBtn = document.createElement('button');
  scrollBtn.id = 'scroll-to-top';
  scrollBtn.innerHTML = '↑';
  scrollBtn.style.display = 'none';
  document.body.appendChild(scrollBtn);
}
window.addEventListener('scroll', () => {
  if (window.scrollY > 300) {
    scrollBtn.style.display = 'block';
  } else {
    scrollBtn.style.display = 'none';
  }
});
scrollBtn.addEventListener('click', () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
});

// --- Toast notification for Apply button ---
let toast = document.getElementById('toast');
if (!toast) {
  toast = document.createElement('div');
  toast.id = 'toast';
  document.body.appendChild(toast);
}
function showToast(msg) {
  toast.textContent = msg;
  toast.className = 'show';
  setTimeout(() => { toast.className = toast.className.replace('show', ''); }, 2200);
}
document.querySelectorAll('.job-card .btn').forEach(btn => {
  btn.addEventListener('click', function(e) {
    e.stopPropagation();
    showToast('Application sent!');
  });
});

// --- User Profile Dropdown ---
const profileBtn = document.getElementById('profile-btn');
const profileDropdown = document.getElementById('profile-dropdown');
const dropdownMenu = document.getElementById('dropdown-menu');
if (profileBtn && profileDropdown && dropdownMenu) {
  profileBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    profileDropdown.classList.toggle('open');
  });
  document.addEventListener('click', function(e) {
    if (!profileDropdown.contains(e.target)) {
      profileDropdown.classList.remove('open');
    }
  });
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      profileDropdown.classList.remove('open');
    }
  });
}

