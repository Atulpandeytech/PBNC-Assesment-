import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_registration_and_login(client: AsyncClient):
    # Register new user
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@pragatibharti.edu", "password": "Password123!", "role": "user"},
    )
    assert reg_res.status_code == 201
    data = reg_res.json()
    assert data["email"] == "newuser@pragatibharti.edu"
    assert "id" in data

    # Duplicate registration returns 409
    dup_res = await client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@pragatibharti.edu", "password": "Password123!"},
    )
    assert dup_res.status_code == 409
    assert dup_res.json()["error"]["code"] == "DUPLICATE_RESOURCE"

    # Login
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "newuser@pragatibharti.edu", "password": "Password123!"},
    )
    assert login_res.status_code == 200
    tokens = login_res.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # Invalid password returns 401
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "newuser@pragatibharti.edu", "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401

    # Refresh token
    ref_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert ref_res.status_code == 200
    assert "access_token" in ref_res.json()

    # Get profile (me)
    me_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "newuser@pragatibharti.edu"
