def test_la_demostracion_se_sirve_en_demo(cliente):
    resp = cliente.get("/demo/")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "Prode Mundial 2030" in resp.text


def test_sus_archivos_estaticos(cliente):
    js = cliente.get("/demo/app.js")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]
    css = cliente.get("/demo/estilos.css")
    assert css.status_code == 200 and css.headers["content-type"].startswith("text/css")


def test_no_carga_nada_de_afuera(cliente):
    for archivo in ("/demo/", "/demo/app.js", "/demo/estilos.css"):
        texto = cliente.get(archivo).text
        assert "http://" not in texto and "https://" not in texto, archivo


def test_la_raiz_lleva_a_la_demostracion(cliente):
    resp = cliente.get("/", follow_redirects=False)
    assert resp.status_code in (302, 307) and resp.headers["location"] == "/demo/"
