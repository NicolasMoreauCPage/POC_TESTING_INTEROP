"""
Tests de base pour vérifier la configuration
"""

def test_home_page(client):
    """
    Test que la page d'accueil répond correctement
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
