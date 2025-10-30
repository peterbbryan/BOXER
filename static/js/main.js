// BOXER Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Navigation scroll behavior
    const mainNav = document.getElementById('main-nav');
    let lastScrollTop = 0;
    let isScrolling = false;

    if (mainNav) {
        let scrollTimeout;

        window.addEventListener('scroll', function() {
            if (!isScrolling) {
                window.requestAnimationFrame(function() {
                    const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                    const scrollDelta = scrollTop - lastScrollTop;

                    // Clear any existing timeout
                    clearTimeout(scrollTimeout);

                    if (scrollDelta > 2 && scrollTop > 20) {
                        // Scrolling down - hide nav immediately
                        mainNav.style.transform = 'translateY(-100%)';
                        mainNav.style.transition = 'transform 0.2s ease-out';
                    } else if (scrollDelta < -2 || scrollTop <= 20) {
                        // Scrolling up or at top - show nav immediately
                        mainNav.style.transform = 'translateY(0)';
                        mainNav.style.transition = 'transform 0.2s ease-out';
                    }

                    lastScrollTop = scrollTop;
                    isScrolling = false;
                });
                isScrolling = true;
            }
        });
    } else {
        // Navigation not present (e.g., in labeling interface)
        console.log('Navigation not found - likely in full-screen interface');
    }

    // Mobile menu toggle
    const mobileMenuButton = document.getElementById('mobile-menu-button');
    const mobileMenu = document.getElementById('mobile-menu');

    if (mobileMenuButton && mobileMenu) {
        mobileMenuButton.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
            mobileMenu.classList.add('mobile-menu-enter');
        });
    }

    // Close mobile menu when clicking outside
    document.addEventListener('click', function(event) {
        if (mobileMenu && !mobileMenuButton.contains(event.target) && !mobileMenu.contains(event.target)) {
            mobileMenu.classList.add('hidden');
        }
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

});
