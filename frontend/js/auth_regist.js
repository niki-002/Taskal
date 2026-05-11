const apiBase = "/api/auth";

// 新規登録関数
async function regist_user(payload) {
    const formData = new URLSearchParams();
    formData.append("username", payload.email);
    formData.append("password", payload.password);

    const response = await fetch(apiBase, {
        method: "POST",
        headers: {"Content-Type": "application/x-www-form-urlencoded"},
        body: formData
    });

    if (!response.ok) {
        throw new Error("Failed to regist user");
    }

    return await response.json();
}

// 登録処理本体
document.querySelector("#regist form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    try {
        await regist_user({ email, password });
        alert("created user");
        location.href = "../html/auth_login.html";
    } catch(error) {
        alert(error.message);
    }
});