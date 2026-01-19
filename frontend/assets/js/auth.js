/**
 * auth.js
 * Handles User Authentication State in UI
 */

const API_AUTH = window.API_URL || "http://127.0.0.1:5000";

document.addEventListener("DOMContentLoaded", () => {
    updateNavAuth();
});

function updateNavAuth() {
    const token = localStorage.getItem("token") || sessionStorage.getItem("token");
    const role = localStorage.getItem("user_role") || sessionStorage.getItem("user_role");
    const username = localStorage.getItem("user_name") || sessionStorage.getItem("user_name");

    const nav = document.getElementById("navbar");
    if (!nav) return;

    // Remove old login link
    const loginLink = nav.querySelector(".nav-login-link");
    if (loginLink) loginLink.remove();

    // Remove old logout link (avoid duplicates)
    const oldLogout = nav.querySelector(".nav-logout-link");
    if (oldLogout) oldLogout.remove();

    if (token) {
        // User is logged in
        // Add Logout Link
        const logoutA = document.createElement("a");
        logoutA.href = "#";
        logoutA.className = "nav-logout-link";
        logoutA.innerText = `Logout (${username})`;
        logoutA.style.color = "#ff4444";
        logoutA.onclick = (e) => {
            e.preventDefault();
            logoutUser();
        };
        nav.appendChild(logoutA);

        // If Admin, Add Dashboard Link
        if (role === 'admin' || role === 'super_admin') {
            const adminA = document.createElement("a");
            adminA.href = "Admin.html";
            adminA.innerText = "Dashboard";
            adminA.style.color = "gold";
            nav.insertBefore(adminA, nav.firstChild);
        }

    } else {
        // User is guest
        const loginA = document.createElement("a");
        loginA.href = "login.html";
        loginA.className = "nav-login-link";
        loginA.innerText = "Login/Register";
        nav.appendChild(loginA);
    }
}


function logoutUser() {
    if (!confirm("Are you sure you want to log out?")) return;

    localStorage.removeItem("token");
    localStorage.removeItem("user_name");
    localStorage.removeItem("user_email");
    localStorage.removeItem("user_role");
    sessionStorage.clear();

    // Optional: Call backend logout
    fetch(`${API_AUTH}/logout`, { method: 'POST' }).catch(e => console.error(e));

    window.location.href = "Home.html";
}
