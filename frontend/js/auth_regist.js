// 登録処理本体（Auth0の新規登録画面へ遷移）
document.querySelector("#regist form").addEventListener("submit", async (e) => {
    e.preventDefault();

    try {
        await login("signup");
    } catch(error) {
        alert(error.message);
    }
});
