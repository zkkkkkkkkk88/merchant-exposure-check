type LoginPageProps = {
  searchParams?: Promise<{ error?: string }>;
};

export default async function LoginPage({ searchParams = Promise.resolve({}) }: LoginPageProps) {
  const params = await searchParams;
  const invalid = params.error === "invalid";

  return (
    <main className="login-page">
      <aside aria-label="见序品牌" className="login-brand-cover">
        <div className="login-cover-copy">
          <div className="login-brand-lockup">
            <strong>见序</strong>
            <span>Visibility Dossier</span>
          </div>
          <hr />
          <p>理解商家在 AI 推荐中的呈现方式</p>
        </div>
      </aside>

      <section className="login-panel" aria-labelledby="login-title">
        <div className="login-panel-inner">
          <p className="kicker">PRIVATE ACCESS</p>
          <h1 id="login-title">进入见序工作台</h1>
          <p className="login-intro">
            访客请使用项目所有者提供的访问凭据。管理员与演示访客将获得不同的访问权限。
          </p>

          <form className="login-form" action="/access/login" method="post" aria-label="访问登录">
            <label>
              <span>用户名</span>
              <input name="username" type="text" autoComplete="username" placeholder="请输入用户名" required />
            </label>
            <label>
              <span>密码</span>
              <input name="password" type="password" autoComplete="current-password" placeholder="请输入密码" required />
            </label>
            {invalid ? <p className="form-error" role="alert">用户名或密码不正确，请重试。</p> : null}
            <button className="button primary" type="submit">登录</button>
          </form>
        </div>
      </section>
    </main>
  );
}
