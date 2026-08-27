type LoginPageProps = {
  searchParams?: Promise<{ error?: string }>;
};

export default async function LoginPage({ searchParams = Promise.resolve({}) }: LoginPageProps) {
  const params = await searchParams;
  const invalid = params.error === "invalid";

  return (
    <main className="login-page">
      <section className="login-panel" aria-labelledby="login-title">
        <p className="kicker">PRIVATE ACCESS</p>
        <h1 id="login-title">进入见序工作台</h1>
        <p className="login-intro">
          访客请使用项目所有者提供的访问凭据。管理员与演示访客将获得不同的访问权限。
        </p>
        <form className="login-form" action="/api/access/login" method="post" aria-label="访问登录">
          <label>
            用户名
            <input name="username" type="text" autoComplete="username" required />
          </label>
          <label>
            密码
            <input name="password" type="password" autoComplete="current-password" required />
          </label>
          {invalid ? <p className="form-error" role="alert">用户名或密码不正确，请重试。</p> : null}
          <button className="button primary" type="submit">登录</button>
        </form>
      </section>
    </main>
  );
}
