// Auth0の設定値（SPA用のApplicationとAPIの値を設定する）
// domain・clientIdは公開されても問題ない値。Client Secretは絶対に書かないこと
const AUTH0_CONFIG = {
    domain: "your-tenant.jp.auth0.com",
    clientId: "your-spa-client-id",
    audience: "https://api.taskal.example",
};
