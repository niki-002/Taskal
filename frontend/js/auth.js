// Auth0のログインフロー共通処理（auth0-spa-js と auth_config.js を先に読み込むこと）
const LOGIN_PATH = "/frontend/html/auth_login.html";
const CALLBACK_PATH = "/frontend/html/index.html";

let auth0ClientPromise = null;

// Auth0クライアントを1回だけ作成して使い回す
function getAuth0Client() {
    if (!auth0ClientPromise) {
        auth0ClientPromise = auth0.createAuth0Client({
            domain: AUTH0_CONFIG.domain,
            clientId: AUTH0_CONFIG.clientId,
            // 画面遷移してもログイン状態が消えないよう、トークンをlocalStorageに保存しリフレッシュトークンで更新する
            cacheLocation: "localstorage",
            useRefreshTokens: true,
            authorizationParams: {
                audience: AUTH0_CONFIG.audience,
                redirect_uri: `${location.origin}${CALLBACK_PATH}`,
            },
        });
    }
    return auth0ClientPromise;
}

// Auth0のログイン画面へ遷移する（signupを渡すと新規登録画面を開く）
async function login(screenHint) {
    const client = await getAuth0Client();
    const authorizationParams = screenHint ? { screen_hint: screenHint } : {};
    await client.loginWithRedirect({ authorizationParams });
}

// Auth0からリダイレクトで戻ってきた場合にログインを完了させる
async function handleRedirectCallback() {
    const params = new URLSearchParams(location.search);
    if (!params.has("state") || !(params.has("code") || params.has("error"))) return;

    const client = await getAuth0Client();
    await client.handleRedirectCallback();
    // URLに残ったcode・stateを消す
    history.replaceState({}, document.title, location.pathname);
}

async function isAuthenticated() {
    const client = await getAuth0Client();
    return await client.isAuthenticated();
}

// API呼び出し用のアクセストークンを取得する（未ログインならログイン画面へ）
async function getAccessToken() {
    const client = await getAuth0Client();
    try {
        return await client.getTokenSilently();
    } catch (error) {
        location.href = LOGIN_PATH;
        throw new Error("ログインしてください");
    }
}

async function logout() {
    const client = await getAuth0Client();
    await client.logout({
        logoutParams: { returnTo: `${location.origin}${LOGIN_PATH}` },
    });
}
