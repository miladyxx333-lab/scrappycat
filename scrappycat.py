#!/usr/bin/env python3
"""
 /\\_____/\\
( o   o  )   ScrappyCat 🐱
 =( Y )=     Lead scraper for indie devs
  )   (      Maps -> Phone - WhatsApp - Email
 (_)-(_)
"""

import asyncio
import csv
import re
import random
import click
from pathlib import Path
from playwright.async_api import async_playwright
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
SKIP_EMAIL_DOMAINS = {'example', 'sentry', 'wix', 'schema', 'email', 'domain', 'yoursite'}

LATAM_QUERIES = {
    'xalapa': [
        'restaurantes en Xalapa Veracruz',
        'cafeterias en Xalapa Veracruz',
        'mariscos en Xalapa Veracruz',
        'fondas en Xalapa Veracruz',
        'taquerias en Xalapa Veracruz',
        'bares en Xalapa Veracruz',
        'pizzerias en Xalapa Veracruz',
    ],
    'cdmx': [
        'restaurantes en CDMX',
        'cafeterias en Ciudad de Mexico',
        'bares en CDMX',
        'taquerias en CDMX',
    ],
    'monterrey': [
        'restaurantes en Monterrey',
        'cafeterias en Monterrey',
        'bares en Monterrey',
    ],
}

def clean_phone(raw: str) -> str:
    return re.sub(r'[^\d+]', '', raw) if raw else ''

def make_whatsapp_link(phone: str) -> str:
    if not phone:
        return ''
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('52') and len(digits) == 12:
        return f"https://wa.me/{digits}"
    if len(digits) == 10:
        return f"https://wa.me/52{digits}"
    return f"https://wa.me/{digits}"

async def extract_emails(page, url: str) -> list[str]:
    try:
        await page.goto(url, timeout=12000, wait_until='domcontentloaded')
        content = await page.content()
        emails = EMAIL_RE.findall(content)
        return list({
            e for e in emails
            if not any(s in e.lower() for s in SKIP_EMAIL_DOMAINS)
        })[:2]
    except Exception:
        return []

async def scrape_place(page, url: str) -> dict:
    result = {'name': '', 'phone': '', 'whatsapp': '', 'address': '', 'website': '', 'rating': '', 'maps_url': url}
    try:
        await page.goto(url, timeout=20000, wait_until='domcontentloaded')
        await page.wait_for_timeout(1500)

        try:
            result['name'] = await page.locator('h1').first.inner_text(timeout=3000)
        except Exception:
            pass

        try:
            btn = page.locator('button[aria-label*="Teléfono"], button[aria-label*="Phone"], [data-item-id*="phone"]').first
            label = await btn.get_attribute('aria-label', timeout=2000) or ''
            phone_raw = re.search(r'[\d\s\(\)\-\+]+', label)
            if phone_raw:
                result['phone'] = clean_phone(phone_raw.group())
                result['whatsapp'] = make_whatsapp_link(result['phone'])
        except Exception:
            pass

        try:
            addr = page.locator('button[data-item-id="address"]').first
            label = await addr.get_attribute('aria-label', timeout=2000) or ''
            result['address'] = label.replace('Dirección: ', '').replace('Address: ', '').strip()
        except Exception:
            pass

        try:
            web = page.locator('a[data-item-id="authority"]').first
            result['website'] = await web.get_attribute('href', timeout=2000) or ''
        except Exception:
            pass

        try:
            rating_el = page.locator('div[jsaction*="pane.rating"] span[aria-hidden]').first
            result['rating'] = await rating_el.inner_text(timeout=2000)
        except Exception:
            pass

    except Exception as e:
        console.print(f"[yellow]  skip: {e}[/yellow]")
    return result

async def collect_links(page, query: str, depth: int) -> list[str]:
    search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
    await page.goto(search_url, timeout=30000, wait_until='domcontentloaded')
    await page.wait_for_timeout(3000)

    feed = page.locator('[role="feed"]')
    links = set()
    last_count = 0
    stale_rounds = 0

    for _ in range(depth):
        hrefs = await page.locator('[role="feed"] a[href*="/maps/place/"]').evaluate_all(
            'els => els.map(e => e.href)'
        )
        links.update(hrefs)
        if len(links) == last_count:
            stale_rounds += 1
            if stale_rounds >= 3:
                break
        else:
            stale_rounds = 0
        last_count = len(links)
        await feed.evaluate('el => el.scrollTop += 800')
        await page.wait_for_timeout(1200 + random.randint(0, 600))

    return list(links)

async def scrape_query(browser, query: str, limit: int, depth: int, do_email: bool, seen_urls: set) -> list[dict]:
    context = await browser.new_context(
        viewport={'width': 1280, 'height': 800},
        locale='es-MX',
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    results = []
    try:
        search_page = await context.new_page()
        console.print(f"\n[bold yellow]→ Query:[/bold yellow] {query}")
        links = await collect_links(search_page, query, depth)
        links = [l for l in links if l not in seen_urls][:limit]
        seen_urls.update(links)
        console.print(f"  [dim]{len(links)} lugares nuevos encontrados[/dim]")

        detail_page = await context.new_page()
        email_page = await context.new_page() if do_email else None

        for i, url in enumerate(links):
            console.print(f"  [dim][{i+1}/{len(links)}][/dim] ", end="")
            data = await scrape_place(detail_page, url)

            if do_email and data.get('website') and email_page:
                emails = await extract_emails(email_page, data['website'])
                data['email'] = ', '.join(emails)
            else:
                data['email'] = ''

            results.append(data)
            name_str = f"[green]{data['name']}[/green]"
            phone_str = f" | 📞 {data['phone']}" if data['phone'] else ""
            email_str = f" | ✉ {data['email']}" if data.get('email') else ""
            console.print(f"{name_str}{phone_str}{email_str}")
            await asyncio.sleep(random.uniform(1.5, 3.0))
    finally:
        await context.close()
    return results

async def run_scraper(queries: list[str], limit: int, depth: int, output: str, do_email: bool):
    console.print(f"\n[bold cyan] /\\_____/\\ [/bold cyan]")
    console.print(f"[bold cyan]( o   o  )  ScrappyCat 🐱[/bold cyan]")
    console.print(f"[bold cyan] =( Y )=    {len(queries)} queries | limit {limit} c/u[/bold cyan]\n")

    all_results = []
    seen_urls = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for query in queries:
            results = await scrape_query(browser, query, limit, depth, do_email, seen_urls)
            all_results.extend(results)
        await browser.close()

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ['name', 'phone', 'whatsapp', 'email', 'address', 'website', 'rating', 'maps_url']

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_results)

    table = Table(title=f"\n🐱 ScrappyCat — {len(all_results)} leads totales")
    table.add_column("Nombre", style="cyan")
    table.add_column("Teléfono")
    table.add_column("Email")
    for r in all_results[:12]:
        table.add_row(r['name'][:38], r['phone'] or '—', r.get('email') or '—')

    console.print(table)
    console.print(f"\n[bold green]✓ Guardado en {out_path}[/bold green]")
    console.print(f"[dim]WhatsApp links en columna 'whatsapp' · {len(all_results)} leads sin duplicados[/dim]\n")

@click.group()
def cli():
    pass

@cli.command()
@click.argument('query')
@click.option('--limit', '-l', default=100, help='Max resultados por query (default: 100)')
@click.option('--depth', '-d', default=8, help='Scroll depth (default: 8)')
@click.option('--output', '-o', default='output/leads.csv', help='Archivo de salida')
@click.option('--email/--no-email', default=True, help='Extraer emails de websites')
def search(query, limit, depth, output, email):
    """Busca una categoria en Google Maps.

    \b
    Ejemplos:
      python scrappycat.py search "restaurantes en Xalapa Veracruz"
      python scrappycat.py search "dentistas en Monterrey" --limit 50
    """
    asyncio.run(run_scraper([query], limit, depth, output, email))

@cli.command()
@click.argument('queries_file', type=click.Path(exists=True))
@click.option('--limit', '-l', default=80, help='Max resultados por query (default: 80)')
@click.option('--depth', '-d', default=8, help='Scroll depth (default: 8)')
@click.option('--output', '-o', default='output/leads.csv', help='Archivo de salida')
@click.option('--email/--no-email', default=True, help='Extraer emails de websites')
def batch(queries_file, limit, depth, output, email):
    """Corre multiples queries desde un archivo (una por linea).

    \b
    Ejemplos:
      python scrappycat.py batch queries.txt
      python scrappycat.py batch queries.txt --output xalapa_leads.csv
    """
    queries = [q.strip() for q in open(queries_file) if q.strip()]
    console.print(f"[bold]Cargadas {len(queries)} queries de {queries_file}[/bold]")
    asyncio.run(run_scraper(queries, limit, depth, output, email))

@cli.command()
@click.argument('city_name')
@click.option('--limit', '-l', default=80, help='Max resultados por query (default: 80)')
@click.option('--output', '-o', default='output/leads.csv', help='Archivo de salida')
@click.option('--email/--no-email', default=True, help='Extraer emails de websites')
def city(city_name, limit, output, email):
    """Scrapea una ciudad completa con queries predefinidas.

    \b
    Ciudades disponibles: xalapa, cdmx, monterrey

    Ejemplos:
      python scrappycat.py city xalapa
      python scrappycat.py city cdmx --limit 50
    """
    queries = LATAM_QUERIES.get(city_name.lower())
    if not queries:
        available = ', '.join(LATAM_QUERIES.keys())
        console.print(f"[red]Ciudad no encontrada. Disponibles: {available}[/red]")
        return
    asyncio.run(run_scraper(queries, limit, 8, output, email))

if __name__ == '__main__':
    cli()
