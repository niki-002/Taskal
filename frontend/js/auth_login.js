const apiBase = "/api/auth";

// トークン取得
async function get_token(payload) {
    const formData = new URLSearchParams();
    formData.append("username", payload.email);
    formData.append("password", payload.password);

    const response = await fetch(`${apiBase}/token`, {
        method: "POST",
        headers: {"Content-Type": "application/x-www-form-urlencoded"},
        body: formData
    });
    if (!response.ok) {
        throw new Error("Failed to get token");
    }
    const result = await response.json();
    return result;
}

// user取得
async function read_user_me() {
    const token = localStorage.getItem("access_token");

    const response = await fetch(`${apiBase}/users/me`, {
        headers: {"Authorization": `Bearer ${token}`}
    });
    if (!response.ok) {
        throw new Error("Failed to read user");
    }
    const result = await response.json();
    return result;
}

// ログイン処理本体
document.querySelector("#login form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    try {
        const result = await get_token({ email, password });

        localStorage.setItem("access_token", result.access_token);

        location.href = "../html/index.html";
    } catch(error) {
        alert(error.message);
    }
});
