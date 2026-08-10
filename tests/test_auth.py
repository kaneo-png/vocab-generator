def test_register_page(client):
    """登録ページが表示される。"""
    response = client.get("/register")
    assert response.status_code == 200
    assert "無料登録" in response.get_data(as_text=True)


def test_register_success(client):
    """正常な登録ができる。"""
    response = client.post(
        "/register",
        data={
            "email": "new@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "ダッシュボード" in response.get_data(as_text=True)


def test_register_password_mismatch(client):
    """パスワード不一致で登録できない。"""
    response = client.post(
        "/register",
        data={
            "email": "new@example.com",
            "password": "password123",
            "confirm_password": "different123",
        },
        follow_redirects=True,
    )
    assert "パスワードが一致しません" in response.get_data(as_text=True)


def test_register_duplicate_email(client, test_user):
    """重複メールアドレスで登録できない。"""
    response = client.post(
        "/register",
        data={
            "email": "test@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
        follow_redirects=True,
    )
    assert "既に登録されています" in response.get_data(as_text=True)


def test_login_page(client):
    """ログインページが表示される。"""
    response = client.get("/login")
    assert response.status_code == 200
    assert "ログイン" in response.get_data(as_text=True)


def test_login_success(client, test_user):
    """正常なログインができる。"""
    response = client.post(
        "/login",
        data={"email": "test@example.com", "password": "password123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "ダッシュボード" in response.get_data(as_text=True)


def test_login_failure(client, test_user):
    """誤ったパスワードでログインできない。"""
    response = client.post(
        "/login",
        data={"email": "test@example.com", "password": "wrongpassword"},
        follow_redirects=True,
    )
    assert "正しくありません" in response.get_data(as_text=True)


def test_dashboard_requires_login(client):
    """未ログインでダッシュボードにアクセスできない。"""
    response = client.get("/dashboard", follow_redirects=True)
    assert "ログイン" in response.get_data(as_text=True)


def test_dashboard_logged_in(logged_in_client):
    """ログイン済みでダッシュボードにアクセスできる。"""
    response = logged_in_client.get("/dashboard")
    assert response.status_code == 200
    assert "ダッシュボード" in response.get_data(as_text=True)