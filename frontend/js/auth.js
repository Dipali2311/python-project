
const API_BASE_URL = "http://127.0.0.1:5000/api";
const userName = localStorage.getItem("user_name");

// 1. NAVBAR & UI
function initializeUI() {
    const welcomeSpan = document.getElementById("welcomeUser");
    if (welcomeSpan && userName) {
        welcomeSpan.innerText = `Hello, ${userName}`;
    }
}

async function logout() {
    try {
        // call backend to clear the cookie
        await fetch(`${API_BASE_URL}/logout`, {
            method: "POST",
            credentials: "include"
        });
    } catch (error) {
        console.error("Logout error:", error);
    } finally {
        // Clear local UI data and redirect
        localStorage.clear();
        window.location.href = "index.html";
    }
}

// 2. REGISTRATION
const registerForm = document.getElementById("registerForm");
if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const name = document.getElementById("name").value;
        const email = document.getElementById("email").value;
        const password = document.getElementById("password").value;

        try {
            const response = await fetch(`${API_BASE_URL}/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, email, password })
            });

            const data = await response.json();
            if (response.ok) {
                alert("Registration Successful! Please Login.");
                window.location.href = "index.html";
            } else {
                alert(data.message || "Registration failed");
            }
        } catch (error) {
            alert("Server error during registration");
        }
    });
}

// 3. LOGIN
const loginForm = document.getElementById("loginForm");
if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const email = document.getElementById("email").value;
        const password = document.getElementById("password").value;

        try {
            const response = await fetch(`${API_BASE_URL}/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password }),
                credentials: "include" // REQUIRED to receive the cookie
            });

            const data = await response.json();
            if (response.ok) {
                // store the name for display purposes
                localStorage.setItem("user_name", data.name);
                window.location.href = "payment.html";
            } else {
                alert(data.message || "Login failed");
            }
        } catch (error) {
            alert("Server error during login");
        }
    });
}

// 4. PAYMENT HISTORY 
async function fetchHistory() {
    const tableBody = document.getElementById("historyTable");
    if (!tableBody) return;

    try {
        const response = await fetch(`${API_BASE_URL}/payment-history`, {
            method: "GET",
            credentials: "include" // Automatically sends the JWT cookie
        });

        if (response.status === 401) {
            // If cookie is missing or expired
            console.warn("Not authenticated");
            return;
        }

        const data = await response.json();
        tableBody.innerHTML = "";

        if (!data || data.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="4" style="text-align:center;">No history found.</td></tr>`;
            return;
        }

        data.forEach(item => {
            const row = `
                <tr>
                    <td>${item.timestamp}</td>
                    <td>${item.order_id}</td>
                    <td>₹${item.amount}</td>
                    <td style="color:${item.status === 'Success' ? 'green' : 'red'}">
                        ${item.status}
                    </td>
                </tr>
            `;
            tableBody.innerHTML += row;
        });
    } catch (error) {
        console.error("History Error:", error);
    }
}

// 5. AUTO-RUN
document.addEventListener("DOMContentLoaded", () => {
    initializeUI();
    fetchHistory();
});