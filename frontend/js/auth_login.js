// ログイン済みならタスク一覧へ
isAuthenticated().then((authenticated) => {
    if (authenticated) {
        location.href = CALLBACK_PATH;
    }
});

// ログイン処理本体（Auth0のログイン画面へ遷移）
document.querySelector("#login form").addEventListener("submit", async (e) => {
    e.preventDefault();

    try {
        await login();
    } catch(error) {
        alert(error.message);
    }
});
