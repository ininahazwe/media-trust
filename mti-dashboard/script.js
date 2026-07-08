document.addEventListener('DOMContentLoaded', () => {
    const hamburgerElement = document.getElementById('mobile-hamburger');
    const navBarElement = document.getElementById('main-editorial-nav');

    if (hamburgerElement && navBarElement) {
        hamburgerElement.addEventListener('click', (e) => {
            e.stopPropagation();
            navBarElement.classList.toggle('js-active-menu');
            hamburgerElement.classList.toggle('js-open');
        });

        // Fermeture automatique du menu mobile si clic à l'extérieur
        document.addEventListener('click', (event) => {
            if (!navBarElement.contains(event.target) && !hamburgerElement.contains(event.target)) {
                navBarElement.classList.remove('js-active-menu');
                hamburgerElement.classList.remove('js-open');
            }
        });
    }

    // Effet d'apparition au défilement des cartes éditoriales (Lazy Loading UX effect)
    const cards = document.querySelectorAll('.editorial-card');
    const observerOptions = {
        threshold: 0.05,
        rootMargin: "0px 0px -10px 0px"
    };

    const cardObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = "1";
                entry.target.style.transform = "translateY(0)";
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    cards.forEach(card => {
        card.style.opacity = "0.95";
        card.style.transition = "all 0.4s ease-out";
        cardObserver.observe(card);
    });
});