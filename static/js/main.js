document.addEventListener("DOMContentLoaded", function() {
    var html = document.documentElement;
    var themeToggle = document.getElementById("themeToggle");
    var darkModeBtn = document.getElementById("darkModeBtn");
    var darkModeIcon = document.getElementById("darkModeIcon");
    var darkModeText = document.getElementById("darkModeText");

    // --- 1. THEME LOGIC ---
    function applyTheme(dark) {
        if (dark) {
            html.setAttribute("data-theme","dark");
            if (darkModeIcon) darkModeIcon.textContent = "☀️";
            if (darkModeText) darkModeText.textContent = "Light Mode";
            if (themeToggle) themeToggle.checked = true;
        } else {
            html.removeAttribute("data-theme");
            if (darkModeIcon) darkModeIcon.textContent = "🌙";
            if (darkModeText) darkModeText.textContent = "Dark Mode";
            if (themeToggle) themeToggle.checked = false;
        }
        try { localStorage.setItem("theme", dark ? "dark" : "light"); } catch(e) {}
    }

    var isDark = false;
    try { isDark = localStorage.getItem("theme") === "dark"; } catch(e) {}
    applyTheme(isDark);

    if (darkModeBtn) {
        darkModeBtn.addEventListener("click", function() { 
            applyTheme(!html.hasAttribute("data-theme")); 
        });
    }
    
    if (themeToggle) {
        themeToggle.addEventListener("change", function() { 
            applyTheme(themeToggle.checked); 
        });
    }

    // --- 2. MODAL LOGIC (MASS MESSAGE) ---
    var modal = document.getElementById("massMessageModal");
    function openModal() { 
        if (modal) {
            modal.classList.add("active"); 
            document.body.style.overflow = "hidden"; 
        }
    }
    
    function closeModalFn() {
        if (modal) {
            modal.classList.remove("active");
            document.body.style.overflow = "";
            var form = document.getElementById("massMessageForm");
            if (form) form.reset();
        }
    }

    var mBtn = document.getElementById("massMessageBtn");
    if (mBtn) mBtn.addEventListener("click", openModal);
    
    var mBtn2 = document.getElementById("massMessageBtn2");
    if (mBtn2) mBtn2.addEventListener("click", openModal);
    
    var cBtn = document.getElementById("closeModal");
    if (cBtn) cBtn.addEventListener("click", closeModalFn);
    
    var canBtn = document.getElementById("cancelBtn");
    if (canBtn) canBtn.addEventListener("click", closeModalFn);
    
    if (modal) {
        modal.addEventListener("click", function(e) { if (e.target === modal) closeModalFn(); });
    }

    // --- 3. THE GLOBAL BUTTON FIX (CRITICAL) ---
    // This removes the "fake" Added/Saved text logic entirely.
    // It only triggers when a form is ACTUALLY being submitted to the server.
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function() {
            const btn = this.querySelector('button[type="submit"]');
            if (btn) {
                // We use 'Processing...' to show the server is working.
                // The text 'Added!' should only ever come from Django after a reload.
                btn.innerHTML = 'Processing...'; 
                btn.style.opacity = '0.7';
                btn.style.cursor = 'not-allowed';
                btn.style.pointerEvents = 'none'; // Prevents double-submissions
            }
        });
    });

    // --- 4. AUTH LOGIC (TAB SWITCHING) ---
    window.switchTab = function(tab) {
        var tLogin = document.getElementById("tabLogin");
        var tSignup = document.getElementById("tabSignup");
        var pLogin = document.getElementById("panelLogin");
        var pSignup = document.getElementById("panelSignup");

        if (tLogin) tLogin.classList.toggle("active", tab === "login");
        if (tSignup) tSignup.classList.toggle("active", tab === "signup");
        if (pLogin) pLogin.classList.toggle("active", tab === "login");
        if (pSignup) pSignup.classList.toggle("active", tab === "signup");
        
        clearErrors();
    };

    function clearErrors() {
        document.querySelectorAll(".auth-error-msg").forEach(function(e){ e.classList.remove("show"); });
        document.querySelectorAll(".auth-field input").forEach(function(e){ e.classList.remove("error"); });
    }

    // Helper functions for Login/Signup
    window.togglePw = function(inputId, btn) {
        var inp = document.getElementById(inputId);
        if (inp) {
            if (inp.type === "password") {
                inp.type = "text";
                btn.textContent = "🙈";
            } else {
                inp.type = "password";
                btn.textContent = "👁️";
            }
        }
    };

    window.checkStrength = function(pw) {
        var bar = document.getElementById("strengthBar");
        var lbl = document.getElementById("strengthLabel");
        if (bar) bar.className = "password-strength-bar";
        if (!pw) { if (lbl) lbl.textContent = ""; return; }
        
        if (pw.length < 6) {
            if (bar) bar.classList.add("strength-weak");
            if (lbl) { lbl.textContent = "Weak"; }
        } else if (pw.length < 10) {
            if (bar) bar.classList.add("strength-medium");
            if (lbl) { lbl.textContent = "Medium"; }
        } else {
            if (bar) bar.classList.add("strength-strong");
            if (lbl) { lbl.textContent = "Strong"; }
        }
    };
});

// --- NOTIFICATION AUTO-DISMISS ---
// --- NOTIFICATION AUTO-DISMISS ---
const msgContainer = document.getElementById('django-messages-container');
if (msgContainer) {
    // Start fading out after 4 seconds
    setTimeout(function() {
        msgContainer.style.opacity = '0';
        msgContainer.style.transform = 'translateY(-20px)';
        
        // Physically remove it from the page after the fade finishes
        setTimeout(function() {
            msgContainer.remove();
        }, 600); 
    }, 4000); 
}
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById("massMessageModal");
    const closeBtn = document.getElementById("closeModal");
    const cancelBtn = document.getElementById("cancelBtn");

    // Listen for clicks on the whole document
    document.addEventListener('click', function(e) {
        // Check if the clicked button is one of your Mass Message triggers
        if (e.target && (e.target.id === 'massMessageBtn' || e.target.id === 'massMessageBtn2')) {
            modal.style.display = "flex";
        }
    });

    // Close logic
    if (closeBtn) closeBtn.onclick = () => modal.style.display = "none";
    if (cancelBtn) cancelBtn.onclick = () => modal.style.display = "none";
    
    window.onclick = (event) => {
        if (event.target == modal) modal.style.display = "none";
    }
});
