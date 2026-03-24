const tabs = document.querySelectorAll(".tab");
const forms = document.querySelectorAll(".auth-form");
const authStatus = document.getElementById("auth-status");

tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
        tabs.forEach((item) => item.classList.remove("is-active"));
        forms.forEach((form) => form.classList.add("hidden"));
        tab.classList.add("is-active");
        document.getElementById(tab.dataset.target).classList.remove("hidden");
    });
});

async function submitAuth(formId, endpoint) {
    const form = document.getElementById(formId);
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        authStatus.textContent = "Processing...";
        const payload = Object.fromEntries(new FormData(form).entries());

        try {
            const response = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || "Unable to continue.");
            }
            window.location.href = "/dashboard";
        } catch (error) {
            authStatus.textContent = error.message;
        }
    });
}

submitAuth("login-form", "/api/auth/login");
submitAuth("signup-form", "/api/auth/signup");
