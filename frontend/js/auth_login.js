const apiBase = "/api/auth";

// トークン取得
async function get_token(payload) {
    try {
        const response = await fetch(`${apiBase}/token`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(payload)
        });
        if (!response.ok) {
            throw new Error("Failed to get token");
        }
        const result = await response.json();
        return result;
    } catch(error) {
        alert(error.message);
    }
}

// user取得
async function read_user_me() {
    try {
        const response = await fetch(`${apiBase}/users/me`);
        if (!response.ok) {
            throw new Error("Failed to read user");
        }
        const reslut = await response.json();
        return reslut;
    } catch(error) {
        alert(error.message);
    }
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