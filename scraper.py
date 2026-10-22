"""SISEO manual-CAPTCHA collector, adapted from the original SISEO source.

Public CLI messages are in English. Existing Spanish field/function names and
source-page selectors are preserved for compatibility with collected records.
"""
import argparse
import asyncio
import csv
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin



URL = "https://www.dgej.cjf.gob.mx/SiseInternet/consulta/busquedaacuerdos.aspx"
OUT_DIR = Path("resultados_sise")


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


async def esperar_enter() -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, input)


async def set_value(page, selector: str, value: str, label: str) -> bool:
    locator = page.locator(selector).first
    if await locator.count() == 0:
        print(f"[!] Field not found {label}: {selector}")
        return False

    await locator.fill("")
    await locator.type(value, delay=35)
    return True


async def seleccionar_si_existe(page, selector: str, value: str, label: str) -> bool:
    locator = page.locator(selector).first
    if await locator.count() == 0:
        print(f"[!] Select element not found {label}: {selector}")
        return False

    await locator.select_option(value)
    return True


async def encontrar_tabla_resultados(page):
    candidatos = [
        'table#GridAmparo',
        'table[id*="Grid"]',
        'table[id*="gv"]',
        'table:has-text("Expediente")',
    ]

    for selector in candidatos:
        locator = page.locator(selector).first
        try:
            await locator.wait_for(timeout=5000)
            if await locator.count() > 0:
                return locator
        except PWTimeout:
            continue

    return None


async def filas_de_tabla(tabla):
    filas = tabla.locator("tr")
    total = await filas.count()
    resultado = []

    for i in range(total):
        fila = filas.nth(i)
        celdas = await fila.locator("td").all_inner_texts()
        if len(celdas) >= 2 and any(c.strip() for c in celdas):
            resultado.append(fila)

    return resultado


def limpiar_texto(texto: str) -> str:
    lineas = [linea.strip() for linea in texto.replace("\xa0", " ").splitlines()]
    return "\n".join(linea for linea in lineas if linea)


def parece_expediente(texto: str) -> bool:
    return bool(re.search(r"\b\d{1,6}/\d{4}\b", texto))


def inferir_campos(celdas: list[str]) -> dict:
    if len(celdas) >= 7:
        return {
            "numero": celdas[0],
            "tipo": celdas[1],
            "expediente": celdas[2],
            "quejoso": celdas[3],
            "autoridad": celdas[4],
            "fecha": celdas[5],
            "sintesis_corta": celdas[6],
        }

    expediente = next((celda for celda in celdas if parece_expediente(celda)), "")
    fecha = next((celda for celda in celdas if re.search(r"\b\d{2}/\d{2}/\d{4}\b", celda)), "")
    return {
        "numero": "",
        "tipo": "",
        "expediente": expediente,
        "quejoso": "",
        "autoridad": "",
        "fecha": fecha,
        "sintesis_corta": celdas[-1] if celdas else "",
    }


def parece_pagina_lista(texto: str) -> bool:
    marcadores = [
        "lista de acuerdos",
        "para ver la sintesis completa",
        "para ver la síntesis completa",
        "organo jurisdiccional",
        "órgano jurisdiccional",
        "validacion de captcha",
        "validación de captcha",
    ]
    texto_bajo = texto.lower()
    expedientes = re.findall(r"\b\d{1,6}/\d{4}\b", texto)
    return sum(marcador in texto_bajo for marcador in marcadores) >= 2 or len(expedientes) > 20


def normalizar_url(base_url: str, url: str) -> str:
    if not url:
        return ""
    return urljoin(base_url, url)


def selector_id(element_id: str) -> str:
    escaped = element_id.replace(":", "\\:")
    return f"#{escaped}"


def postback_target_desde_link(link_id: str, href: str) -> str:
    match = re.search(r'WebForm_PostBackOptions\("([^"]+)"', href or "")
    if match:
        return match.group(1)
    if link_id:
        return link_id.replace("_", "$")
    return ""


def descripcion_id_desde_link(link_id: str) -> str:
    if not link_id:
        return ""
    return link_id.replace("_ReadMoreLinkButton", "_lblDescription")


def url_sintesis_desde_html(html: str) -> str:
    match = re.search(r"AbrirVentanaTotal\('([^']+)'", html)
    return match.group(1) if match else ""


async def preparar_detector_window_open(page) -> None:
    await page.evaluate(
        """
        () => {
            window.__siseLastOpenUrl = "";
            if (!window.__siseOriginalOpen) {
                window.__siseOriginalOpen = window.open;
                window.open = function(url, name, features) {
                    window.__siseLastOpenUrl = url || "";
                    return window.__siseOriginalOpen.call(window, url, name, features);
                };
            }
        }
        """
    )


async def extraer_texto_detalle(pagina_detalle) -> dict:
    selectores = {
        "expediente_detalle": [
            "#lblNoExp",
            '[id*="lblNoExp"]',
            '[id*="Expediente"]',
        ],
        "fecha_acuerdo_detalle": [
            "#lblFAuto",
            '[id*="lblFAuto"]',
            '[id*="Fecha"]',
        ],
        "sintesis_completa": [
            "#lblAcuerdo",
            '[id*="lblAcuerdo"]',
            '[id*="Acuerdo"]',
            '[id*="Sintesis"]',
            '[id*="Síntesis"]',
        ],
    }

    datos = {}
    for campo, candidatos in selectores.items():
        for selector in candidatos:
            locator = pagina_detalle.locator(selector).first
            if await locator.count() == 0:
                continue

            texto = limpiar_texto(await locator.inner_text())
            if texto:
                datos[campo] = texto
                break

    if "sintesis_completa" not in datos:
        body = limpiar_texto(await pagina_detalle.locator("body").inner_text())
        if parece_pagina_lista(body):
            return {}
        datos["sintesis_completa"] = body

    return datos


async def extraer_por_postback(page, enlace, pausa_detalle: float, debug: bool) -> dict:
    link_id = await enlace.get_attribute("id") or ""
    href = await enlace.get_attribute("href") or ""
    target = postback_target_desde_link(link_id, href)
    descripcion_id = descripcion_id_desde_link(link_id)

    if not target or not descripcion_id:
        return {}

    selector_descripcion = selector_id(descripcion_id)
    texto_antes = ""
    if await page.locator(selector_descripcion).count() > 0:
        texto_antes = limpiar_texto(await page.locator(selector_descripcion).inner_text())

    try:
        async with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
            await page.evaluate(
                """
                (target) => {
                    if (window.WebForm_DoPostBackWithOptions && window.WebForm_PostBackOptions) {
                        window.WebForm_DoPostBackWithOptions(
                            new window.WebForm_PostBackOptions(target, "", true, "", "", false, true)
                        );
                        return;
                    }
                    const form = document.forms["form1"] || document.form1;
                    form.__EVENTTARGET.value = target;
                    form.__EVENTARGUMENT.value = "";
                    form.submit();
                }
                """,
                target,
            )
    except PWTimeout:
        await page.wait_for_load_state("domcontentloaded")

    if pausa_detalle:
        await page.wait_for_timeout(int(pausa_detalle * 1000))

    if debug:
        OUT_DIR.mkdir(exist_ok=True)
        safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", link_id or "detalle")
        detalle_path = OUT_DIR / f"detalle_{safe_id}_{timestamp()}.html"
        html_detalle = await page.content()
        detalle_path.write_text(html_detalle, encoding="utf-8")
        print(f"    [debug] Detail HTML saved: {detalle_path.resolve()}")
    else:
        html_detalle = await page.content()

    reporte_url = url_sintesis_desde_html(html_detalle)
    if reporte_url:
        datos_reporte = await extraer_desde_url_detalle(page.context, page.url, reporte_url, pausa_detalle)
        if datos_reporte:
            datos_reporte["detalle_url"] = normalizar_url(page.url, reporte_url)
            return datos_reporte

    if await page.locator(selector_descripcion).count() == 0:
        return {}

    texto_despues = limpiar_texto(await page.locator(selector_descripcion).inner_text())
    if not texto_despues:
        return {}

    if texto_despues == texto_antes and texto_despues.endswith("..."):
        return {}

    return {
        "sintesis_completa": texto_despues,
        "detalle_selector": descripcion_id,
    }


async def extraer_desde_url_detalle(context, base_url: str, detalle_url: str, pausa_detalle: float = 0) -> dict:
    detalle_url = normalizar_url(base_url, detalle_url)
    if not detalle_url:
        return {}

    popup = await context.new_page()
    try:
        await popup.goto(detalle_url, wait_until="domcontentloaded", timeout=15000)
        if pausa_detalle:
            await popup.wait_for_timeout(int(pausa_detalle * 1000))
        return await extraer_texto_detalle(popup)
    finally:
        await popup.close()


async def abrir_y_extraer_sintesis(page, enlace, pausa_detalle: float = 0, debug: bool = False):
    url_lista = page.url
    await preparar_detector_window_open(page)

    datos_postback = await extraer_por_postback(page, enlace, pausa_detalle, debug)
    if datos_postback:
        return datos_postback

    try:
        async with page.expect_popup(timeout=5000) as popup_info:
            await enlace.click()

        popup = await popup_info.value
        await popup.wait_for_load_state("domcontentloaded", timeout=15000)
        if pausa_detalle:
            await popup.wait_for_timeout(int(pausa_detalle * 1000))
        datos = await extraer_texto_detalle(popup)
        await popup.close()
        return datos

    except PWTimeout:
        detalle_url = await page.evaluate("() => window.__siseLastOpenUrl || ''")
        if detalle_url:
            datos = await extraer_desde_url_detalle(page.context, url_lista, detalle_url, pausa_detalle)
            if datos:
                return datos

        if page.url != url_lista:
            if pausa_detalle:
                await page.wait_for_timeout(int(pausa_detalle * 1000))
            datos = await extraer_texto_detalle(page)
            await page.goto(url_lista, wait_until="domcontentloaded")
            return datos

    try:
        await enlace.click()
        await page.wait_for_load_state("domcontentloaded", timeout=15000)
        await page.wait_for_timeout(1000)
        if pausa_detalle:
            await page.wait_for_timeout(int(pausa_detalle * 1000))

        detalle_url = await page.evaluate("() => window.__siseLastOpenUrl || ''")
        if detalle_url:
            datos = await extraer_desde_url_detalle(page.context, url_lista, detalle_url, pausa_detalle)
            if datos:
                return datos

        datos = await extraer_texto_detalle(page)

        if page.url != url_lista:
            await page.goto(url_lista, wait_until="domcontentloaded")

        return datos

    except Exception as exc:
        print(f"[!] Could not open agreement details: {exc}")
        if page.url != url_lista:
            await page.goto(url_lista, wait_until="domcontentloaded")
        return {}


async def extraer_registro_desde_fila(page, fila, indice: int, total: int, args) -> dict:
    celdas = [limpiar_texto(texto) for texto in await fila.locator("td").all_inner_texts()]
    registro = {
        "indice": indice + 1,
        "columnas": celdas,
        "numero": "",
        "tipo": "",
        "expediente": "",
        "quejoso": "",
        "autoridad": "",
        "fecha": "",
        "sintesis_corta": "",
        "sintesis_completa": "",
    }

    registro.update(inferir_campos(celdas))

    etiqueta = registro["expediente"] or f"fila {indice + 1}"
    print(f"[*] {indice + 1}/{total}: {etiqueta}")

    enlaces = fila.locator(
        'a, input[type="image"], input[type="submit"], input[type="button"], button'
    )
    cantidad_enlaces = await enlaces.count()

    candidatos = []
    for posicion in range(cantidad_enlaces):
        enlace = enlaces.nth(posicion)
        texto = limpiar_texto(await enlace.inner_text()) if await enlace.count() else ""
        atributos = []
        for nombre in ["id", "href", "title", "alt", "value", "onclick"]:
            valor = await enlace.get_attribute(nombre)
            if valor:
                atributos.append(valor)

        pista = " ".join([texto, *atributos]).lower()
        score = 0
        for palabra in ["sint", "acuerdo", "readmore", "ver", "detalle"]:
            if palabra in pista:
                score += 5
        if "postback" in pista or "javascript:" in pista:
            score += 2
        if "grid" in pista or "amparo" in pista:
            score += 1

        candidatos.append((score, posicion, pista[:180]))

    candidatos.sort(reverse=True)
    if args.debug_enlaces:
        print(f"    links detected: {cantidad_enlaces}")
        for score, posicion, pista in candidatos[:5]:
            print(f"    - link {posicion + 1}, score={score}: {pista}")

    for score, posicion, _pista in candidatos:
        if score <= 0 and cantidad_enlaces > 1:
            continue

        print(f"    opening full agreement text using link {posicion + 1}...")
        enlace = enlaces.nth(posicion)
        detalle = await abrir_y_extraer_sintesis(page, enlace, args.pausa_detalle, args.debug_enlaces)
        if detalle:
            registro.update(detalle)
            longitud = len(registro.get("sintesis_completa", ""))
            print(f"    agreement text captured: {longitud} characters")
            break
        print("    this link did not return valid agreement text; trying another if available...")

    if not registro["sintesis_completa"]:
        registro["sintesis_completa"] = registro["sintesis_corta"]

    return registro


def guardar_resultados(resultados: list[dict], nombre_base: str) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    json_path = OUT_DIR / f"{nombre_base}.json"
    csv_path = OUT_DIR / f"{nombre_base}.csv"

    json_path.write_text(json.dumps(resultados, indent=2, ensure_ascii=False), encoding="utf-8")

    campos = [
        "indice",
        "numero",
        "tipo",
        "expediente",
        "quejoso",
        "autoridad",
        "fecha",
        "sintesis_corta",
        "sintesis_completa",
        "expediente_detalle",
        "fecha_acuerdo_detalle",
        "detalle_url",
    ]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as archivo:
        writer = csv.DictWriter(archivo, fieldnames=campos, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(resultados)

    print(f"[+] JSON: {json_path.resolve()}")
    print(f"[+] CSV:  {csv_path.resolve()}")


async def ejecutar_scraper(args, endpoint_url: str):
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(endpoint_url)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()

        print("[*] Opening SISE...")
        await page.goto(URL, wait_until="domcontentloaded")

        await seleccionar_si_existe(page, 'select[name*="ddlCircuito"]', args.circuito, "circuito")
        await page.wait_for_timeout(2500)
        await seleccionar_si_existe(page, 'select[name*="ddlOrgano"]', args.organo, "organo")
        await set_value(page, 'input[name*="FechaInicial"]', args.fecha, "fecha")

        if args.expediente:
            await set_value(page, 'input[name*="txtExpediente"]', args.expediente, "expediente")

        print("\n[!] Complete the CAPTCHA manually in the Chrome window.")
        print("[!] Once completed, return to this terminal and press ENTER.")
        await esperar_enter()

        boton = page.locator('input[id*="btnBuscar"], input[name*="btnBuscar"], button:has-text("Buscar")').first
        if await boton.count() == 0:
            print("[X] Search button not found.")
            return

        print("[*] Searching for agreements...")
        await boton.click()

        tabla = await encontrar_tabla_resultados(page)
        if tabla is None:
            html_path = OUT_DIR / f"sin_tabla_{timestamp()}.html"
            OUT_DIR.mkdir(exist_ok=True)
            html_path.write_text(await page.content(), encoding="utf-8")
            print("[X] Results table not found.")
            print(f"[!] Diagnostic HTML saved: {html_path.resolve()}")
            return

        filas = await filas_de_tabla(tabla)
        total = len(filas)
        if args.max_registros:
            total = min(total, args.max_registros)
        print(f"[+] Records found: {total}")

        if args.debug_enlaces:
            OUT_DIR.mkdir(exist_ok=True)
            lista_path = OUT_DIR / f"lista_resultados_{timestamp()}.html"
            lista_path.write_text(await page.content(), encoding="utf-8")
            print(f"[debug] Result-list HTML saved: {lista_path.resolve()}")

        resultados = []
        for indice in range(total):
            tabla = await encontrar_tabla_resultados(page)
            filas = await filas_de_tabla(tabla)
            if indice >= len(filas):
                break

            registro = await extraer_registro_desde_fila(page, filas[indice], indice, total, args)
            resultados.append(registro)

        nombre_base = f"sise_sintesis_{args.fecha.replace('/', '-')}_{timestamp()}"
        guardar_resultados(resultados, nombre_base)
        print(f"[OK] Records saved: {len(resultados)}")

def valid_date(value: str) -> str:
    try:
        datetime.strptime(value, "%d/%m/%Y")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use a valid date in DD/MM/YYYY format") from exc
    return value


def nonnegative_int(value: str) -> int:
    result = int(value)
    if result < 0:
        raise argparse.ArgumentTypeError("Value must be nonnegative")
    return result


def nonnegative_float(value: str) -> float:
    result = float(value)
    if not __import__("math").isfinite(result) or result < 0:
        raise argparse.ArgumentTypeError("Value must be finite and nonnegative")
    return result


def parse_args():
    parser = argparse.ArgumentParser(
        description="Collect SISE judicial agreements with manual CAPTCHA completion."
    )
    parser.add_argument("--circuit", "--circuito", dest="circuito", required=True,
                        help="Official circuit option value from the source portal")
    parser.add_argument("--court", "--organo", dest="organo", required=True,
                        help="Official court-body option value within that circuit")
    parser.add_argument("--date", "--fecha", dest="fecha", required=True, type=valid_date,
                        help="Collection query date in DD/MM/YYYY format")
    parser.add_argument("--case", "--expediente", dest="expediente", default="",
                        help="Optional case-number filter")
    parser.add_argument("--profile", "--perfil", dest="perfil", default="./browser-profile",
                        help="Local persistent Chrome profile; never commit it")
    parser.add_argument("--detail-delay", "--pausa-detalle", dest="pausa_detalle", type=nonnegative_float,
                        default=3, help="Seconds to leave each detail visible (default: 3)")
    parser.add_argument("--debug-links", "--debug-enlaces", dest="debug_enlaces", action="store_true",
                        help="Save diagnostic HTML and show candidate links")
    parser.add_argument("--max-records", "--max-registros", dest="max_registros", type=nonnegative_int,
                        default=0, help="Maximum records to process; 0 means all returned rows")
    return parser.parse_args()


def main():
    args = parse_args()
    global PWTimeout, async_playwright
    try:
        from playwright.async_api import TimeoutError as PWTimeout
        from playwright.async_api import async_playwright
        from seleniumbase import sb_cdp
    except ImportError as exc:
        raise SystemExit("Install requirements.txt before running browser collection") from exc
    perfil = os.path.abspath(args.perfil)
    sb = sb_cdp.Chrome(browser="chrome", user_data_dir=perfil)

    try:
        asyncio.run(ejecutar_scraper(args, sb.get_endpoint_url()))
    finally:
        try:
            sb.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
