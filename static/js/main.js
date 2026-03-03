document.addEventListener("DOMContentLoaded", function() {
    const html = document.documentElement;
    const darkModeBtn = document.getElementById("darkModeBtn");
    const darkModeIcon = document.getElementById("darkModeIcon");
    const darkModeText = document.getElementById("darkModeText");
    const themeToggle = document.getElementById("themeToggle"); // 👈 The Settings Switch

    // --- 1. THEME LOGIC ---
    function applyTheme(dark) {
        if (dark) {
            html.setAttribute("data-theme", "dark");
            if (darkModeIcon) darkModeIcon.textContent = "☀️";
            if (darkModeText) darkModeText.textContent = "Light Mode";
            // Checkbox on settings page should be UNCHECKED for dark
            if (themeToggle) themeToggle.checked = false; 
        } else {
            html.removeAttribute("data-theme");
            if (darkModeIcon) darkModeIcon.textContent = "🌙";
            if (darkModeText) darkModeText.textContent = "Dark Mode";
            // Checkbox on settings page should be CHECKED for light
            if (themeToggle) themeToggle.checked = true;
        }
        localStorage.setItem("theme", dark ? "dark" : "light");
    }

    // Initial Load
    const savedTheme = localStorage.getItem("theme") === "dark";
    applyTheme(savedTheme);

    // Header Button Listener
    if (darkModeBtn) {
        darkModeBtn.addEventListener("click", () => {
            const isNowDark = !html.hasAttribute("data-theme");
            applyTheme(isNowDark);
        });
    }

    // ⭐ NEW: Settings Toggle Listener
    if (themeToggle) {
        themeToggle.addEventListener("change", function() {
            // If checked, it's light mode. If unchecked, it's dark mode.
            applyTheme(!this.checked); 
        });
    }

    // --- 2. GLOBAL FORM PROTECTION ---
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function() {
            const btn = this.querySelector('button[type="submit"]');
            if (btn && !btn.classList.contains('no-process')) {
                btn.innerHTML = 'Processing...';
                btn.style.opacity = '0.7';
                btn.style.pointerEvents = 'none'; 
            }
        });
    });

    // --- 3. NOTIFICATION AUTO-DISMISS ---
    const msgContainer = document.getElementById('django-messages-container');
    if (msgContainer) {
        setTimeout(() => {
            msgContainer.style.opacity = '0';
            msgContainer.style.transform = 'translateY(-20px)';
            msgContainer.style.transition = 'all 0.6s ease';
            setTimeout(() => msgContainer.remove(), 600);
        }, 4000);
    }
});